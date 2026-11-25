# Booth App LAN Remake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remake `apps/booth_app` as a zero-dependency thin LAN client talking to an embedded stdlib HTTP/1.1 API in `apps/librarian_management_app` so separate LAN PCs stay in sync with monthly student `.xlsx` imports.

**Architecture:** `core/network/` provides a thread-safe stdlib `ThreadingHTTPServer` (`BoothLanServer`), a keep-alive `http.client` client (`BoothLanClient`), a UDP broadcast auto-discovery responder/client (`lan_discovery.py`), and JSON config persistence (`booth_config.py`). `librarian_management_app` hosts the server on startup; `booth_app` drops local SQLite and routes `BoothAdapter` calls over LAN while preserving `BoothAdapter(conn)` for existing tests.

**Tech Stack:** Python 3.14 stdlib (`http.server`, `http.client`, `socket`, `threading`, `hmac`, `json`), PySide6 / QML, SQLite, pytest.

**Spec:** `docs/superpowers/specs/2026-11-24-booth-lan-remake-design.md`

## Global Constraints

- Zero new third-party Python dependencies (`requirements.txt` unchanged).
- All SQLite access from LAN server threads must be serialized through a single `threading.Lock`.
- All `/api/*` endpoints require `X-Booth-Token` verified with `hmac.compare_digest`.
- All QML-bound dicts sanitized with `_sanitize_for_qml`; existing Booth QML `objectName`s preserved verbatim.
- Run `.venv/bin/pytest tests/` after changes; commit exclusively to `dev`.

## Review Focus

- **Wrong or missing `X-Booth-Token`:** Server must return HTTP `401` with `{"ok": false, "error": "Unauthorized"}` without touching SQLite.
- **Librarian PC offline or restarted mid-session:** `BoothLanClient` must catch `OSError`/`http.client.HTTPException`, retry once on stale keep-alive socket, and return `{"ok": False, "error": "..."}` without crashing QML.
- **Malformed JSON or missing fields on `POST /api/checkout` or `/api/return`:** Server must return HTTP `400` with `{"ok": false, "error": "..."}` instead of a 500 traceback.
- **Concurrent Booth checkout + Librarian GUI write:** Server `threading.Lock` prevents `sqlite3.ProgrammingError` / recursive cursor corruption across threads.
- **UDP broadcast blocked by school router/firewall:** `discover_librarian()` must time out cleanly and return `None`, falling back to manual IP/port entry in Booth settings.

---

## File Structure

- Create: `core/network/__init__.py` — package exports.
- Create: `core/network/booth_config.py` — load/save `{host, port, token}` JSON config.
- Create: `core/network/lan_server.py` — `BoothLanServer` (`ThreadingHTTPServer` HTTP/1.1 + route table + token auth + SQLite lock).
- Create: `core/network/lan_client.py` — `BoothLanClient` (`http.client.HTTPConnection` keep-alive + 1-retry reconnect).
- Create: `core/network/lan_discovery.py` — `LanDiscoveryResponder` and `discover_librarian()` over UDP broadcast.
- Modify: `apps/booth_app/adapters/booth_adapter.py` — support both `client: BoothLanClient` and legacy `conn: sqlite3.Connection`; add connection/discovery slots.
- Modify: `apps/booth_app/main.py` — boot in LAN client mode using `booth_config.py` + `discover_librarian()`, no local SQLite.
- Modify: `apps/booth_app/qml/Main.qml` — add LAN connection status pill + settings dialog while keeping all existing `objectName`s.
- Modify: `apps/librarian_management_app/adapters/librarian_admin_adapter.py` — add `getLanServerInfo()` slot.
- Modify: `apps/librarian_management_app/main.py` — start/stop `BoothLanServer` + `LanDiscoveryResponder`.
- Test: `tests/test_booth_lan.py` — unit + integration tests covering config, server auth/routes/errors, keep-alive client reconnect, UDP discovery, and `BoothAdapter(client=...)`.

---

### Task 1: Booth LAN Config (`core/network/booth_config.py`)

**Files:**
- Create: `core/network/__init__.py`
- Create: `core/network/booth_config.py`
- Test: `tests/test_booth_lan.py`

**Interfaces:**
- Produces:
  - `DEFAULT_LAN_PORT = 8765`
  - `DEFAULT_DISCOVERY_PORT = 8766`
  - `DEFAULT_BOOTH_TOKEN = "123456"`
  - `load_booth_config(path: str) -> dict[str, object]` returning `{"host": str, "port": int, "token": str}`
  - `save_booth_config(path: str, config: dict[str, object]) -> None`

- [ ] **Step 1: Write the failing test**

```python
from core.network.booth_config import (
    DEFAULT_BOOTH_TOKEN,
    DEFAULT_LAN_PORT,
    load_booth_config,
    save_booth_config,
)

def test_booth_config_defaults_and_roundtrip(tmp_path):
    cfg_path = str(tmp_path / "booth_config.json")
    assert load_booth_config(cfg_path) == {
        "host": "",
        "port": DEFAULT_LAN_PORT,
        "token": DEFAULT_BOOTH_TOKEN,
    }
    save_booth_config(cfg_path, {"host": "192.168.1.50", "port": 9000, "token": "secret"})
    assert load_booth_config(cfg_path) == {
        "host": "192.168.1.50",
        "port": 9000,
        "token": "secret",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_booth_lan.py::test_booth_config_defaults_and_roundtrip -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.network'`

- [ ] **Step 3: Implement `core/network/__init__.py` and `core/network/booth_config.py`**

Create `core/network/__init__.py` (empty or re-exports) and `core/network/booth_config.py` with `load_booth_config` (gracefully returning defaults on missing or corrupt JSON) and `save_booth_config` (creating parent dirs, writing UTF-8 JSON).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_booth_lan.py::test_booth_config_defaults_and_roundtrip -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/network/__init__.py core/network/booth_config.py tests/test_booth_lan.py
git commit -m "feat(network): add booth LAN config persistence"
```

---

### Task 2: Embedded LAN HTTP/1.1 Server (`core/network/lan_server.py`)

**Files:**
- Create: `core/network/lan_server.py`
- Test: `tests/test_booth_lan.py`

**Interfaces:**
- Consumes: `StudentService`, `CatalogService`, `LoanService`, `_sanitize_for_qml`, `APP_VERSION`
- Produces:
  - `BoothLanServer(conn: sqlite3.Connection, host: str = "0.0.0.0", port: int = 8765, token: str = "123456", db_lock: Optional[threading.Lock] = None)`
  - Methods: `start() -> None`, `stop() -> None`, `port: int` (property returning bound port, supports `port=0` in tests), `get_lan_ip() -> str`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_booth_lan.py`:
- `test_lan_server_rejects_missing_or_wrong_token`: `GET /api/health` without token or wrong token returns HTTP `401` and `{"ok": False, "error": "Unauthorized"}`.
- `test_lan_server_health_students_copy_checkout_return`: starts `BoothLanServer(conn, host="127.0.0.1", port=0, token="tok")` against an in-memory SQLite DB (`check_same_thread=False`) seeded with 1 student + 1 book copy, verifies `GET /api/health`, `GET /api/students?q=...`, `GET /api/copies/<barcode>`, `POST /api/checkout`, and `POST /api/return` (by barcode).
- `test_lan_server_bad_json_returns_400`: `POST /api/checkout` with invalid JSON returns HTTP `400` and `{"ok": False, ...}`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_booth_lan.py -k "lan_server" -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `core/network/lan_server.py`**

Use `http.server.ThreadingHTTPServer` with `protocol_version = "HTTP/1.1"` and `Content-Length` on every response (required for keep-alive). Dispatch via a clean route table (`GET /api/health`, `GET /api/students`, `GET /api/copies/<barcode>`, `POST /api/checkout`, `POST /api/return`), each handler <=20 lines, acquiring `self.db_lock` around SQLite calls. Verify `X-Booth-Token` with `hmac.compare_digest`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_booth_lan.py -k "lan_server" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/network/lan_server.py tests/test_booth_lan.py
git commit -m "feat(network): add stdlib HTTP/1.1 BoothLanServer"
```

---

### Task 3: Keep-Alive LAN Client (`core/network/lan_client.py`)

**Files:**
- Create: `core/network/lan_client.py`
- Test: `tests/test_booth_lan.py`

**Interfaces:**
- Consumes: `BoothLanServer` HTTP contract from Task 2
- Produces:
  - `BoothLanClient(host: str, port: int = 8765, token: str = "123456", timeout: float = 3.0)`
  - Methods:
    - `health() -> dict`
    - `is_database_empty() -> bool`
    - `search_students(query: str) -> list[dict]`
    - `get_copy_by_barcode(barcode: str) -> dict`
    - `checkout(student_id: int, barcode: str) -> dict`
    - `return_book(loan_id: int) -> dict`
    - `return_by_barcode(barcode: str) -> dict`
    - `close() -> None`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_booth_lan.py`:
- `test_lan_client_keep_alive_and_operations`: runs `health()`, `search_students()`, `get_copy_by_barcode()`, `checkout()`, `return_by_barcode()` against live `BoothLanServer` on `127.0.0.1:0`.
- `test_lan_client_handles_offline_server_gracefully`: pointing `BoothLanClient` at an unused port returns `{"ok": False, "error": ...}` (never raises) and `is_database_empty()` returns `False` when offline (so UI shows offline banner, not empty-DB banner).
- `test_lan_client_reconnects_after_server_restart`: stops server, restarts on same port, verifies next `health()` succeeds via 1-retry reconnect.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_booth_lan.py -k "lan_client" -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `core/network/lan_client.py`**

Wrap `http.client.HTTPConnection` under a `threading.Lock` with a single `_request(method, path, body=None)` helper that sends `X-Booth-Token` + `Connection: keep-alive`, retries once on `http.client.RemoteDisconnected` / `BrokenPipeError` / `ConnectionResetError`, and catches all `OSError`/`HTTPException`/`JSONDecodeError` returning `{"ok": False, "error": "..."}`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_booth_lan.py -k "lan_client" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/network/lan_client.py tests/test_booth_lan.py
git commit -m "feat(network): add keep-alive BoothLanClient"
```

---

### Task 4: UDP LAN Auto-Discovery (`core/network/lan_discovery.py`)

**Files:**
- Create: `core/network/lan_discovery.py`
- Test: `tests/test_booth_lan.py`

**Interfaces:**
- Produces:
  - `DISCOVERY_MAGIC = b"SMTE_DISCOVER_LIBRARIAN"`
  - `LanDiscoveryResponder(http_port: int, discovery_port: int = 8766, bind_host: str = "")` with `start() -> None`, `stop() -> None`, `discovery_port: int`
  - `discover_librarian(discovery_port: int = 8766, timeout: float = 1.5, broadcast_addr: str = "<broadcast>") -> Optional[dict]` returning `{"host": str, "port": int, "version": str}` or `None`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_booth_lan.py`:
- `test_udp_discovery_finds_responder`: starts `LanDiscoveryResponder(http_port=8765, discovery_port=0, bind_host="127.0.0.1")`, calls `discover_librarian(discovery_port=responder.discovery_port, timeout=1.0, broadcast_addr="127.0.0.1")`, asserts `result["port"] == 8765` and `result["host"] == "127.0.0.1"`.
- `test_udp_discovery_timeout_returns_none`: calls `discover_librarian` on an unused port with `timeout=0.1`, asserts `result is None`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_booth_lan.py -k "udp_discovery" -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `core/network/lan_discovery.py`**

Implement `LanDiscoveryResponder` (daemon thread with 0.2s socket timeout checking `self._stop_event`) and `discover_librarian()` using stdlib `socket` (`SO_BROADCAST`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_booth_lan.py -k "udp_discovery" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/network/lan_discovery.py tests/test_booth_lan.py
git commit -m "feat(network): add stdlib UDP LAN discovery"
```

---

### Task 5: Wire `BoothAdapter` & `apps/booth_app` to LAN Client

**Files:**
- Modify: `apps/booth_app/adapters/booth_adapter.py`
- Modify: `apps/booth_app/main.py`
- Modify: `apps/booth_app/qml/Main.qml`
- Test: `tests/test_booth_lan.py`

**Interfaces:**
- Consumes: `BoothLanClient`, `load_booth_config`, `save_booth_config`, `discover_librarian`
- Produces:
  - `BoothAdapter(conn: Optional[sqlite3.Connection] = None, client: Optional[BoothLanClient] = None, config_path: Optional[str] = None)`
  - New `@Slot`s on `BoothAdapter`:
    - `getConnectionStatus() -> str` (JSON `{"connected": bool, "host": str, "port": int, "mode": "lan"|"local", "error": str}`)
    - `configureConnection(host: str, port: int, token: str) -> str` (saves config, swaps `BoothLanClient`, returns `getConnectionStatus()`)
    - `discoverServer() -> str` (JSON `{"ok": bool, "host": str, "port": int}`)

- [ ] **Step 1: Write the failing test**

Add `test_booth_adapter_lan_mode` to `tests/test_booth_lan.py` verifying `BoothAdapter(client=BoothLanClient(...), config_path=...)` works end-to-end for `getConnectionStatus`, `searchStudents`, `getCopyByBarcode`, `checkout`, `returnByBarcode`, and `configureConnection`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_booth_lan.py::test_booth_adapter_lan_mode -v`
Expected: FAIL with `TypeError` (unexpected keyword argument `client`)

- [ ] **Step 3: Update `booth_adapter.py`, `apps/booth_app/main.py`, and `apps/booth_app/qml/Main.qml`**

- In `booth_adapter.py`: keep `conn` path intact for existing tests; delegate to `self.client` when in LAN mode; add `getConnectionStatus`, `configureConnection`, `discoverServer`.
- In `apps/booth_app/main.py`: remove local SQLite opening (`get_connection`/`apply_migrations`); load `booth_config.json` (with `BOOTH_SERVER_HOST`/`PORT`/`TOKEN` env overrides); auto-discover if host is empty; pass `BoothLanClient` to `BoothAdapter`.
- In `apps/booth_app/qml/Main.qml`: add top connection status bar (`lanStatusBanner` + "ตั้งค่าเซิร์ฟเวอร์" button) and a clean connection settings `Dialog` (host, port, token, "ค้นหาอัตโนมัติ" button) using responsive `implicitHeight` and left-aligned inputs; preserve all existing `objectName`s.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_booth_lan.py tests/test_ui_booth.py tests/test_adapters.py tests/test_qml_loads.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/booth_app/adapters/booth_adapter.py apps/booth_app/main.py apps/booth_app/qml/Main.qml tests/test_booth_lan.py
git commit -m "feat(booth): switch booth_app to thin LAN client with connection settings"
```

---

### Task 6: Wire Embedded LAN Server into `apps/librarian_management_app` + Wiki Sync

**Files:**
- Modify: `apps/librarian_management_app/adapters/librarian_admin_adapter.py`
- Modify: `apps/librarian_management_app/main.py`
- Modify: `wiki/apps/booth-app.md`
- Modify: `wiki/architecture/overview.md`
- Modify: `wiki/log.md`
- Test: `tests/test_booth_lan.py`

**Interfaces:**
- Consumes: `BoothLanServer`, `LanDiscoveryResponder`
- Produces: `LibrarianAdminAdapter.getLanServerInfo() -> str` (JSON `{"running": bool, "ip": str, "port": int, "token": str}`)

- [ ] **Step 1: Write the failing test**

Add `test_librarian_adapter_reports_lan_server_info` to `tests/test_booth_lan.py` verifying `LibrarianAdminAdapter(conn, lan_server=server).getLanServerInfo()` returns valid JSON with `running: True`, `ip`, `port`, and `token`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_booth_lan.py::test_librarian_adapter_reports_lan_server_info -v`
Expected: FAIL with `TypeError` or `AttributeError`

- [ ] **Step 3: Update `librarian_admin_adapter.py`, `apps/librarian_management_app/main.py`, and wiki docs**

- In `librarian_admin_adapter.py`: accept optional `lan_server=None` and add `@Slot(result=str) def getLanServerInfo(self) -> str`.
- In `apps/librarian_management_app/main.py`: start `BoothLanServer` + `LanDiscoveryResponder` (unless `--cli` or `LIBRARIAN_LAN_DISABLED=1`), pass `lan_server` to `LibrarianAdminAdapter`, and call `stop()` cleanly before `conn.close()`.
- Update `wiki/apps/booth-app.md`, `wiki/architecture/overview.md`, and append to `wiki/log.md`.

- [ ] **Step 4: Run full test suite**

Run: `.venv/bin/pytest tests/`
Expected: 100% PASS

- [ ] **Step 5: Commit**

```bash
git add apps/librarian_management_app/adapters/librarian_admin_adapter.py apps/librarian_management_app/main.py wiki/apps/booth-app.md wiki/architecture/overview.md wiki/log.md tests/test_booth_lan.py
git commit -m "feat(librarian): host embedded Booth LAN server and update wiki"
```
