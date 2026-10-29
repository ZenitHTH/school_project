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
