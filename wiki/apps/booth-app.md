# Self-Service Kiosk Booth App Architecture (`apps/booth_app/`)

## 1. Overview
The Booth App is a lightweight, high-speed, self-service kiosk intended for library entrance stations where students checkout and return books by scanning their student ID card and book barcodes.

---

## 2. Directory Structure
```
apps/booth_app/
├── main.py
├── adapters/
│   └── booth_adapter.py
└── qml/
    └── Main.qml
```

---

## 3. UI & Interaction Flow

```
[ Step 1: Scan Student ID Card ]
             │
             ▼
[ Validate Active Status & Fines ] ──> If Blocked / Disposed ──> [ Show Red Warning Toast ]
             │
             ▼ (Success: Show Student Name & Active Loans)
[ Step 2: Scan Book Barcode ]
             │
             ├──────────────────────────┐
             ▼                          ▼
     [ Click Checkout ]          [ Click Return ]
             │                          │
             ▼                          ▼
    [ Record Loan & Due Date ]   [ Mark Returned & Check Fine ]
```

---

## 4. Key ObjectNames (for Testing & Automation)
- `emptyDbWarningBanner`: Warning displayed if database has zero students or books.
- `studentIdInput`: `StyledSearchField` for barcode scanner or keypad entry.
- `btnIdentify`: Button to lookup student.
- `studentStatusMsg`: Status label displaying student name, grade/room, or warning messages.
- `bookBarcodeInput`: `StyledSearchField` for book barcode scans.
- `btnCheckout`: Triggers loan checkout.
- `btnReturn`: Triggers book return.
- `feedbackBanner`: `ActionFeedbackBanner` displaying operation result.
- `btnLogout`: Resets the kiosk state for the next student.
