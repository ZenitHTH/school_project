# Design Document: Chulabook Book Detection & Fetching in Librarian Management

## 1. Intent & Context
The school catalog contains books published/distributed by **Chulabook (ศูนย์หนังสือจุฬาฯ)** whose ISBNs resolve in **none** of the three existing metadata providers (NLT Primo VE, SE-ED BFF, Open Library). Librarians need to (a) identify those books in the catalog and (b) have their metadata (title/author) auto-filled from the Chulabook store when registering them.

## 2. Discovered Access Facts (live-verified 2026-11-10)
- `https://api.chulabook.com` is the site's public REST API (axios `baseUrl` in the site's JS chunks). It is **not** behind the Sucuri JS challenge that blocks `www.chulabook.com` HTML pages — plain `urllib` GETs work, no auth, no cookies.
- **Search**: `GET /products?search=<query>&limit=<n>` → `{"count": int, "rows": [product…])` (search matches title/author/barcode/ISBN).
- **Detail**: `GET /products/<id>` → single product dict.
- Product row fields (search): `id, barcode, name, author, price, stock, picture, cover_price, total_sales, …`
- Detail fields (superset): adds `isbn`, `edition`, `pub_year`, `translator`, `pages`, `weight`, `detail_th`, `detail_en`, `category_main_th`, `category_name_th`, `remark`, `promotions`, `images`, `stock`, `total_sales`.
- **No publisher-name field exists** (only `pbls_code` numeric code) → `publisher` is reported as `""`, never fabricated.
- Verified examples: `GET /products?search=9786169444541&limit=5` → `count: 1`, row id `258216`; `GET /products/258216` → `name: "BIOLOGY THE PROBLEM BOOK: REVISED A-LEVEL EDITION"`, `isbn: "9786169444541"`, `price: 441`, `pub_year: "2569"`.
- Full store size: `count ≈ 112,698` products.

## 3. Detection Rule
For a book with normalized ISBN `I`:
1. **In Chulabook?** `fetch_chulabook(I)` finds a row with `barcode == I` (exact, normalized).
2. **In the standard ISBN databases?** `I` present in local `isbn_cache` (a prior remote hit), OR any of NLT/SE-ED/OpenLibrary resolves `I`.
3. **Flag as Chulabook-exclusive** when (1) is true AND (2) is false.

## 4. Decisions & Constraints
1. **Provider placement** — Chulabook becomes the **4th (last) provider** in `fetch_remote_providers` (after OpenLibrary) in `core/library/services/isbn_providers.py`. This makes the existing autofill (`LibrarianAdminAdapter.fetchIsbnMetadata` → `IsbnLookupService.lookup`) resolve Chulabook ISBNs with **zero UI changes**, and successful lookups are persisted to `isbn_cache` by the existing service.
2. **Non-overwrite policy preserved** — autofill only fills blank Title/Author; existing QML guard untouched.
3. **Detection service** — new `core/library/services/chulabook_service.py` with `detect_chulabook_books(conn, timeout=5.0, workers=8) -> Result[list[dict], str]`. Pure function over `books` + `isbn_cache`; threaded via `concurrent.futures` (same pattern as `IsbnLookupService._fetch_remote`).
4. **Adapter** — one new slot `LibrarianAdminAdapter.detectChulabookBooks() -> str` returning sanitized JSON `{"ok": bool, "error": str, "count": int, "books": [{book_id, isbn, title, author}]}`, with `chulabookCheckStarted` / `chulabookCheckCompleted(str)` signals mirroring `isbnLookupStarted/Completed`. All dicts pass through `_sanitize_for_qml`.
5. **UI** — one `StyledButton` (`btnDetectChulabook`, "📕 ตรวจ Chulabook") in `BookCatalogView.qml` header RowLayout + `ActionFeedbackBanner`-style status Text + a results `Dialog` listing flagged books (ListView; font sizes reactive to `window.fontScale`; dynamic `implicitHeight`, no hardcoded pixel heights; inputs/combos keep the existing alignment rules). Wiring in `Main.qml` mirrors `onSearchRequested: window.searchBooks()`: new signal `detectChulabookRequested` → `window.detectChulabook()`.
6. **HTTP** — reuse `_fetch_json` (adds `Origin`/`Referer` `https://www.chulabook.com` headers, browser `User-Agent`), 5s timeout per request.
7. **Testing** — 100% coverage target; unit tests monkeypatch at `urllib.request.urlopen` / module-level `_fetch_*` names (house pattern, see `tests/test_isbn_service.py`); UI test via offscreen QML engine with `_fetch_chulabook` + `_fetch_primo/_seed/_openlibrary` monkeypatched (no network in tests). Real API fixtures captured 2026-11-10 stored under `tests/fixtures/chulabook/`.

## 5. Out of Scope
- Bulk import from Chulabook (catalog of 112k products) — detection + single-book fetch only.
- Publisher-name enrichment (API has none).
- Chulabook price/ebook/course data (not needed by the books schema).
- The `www.chulabook.com` headless-Chrome scraping path (only needed if the API host gains a challenge; the API host is the access path).
