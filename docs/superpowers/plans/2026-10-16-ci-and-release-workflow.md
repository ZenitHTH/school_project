# Standard CI & Tag-Driven Release Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the monolithic push-to-main `.github/workflows/build.yml` with a standard two-workflow pipeline: a fast test-only `.github/workflows/ci.yml` on pushes/PRs and a tag-triggered (`v*.*.*`), test-gated, semver-propagated `.github/workflows/release.yml` with `SHA256SUMS.txt` and per-app installer isolation.

**Architecture:** Split continuous integration from release distribution. `.github/workflows/ci.yml` runs offscreen `pytest` with pip caching on every push and pull request to `main`. `.github/workflows/release.yml` triggers only on semantic version tags (`v*.*.*`) or manual `workflow_dispatch`, gates all 4 OS matrix builds (`windows-latest`, `macos-latest`, `ubuntu-24.04`, `fedora:latest`) behind a passing `test` job, propagates the dynamic `VERSION` (stripped of leading `v`) into all installer scripts, uses macOS `ditto` to preserve `.app` framework symlinks, generates `SHA256SUMS.txt`, and publishes immutable GitHub Releases with `generate_release_notes: true`.

**Tech Stack:** GitHub Actions (`actions/checkout@v4`, `actions/setup-python@v5`, `actions/upload-artifact@v4`, `actions/download-artifact@v4`, `softprops/action-gh-release@v2`), PyInstaller, Inno Setup (`iscc`), macOS `ditto` & `hdiutil`, Debian `dpkg-deb`, Fedora `rpmbuild`, pytest.

**Spec:** `wiki/architecture/packaging.md`, `README.md`

## Global Constraints

- **No Release Builds on `main` Pushes:** Ordinary commits and PRs to `main` must only run fast tests (`ci.yml`), never 4-OS PyInstaller builds or mutable `latest` release overwrites.
- **Single Source of Version Truth:** Release version must derive from the Git tag (`${GITHUB_REF_NAME#v}`) or `workflow_dispatch` input `version`, never hardcoded `1.0.0` in workflow steps.
- **Unique Windows `AppId` Per Application:** `StudentManagement`, `LibrarianManagement`, and `BoothApp` must have distinct Inno Setup `AppId` values in `packaging/installers/windows/installer.iss` so installing one never overwrites another's Windows Uninstall registry key.
- **macOS `.app` Symlink Integrity:** Archive `.app` bundles with `ditto -c -k --sequesterRsrc --keepParent <App>.app <App>-macOS-${VERSION}.zip` (never `zip -r` with both `.app` and raw binary).
- **Pre-Release SemVer Safety:** Tags containing a hyphen (e.g. `v1.1.0-rc1`) must mark the GitHub Release as `prerelease: true` and convert `-` to `~` in `build_rpm.sh` (`Version:` field in `rpmbuild` forbids `-`).

## Review Focus

1. **Installing two SMTE apps on the same Windows PC via `Setup.exe`:** `packaging/installers/windows/installer.iss` previously hardcoded one static GUID `AppId` for all three apps; appending `-{#AppName}` ensures three distinct Windows Registry uninstall entries.
2. **Pre-release Git tags such as `v1.0.0-beta.1` or `v1.0.0-rc1` in `build_rpm.sh` and GitHub Releases:** `rpmbuild` fails with `error: Illegal char '-' in: Version:` unless `-` is replaced with `~` (`RPM_VERSION="${VERSION//-/\~}"`), and `softprops/action-gh-release` must set `prerelease: ${{ contains(github.ref_name, '-') }}`.
3. **macOS `.zip` portable archive bloat and broken framework symlinks:** `zip -r ../macos-artifacts/LibrarianManagement-macOS.zip LibrarianManagement.app LibrarianManagement` bundled both the `.app` and duplicate standalone binary while dereferencing Qt `.framework` symlinks; `ditto -c -k --sequesterRsrc --keepParent` packages only the `.app` bundle with symlinks intact.
4. **Manual `workflow_dispatch` dry-run builds on `release.yml`:** When triggered manually via `workflow_dispatch` (where `github.ref` is `refs/heads/main`, not `refs/tags/v*`), the 4 OS build jobs must upload workflow artifacts for inspection while skipping the `publish-release` GitHub Release creation step (`if: startsWith(github.ref, 'refs/tags/v')`).
5. **Artifact Integrity Verification (`SHA256SUMS.txt`):** Release assets must be flattened into a single release directory and accompanied by a generated `SHA256SUMS.txt` file uploaded alongside the installers.

---

### Task 1: Fix Windows Per-App `AppId` & RPM Pre-Release Version Sanitization

**Files:**
- Modify: `packaging/installers/windows/installer.iss:28-35`
- Modify: `packaging/installers/rpm/build_rpm.sh:7-32`
- Test: `tests/test_spec_exclusions.py`

**Interfaces:**
- Consumes: `AppName` preprocessor variable in `installer.iss`; `VERSION` positional argument `$3` in `build_rpm.sh`
- Produces:
  - `AppId={{C78DFE32-0941-4E7B-BFA6-92AE8997321F}-{#AppName}` in `packaging/installers/windows/installer.iss`
  - `RPM_VERSION="${VERSION//-/\~}"` in `packaging/installers/rpm/build_rpm.sh`

- [ ] **Step 1: Write the failing test in `tests/test_spec_exclusions.py`**

```python
def test_installer_iss_has_per_app_id_and_rpm_sanitizes_hyphen_version():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    iss_path = os.path.join(repo_root, "packaging", "installers", "windows", "installer.iss")
    with open(iss_path, "r", encoding="utf-8") as f:
        iss_content = f.read()
    assert "AppId={{C78DFE32-0941-4E7B-BFA6-92AE8997321F}-{#AppName}" in iss_content

    rpm_path = os.path.join(repo_root, "packaging", "installers", "rpm", "build_rpm.sh")
    with open(rpm_path, "r", encoding="utf-8") as f:
        rpm_content = f.read()
    assert 'RPM_VERSION="${VERSION//-/\\~}"' in rpm_content
    assert "Version:        $RPM_VERSION" in rpm_content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_spec_exclusions.py::test_installer_iss_has_per_app_id_and_rpm_sanitizes_hyphen_version -v`
Expected: FAIL with `AssertionError`

- [ ] **Step 3: Update `packaging/installers/windows/installer.iss` and `packaging/installers/rpm/build_rpm.sh`**

In `packaging/installers/windows/installer.iss`, change line 29 to:
```ini
AppId={{C78DFE32-0941-4E7B-BFA6-92AE8997321F}-{#AppName}
```
In `packaging/installers/rpm/build_rpm.sh`, add `RPM_VERSION="${VERSION//-/\~}"` after `VERSION="${3:-1.0.0}"` and use `Version:        $RPM_VERSION` and `* Fri Oct 02 2026 Admin <admin@school.local> - $RPM_VERSION-1` in the generated spec.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_spec_exclusions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packaging/installers/windows/installer.iss packaging/installers/rpm/build_rpm.sh tests/test_spec_exclusions.py
git commit -m "fix(packaging): isolate Windows AppId per app and sanitize RPM pre-release versions"
```

---

### Task 2: Replace `.github/workflows/build.yml` with `ci.yml` and Tag-Driven `release.yml`

**Files:**
- Delete: `.github/workflows/build.yml`
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/release.yml`
- Modify: `tests/test_spec_exclusions.py`

**Interfaces:**
- Consumes: `requirements.txt`, `packaging/*.spec`, `packaging/installers/**`
- Produces:
  - `.github/workflows/ci.yml`: runs `pytest` on `push` and `pull_request` to `main` with `cache: 'pip'` and `QT_QPA_PLATFORM: offscreen`
  - `.github/workflows/release.yml`: runs `test` job -> 4 OS build jobs (`build-windows`, `build-macos`, `build-ubuntu`, `build-fedora`) -> `publish-release` job with dynamic `VERSION`, `ditto` macOS archiving, `SHA256SUMS.txt`, and `generate_release_notes: true`

- [ ] **Step 1: Write the failing test in `tests/test_spec_exclusions.py`**

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
    assert "pull_request:" in ci_yml
    assert "pytest" in ci_yml
    assert "cache: 'pip'" in ci_yml

    with open(rel_path, "r", encoding="utf-8") as f:
        rel_yml = f.read()
    assert "- 'v*.*.*'" in rel_yml
    assert "workflow_dispatch:" in rel_yml
    assert "needs: [test]" in rel_yml
    assert "ditto -c -k --sequesterRsrc --keepParent" in rel_yml
    assert "SHA256SUMS.txt" in rel_yml
    assert "generate_release_notes: true" in rel_yml
    assert "startsWith(github.ref, 'refs/tags/v')" in rel_yml
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_spec_exclusions.py::test_ci_and_release_workflows_follow_standard_release_pipeline -v`
Expected: FAIL with `"Legacy build.yml must be removed"`

- [ ] **Step 3: Delete `.github/workflows/build.yml` and create `.github/workflows/ci.yml` and `.github/workflows/release.yml`**

1. In `.github/workflows/ci.yml`:
   - Trigger on `push: branches: [main]` and `pull_request: branches: [main]`.
   - Use `concurrency` group `${{ github.workflow }}-${{ github.ref }}` with `cancel-in-progress: true`.
   - Run `test` job on `ubuntu-24.04` with `actions/setup-python@v5` (`python-version: "3.11"`, `cache: 'pip'`), install headless X11/EGL packages, `pip install -r requirements.txt`, and run `QT_QPA_PLATFORM=offscreen pytest -v`.
2. In `.github/workflows/release.yml`:
   - Trigger on `push: tags: ['v*.*.*']` and `workflow_dispatch: inputs: version: { description: 'Release version (e.g. 1.0.0)', required: false, default: '1.0.0' }`.
   - Define `test` job on `ubuntu-24.04` running `QT_QPA_PLATFORM=offscreen pytest -v`.
   - In `build-windows`, `build-macos`, `build-ubuntu`, and `build-fedora` (`needs: [test]`):
     - Compute `VERSION`: on tag push strip leading `v` (`${GITHUB_REF_NAME#v}`), otherwise use `${{ inputs.version || '1.0.0' }}`.
     - Pass `VERSION` into `iscc /DAppVersion=...`, `create_dmg.sh ... "$VERSION"`, `build_deb.sh ... "$VERSION"`, and `build_rpm.sh ... "$VERSION"`.
     - On macOS, archive each `.app` via `ditto -c -k --sequesterRsrc --keepParent dist/<App>.app macos-artifacts/<App>-macOS-${VERSION}.zip`.
   - In `publish-release` (`needs: [build-windows, build-macos, build-ubuntu, build-fedora]`, `if: startsWith(github.ref, 'refs/tags/v')`):
     - Download all artifacts, collect into `release-assets/`, generate `SHA256SUMS.txt` (`cd release-assets && sha256sum * > SHA256SUMS.txt`), and publish with `softprops/action-gh-release@v2` (`tag_name: ${{ github.ref_name }}`, `name: Release ${{ github.ref_name }}`, `prerelease: ${{ contains(github.ref_name, '-') }}`, `generate_release_notes: true`, `files: release-assets/*`).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_spec_exclusions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ tests/test_spec_exclusions.py
git commit -m "ci(release): split fast CI test workflow from tag-driven release pipeline"
```

---

### Task 3: Update Packaging Wiki & README Release Instructions

**Files:**
- Modify: `wiki/architecture/packaging.md`
- Modify: `wiki/log.md`
- Modify: `README.md:235-252`

**Interfaces:**
- Consumes: `.github/workflows/ci.yml`, `.github/workflows/release.yml`
- Produces: Updated release documentation in `wiki/architecture/packaging.md`, `wiki/log.md`, and `README.md`

- [ ] **Step 1: Update `wiki/architecture/packaging.md`, `wiki/log.md`, and `README.md`**

- In `wiki/architecture/packaging.md`: remove references to deleted `*_windows.spec` files and document the two-workflow architecture (`ci.yml` on `main` pushes/PRs; `release.yml` on `v*.*.*` tags with `test` gate, dynamic `VERSION`, `ditto` macOS bundles, per-app Windows `AppId`, and `SHA256SUMS.txt`).
- In `README.md`: update the **GitHub Actions Multi-Platform CI/CD** section to explain that pushing to `main` runs automated tests (`ci.yml`) and pushing a version tag (`git tag v1.0.0 && git push origin v1.0.0`) builds and publishes versioned installers + `SHA256SUMS.txt` to GitHub Releases (`release.yml`).
- In `wiki/log.md`: append `[2026-10-16] ci | Standard CI & Tag-Driven Release Pipeline`.

- [ ] **Step 2: Run full verification test suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add wiki/architecture/packaging.md wiki/log.md README.md docs/superpowers/plans/2026-10-16-ci-and-release-workflow.md
git commit -m "docs(release): document tag-driven release workflow and CI split"
```
