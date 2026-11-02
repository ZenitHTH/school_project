# Design Document: ISBN Lookup & Auto-fill for Book Registration

## 1. Intent & Context
Librarians frequently register physical books by scanning or entering a 13-digit ISBN. Manually typing titles and authors is time-consuming and prone to typos. This feature adds on-demand ISBN metadata lookup targeting the National Library of Thailand (NLT) and local cache directly in the Book Registration views (`BarcodeGeneratorView.qml` Tab 6 and `BookActionDialogs.qml`).

---

## 2. Decisions & User Constraints
1. **Scraper Protocol**:
   - HTTP GET / POST against the NLT search endpoint (`https://e-service.nlt.go.th/ISBNReq/ListSearchPub`) using parameters:
     - `KeywordTypeKey`: `4` (Search by ISBN)
     - `Keyword`: `<13-digit-isbn>`
     - `ISBNReqTypeKey`: `""`
   - Built with Python standard library (`urllib.request` + `html.parser`). Zero external dependencies (`requests`, `beautifulsoup4` avoided for packaging integrity).
   - If NLT returns unexpected HTML, redirects, or times out, the service safely traps the error and returns `Err("cannot fetch data")`.
2. **Autofill & Overwrite Policy**:
   - Only fill blank fields: If the librarian has already typed text into Title or Author, do not overwrite their manual input.
   - On lookup failure: Display "cannot fetch data" (ไม่พบข้อมูลหนังสือ) in the status banner. Leave all input fields intact.
3. **Caching**:
   - Checks local SQLite table `isbn_cache` first. If cached, returns immediately without network calls.
   - Successful NLT lookups are automatically stored in `isbn_cache`.
4. **Threading & Responsiveness**:
   - Background worker (`QThread` / `QRunnable`) in `LibrarianAdminAdapter`. UI remains responsive and fetch button disables while request is active.

---

## 3. System Architecture & Component Design

```
+--------------------------------------------------------------+
|                    QML UI Layer                              |
|  - BarcodeGeneratorView.qml (Tab 6: Book Registration)       |
|  - BookActionDialogs.qml (Add Book Dialog)                   |
|                                                              |
|  [ ISBN TextField ]  [ 🔍 ดึงข้อมูล ]  [ Status Banner ]     |
|  [ Title TextField  (autofilled if blank) ]                  |
|  [ Author TextField (autofilled if blank) ]                  |
+------------------------------+-------------------------------+
                               | PySide6 Slot call
                               v
+--------------------------------------------------------------+
|            LibrarianAdminAdapter (PySide6 QObject)           |
|  - fetchIsbnMetadata(isbn) -> spawns QThread worker          |
|  - Signals: isbnLookupStarted(), isbnLookupCompleted(json)    |
+------------------------------+-------------------------------+
                               | worker thread execution
                               v
+--------------------------------------------------------------+
|                 IsbnLookupService (Core)                     |
|  1. Validate ISBN format (10 or 13 digits)                   |
|  2. Query SQLite `isbn_cache` table                          |
|  3. On cache miss: HTTP GET/POST to NLT endpoint (timeout 5s)|
|  4. Parse DOM table (`<tr>`, `<td>`) via `html.parser`       |
|  5. If found: insert into `isbn_cache`, return Ok(BookMeta)  |
|  6. If failed/empty/redirect: return Err("cannot fetch data")|
+--------------------------------------------------------------+
```

---

## 4. Database Schema
In `library.sqlite`:
```sql
CREATE TABLE IF NOT EXISTS isbn_cache (
    isbn TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    publisher TEXT,
    published_year TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. UI / QML Interaction Flow
1. User enters or scans 13-digit ISBN (e.g. `9786167706955`).
2. User clicks `[🔍 ดึงข้อมูล]` (Fetch Data).
3. Button enters disabled state (`enabled: false`) with indicator text `กำลังค้นหา...`.
4. Result received:
   - **Success (`ok: true`)**:
     - If `titleInput.text.trim() === ""`, populate with fetched title.
     - If `authorInput.text.trim() === ""`, populate with fetched author.
     - Status banner shows `✓ ดึงข้อมูลสำเร็จ`.
   - **Failure (`ok: false`)**:
     - Status banner shows `✗ cannot fetch data` (or `✗ ไม่สามารถดึงข้อมูลได้`).
     - Text inputs are untouched.
5. Button re-enables.

---

## 6. Verification & Test Plan
1. **Unit Tests (`tests/test_isbn_service.py`)**:
   - ISBN format validation (valid 10/13 digits vs invalid letters/lengths).
   - Local SQLite cache hit returns without network call.
   - NLT HTML table parser extracting title, author, and publisher from real HTML fixtures.
   - Graceful handling of network timeouts and HTML pages without tables -> returns `Err("cannot fetch data")`.
2. **Adapter & Integration Tests**:
   - Worker thread execution and JSON serialization matching `Result[T, E]`.
   - Non-overwrite verification when fields contain existing text.
3. **Wiki Documentation**:
   - Update `wiki/services/library-services.md` and `wiki/log.md`.
