# Self-Service Kiosk Booth App Architecture (`apps/booth_app/`)

## 1. Overview
The Booth App is a lightweight, high-speed, self-service kiosk intended for library entrance stations where students checkout and return books by scanning their student ID card and book barcodes.

In production deployment, `apps/booth_app` runs as a **thin LAN client** with no local `library.sqlite` file:
- Talks to the embedded `BoothLanServer` hosted by `apps/librarian_management_app` over stdlib **HTTP/1.1 keep-alive** (`core/network/lan_client.py`, default port `8765`, `X-Booth-Token` header).
- Discovers the Librarian PC automatically via **UDP broadcast** (`core/network/lan_discovery.py`, port `8766`, magic `SMTE_DISCOVER_LIBRARIAN`), with manual host/port/token fallback persisted to `SMTE-Booth/booth_config.json` (`core/network/booth_config.py`) and optional env overrides (`BOOTH_SERVER_HOST`, `BOOTH_SERVER_PORT`, `BOOTH_SERVER_TOKEN`).
- **Auto-Rediscovery Across Boot Order & DHCP Changes**: `BoothAdapter(..., auto_discover=True)` automatically probes `discover_librarian(timeout=0.4)` inside `getConnectionStatus()` whenever the saved Librarian host is unreachable; if a healthy server responds, it swaps the client and persists the updated `{host, port}` (preserving `token`) to `booth_config.json`. In `Main.qml`, `lanReconnectTimer` (`interval: 5000`) polls `refreshConnectionStatus()` **only** while `mode === "lan" && !connected && !lanSettingsDialog.visible`.
- Monthly student `.xlsx` imports and catalog updates in `librarian_management_app` are immediately live on the Booth kiosk without file copying or sync.
- `BoothAdapter` preserves its legacy `BoothAdapter(conn)` mode alongside `BoothAdapter(client=BoothLanClient(...), config_path=...)` so unit and UI tests continue to run offline (with `auto_discover=False` or mocked discovery for deterministic tests).

---

## 2. Directory Structure
```
apps/booth_app/
├── main.py
├── adapters/
│   └── booth_adapter.py     # Supports LAN client mode, legacy SQLite conn mode & SettingsAdapterMixin
└── qml/
    ├── BookSearchView.qml    # Self-service book search, category filter, shelf locator & availability
    ├── LanSettingsDialog.qml # Modal dialog for host/port/token & auto-discover
    └── Main.qml              # StackLayout (kiosk home, SettingsView, BookSearchView), LAN status bar & reconnect timer
```

---

## 3. UI & Interaction Flow

```
[ Startup: Load booth_config.json -> Auto-discover UDP if host empty -> BoothLanClient ]
             │
             ├──> [ ⚙️ ตั้งค่าระบบ (btnOpenBoothSettings) -> kioskStack[1]: SettingsView + SettingsLanClientCard ]
             ├──> [ 🔍 ค้นหาหนังสือ (btnOpenBookSearch) -> kioskStack[2]: BookSearchView (GET /api/categories, /api/books) ]
             │
             ▼ (kioskStack[0]: Kiosk Home)
[ Step 1: Scan Student ID Card ]
             │
             ▼
[ Validate Active Status & Fines (via LAN /api/students) ] ──> If Blocked / Disposed ──> [ Show Red Warning Toast ]
             │
             ▼ (Success: Show Student Name & Active Loans)
[ Step 2: Scan Book Barcode ]
             │
             ├──────────────────────────┐
             ▼                          ▼
     [ Click Checkout ]          [ Click Return ]
             │                          │
             ▼                          ▼
   [ POST /api/checkout ]      [ POST /api/return ]
```

---

## 4. Key Adapter Slots & ObjectNames (for Testing & Automation)
- **LAN Slots (`BoothAdapter`)**: `getConnectionStatus()`, `configureConnection(host, port, token)`, `discoverServer()`.
- **Book Search Slots (`BoothAdapter`)**: `listCategories()` (JSON array of sorted `{category_id, name}` via `GET /api/categories` or local `CatalogService.list_categories()`), `searchBooks(query, category_id=0, limit=50, offset=0)` (JSON array of sanitized book records including `shelf_location`, `category_name`, `available_copies`, `total_copies` via `GET /api/books` or local `CatalogService.search()`; `category_id <= 0` searches all categories and `BoothLanServer` safely clamps/parses invalid query params).
- **Settings Slots (`BoothAdapter` via `SettingsAdapterMixin`)**: `loadSettings()`, `saveSettings(fontFamily, fontSize, uiScale)`, `resetSettings()`, `setAppFont(family, pixelSize)` backed by `SettingsService`.
- **Librarian Host Slot (`LibrarianAdminAdapter`)**: `getLanServerInfo()` returning `{"running", "ip", "port", "token"}`.
- `kioskStack`: Root `StackLayout` switching between Kiosk Home (`currentIndex: 0`), Booth System Settings (`currentIndex: 1`), and Self-Service Book Search (`currentIndex: 2`).
- `lanStatusBanner`: Top status banner showing LAN connection state (`connected`, `host`, `port`), Book Search trigger (`btnOpenBookSearch`), modal settings trigger (`btnLanSettings`), and System Settings trigger (`btnOpenBoothSettings`).
- `boothSettingsView` (`SettingsView` with `showLanClientCard: true`, `targetWindow: boothWindow`): Embedded visual settings and Connect/Switch Server card (`SettingsLanClientCard`), paired with `btnBackToKiosk` to return to `kioskStack` index `0` and refresh connection status + DB emptiness.
- `boothBookSearchView` (`BookSearchView.qml`): Self-service book search and shelf locator screen at `kioskStack` index `2`, featuring `btnBackFromBookSearch`, `boothBookSearchInput` (`StyledSearchField`), `boothCategoryFilter` (`StyledComboBox` backed by `boothCategoryFilterModel` prepending `"ทุกหมวดหมู่"`), `btnBoothSearchBooks`, `boothBookSearchStatus`, and `boothBookResultsList` (backed by `bookResultsModel` with dynamic card heights, `Typography.applyToItem`, fallback labels `"ไม่ระบุหมวดหมู่"` / `"ไม่ระบุชั้นวาง"`, and available vs. borrowed-out copy badges).
- `lanReconnectTimer`: Background `Timer` (`interval: 5000`) polling `refreshConnectionStatus()` while `mode === "lan" && !connected && !lanSettingsDialog.visible`.
- `lanSettingsDialog` (`LanSettingsDialog.qml`): Modal connection settings dialog (`lanHostInput`, `lanPortInput`, `lanTokenInput`, `btnAutoDiscover`, `discoverStatusLabel`).
- `emptyDbWarningBanner`: Warning displayed if database has zero students or books.
- `studentIdInput`: `StyledSearchField` for barcode scanner or keypad entry.
- `btnIdentify`: Button to lookup student.
- `studentStatusMsg`: Status label displaying student name, grade/room, or warning messages.
- `bookBarcodeInput`: `StyledSearchField` for book barcode scans.
- `btnCheckout`: Triggers loan checkout.
- `btnReturn`: Triggers book return.
- `feedbackBanner`: `ActionFeedbackBanner` displaying operation result.
- `btnLogout`: Resets the kiosk state for the next student.
