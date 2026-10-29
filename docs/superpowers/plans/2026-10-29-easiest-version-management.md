# Single-Command Version Management & Duplicate Prevention Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide the easiest, single-command method to bump and synchronize the project release version (`VERSION` file as single source of truth) with automated SemVer calculation, Inno Setup sync, and duplicate tag prevention.

**Architecture:** Establish the root `VERSION` file as the sole canonical source of truth for all platforms (Windows Inno Setup, macOS DMG, Debian .deb, Fedora RPM, PyInstaller .spec, and runtime Qt app). Introduce a zero-dependency CLI utility (`scripts/bump_version.py`) and module entrypoint (`python -m core.shared.version`) that inspects existing git tags to prevent duplicate release versions, auto-increments SemVer (`patch`, `minor`, `major`), updates `VERSION` and `installer.iss`, and refactors tests to validate dynamic version sync rather than hardcoded string literals.

**Tech Stack:** Python 3.14 (stdlib: `sys`, `os`, `re`, `subprocess`, `argparse`), Inno Setup, Git.

**Spec:** User request: "how to change version easiest if you can. beware version too. don't release duplicated version. add more x.x.1 example . original 1.1.1 -> release new 1.1.2".

---

## Global Constraints

- Root `VERSION` is the single canonical source of truth for the entire repository.
- Functions must obey Clean Code: max 20 lines, max 3 arguments, max 2 indentation levels.
- Zero external runtime dependencies: use standard library only (`re`, `subprocess`, `argparse`, `pathlib`).
- Never allow bumping to a version that already exists in local or remote git tags (`git tag --list`).
- All 217 tests must pass under `.venv/bin/pytest tests/ -W error::ResourceWarning`.

## Review Focus

1. **Tag Collision Detection**: A version bump to a version that already exists in git tags (e.g. `v1.1.0`) must be rejected with an actionable error message suggesting the next unused SemVer.
2. **Inno Setup Synchronization**: `packaging/installers/windows/installer.iss` `#define AppVersion "..."` must automatically match `VERSION` so Windows `Setup.exe` installers always reflect the bumped version.
3. **Decoupled Test Suite**: `tests/test_spec_exclusions.py` must dynamically test that all components match the current `VERSION` without hardcoding specific version strings like `"1.1.0"`.
4. **Shell Script Resilience**: Fallback versions in packaging shell scripts (`build_deb.sh`, `build_rpm.sh`, `create_dmg.sh`) and PyInstaller `.spec` files must point to standard fallback `0.0.0` or dynamic read so they never drift out of sync when `VERSION` changes.
5. **Interactive & Non-Interactive CLI**: The bump tool must work smoothly in both interactive mode (showing current version and next suggestions) and automated CI mode (`python scripts/bump_version.py patch`).

---

## File Structure & Module Map

| File Path | Role / Responsibility |
|---|---|
| `scripts/bump_version.py` | Standalone CLI script: calculates SemVer, checks git tags for duplicates, updates `VERSION` & `installer.iss`, outputs summary |
| `core/shared/version.py` | Canonical module: provides `get_version()`, `bump_semver()`, duplicate tag check, and `python -m core.shared.version` CLI |
| `packaging/installers/windows/installer.iss` | Windows Inno Setup script with `#define AppVersion` synchronized with `VERSION` |
| `packaging/installers/deb/build_deb.sh` | Linux Debian packaging: reads `VERSION` with safe `0.0.0` fallback |
| `packaging/installers/rpm/build_rpm.sh` | Linux RPM packaging: reads `VERSION` with safe `0.0.0` fallback |
| `packaging/installers/macos/create_dmg.sh` | macOS DMG packaging: reads `VERSION` with safe `0.0.0` fallback |
| `packaging/*.spec` | PyInstaller spec files: read `VERSION` with safe `0.0.0` fallback |
| `tests/test_version_bump.py` | New unit tests for SemVer calculations, tag collision guards, and CLI bump behavior |
| `tests/test_spec_exclusions.py` | Refactored integration tests verifying dynamic version sync across all installer files |
| `wiki/architecture/packaging.md` | Knowledge base update documenting the single-command version bump procedure |
| `wiki/log.md` | Changelog entry for version tooling enhancement |

---

## Implementation Tasks

### Task 1: Decouple Hardcoded Version Strings in Packaging Scripts and Tests

**Files:**
- Modify: `packaging/installers/deb/build_deb.sh:9`
- Modify: `packaging/installers/rpm/build_rpm.sh:9`
- Modify: `packaging/installers/macos/create_dmg.sh:8`
- Modify: `packaging/librarian_management.spec:8`
- Modify: `packaging/student_management.spec:8`
- Modify: `packaging/booth_app.spec:8`
- Modify: `tests/test_spec_exclusions.py:119-158`

- [ ] **Step 1: Write failing test in `tests/test_spec_exclusions.py`**
  Refactor `test_setup_files_and_app_version_synchronized` to verify that packaging shell scripts and `.spec` files read `VERSION` without requiring hardcoded version echoes, and verify `ver` matches SemVer regex `^\d+\.\d+\.\d+$`.
- [ ] **Step 2: Run test to confirm failure / current behavior**
  Run `.venv/bin/pytest tests/test_spec_exclusions.py -v`.
- [ ] **Step 3: Update packaging scripts and spec files to use safe generic fallbacks**
  Change fallback `echo "1.1.0"` in `build_deb.sh`, `build_rpm.sh`, `create_dmg.sh`, and `.spec` files to generic fallback `"0.0.0"`.
- [ ] **Step 4: Verify tests pass**
  Run `.venv/bin/pytest tests/test_spec_exclusions.py -v`.
- [ ] **Step 5: Commit task 1**
  `git commit -m "refactor(packaging): decouple packaging script fallbacks from hardcoded version literals"`

---

### Task 2: Implement Canonical SemVer Calculation & Duplicate Tag Protection

**Files:**
- Modify: `core/shared/version.py`
- Create: `tests/test_version_bump.py`

- [ ] **Step 1: Write unit tests in `tests/test_version_bump.py`**
  Test SemVer increments (`1.1.0` -> `patch: 1.1.1`, `minor: 1.2.0`, `major: 2.0.0`), explicit version parsing (`1.1.5`), invalid version rejection (`1.1`, `abc`), and duplicate git tag detection (`v1.1.0` -> `is_duplicate_tag == True`).
- [ ] **Step 2: Run test to confirm failure**
  Run `.venv/bin/pytest tests/test_version_bump.py -v`.
- [ ] **Step 3: Implement SemVer calculation and tag collision checks in `core/shared/version.py`**
  - Add `calculate_next_version(current: str, action: str) -> str` (`patch`, `minor`, `major`, or explicit `X.Y.Z`).
  - Add `get_existing_tags() -> List[str]` reading `git tag --list`.
  - Add `is_version_already_released(version: str) -> bool`.
  - Keep each helper <= 20 lines.
- [ ] **Step 4: Verify unit tests pass**
  Run `.venv/bin/pytest tests/test_version_bump.py -v`.
- [ ] **Step 5: Commit task 2**
  `git commit -m "feat(version): add semver calculator and git tag collision protection"`

---

### Task 3: Build Single-Command Version Bump CLI (`scripts/bump_version.py`)

**Files:**
- Create: `scripts/bump_version.py`
- Modify: `core/shared/version.py` (wire `__main__` entrypoint)
- Test: `tests/test_version_bump.py`

- [ ] **Step 1: Write CLI end-to-end test in `tests/test_version_bump.py`**
  Test running `python scripts/bump_version.py patch --dry-run` and `--write` on a temporary test directory with simulated `VERSION` and `installer.iss`.
- [ ] **Step 2: Implement `scripts/bump_version.py`**
  - Parse arguments: `patch`, `minor`, `major`, explicit version (e.g. `1.1.2`), `--dry-run`, `--no-tag-check`.
  - Read current `VERSION`.
  - Calculate target version.
  - Check against existing git tags (`v<target>`). If duplicate exists, abort with clear warning:
    `✗ Error: Version 1.1.0 is already tagged as 'v1.1.0'. Did you mean 1.1.1?`
  - Update `VERSION` file.
  - Update `packaging/installers/windows/installer.iss` (`#define AppVersion "<target>"` and `; /DAppVersion=<target>`).
  - Print summary with next git commands:
    ```
    ✓ Bumped version: 1.1.0 -> 1.1.1
    Updated files:
      - VERSION
      - packaging/installers/windows/installer.iss
    Ready to push:
      git commit -am "ci(release): bump version to 1.1.1" && git push origin dev
    ```
- [ ] **Step 3: Verify CLI end-to-end tests pass**
  Run `.venv/bin/pytest tests/test_version_bump.py -v`.
- [ ] **Step 4: Commit task 3**
  `git commit -m "feat(cli): introduce single-command bump_version script with duplicate prevention"`

---

### Task 4: Execute Version Bump to 1.1.1, Validate Suite & Push to Main

**Files:**
- Run: `python scripts/bump_version.py patch`
- Modify: `wiki/architecture/packaging.md`
- Modify: `wiki/log.md`

- [ ] **Step 1: Run version bump CLI to increment 1.1.0 -> 1.1.1**
  Execute `.venv/bin/python scripts/bump_version.py patch`.
- [ ] **Step 2: Run full test suite with zero warnings**
  Execute `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -W error::ResourceWarning -v`.
- [ ] **Step 3: Update documentation**
  Update `wiki/architecture/packaging.md` with the new single-command bump instructions and append entry to `wiki/log.md`.
- [ ] **Step 4: Commit on `dev`**
  `git commit -am "ci(release): bump version to 1.1.1 and streamline release workflow"`
- [ ] **Step 5: Push `dev`, merge to `main`, and push `main`**
  `git push origin dev && git checkout main && git merge --ff-only dev && git push origin main && git checkout dev`.
- [ ] **Step 6: Confirm GitHub Actions Release workflow starts cleanly with tag `v1.1.1`**
  Run `gh run list -L 2`.
