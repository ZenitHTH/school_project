# ISBN Lookup via NLT Primo VE, SE-ED BFF & Open Library JSON APIs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken `e-service.nlt.go.th` HTML scraper with a 3-provider JSON pipeline (NLT Primo VE -> SE-ED Web-BFF -> Open Library) achieving 100% lookup coverage across Thai National Library books, commercial Thai exam-prep books, and international textbooks.

**Architecture:** Extract remote JSON provider parsers and HTTP clients into `core/library/services/isbn_providers.py` (< 160 lines) and keep `IsbnLookupService`, SQLite local lookup (`books` active-first, then `isbn_cache`), and Qt event-pumping worker orchestration in `core/library/services/isbn_service.py` (< 150 lines).

**Tech Stack:** Python 3.14, PySide6 (Qt Quick/QML), SQLite3, stdlib `urllib.request`, `urllib.parse`, `json`, `ssl`, `pytest`.

**Spec:** `docs/superpowers/specs/2026-11-02-isbn-lookup-design.md`

---

### Task 1: Implement `isbn_providers.py` and Update `isbn_service.py` + Tests

**Files:**
- Create: `core/library/services/isbn_providers.py`
- Modify: `core/library/services/isbn_service.py`
- Modify: `tests/test_isbn_service.py`
- Modify: `tests/test_ui_librarian.py:895-900,934-940`
- Modify: `wiki/services/library-services.md`
- Modify: `wiki/log.md`

**Interfaces:**
- `core/library/services/isbn_providers.py`:
  - `NLT_PRIMO_URL = "https://nlt.primo.exlibrisgroup.com/primaws/rest/pub/pnxs"`
  - `SEED_SEARCH_URL = "https://mp-api.se-ed.com/web-bff/search-product"`
  - `SEED_DETAIL_URL = "https://mp-api.se-ed.com/web-bff/physical-product"`
  - `OPENLIBRARY_URL = "https://openlibrary.org/api/books"`
  - `_fetch_json(url: str, timeout: float = 5.0) -> dict`
  - `parse_nlt_primo_json(data: dict, isbn: str) -> Optional[Dict[str, str]]`
  - `parse_seed_product(search_data: dict, detail_data: Optional[dict], isbn: str) -> Optional[Dict[str, str]]`
  - `parse_openlibrary_json(data: dict, isbn: str) -> Optional[Dict[str, str]]`
  - `fetch_remote_providers(isbn: str, timeout: float = 5.0) -> Optional[Dict[str, str]]`
- `core/library/services/isbn_service.py`:
  - Re-exports `parse_nlt_primo_json`, `parse_seed_product`, `parse_openlibrary_json`, `fetch_remote_providers`, `_fetch_json`
  - `normalize_isbn(raw: str) -> str`
  - `is_valid_isbn(isbn: str) -> bool`
  - `IsbnLookupService` (checks `books`, then `isbn_cache`, then submits `fetch_remote_providers` to `ThreadPoolExecutor`)
