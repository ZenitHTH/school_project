# Self-Service Kiosk Booth App Architecture (`apps/booth_app/`)

## 1. Overview
The Booth App is a lightweight, high-speed, self-service kiosk intended for library entrance stations where students checkout and return books by scanning their student ID card and book barcodes.

In production deployment, `apps/booth_app` runs as a **thin LAN client** with no local `library.sqlite` file:
- Talks to the embedded `BoothLanServer` hosted by `apps/librarian_management_app` over stdlib **HTTP/1.1 keep-alive** (`core/network/lan_client.py`, default port `8765`, `X-Booth-Token` header).
- Discovers the Librarian PC automatically via **UDP broadcast** (`core/network/lan_discovery.py`, port `8766`, magic `SMTE_DISCOVER_LIBRARIAN`), with manual host/port/token fallback persisted to `SMTE-Booth/booth_config.json` (`core/network/booth_config.py`) and optional env overrides (`BOOTH_SERVER_HOST`, `BOOTH_SERVER_PORT`, `BOOTH_SERVER_TOKEN`).
- Monthly student `.xlsx` imports and catalog updates in `librarian_management_app` are immediately live on the Booth kiosk without file copying or sync.
- `BoothAdapter` preserves its legacy `BoothAdapter(conn)` mode alongside `BoothAdapter(client=BoothLanClient(...), config_path=...)` so unit and UI tests continue to run offline.

---

## 2. Directory Structure
```
apps/booth_app/
├── main.py
├── adapters/
│   └── booth_adapter.py     # Supports LAN client mode & legacy SQLite conn mode
└── qml/
    └── Main.qml             # Kiosk UI + LAN status bar & connection settings dialog
```

---

## 3. UI & Interaction Flow

```
[ Startup: Load booth_config.json -> Auto-discover UDP if host empty -> BoothLanClient ]
             │
             ▼
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
- **Librarian Host Slot (`LibrarianAdminAdapter`)**: `getLanServerInfo()` returning `{"running", "ip", "port", "token"}`.
- `lanStatusBanner`: Top status banner showing LAN connection state (`connected`, `host`, `port`) and settings trigger.
- `emptyDbWarningBanner`: Warning displayed if database has zero students or books.
- `studentIdInput`: `StyledSearchField` for barcode scanner or keypad entry.
- `btnIdentify`: Button to lookup student.
- `studentStatusMsg`: Status label displaying student name, grade/room, or warning messages.
- `bookBarcodeInput`: `StyledSearchField` for book barcode scans.
- `btnCheckout`: Triggers loan checkout.
- `btnReturn`: Triggers book return.
- `feedbackBanner`: `ActionFeedbackBanner` displaying operation result.
- `btnLogout`: Resets the kiosk state for the next student.
