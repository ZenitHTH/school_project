# Design Document: ISBN Lookup & Auto-fill via Chained JSON APIs (NLT Primo VE, SE-ED BFF, Open Library)

## 1. Intent & Context
Librarians frequently register physical books by scanning or entering a 10 or 13-digit ISBN. Manually typing titles and authors is time-consuming and prone to typos.

Live testing across 10 real school ISBNs (`9786167706603`, `9786167706580`, `9786164000865`, `9786164874749`, `9786164681255`, `9786164400672`, `9786167706955`, `9786167082493`, `9786162137792`, `9780132350884`) showed:
- `e-service.nlt.go.th` blocks unauthenticated requests via HTTP 302 login redirects and reCAPTCHA v3.
- **NLT Primo VE (`nlt.primo.exlibrisgroup.com`)** resolves books deposited with the National Library of Thailand.
- **SE-ED Web-BFF JSON API (`mp-api.se-ed.com/web-bff`)** resolves commercial Thai exam-prep and tutor books (e.g. *Hi-Speed Gifted Math*, *SYNTAX / VACCINE*, *Science Center*) that have not yet been cataloged in NLT Primo.
- **Open Library Books JSON API (`openlibrary.org`)** resolves international/English books.

Combining **NLT Primo VE -> SE-ED BFF -> Open Library** achieves a **10/10 (100%) live hit rate** across all tested Thai and international ISBNs using only Python standard library JSON requests.

---

## 2. Decisions & User Constraints
1. **Chained JSON Provider Protocol (`core/library/services/isbn_providers.py`)**:
   - **Provider 1 — NLT Primo VE REST API**:
     - `GET https://nlt.primo.exlibrisgroup.com/primaws/rest/pub/pnxs?vid=66NLT_INST:66NLT&q=isbn,exact,<isbn>&offset=0&limit=1&lang=th`
     - Extracts `title` (`addata.btitle[0]` or `display.title[0]`), `author` (`addata.au[0]` or `addata.creatorfull[0]` or `display.creator[0]`, stripping MARC `$$` subfields and trailing `.`), and `publisher` (`addata.pub[0]` or `display.publisher[0]`). Falls back `author` to `publisher` when personal author is blank.
   - **Provider 2 — SE-ED Web-BFF REST API**:
     - Step A (Search): `GET https://mp-api.se-ed.com/web-bff/search-product?filter.keyword=<isbn>&option.limit=1&option.skip=0`
     - Verifies `products[0].physicalProduct.physicalProduct` matches the target SKU (when `variants` is present) and extracts `id` and `name` (`title`).
     - Step B (Detail): `GET https://mp-api.se-ed.com/web-bff/physical-product/<id>`
     - Parses the Lexical JSON `physicalProduct.detail` tree to extract the text node immediately following `"ผู้เขียน"` (`author`) and `"สำนักพิมพ์"` (`publisher`). Falls back `author` to `publisher` if `author` is empty.
   - **Provider 3 — Open Library Books REST API**:
     - `GET https://openlibrary.org/api/books?bibkeys=ISBN:<isbn>&format=json&jscmd=data`
     - Extracts `title`, `authors`, and `publishers`.
2. **Modular Clean Code Split**:
   - `core/library/services/isbn_providers.py`: Pure stdlib HTTP JSON fetching and provider parsers (`parse_nlt_primo_json`, `parse_seed_Book`, `parse_openlibrary_json`, `fetch_remote_providers`).
   - `core/library/services/isbn_service.py`: ISBN normalization/validation, local SQLite authority (`books` active-first, then `isbn_cache`), non-blocking `ThreadPoolExecutor` + Qt event loop pumping, and `IsbnLookupService`.
   - Both files stay well under 200 lines with functions $\le 20$ lines.
3. **Autofill & Overwrite Policy**:
   - Only fill blank `Title` and `Author` fields in QML; never overwrite manual user input.
   - On lookup failure across all providers: display `"✗ cannot fetch data"` and leave inputs intact.
