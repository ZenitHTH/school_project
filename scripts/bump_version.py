#!/usr/bin/env python3
"""CLI utility to easily bump project version and synchronize installer files."""

import argparse
import os
import sys
from typing import List, Optional

# Ensure project root in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.shared.version import (
    calculate_next_version,
    get_git_tags,
    get_version,
    is_version_released,
    update_version_files,
)


def _resolve_repo_root() -> str:
    return PROJECT_ROOT


def _show_current_status(current: str, tags: List[str]) -> None:
    print(f"Current version: {current}")
    print(f"Latest git tags: {', '.join(tags[-5:]) if tags else 'none'}")
    print("\nAvailable bump actions:")
    print(f"  patch -> {calculate_next_version(current, 'patch')}")
    print(f"  minor -> {calculate_next_version(current, 'minor')}")
    print(f"  major -> {calculate_next_version(current, 'major')}")
    print("\nUsage: python scripts/bump_version.py [patch|minor|major|<version>] [--dry-run] [--force]")


def _validate_target_version(target: str, force: bool, tags: List[str]) -> None:
    if not force and is_version_released(target, tags):
        sys.stderr.write(
            f"✗ Error: Version '{target}' is already tagged as 'v{target}' in git!\n"
            f"  Cannot release duplicate version.\n"
            f"  To force anyway, run with --force.\n"
        )
        sys.exit(1)


def _perform_bump(target: str, dry_run: bool, root: str) -> None:
    if dry_run:
        print(f"[DRY-RUN] Would update VERSION and packaging/installers/windows/installer.iss to {target}")
        return
    updated = update_version_files(target, repo_root=root)
    print("Updated files:")
    for f in updated:
        rel = os.path.relpath(f, root)
        print(f"  ✓ {rel}")
    print("\nReady to commit and push:")
    print(f'  git commit -am "ci(release): bump version to {target}"')
    print("  git push origin dev")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Bump project version and sync setup files.")
    parser.add_argument("action", nargs="?", help="patch, minor, major, or explicit X.Y.Z")
    parser.add_argument("--dry-run", action="store_true", help="Preview bump without writing files")
    parser.add_argument("--force", action="store_true", help="Allow bumping to an already tagged version")
    args = parser.parse_args(argv)

    root = _resolve_repo_root()
    current = get_version(root)
    tags = get_git_tags()

    if not args.action:
        _show_current_status(current, tags)
        return

    target = calculate_next_version(current, args.action)
    _validate_target_version(target, args.force, tags)

    print(f"Version transition: {current} -> {target}")
    _perform_bump(target, args.dry_run, root)


if __name__ == "__main__":
    main()
