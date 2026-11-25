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
