import pytest
from core.shared.version import (
    calculate_next_version,
    is_version_released,
    update_version_files,
)


def test_calculate_next_version_semver():
    assert calculate_next_version("1.1.0", "patch") == "1.1.1"
    assert calculate_next_version("1.1.1", "patch") == "1.1.2"
    assert calculate_next_version("1.1.0", "minor") == "1.2.0"
    assert calculate_next_version("1.1.0", "major") == "2.0.0"


def test_calculate_next_version_explicit():
    assert calculate_next_version("1.1.0", "1.1.5") == "1.1.5"
    assert calculate_next_version("1.1.0", "v1.2.3") == "1.2.3"


def test_calculate_next_version_invalid():
    with pytest.raises(ValueError, match="Invalid version or action"):
        calculate_next_version("1.1.0", "invalid_action")
    with pytest.raises(ValueError, match="Invalid version or action"):
        calculate_next_version("1.1.0", "1.2")


def test_is_version_released_duplicate_detection():
    known_tags = ["v1.0.0", "v1.1.0", "v1.1.0-rc1"]
    assert is_version_released("1.1.0", known_tags) is True
    assert is_version_released("v1.1.0", known_tags) is True
    assert is_version_released("1.1.1", known_tags) is False
    assert is_version_released("1.2.0", known_tags) is False


def test_update_version_files_syncs_version_and_iss(tmp_path):
    # Setup mock repo structure
    version_file = tmp_path / "VERSION"
    version_file.write_text("1.1.0\n", encoding="utf-8")

    iss_dir = tmp_path / "packaging" / "installers" / "windows"
    iss_dir.mkdir(parents=True)
    iss_file = iss_dir / "installer.iss"
    iss_file.write_text(
        ';   /DAppVersion=1.1.0\n#define AppVersion "1.1.0"\nVersionInfoProductVersion={#AppVersion}\n',
        encoding="utf-8",
    )

    updated = update_version_files("1.1.1", repo_root=str(tmp_path))
    assert len(updated) == 2
    assert version_file.read_text(encoding="utf-8").strip() == "1.1.1"

    new_iss = iss_file.read_text(encoding="utf-8")
    assert '#define AppVersion "1.1.1"' in new_iss
    assert ";   /DAppVersion=1.1.1" in new_iss


def test_cli_bump_version_duplicate_abort(monkeypatch, capsys):
    import scripts.bump_version as bump_mod

    # Current is 1.1.0, and v1.1.0 is already tagged
    monkeypatch.setattr(bump_mod, "get_git_tags", lambda: ["v1.1.0"])
    with pytest.raises(SystemExit) as exc:
        bump_mod.main(["1.1.0"])
    assert exc.value.code == 1
    out = capsys.readouterr().err
    assert "already tagged" in out


def test_cli_bump_version_dry_run(tmp_path, monkeypatch, capsys):
    import scripts.bump_version as bump_mod

    v_file = tmp_path / "VERSION"
    v_file.write_text("1.1.0\n", encoding="utf-8")
    monkeypatch.setattr(bump_mod, "_resolve_repo_root", lambda: str(tmp_path))
    monkeypatch.setattr(bump_mod, "get_git_tags", lambda: ["v1.1.0"])

    bump_mod.main(["patch", "--dry-run"])
    out = capsys.readouterr().out
    assert "1.1.0 -> 1.1.1" in out
    # Dry run must not modify the file
    assert v_file.read_text(encoding="utf-8").strip() == "1.1.0"

