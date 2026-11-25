# Zero-Click LAN Install & Auto-Rediscovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guarantee zero-click LAN setup after installation by auto-allowing Librarian LAN ports (`8765/tcp`, `8766/udp`) in Linux (`.deb`/`.rpm`) and Windows (`Setup.exe`) installers and auto-rediscovering the Librarian PC in `BoothApp` across any launch order or DHCP IP change.

**Architecture:** Installer build scripts (`build_deb.sh`, `build_rpm.sh`, `installer.iss` + `release.yml`) conditionally inject idempotent, non-fatal firewall allow/cleanup hooks exclusively for `LibrarianManagement`. `BoothAdapter.getConnectionStatus()` performs a fast (`0.4s`) UDP broadcast rediscovery fallback when the saved host is empty or unreachable, paired with a disconnected-only 5s `Timer` in `apps/booth_app/qml/Main.qml`.

**Tech Stack:** Bash (`dpkg-deb`, `rpmbuild`, `ufw`, `firewall-cmd`), Inno Setup (`netsh advfirewall`), GitHub Actions YAML, Python 3.14, PySide6 / QML, pytest.

**Spec:** `docs/superpowers/specs/2026-11-25-zero-click-lan-install-design.md`

## Global Constraints

- Zero new third-party Python dependencies (`requirements.txt` unchanged).
- Firewall hooks MUST apply **only** to `LibrarianManagement` (`librarianmanagement`); `StudentManagement` and `BoothApp` installers must remain untouched (`PrivilegesRequired=lowest` on Windows, no firewall scripts on Linux).
- All Linux/Windows firewall commands in install/uninstall hooks MUST be non-fatal (`|| true` / `Flags: runhidden`) so installation never fails on minimal systems without `ufw` or `firewalld`.
- Keep all Python files `<200` lines and functions `<20` lines; preserve all existing QML `objectName`s.
- Run `.venv/bin/pytest tests/` before completion; commit exclusively to `dev`.

## Review Focus

- **Linux PC without `ufw` or `firewalld` installed (e.g., bare Debian/minimal Ubuntu):** `postinst` / `%post` must check `command -v` and append `|| true` so `dpkg`/`rpm` never exits non-zero.
- **Package upgrade (`dpkg -i` upgrade / `rpm -Uvh`):** `prerm` must only delete rules on `remove`/`purge` (not `upgrade`), and `%postun` must guard with `if [ "$1" -eq 0 ]` so upgrading `librarianmanagement` does not strip firewall rules!
- **`BoothApp` unit tests testing offline status (`test_booth_adapter_lan.py`):** Offline tests pass `auto_discover=False` (or mock `discover_librarian` -> `None`) so they don't wait `0.4s` on real UDP broadcast or accidentally pick up a live LAN server during pytest.
- **Manual IP entry while server is temporarily offline:** `BoothAdapter.configureConnection()` must still save the user's typed host/port first, and `Main.qml`'s `reconnectTimer` must pause while `lanSettingsDialog.visible` is true so background polling never overwrites fields mid-edit.
- **Public Wi-Fi exposure on Windows laptops:** `netsh advfirewall` rules must specify `profile=private,domain` (excluding `public`) and scope to `{app}\{#AppExe}` or ports `8765`/`8766`.

---

## File Structure

- Modify: `packaging/installers/deb/build_deb.sh` — generate `DEBIAN/postinst` and `DEBIAN/prerm` for `librarianmanagement`.
- Modify: `packaging/installers/rpm/build_rpm.sh` — generate `%post` and `%postun` for `librarianmanagement`.
- Modify: `packaging/installers/windows/installer.iss` — `#ifdef EnableLanFirewall` sets `PrivilegesRequired=admin` and adds `[Run]` / `[UninstallRun]` `netsh` rules.
- Modify: `.github/workflows/release.yml` — pass `/DEnableLanFirewall=1` to `iscc` only for `LibrarianManagement`.
- Modify: `apps/booth_app/adapters/booth_adapter.py` — add `auto_discover: bool = True` and `_try_rediscover()` fallback on failed `health()`, keeping file `<200` lines and functions `<20` lines.
- Modify: `apps/booth_app/qml/Main.qml` — add `reconnectTimer` (`objectName: "lanReconnectTimer"`, `interval: 5000`, active only when disconnected and settings dialog closed).
- Modify: `wiki/architecture/packaging.md`, `wiki/apps/booth-app.md`, `wiki/log.md` — document firewall hooks and auto-rediscovery.
- Create: `assets/icons/` (`boothapp`, `librarianmanagement`, `studentmanagement` `.svg`/`.png`/`.ico`/`.icns`) — vector-generated clean app icons.
- Modify: `packaging/{booth_app,librarian_management,student_management}.spec`, `packaging/installers/windows/installer.iss`, `.github/workflows/release.yml`, `packaging/installers/{deb/build_deb.sh,rpm/build_rpm.sh}`, and `apps/{booth_app,librarian_management_app,student_management_app}/main.py` — wire app icons everywhere.
- Create: `tests/test_installer_firewall.py` — tests verifying `.deb`, `.rpm`, `installer.iss`, and `release.yml` firewall rules, upgrade guards (`$1 -eq 0` / `remove|purge`), `BoothApp`/`StudentManagement` isolation, and icon wiring.
- Modify: `tests/test_booth_adapter_lan.py` — tests verifying `BoothAdapter` auto-rediscovery on launch-order mismatch and DHCP IP change, plus `lanReconnectTimer` in QML.

---

### Task 1: Linux (`.deb` / `.rpm`) & Windows (`installer.iss` / `release.yml`) Auto-Firewall Rules

**Files:**
- Modify: `packaging/installers/deb/build_deb.sh`
- Modify: `packaging/installers/rpm/build_rpm.sh`
- Modify: `packaging/installers/windows/installer.iss`
- Modify: `.github/workflows/release.yml`
- Create: `tests/test_installer_firewall.py`

**Interfaces:**
- Produces:
  - `build_deb.sh`: when `PKG_NAME == "librarianmanagement"`, writes executable (`0755`) `DEBIAN/postinst` (`configure` -> `ufw allow 8765/tcp`, `ufw allow 8766/udp`, `firewall-cmd --permanent --add-port=8765/tcp --add-port=8766/udp` + `--reload`, all guarded by `command -v` and `|| true`) and `DEBIAN/prerm` (`remove|purge` only -> `ufw delete allow ...`, `firewall-cmd --permanent --remove-port=...` + `--reload`, `|| true`).
  - `build_rpm.sh`: when `PKG_NAME == "librarianmanagement"`, writes `%post` (same `firewall-cmd` / `ufw` allow commands with `|| true`) and `%postun` (`if [ "$1" -eq 0 ]; then ... fi` cleanup so `rpm -U` upgrades keep rules).
  - `installer.iss`: under `#ifdef EnableLanFirewall`, sets `PrivilegesRequired=admin` (else `lowest`), adds `[Run]` `netsh.exe` rules (`SMTE Librarian LAN HTTP` TCP `8765`, `SMTE Librarian LAN Discovery` UDP `8766`, `dir=in action=allow profile=private,domain`, `Flags: runhidden waituntilterminated`) and `[UninstallRun]` `netsh.exe advfirewall firewall delete rule` (`RunOnceId` set).
  - `.github/workflows/release.yml`: passes `/DEnableLanFirewall=1` on the `LibrarianManagement` `iscc` line only.

- [ ] **Step 1: Write the failing tests in `tests/test_installer_firewall.py`**

Write tests that:
1. Inspect/execute `build_deb.sh` (or dry-run / inspect generated control scripts if `dpkg-deb` is unavailable on macOS — extract a helper or test script generation directly when `dpkg-deb` is mocked on `PATH` in `tmp_path`!) for `LibrarianManagement` vs `BoothApp`:
   - `LibrarianManagement` produces `DEBIAN/postinst` and `DEBIAN/prerm` (`0755`) allowing `8765/tcp` and `8766/udp` via `ufw` and `firewall-cmd` with `|| true`, and `prerm` guards on `remove|purge` (not `upgrade`).
   - `BoothApp` produces NO `DEBIAN/postinst` or `DEBIAN/prerm`.
2. Run `build_rpm.sh` with a mocked `rpmbuild` in `tmp_path` that captures the generated `.spec` file for `LibrarianManagement` vs `BoothApp`:
   - `LibrarianManagement` `.spec` contains `%post` (`8765/tcp`, `8766/udp`, `|| true`) and `%postun` with `if [ "$1" -eq 0 ]`.
   - `BoothApp` `.spec` contains neither `%post` nor `%postun`.
3. Assert `packaging/installers/windows/installer.iss` gates `PrivilegesRequired=admin` and `netsh` rules (`8765`, `8766`, `profile=private,domain`) behind `#ifdef EnableLanFirewall` while keeping `PrivilegesRequired=lowest` in `#else`, and `.github/workflows/release.yml` passes `/DEnableLanFirewall=1` on `LibrarianManagement` only (not `StudentManagement` or `BoothApp`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_installer_firewall.py -v`
Expected: FAIL (missing `postinst`/`%post`/`EnableLanFirewall`)

- [ ] **Step 3: Implement firewall rules in `build_deb.sh`, `build_rpm.sh`, `installer.iss`, and `release.yml`**

Update the 4 packaging/CI files following the exact guards above. Ensure `DEBIAN/postinst` and `DEBIAN/prerm` are `chmod 755` (required by `dpkg-deb`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_installer_firewall.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packaging/installers/deb/build_deb.sh packaging/installers/rpm/build_rpm.sh packaging/installers/windows/installer.iss .github/workflows/release.yml tests/test_installer_firewall.py
git commit -m "feat(packaging): auto-allow Librarian LAN ports in deb, rpm, and Windows installers"
```

---

### Task 2: Booth Auto-Rediscovery on Boot Order Mismatch & DHCP IP Change

**Files:**
- Modify: `apps/booth_app/adapters/booth_adapter.py`
- Modify: `apps/booth_app/qml/Main.qml`
- Modify: `tests/test_booth_adapter_lan.py`

**Interfaces:**
- Consumes: `discover_librarian`, `save_booth_config`, `BoothLanClient`
- Produces:
  - `BoothAdapter(..., auto_discover: bool = True)`
  - When `self.client` is set and `self.client.health()["ok"]` is `False` and `self.auto_discover` is `True`: calls `_try_rediscover()` (`discover_librarian(timeout=0.4)`). If a server is discovered at `(new_host, new_port)`, swaps `self.client` (preserving existing `token`), re-checks `health()`, and if `ok` (or `self.client.host` was empty), saves updated config to `self.config_path` (when set).
  - `apps/booth_app/qml/Main.qml`: `Timer` (`id: reconnectTimer`, `objectName: "lanReconnectTimer"`, `interval: 5000`, `repeat: true`, `running: connectionStatus.mode === "lan" && !connectionStatus.connected && !lanSettingsDialog.visible`) calling `refreshConnectionStatus(); if (connectionStatus.connected) refreshDbEmpty()`.

- [ ] **Step 1: Write the failing tests in `tests/test_booth_adapter_lan.py`**

Add tests:
1. `test_booth_adapter_auto_rediscovers_when_server_starts_later_or_ip_changes`: creates `BoothAdapter` pointing at a dead port (`127.0.0.1:1`, `token="tok"`, `config_path=cfg_path`, `auto_discover=True`); starts a live `BoothLanServer` on `127.0.0.1:0`; monkeypatches `discover_librarian` in `booth_adapter` to return `{"host": "127.0.0.1", "port": server.port, "version": "1.0"}`; calls `adapter.getConnectionStatus()` -> asserts `connected is True`, `port == server.port`, and `load_booth_config(cfg_path)["port"] == server.port` with `"token": "tok"` preserved.
2. `test_booth_qml_has_lan_reconnect_timer`: loads `apps/booth_app/qml/Main.qml` (or inspects root QML object in `test_booth_adapter_lan.py`) and asserts child `lanReconnectTimer` exists with `interval == 5000`.
3. Ensure existing offline test passes `auto_discover=False` (or mocks `discover_librarian` -> `None`) so tests stay instant and deterministic.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_booth_adapter_lan.py -v`
Expected: FAIL (`TypeError: unexpected keyword argument 'auto_discover'` / missing `lanReconnectTimer`)

- [ ] **Step 3: Implement auto-rediscovery in `booth_adapter.py` and `reconnectTimer` in `Main.qml`**

Keep `apps/booth_app/adapters/booth_adapter.py` `<200` lines and every function `<20` lines (extract small module-level helper if needed). Add `reconnectTimer` to `apps/booth_app/qml/Main.qml` without altering any existing `objectName`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_booth_adapter_lan.py tests/test_ui_booth.py tests/test_qml_loads.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/booth_app/adapters/booth_adapter.py apps/booth_app/qml/Main.qml tests/test_booth_adapter_lan.py
git commit -m "feat(booth): auto-rediscover Librarian server on disconnect and DHCP change"
```

---

### Task 3: Clean Generated App Icons Across Assets, Specs, Installers & Qt Windows

**Files:**
- Create: `assets/icons/boothapp.{svg,png,ico,icns}`
- Create: `assets/icons/librarianmanagement.{svg,png,ico,icns}`
- Create: `assets/icons/studentmanagement.{svg,png,ico,icns}`
- Modify: `apps/common_linux_env.py` (or `core/shared/mock_qt.py`) — add `apply_app_icon(app, icon_stem: str) -> None`
- Modify: `apps/booth_app/main.py`, `apps/librarian_management_app/main.py`, `apps/student_management_app/main.py`
- Modify: `packaging/booth_app.spec`, `packaging/librarian_management.spec`, `packaging/student_management.spec`
- Modify: `packaging/installers/deb/build_deb.sh`, `packaging/installers/rpm/build_rpm.sh`
- Modify: `packaging/installers/windows/installer.iss`, `.github/workflows/release.yml`
- Modify: `tests/test_installer_firewall.py`

**Interfaces:**
- Produces:
  - `assets/icons/<stem>.{svg,png,ico,icns}` for `boothapp`, `librarianmanagement`, `studentmanagement` (256×256 PNG, multi-size PNG-in-ICO 16..256, Apple `icns`).
  - `apply_app_icon(app: QGuiApplication, icon_stem: str) -> None` resolving `assets/icons/<icon_stem>.png` from `sys._MEIPASS` or repo root and calling `app.setWindowIcon(QIcon(path))` if present.

- [ ] **Step 1: Write the failing tests in `tests/test_installer_firewall.py`**

Add tests checking:
1. All 3 icon stems (`boothapp`, `librarianmanagement`, `studentmanagement`) have `.png`, `.ico`, `.icns` files under `assets/icons/`.
2. `build_deb.sh` and `build_rpm.sh` install `/usr/share/icons/hicolor/256x256/apps/$PKG_NAME.png` and write `Icon=$PKG_NAME` in the `.desktop` file when `assets/icons/$PKG_NAME.png` exists.
3. All 3 `.spec` files include `assets/icons/*.png` in `datas`, pass `icon=` to `EXE(...)`, and pass `.icns` to `BUNDLE(...)`.
4. `installer.iss` supports `#ifdef AppIcon` -> `SetupIconFile={#AppIcon}`, and `.github/workflows/release.yml` passes `/DAppIcon=...` for all 3 apps.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_installer_firewall.py -v`
Expected: FAIL (icons and wiring missing)

- [ ] **Step 3: Generate icons and wire into specs, installers, CI, and Qt entrypoints**

Generate 3 distinct clean SVGs and render `.png` (via `PySide6.QtSvg`), `.ico` (multi-size 16/32/48/64/128/256), and `.icns` (via `iconutil`); wire `apply_app_icon`, `.spec` `datas`/`icon=`, `.deb`/`.rpm` `hicolor` + `Icon=`, `installer.iss`, and `release.yml`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_installer_firewall.py tests/test_qml_loads.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add assets/icons apps/ packaging/ .github/workflows/release.yml tests/test_installer_firewall.py
git commit -m "feat(packaging): generate clean app icons and wire across installers and Qt apps"
```

---

### Task 4: Wiki Documentation Sync & Full Suite Verification

**Files:**
- Modify: `wiki/architecture/packaging.md`
- Modify: `wiki/apps/booth-app.md`
- Modify: `wiki/log.md`

**Interfaces:**
- None (documentation + full regression gate).

- [ ] **Step 1: Read `wiki/architecture/packaging.md` and `wiki/apps/booth-app.md`**

Check current sections so updates blend cleanly.

- [ ] **Step 2: Update `wiki/architecture/packaging.md`, `wiki/apps/booth-app.md`, and `wiki/log.md`**

Document:
- Linux `.deb`/`.rpm` and Windows Inno Setup automatic LAN firewall rules (`8765/tcp`, `8766/udp`) scoped strictly to `LibrarianManagement`, plus macOS `.dmg` behavior.
- `BoothApp` automatic 5s reconnect + UDP rediscovery across launch order and DHCP changes.
- Append summary entry to `wiki/log.md`.

- [ ] **Step 3: Run full test suite**

Run: `.venv/bin/pytest tests/ -q`
Expected: 100% PASS (0 failed)

- [ ] **Step 4: Commit**

```bash
git add wiki/architecture/packaging.md wiki/apps/booth-app.md wiki/log.md docs/superpowers/specs/2026-11-25-zero-click-lan-install-design.md docs/superpowers/plans/2026-11-25-zero-click-lan-install.md
git commit -m "docs(wiki): document zero-click LAN installer firewall rules and booth auto-rediscovery"
```
