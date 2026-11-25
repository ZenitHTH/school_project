# Zero-Click LAN Install & Auto-Rediscovery — Design Spec

**Date:** 2026-11-25
**Status:** Approved

## 1. Intent & Why

School staff must be able to download the installer, install it, and launch `LibrarianManagement` and `BoothApp` on two LAN PCs in any order with **zero manual firewall commands, zero launch firewall popups on Windows/Linux, and zero manual IP configuration** — even after router DHCP IP changes.

## 2. Goals, Non-Goals, Anti-Goals

- **Goals:**
  - **Linux (`.deb` / `.rpm`):** `librarianmanagement` package `postinst`/`%post` automatically allows inbound `8765/tcp` and `8766/udp` on `ufw` or `firewall-cmd` when installed/active, and removes those rules in `prerm`/`%postun` on package removal (`StudentManagement` and `BoothApp` packages do not touch firewall rules).
  - **Windows (`Setup.exe`):** `LibrarianManagement` Inno Setup installer runs elevated (`PrivilegesRequired=admin` via `/DEnableLanFirewall=1` in `.github/workflows/release.yml`) and registers `netsh advfirewall` inbound allow rules for `8765/tcp` and `8766/udp` (Private/Domain profiles) during install, removing them on uninstall (`StudentManagement` and `BoothApp` stay `PrivilegesRequired=lowest`).
  - **macOS (`.dmg`):** Keep `.dmg` drag-to-Applications without unsigned `.pkg` Gatekeeper friction (macOS Application Firewall is off by default and auto-prompts once if enabled).
  - **Zero-click boot order & DHCP recovery (`BoothApp`):** When `BoothAdapter` is in LAN mode and `health()` fails, automatically probe `discover_librarian(timeout=0.4)`; if found and healthy, swap client + persist `{host, port}` to `booth_config.json`. Add a 5s QML `Timer` in `apps/booth_app/qml/Main.qml` that runs **only while disconnected** (`mode === "lan" && !connected`) so launching Librarian after Booth connects automatically within 5 seconds.
- **Non-Goals:**
  - Modifying runtime OS firewall settings from inside unprivileged Python code.
  - Converting macOS `.dmg` into an unsigned `.pkg`.
  - Opening inbound firewall ports on `BoothApp` or `StudentManagement` PCs.
- **Anti-Goals:**
  - Failing `.deb`/`.rpm`/Windows install when `ufw`, `firewall-cmd`, or Windows Firewall service is absent or disabled (`|| true` / non-fatal exit codes required).

## 3. Approaches Considered

1. **Installer-Time Firewall Rules + Disconnected-Only Auto-Rediscovery (Selected)**
   - Uses native package manager root/admin hooks (`DEBIAN/postinst`, RPM `%post`, Inno Setup `[Run]`/`[UninstallRun]`) only for `LibrarianManagement`, paired with a 0.4s UDP rediscovery fallback + 5s disconnected QML timer in `BoothApp`.
2. **Runtime `pkexec`/`sudo`/UAC Elevation Inside Python App**
   - Rejected: prompts users on launch, fragile across Linux desktop environments, and violates least-privilege runtime boundaries.

## 4. Architecture & File Touchpoints

- `packaging/installers/deb/build_deb.sh`: emit `DEBIAN/postinst` and `DEBIAN/prerm` (`chmod 755`) only when `PKG_NAME == "librarianmanagement"`.
- `packaging/installers/rpm/build_rpm.sh`: emit `%post` and `%postun` in the generated `.spec` only when `PKG_NAME == "librarianmanagement"`.
- `packaging/installers/windows/installer.iss` & `.github/workflows/release.yml`: conditional `#ifdef EnableLanFirewall` setting `PrivilegesRequired=admin` and adding `[Run]` / `[UninstallRun]` `netsh advfirewall firewall` rules (`SMTE Librarian LAN HTTP` TCP `8765`, `SMTE Librarian LAN Discovery` UDP `8766`, `profile=private,domain`); pass `/DEnableLanFirewall=1` only for `LibrarianManagement` in `release.yml`.
- `apps/booth_app/adapters/booth_adapter.py` & `apps/booth_app/qml/Main.qml`: add `auto_discover: bool = True` to `BoothAdapter`; on failed `health()` in `getConnectionStatus()`, attempt `discover_librarian(timeout=0.4)` and update client/config if a server responds; add `reconnectTimer` (`interval: 5000`, active only when `mode === "lan" && !connected`) in `Main.qml`.
- `wiki/architecture/packaging.md`, `wiki/apps/booth-app.md`, `wiki/log.md`: document installer firewall automation and Booth auto-rediscovery.
- `assets/icons/{booth_app,librarian_management,student_management}.{svg,png,ico,icns}`: distinct clean vector-rendered app icons bundled into PyInstaller (`EXE` + `BUNDLE` + `assets/icons/*.png`), Linux `.deb`/`.rpm` (`hicolor/256x256/apps` + `.desktop` `Icon=`), Windows `installer.iss` (`SetupIconFile`), and runtime `QGuiApplication.setWindowIcon()`.
