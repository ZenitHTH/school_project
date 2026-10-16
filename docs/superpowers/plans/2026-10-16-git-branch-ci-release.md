# Dev vs Main Git Branch & CI/CD Packaging Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Organize Git branches so `dev` runs lightweight test-only CI without building packages, and pushing/merging `dev` to `main` (or pushing `v*.*.*` tags) automatically builds and releases all desktop packages (`.exe`, `Setup.exe`, `.dmg`, `.deb`, `.rpm`, `.tar.gz`, `SHA256SUMS.txt`).

**Architecture:** Split GitHub Actions triggers cleanly by branch role: `.github/workflows/ci.yml` runs headless `pytest` on `push` to `dev` and `pull_request` to `main`/`dev` (zero PyInstaller/packaging jobs). `.github/workflows/release.yml` runs on `push` to `main`, `v*.*.*` tags, and `workflow_dispatch`, gating 4-OS installer builds behind `test` and publishing assets to GitHub Releases (`latest` pre-release on `main` push, or versioned release on `v*.*.*` tag). Create and check out the `dev` branch for ongoing development and remove the merged local `feature/ci-and-release-workflow` branch.

**Tech Stack:** Git, GitHub Actions (`actions/checkout@v4`, `actions/setup-python@v5`, `softprops/action-gh-release@v2`), PyInstaller, Inno Setup, `dpkg-deb`, `rpmbuild`, `hdiutil`, `pytest`.

**Spec:** `wiki/architecture/packaging.md`

## Global Constraints

- Maintain 100% test pass rate via `.venv/bin/pytest tests/` (`AGENTS.md` Rule 3.5).
- Update `wiki/architecture/packaging.md` and append a summary entry to `wiki/log.md` (`AGENTS.md` Rule 4).
- Never run `pyinstaller` or installer scripts inside `.github/workflows/ci.yml` on `dev` pushes.
- `release.yml` must publish all built packages (`.exe`, `Setup.exe`, `.dmg`, `.zip`, `.deb`, `.rpm`, `.tar.gz`, `SHA256SUMS.txt`) to GitHub Releases both on `push` to `main` (tag `latest`) and on `v*.*.*` tags.

## Review Focus

- Pushing to `main` without a `v*.*.*` tag previously skipped `publish-release` because of `if: startsWith(github.ref, 'refs/tags/v')`; removing that guard and falling back to `tag_name: 'latest'` ensures pushes from `dev` to `main` actually publish release packages.
- Rapid pushes to `main` could spawn duplicate expensive 4-OS builds; adding `concurrency` with `cancel-in-progress: true` on `release.yml` prevents runner queue exhaustion.
- `SHA256SUMS.txt` generation in `release.yml` must remain outside `release-assets/` (`sha256sum * > ../SHA256SUMS.txt`) so it does not hash itself.
- Local stale branch `feature/ci-and-release-workflow` is already merged into `main` (`839cf86`) and should be cleaned up when creating `dev`.

---

### Task 1: Split `ci.yml` (dev test-only) and `release.yml` (main + tag package release) with regression tests

**Files:**
- Modify: `tests/test_spec_exclusions.py:87-112`
- Modify: `.github/workflows/ci.yml:1-12`
- Modify: `.github/workflows/release.yml:1-17`
- Modify: `.github/workflows/release.yml:279-306`
- Test: `tests/test_spec_exclusions.py`

**Interfaces:**
- Consumes: `.github/workflows/ci.yml`, `.github/workflows/release.yml`
- Produces: Updated workflow YAML files verified by `test_ci_and_release_workflows_follow_standard_release_pipeline()`

- [ ] **Step 1: Update the workflow test in `tests/test_spec_exclusions.py` to require `dev` on CI and `main` on Release**

```python
def test_ci_and_release_workflows_follow_standard_release_pipeline():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    workflows_dir = os.path.join(repo_root, ".github", "workflows")

    assert not os.path.exists(os.path.join(workflows_dir, "build.yml")), "Legacy build.yml must be removed"
    ci_path = os.path.join(workflows_dir, "ci.yml")
    rel_path = os.path.join(workflows_dir, "release.yml")
    assert os.path.exists(ci_path), "ci.yml missing"
    assert os.path.exists(rel_path), "release.yml missing"

    with open(ci_path, "r", encoding="utf-8") as f:
        ci_yml = f.read()
    assert "branches: [dev]" in ci_yml
    assert "branches: [main, dev]" in ci_yml
    assert "pull_request:" in ci_yml
    assert "pytest" in ci_yml
    assert "cache: 'pip'" in ci_yml
    assert "pyinstaller" not in ci_yml

    with open(rel_path, "r", encoding="utf-8") as f:
        rel_yml = f.read()
    assert "- main" in rel_yml
    assert "- 'v*.*.*'" in rel_yml
    assert "workflow_dispatch:" in rel_yml
    assert "needs: [test]" in rel_yml
    assert "ditto -c -k --sequesterRsrc --keepParent" in rel_yml
    assert "SHA256SUMS.txt" in rel_yml
    assert "generate_release_notes: true" in rel_yml
    assert "startsWith(github.ref, 'refs/tags/v') && github.ref_name || 'latest'" in rel_yml
```

- [ ] **Step 2: Run pytest to verify the test fails**

Run: `.venv/bin/pytest tests/test_spec_exclusions.py::test_ci_and_release_workflows_follow_standard_release_pipeline -v`
Expected: FAIL with `AssertionError: assert 'branches: [dev]' in ci_yml`

- [ ] **Step 3: Update `.github/workflows/ci.yml` and `.github/workflows/release.yml`**

In `.github/workflows/ci.yml`, set `on.push.branches: [dev]` and `on.pull_request.branches: [main, dev]`.

In `.github/workflows/release.yml`:
1. Add `branches: [main]` under `on.push` alongside `tags: ['v*.*.*']`.
2. Add top-level `concurrency` (`group: ${{ github.workflow }}-${{ github.ref }}`, `cancel-in-progress: true`).
3. In `publish-release`, remove `if: startsWith(github.ref, 'refs/tags/v')` and configure `softprops/action-gh-release@v2` with:
   - `tag_name: ${{ startsWith(github.ref, 'refs/tags/v') && github.ref_name || 'latest' }}`
   - `name: ${{ startsWith(github.ref, 'refs/tags/v') && format('Release {0}', github.ref_name) || 'Latest Multi-Platform Build (main)' }}`
   - `prerelease: ${{ !startsWith(github.ref, 'refs/tags/v') || contains(github.ref_name, '-') }}`

- [ ] **Step 4: Run pytest to verify the test passes**

Run: `.venv/bin/pytest tests/test_spec_exclusions.py -v`
Expected: PASS (5/5 tests in `test_spec_exclusions.py`)

---

### Task 2: Organize Git Branches (`dev` & `main`), Update Wiki, and Commit

**Files:**
- Modify: `wiki/architecture/packaging.md:50-65`
- Modify: `wiki/log.md:100-106`
- Test: `tests/`

**Interfaces:**
- Consumes: Task 1 workflow changes
- Produces: Clean `dev` and `main` branches with updated `wiki/architecture/packaging.md` and `wiki/log.md`

- [ ] **Step 1: Update `wiki/architecture/packaging.md` and `wiki/log.md`**

In `wiki/architecture/packaging.md` (Section 5), document:
- `ci.yml` triggers on `push` to `dev` and `pull_request` to `main`/`dev` (test-only, no packaging).
- `release.yml` triggers on `push` to `main`, `v*.*.*` tags, and `workflow_dispatch` (builds `.exe`, `Setup.exe`, `.dmg`, `.deb`, `.rpm`, `.tar.gz` and publishes to GitHub Releases).

In `wiki/log.md`, append `## [2026-10-16] ci | Dev vs Main Branch CI/CD Separation`.

- [ ] **Step 2: Run full test suite to verify 100% pass rate**

Run: `.venv/bin/pytest tests/`
Expected: PASS (all tests green, 0 failures)

- [ ] **Step 3: Organize Git branches (`main` and `dev`) and commit changes**

```bash
git branch -d feature/ci-and-release-workflow
git checkout -b dev
git add .github/workflows/ci.yml .github/workflows/release.yml tests/test_spec_exclusions.py wiki/architecture/packaging.md wiki/log.md
git commit -m "ci: run test-only CI on dev and full package release on main"
```

- [ ] **Step 4: Verify git status and branch topology**

Run: `git status -s && git branch -a`
Expected: Working tree clean (excluding untracked `docs/superpowers/` if not committed), active branch `* dev`, `main` intact.
