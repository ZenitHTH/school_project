import os
import re
import subprocess
import sys
from typing import List, Optional

DEFAULT_VERSION = "1.1.0"


def _resolve_version_file(repo_root: Optional[str] = None) -> str:
    if repo_root:
        return os.path.join(repo_root, "VERSION")
    base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    return os.path.join(base, "VERSION")


def get_version(repo_root: Optional[str] = None) -> str:
    """Return canonical application semantic version string."""
    version_path = _resolve_version_file(repo_root)
    if os.path.exists(version_path):
        with open(version_path, "r", encoding="utf-8") as f:
            ver = f.read().strip()
            if ver:
                return ver
    return DEFAULT_VERSION


def calculate_next_version(current: str, action: str) -> str:
    """Calculate next SemVer based on action ('patch', 'minor', 'major' or explicit 'X.Y.Z')."""
    act = action.strip().lstrip("v")
    if re.match(r"^\d+\.\d+\.\d+", act):
        return act
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", current.strip().lstrip("v"))
    if not m:
        raise ValueError(f"Cannot parse current version '{current}'")
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if action == "patch":
        return f"{major}.{minor}.{patch + 1}"
    if action == "minor":
        return f"{major}.{minor + 1}.0"
    if action == "major":
        return f"{major + 1}.0.0"
    raise ValueError(f"Invalid version or action: '{action}'. Use patch, minor, major, or X.Y.Z")


def get_git_tags() -> List[str]:
    """Retrieve existing git tags in local repository."""
    try:
        proc = subprocess.run(["git", "tag", "--list"], capture_output=True, text=True, check=True)
        return [t.strip() for t in proc.stdout.splitlines() if t.strip()]
    except Exception:
        return []


def is_version_released(version: str, tags: Optional[List[str]] = None) -> bool:
    """Check if target version already exists in git release tags."""
    v_clean = version.strip().lstrip("v")
    tag_list = tags if tags is not None else get_git_tags()
    normalized = {t.strip().lstrip("v") for t in tag_list}
    return v_clean in normalized


def _sync_inno_setup_iss(iss_path: str, target_ver: str) -> None:
    """Update version definition in Windows Inno Setup script."""
    if not os.path.exists(iss_path):
        return
    with open(iss_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(r'#define AppVersion "[^"]+"', f'#define AppVersion "{target_ver}"', content)
    content = re.sub(r';\s*/DAppVersion=[^\r\n]+', f';   /DAppVersion={target_ver}', content)
    with open(iss_path, "w", encoding="utf-8") as f:
        f.write(content)


def update_version_files(target_ver: str, repo_root: Optional[str] = None) -> List[str]:
    """Synchronize target version into VERSION and Inno Setup script."""
    root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    version_file = os.path.join(root, "VERSION")
    with open(version_file, "w", encoding="utf-8") as f:
        f.write(f"{target_ver.strip()}\n")

    iss_file = os.path.join(root, "packaging", "installers", "windows", "installer.iss")
    _sync_inno_setup_iss(iss_file, target_ver)
    return [version_file, iss_file]


APP_VERSION = get_version()

if __name__ == "__main__":
    from scripts.bump_version import main as _bump_main
    _bump_main()

