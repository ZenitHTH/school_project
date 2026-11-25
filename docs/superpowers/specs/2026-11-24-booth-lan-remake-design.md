# Booth App LAN Remake — Design Spec

**Date:** 2026-11-24
**Status:** Approved

## 1. Intent & Why

`apps/booth_app` currently opens a local `library.sqlite` file assuming it runs on the same PC as `apps/librarian_management_app`. In real school deployment:
- `booth_app` and `librarian_management_app` run on **different PCs on the same LAN**.
- The student `.xlsx` roster changes **every month** and is imported into `librarian_management_app`.
- Booth PCs are **10+ year old Linux PCs**, so low RAM, fast cold start, and zero dependency bloat matter.

## 2. Goals, Non-Goals, Anti-Goals

- **Goals:**
  - `booth_app` operates as a thin LAN client talking to `librarian_management_app` over HTTP/1.1 keep-alive.
  - Monthly student `.xlsx` imports in `librarian_management_app` are immediately live on `booth_app` with zero manual sync.
  - Checkouts and returns from `booth_app` write directly to `librarian_management_app`'s `library.sqlite` under a single thread-safe write lock.
  - Automatic LAN discovery via UDP broadcast, with manual IP/port/token fallback saved in local JSON config.
  - Zero new third-party Python dependencies (100% Python stdlib).
  - Backward compatibility for existing unit/UI tests that instantiate `BoothAdapter(conn)`.
- **Non-Goals:**
  - Offline checkout queue or local SQLite cache on the Booth PC.
  - Internet/cloud exposure or TLS (LAN-only, shared token header).
  - Changing the student `.xlsx` importer or `student_management_app`.
  - Barcode plain printout improvements (tracked as a separate spec/plan).
- **Anti-Goals:**
  - Sharing `library.sqlite` directly over SMB/NFS (risks SQLite locking errors and DB corruption).
  - Adding heavy web frameworks (`fastapi`, `uvicorn`, `pydantic`, `httpx`, `zeroconf`) that bloat PyInstaller bundles and RAM on 10+ year old Linux PCs.

## 3. Approaches Considered

1. **Approach A — Embedded Stdlib LAN HTTP API in Librarian App + Thin LAN Client in Booth App (Selected)**
   - Python stdlib `ThreadingHTTPServer` (HTTP/1.1) + `http.client` keep-alive + stdlib UDP broadcast discovery.
   - Benchmarked at 26.0 MB RSS, 0.11ms p50 keep-alive JSON latency, 0 new dependencies.
   - Trade-off: Librarian App must be open while Booth is in use (Booth displays an offline/reconnecting banner when unreachable).
2. **Approach B — Standalone Headless Server Process**
   - Keeps Booth online when Librarian GUI is closed, but adds an extra binary/service to package, install, and manage across Windows/macOS/Linux. Rejected for operational complexity.
3. **Approach C — Direct SQLite over SMB/Shared Folder**
   - Rejected due to SQLite concurrent-write corruption risk over network filesystems.

## 4. Architecture & Interfaces

### 4.1 Shared LAN Protocol (`core/network/`)
- `core/network/lan_server.py`: `BoothLanServer` wrapping `ThreadingHTTPServer` (`protocol_version = "HTTP/1.1"`), bound to `0.0.0.0:<port>` (default `8765`), guarding all SQLite access with a `threading.Lock`, and authenticating every `/api/*` request with `X-Booth-Token` header (constant-time `hmac.compare_digest`).
  - `GET /api/health` -> `{"ok": true, "empty": bool, "version": str}`
  - `GET /api/students?q=<query>` -> `{"ok": true, "data": [...]}`
  - `GET /api/copies/<barcode>` -> `{"ok": bool, "data": {...}, "error": str|null}`
  - `POST /api/checkout` (`{"student_id": int, "barcode": str}`) -> `{"ok": bool, "data": {...}, "error": str|null}`
  - `POST /api/return` (`{"loan_id": int}` or `{"barcode": str}`) -> `{"ok": bool, "data": {...}, "error": str|null}`
- `core/network/lan_discovery.py`:
  - `LanDiscoveryResponder`: background UDP listener on port `8766` replying to `SMTE_DISCOVER_LIBRARIAN` with JSON `{"service": "smte-librarian", "port": <http_port>, "version": str}`.
  - `discover_librarian(timeout=1.5) -> Optional[dict]`: sends UDP broadcast and returns `{"host": ip, "port": port}` or `None`.
- `core/network/lan_client.py`: `BoothLanClient(host, port, token, timeout=3.0)` using `http.client.HTTPConnection` with HTTP/1.1 keep-alive and automatic single retry on stale/dropped socket. Returns structured error dicts (`{"ok": False, "error": "..."}`) on network/auth failure — never raises unhandled exceptions.
- `core/network/booth_config.py`: `load_booth_config(path)` / `save_booth_config(path, cfg)` reading/writing `{host, port, token}` JSON in `SMTE-Booth/booth_config.json` (via `data.paths.get_default_db_path` parent dir).

### 4.2 Librarian Management App Integration
- `apps/librarian_management_app/main.py`: starts `BoothLanServer` + `LanDiscoveryResponder` on launch (unless `--cli` or `LIBRARIAN_LAN_DISABLED=1`), shuts both down cleanly on exit.
- `apps/librarian_management_app/adapters/librarian_admin_adapter.py`: exposes `getLanServerInfo() -> str` (JSON with `running`, `ip`, `port`, `token`) so the Librarian UI can display connection info for staff.

### 4.3 Booth App Integration
- `apps/booth_app/main.py`: loads `booth_config.json` (with env overrides `BOOTH_SERVER_HOST`, `BOOTH_SERVER_PORT`, `BOOTH_SERVER_TOKEN`); if no host is configured, attempts `discover_librarian()`; instantiates `BoothAdapter(client=BoothLanClient(...))` with zero local SQLite DB.
- `apps/booth_app/adapters/booth_adapter.py`: accepts either `conn: sqlite3.Connection` (legacy/test mode) or `client: BoothLanClient` (LAN mode). Adds slots `getConnectionStatus() -> str`, `configureConnection(host, port, token) -> str`, `discoverServer() -> str`.
- `apps/booth_app/qml/Main.qml`: preserves all existing `objectName`s (`emptyDbWarningBanner`, `studentIdInput`, `btnIdentify`, `studentStatusMsg`, `bookBarcodeInput`, `btnCheckout`, `btnReturn`, `feedbackBanner`, `btnLogout`), adds a connection status indicator + settings dialog for LAN IP/port/token and "Auto-Discover" button.

## 5. Constraints
- Python 3.14, PySide6, SQLite, zero new third-party dependencies.
- All QML data sanitized via `_sanitize_for_qml`; responsive QML heights (no hardcoded heights on new controls).
- 100% pytest pass rate on `.venv/bin/pytest tests/`.
- Commit exclusively to `dev` branch.
