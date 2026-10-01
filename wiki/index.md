# LLM Wiki Index — School Project (SMTE)

Welcome to the internal, persistent knowledge base for the **School Project (SMTE)**.
This wiki synthesizes all architecture, database schemas, core business logic, UI adapters, and shared components into concise, interlinked pages. Consult these pages first before scanning hundreds of raw source code lines.

---

## 🏛️ Architecture & System Overview
- [[wiki/architecture/overview|System Architecture & Topology]] — High-level layout of Student Management, Librarian Management, and Kiosk Booth apps with air-gapped sync.
- [[wiki/architecture/result-type|Rust-Style Result Type]] — Generic `Result[T, E]` return system with warnings, unwrap combinators, and backward-compatible serialization.
- [[wiki/architecture/packaging|Cross-Platform Packaging & GitHub Actions]] — PyInstaller specs, frozen `sys._MEIPASS` asset resolution, and multi-OS desktop build configs.

---

## 🗄️ Database & Data Layer
- [[wiki/database/schema|SQLite Schema & Migrations]] — Table schemas for `students`, `enrollments`, `books`, `book_copies`, `loans`, `fines`, and `sync_state`.
- [[wiki/database/encryption-and-security|Encryption & Security]] — SQLCipher / PRAGMA key PIN hashing, PBKDF2 salts, and local storage safety.
- [[wiki/database/student-search-fts5|FTS5 Trigram Search Algorithm]] — Trigram tokenization on full names, ID suffix matching, and national ID exclusion rules.

---

## ⚙️ Services & Business Logic
- [[wiki/services/student-service|Student & Enrollment Services]] — Status transition state machines, class promotions, ID renumbering with cascade.
- [[wiki/services/library-services|Catalog, Loans & Fines Services]] — CirculationDesk rules, barcode auto-incrementation, fine calculations, and loan policies.
- [[wiki/services/excel-diff-importer|Excel Diff Roster Importer]] — Fast read-only streaming parser, categorization diffs, and non-destructive yearly promotion application.
- [[wiki/services/sync-service|Air-Gapped Sync & Snapshot Export]] — Snapshot generation, hash verification, diff computation, and merge conflicts.

---

## 🖥️ Applications & QML UI Layer
- [[wiki/apps/common-qml|Common QML Components Library]] — Shared components: `StyledSearchField`, `PaginationBar`, `AuditLogView`, `ActionFeedbackBanner`, `FirstLaunchDialog`.
- [[wiki/apps/student-management-app|Student Management App]] — Modular views (`StudentSearchView`, `StudentDetailView`, `ExcelImportView`), action dialogs, and admin adapter.
- [[wiki/apps/librarian-management-app|Librarian Management App]] — Modular catalog, circulation desk, category action dialogs, barcode generator view.
- [[wiki/apps/booth-app|Self-Service Kiosk Booth App]] — Touch-friendly scanner interface, auto student identification, checkout/return workflows.

---

## 📜 Maintenance Log
- See [[wiki/log|Wiki Revision Log]] for incremental updates and change tracking.
