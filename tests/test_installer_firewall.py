"""Tests for installer LAN firewall rules and application icon wiring."""

import os
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEB_SCRIPT = REPO_ROOT / "packaging" / "installers" / "deb" / "build_deb.sh"
RPM_SCRIPT = REPO_ROOT / "packaging" / "installers" / "rpm" / "build_rpm.sh"
ISS_PATH = REPO_ROOT / "packaging" / "installers" / "windows" / "installer.iss"
RELEASE_YML = REPO_ROOT / ".github" / "workflows" / "release.yml"
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _make_mock_dpkg_deb(bin_dir: Path) -> Path:
    mock = bin_dir / "dpkg-deb"
    mock.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'BUILD_ROOT="${@: -2:1}"\n'
        'DEB_OUT="${@: -1:1}"\n'
        'if [ -n "${CAPTURE_DIR:-}" ]; then\n'
        '  rm -rf "$CAPTURE_DIR"\n'
        '  mkdir -p "$CAPTURE_DIR"\n'
        '  cp -pR "$BUILD_ROOT"/. "$CAPTURE_DIR"/\n'
        "fi\n"
        'mkdir -p "$(dirname "$DEB_OUT")"\n'
        'touch "$DEB_OUT"\n',
        encoding="utf-8",
    )
    mock.chmod(0o755)
    return mock


def _make_mock_rpmbuild(bin_dir: Path) -> Path:
    mock = bin_dir / "rpmbuild"
    mock.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'TOPDIR=""\n'
        'SPEC_FILE="${@: -1:1}"\n'
        'for arg in "$@"; do\n'
        '  case "$arg" in\n'
        '    _topdir\\ *) TOPDIR="${arg#_topdir }" ;;\n'
        "  esac\n"
        "done\n"
        'if [ -n "${CAPTURE_SPEC:-}" ]; then\n'
        '  cp "$SPEC_FILE" "$CAPTURE_SPEC"\n'
        "fi\n"
        'if [ -n "${CAPTURE_SPEC_CONTENT_ONLY:-}" ]; then\n'
        "  exit 0\n"
        "fi\n"
        'mkdir -p "$TOPDIR/RPMS/x86_64"\n'
        'touch "$TOPDIR/RPMS/x86_64/mock.rpm"\n',
        encoding="utf-8",
    )
    mock.chmod(0o755)
    return mock


def _run_deb_build(tmp_path: Path, app_name: str) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    _make_mock_dpkg_deb(bin_dir)
    dummy_bin = tmp_path / app_name
    dummy_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    dummy_bin.chmod(0o755)
    capture = tmp_path / f"capture_{app_name}"
    out_dir = tmp_path / "out"
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CAPTURE_DIR"] = str(capture)
    subprocess.run(
        ["bash", str(DEB_SCRIPT), app_name, app_name, "1.0.0", str(dummy_bin), str(out_dir), "amd64"],
        env=env,
        check=True,
        cwd=str(REPO_ROOT),
    )
    return capture


def _run_rpm_build(tmp_path: Path, app_name: str) -> str:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    _make_mock_rpmbuild(bin_dir)
    dummy_bin = tmp_path / app_name
    dummy_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    dummy_bin.chmod(0o755)
    capture_spec = tmp_path / f"{app_name}.spec"
    out_dir = tmp_path / "out"
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CAPTURE_SPEC"] = str(capture_spec)
    subprocess.run(
        ["bash", str(RPM_SCRIPT), app_name, app_name, "1.0.0", str(dummy_bin), str(out_dir), "x86_64"],
        env=env,
        check=True,
        cwd=str(REPO_ROOT),
    )
    return capture_spec.read_text(encoding="utf-8")


def test_deb_firewall_scripts_only_for_librarian(tmp_path):
    lib_root = _run_deb_build(tmp_path, "LibrarianManagement")
    postinst = lib_root / "DEBIAN" / "postinst"
    prerm = lib_root / "DEBIAN" / "prerm"

    assert postinst.exists(), "LibrarianManagement .deb must generate DEBIAN/postinst"
    assert prerm.exists(), "LibrarianManagement .deb must generate DEBIAN/prerm"
    assert stat.S_IMODE(postinst.stat().st_mode) == 0o755
    assert stat.S_IMODE(prerm.stat().st_mode) == 0o755

    postinst_txt = postinst.read_text(encoding="utf-8")
    assert "8765/tcp" in postinst_txt
    assert "8766/udp" in postinst_txt
    assert "ufw" in postinst_txt
    assert "firewall-cmd" in postinst_txt
    assert "|| true" in postinst_txt

    prerm_txt = prerm.read_text(encoding="utf-8")
    assert "remove|purge" in prerm_txt
    assert "8765/tcp" in prerm_txt
    assert "8766/udp" in prerm_txt
    assert "|| true" in prerm_txt

    for other in ("BoothApp", "StudentManagement"):
        other_root = _run_deb_build(tmp_path, other)
        assert not (other_root / "DEBIAN" / "postinst").exists(), f"{other} must not have postinst"
        assert not (other_root / "DEBIAN" / "prerm").exists(), f"{other} must not have prerm"


def test_rpm_firewall_scripts_only_for_librarian(tmp_path):
    lib_spec = _run_rpm_build(tmp_path, "LibrarianManagement")
    assert "%post\n" in lib_spec
    assert "%postun\n" in lib_spec
    assert "8765/tcp" in lib_spec
    assert "8766/udp" in lib_spec
    assert "|| true" in lib_spec
    assert 'if [ "$1" -eq 0 ]' in lib_spec

    for other in ("BoothApp", "StudentManagement"):
        other_spec = _run_rpm_build(tmp_path, other)
        assert "%post\n" not in other_spec, f"{other} RPM must not have %post"
        assert "%postun\n" not in other_spec, f"{other} RPM must not have %postun"


def test_windows_installer_iss_conditional_firewall_and_privileges():
    iss = ISS_PATH.read_text(encoding="utf-8")
    assert "#ifdef EnableLanFirewall" in iss
    assert "PrivilegesRequired=admin" in iss
    assert "PrivilegesRequired=lowest" in iss
    assert "netsh.exe" in iss
    assert "advfirewall" in iss
    assert "8765" in iss
    assert "8766" in iss
    assert "profile=private,domain" in iss
    assert "[UninstallRun]" in iss

    # Verify #else keeps PrivilegesRequired=lowest outside EnableLanFirewall
    ifdef_idx = iss.index("#ifdef EnableLanFirewall")
    else_idx = iss.index("#else", ifdef_idx)
    endif_idx = iss.index("#endif", else_idx)
    assert "PrivilegesRequired=admin" in iss[ifdef_idx:else_idx]
    assert "PrivilegesRequired=lowest" in iss[else_idx:endif_idx]


def test_release_yml_enables_lan_firewall_only_for_librarian():
    yml = RELEASE_YML.read_text(encoding="utf-8")
    iscc_lines = [line.strip() for line in yml.splitlines() if "iscc " in line]
    assert len(iscc_lines) == 3

    lib_lines = [l for l in iscc_lines if "LibrarianManagement" in l]
    stu_lines = [l for l in iscc_lines if "StudentManagement" in l]
    booth_lines = [l for l in iscc_lines if "BoothApp" in l]

    assert len(lib_lines) == 1 and "/DEnableLanFirewall=1" in lib_lines[0]
    assert len(stu_lines) == 1 and "EnableLanFirewall" not in stu_lines[0]
    assert len(booth_lines) == 1 and "EnableLanFirewall" not in booth_lines[0]


ICON_STEMS = ("boothapp", "librarianmanagement", "studentmanagement")


def test_app_icons_exist_and_have_valid_formats():
    icons_dir = REPO_ROOT / "assets" / "icons"
    for stem in ICON_STEMS:
        svg = icons_dir / f"{stem}.svg"
        png = icons_dir / f"{stem}.png"
        ico = icons_dir / f"{stem}.ico"
        icns = icons_dir / f"{stem}.icns"
        assert svg.is_file() and "<svg" in svg.read_text(encoding="utf-8")
        png_bytes = png.read_bytes()
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        # IHDR width/height at bytes 16..24
        width = int.from_bytes(png_bytes[16:20], "big")
        height = int.from_bytes(png_bytes[20:24], "big")
        assert (width, height) == (256, 256)
        ico_bytes = ico.read_bytes()
        assert ico_bytes[:4] == b"\x00\x00\x01\x00"
        assert int.from_bytes(ico_bytes[4:6], "little") >= 5
        icns_bytes = icns.read_bytes()
        assert icns_bytes[:4] == b"icns"


def test_deb_and_rpm_install_hicolor_icons_and_desktop_entry(tmp_path):
    for app_name, stem in [
        ("BoothApp", "boothapp"),
        ("LibrarianManagement", "librarianmanagement"),
        ("StudentManagement", "studentmanagement"),
    ]:
        deb_root = _run_deb_build(tmp_path, app_name)
        icon_dest = deb_root / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps" / f"{stem}.png"
        desktop = deb_root / "usr" / "share" / "applications" / f"{stem}.desktop"
        assert icon_dest.is_file(), f"Missing DEB icon for {app_name}"
        assert f"Icon={stem}" in desktop.read_text(encoding="utf-8")

        spec_txt = _run_rpm_build(tmp_path, app_name)
        assert f"/usr/share/icons/hicolor/256x256/apps/{stem}.png" in spec_txt
        assert f"Icon={stem}" in spec_txt


def test_pyinstaller_specs_wire_icons():
    spec_map = [
        ("packaging/booth_app.spec", "boothapp"),
        ("packaging/librarian_management.spec", "librarianmanagement"),
        ("packaging/student_management.spec", "studentmanagement"),
    ]
    for rel_path, stem in spec_map:
        txt = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert "assets/icons/*.png" in txt
        assert f"assets/icons/{stem}.ico" in txt
        assert f"assets/icons/{stem}.png" in txt
        assert f"assets/icons/{stem}.icns" in txt
        assert "icon=None" not in txt


def test_windows_iss_and_release_yml_wire_app_icons():
    iss = ISS_PATH.read_text(encoding="utf-8")
    assert "#ifdef AppIcon" in iss
    assert "SetupIconFile={#AppIcon}" in iss

    yml = RELEASE_YML.read_text(encoding="utf-8")
    iscc_lines = [line.strip() for line in yml.splitlines() if "iscc " in line]
    assert len(iscc_lines) == 3
    for app_name, stem in [
        ("LibrarianManagement", "librarianmanagement"),
        ("StudentManagement", "studentmanagement"),
        ("BoothApp", "boothapp"),
    ]:
        matching = [l for l in iscc_lines if app_name in l]
        assert len(matching) == 1
        assert f"{stem}.ico" in matching[0]
        assert "/DAppIcon=" in matching[0]


def test_apply_app_icon_and_entrypoints(monkeypatch):
    import sys
    from PySide6.QtGui import QGuiApplication
    from core.shared.mock_qt import apply_app_icon

    # No-op cleanly for missing icon or None app
    apply_app_icon(None, "nonexistent_icon_stem")

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qapp = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])

    class _FakeApp:
        def __init__(self):
            self.icon = None

        def setWindowIcon(self, icon):
            self.icon = icon

    fake = _FakeApp()
    apply_app_icon(fake, "nonexistent_icon_stem")
    assert fake.icon is None

    apply_app_icon(fake, "boothapp")
    assert fake.icon is not None and not fake.icon.isNull()
    assert qapp is not None

    for rel, stem in [
        ("apps/booth_app/main.py", "boothapp"),
        ("apps/librarian_management_app/main.py", "librarianmanagement"),
        ("apps/student_management_app/main.py", "studentmanagement"),
    ]:
        txt = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert f'apply_app_icon(app, "{stem}")' in txt


def test_ci_yml_triggers_and_has_no_release_publishing():
    assert CI_YML.is_file(), ".github/workflows/ci.yml must exist"
    yml = CI_YML.read_text(encoding="utf-8")

    assert "name: CI (Test & Build)" in yml
    assert "dev" in yml
    assert "workflow_dispatch" in yml
    assert "pull_request:" in yml

    # Test-only CI must never publish releases or request write permissions
    assert "gh release" not in yml
    assert "action-gh-release" not in yml
    assert "publish-release" not in yml
    assert "contents: write" not in yml
    assert "tags:" not in yml


def test_ci_yml_contains_test_and_platform_build_jobs():
    assert CI_YML.is_file(), ".github/workflows/ci.yml must exist"
    yml = CI_YML.read_text(encoding="utf-8")

    for job_id in ("test:", "build-windows:", "build-linux:", "build-macos:"):
        assert job_id in yml, f"Missing CI job: {job_id}"

    # Windows build must enable LAN firewall only for LibrarianManagement and verify rules live
    iscc_lines = [line.strip() for line in yml.splitlines() if "iscc " in line]
    assert len(iscc_lines) == 3
    lib_lines = [l for l in iscc_lines if "LibrarianManagement" in l]
    stu_lines = [l for l in iscc_lines if "StudentManagement" in l]
    booth_lines = [l for l in iscc_lines if "BoothApp" in l]

    assert len(lib_lines) == 1 and "/DEnableLanFirewall=1" in lib_lines[0] and "/DAppIcon=" in lib_lines[0]
    assert len(stu_lines) == 1 and "EnableLanFirewall" not in stu_lines[0] and "/DAppIcon=" in stu_lines[0]
    assert len(booth_lines) == 1 and "EnableLanFirewall" not in booth_lines[0] and "/DAppIcon=" in booth_lines[0]

    assert "netsh advfirewall firewall show rule" in yml
    assert "SMTE Librarian LAN HTTP" in yml
    assert "SMTE Librarian LAN Discovery" in yml
    assert "unins000.exe" in yml
    assert "dpkg -I" in yml
    assert "dpkg -c" in yml
    assert "create_dmg.sh" in yml
    assert "retention-days: 7" in yml
