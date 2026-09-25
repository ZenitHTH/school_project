# Book Adding & Barcode Generation — Librarian Management

Covers `catalog_service.add_book`/`add_copies`
(`application_layer_design.md` §5), specifically the one piece not
designed anywhere else yet: **generating the library's own per-copy
tracking barcode**. The two-barcode split itself was already confirmed
(`database_layer_design.md` §5) — `books.isbn` is the printed
shop/manufacturer barcode (scanned off the book, shared across every
copy of a title), `book_copies.barcode` is the library's own sticker,
unique per physical copy. This doc is about where that second one
actually comes from.

## 1. What triggers generation

- Adding a brand-new title, with some number of initial copies.
- Adding more copies to a title the catalog already has.
- (Edge case, not designed here — see §6) Replacing a damaged/unreadable
  physical sticker on an otherwise fine copy.

## 2. Barcode format

```
{PREFIX}-{book_id:05d}-{copy_seq:02d}
```

Example: a book with `book_id = 42` and two copies gets `SMTE-00042-01`
and `SMTE-00042-02`.

- **`PREFIX`** — a short fixed library identifier, confirmed as
  `"SMTE"` (§7).
- **`book_id`** — the book's own primary key, zero-padded to 5 digits
  (room for up to 99,999 titles).
- **`copy_seq`** — a 2-digit sequence number for this copy *within its
  book* (room for 99 copies of one title — more than enough for a school
  library).

**Self-describing on purpose**: scanning any copy's barcode reveals
which book it belongs to without a database lookup — useful during a
physical inventory check or when troubleshooting a scan that isn't
matching anything.

## 3. Unique by construction, not by chance

Because the barcode is built deterministically from `book_id` (already
unique) and `copy_seq` (unique *within* that book), there's no need for
random-code generation with collision detection and retry — the
`UNIQUE` constraint on `book_copies.barcode`
(`database_layer_design.md` §7) is satisfied automatically as long as
`copy_seq` is computed correctly.

**`copy_seq` computation**: one more than however many copies this book
has *ever* had — counted from all `book_copies` rows for that `book_id`,
including retired or lost ones, not just currently-available copies.
This means a retired copy's sequence number is never reused for a
different physical item, which matters given how much this project has
already emphasized not losing track of individual items
(`application_layer_design.md` §11's accountability discussion).

## 4. Add-book algorithm

```python
def add_book(title, author, isbn, category_id, shelf_location, copy_count):
    book_id = book_repo.insert_book(title, author, isbn, category_id, shelf_location)
    generated = []
    for seq in range(1, copy_count + 1):
        barcode = f"{PREFIX}-{book_id:05d}-{seq:02d}"
        copy_id = book_repo.insert_copy(book_id, barcode, status="available")
        generated.append((copy_id, barcode))
    log_service.record("book.add", "book", book_id,
                        detail=f"{copy_count} cop{'y' if copy_count == 1 else 'ies'} added")
    return generated  # shown to staff for label printing, §5
```

## 5. Add-copies algorithm (existing title)

```python
def add_copies(book_id, additional_count):
    existing = book_repo.count_copies_ever(book_id)  # includes retired/lost
    generated = []
    for seq in range(existing + 1, existing + additional_count + 1):
        barcode = f"{PREFIX}-{book_id:05d}-{seq:02d}"
        copy_id = book_repo.insert_copy(book_id, barcode, status="available")
        generated.append((copy_id, barcode))
    log_service.record("book.add_copies", "book", book_id,
                        detail=f"{additional_count} more cop{'y' if additional_count == 1 else 'ies'}")
    return generated
```

Both write to `activity_log` (`application_layer_design.md` §11) the
same way every other state-changing operation in this design does —
adding inventory is exactly the kind of event the accountability
requirement cares about.

## 6. UI flow

Since generation is deterministic and cheap, commit immediately (no
diff-preview needed here — unlike the sync/import flows, there's nothing
to reconcile against, just new rows to create), then show staff a
confirmation screen listing the newly generated copy barcodes with an
"Export Labels (PDF)" action.

**Confirmed: label output is a PDF for A4, not a dedicated label
printer.** No printer-driver integration needed — the app generates a
PDF laid out for standard paper, and the school prints it on their own
inkjet. Full approach in §8.

**Label reprint, confirmed simple**: if a physical sticker gets damaged
or unreadable but the book itself is fine, there's no new barcode
value and no database change at all — the barcode is deterministic
(§2), so reprinting means re-rendering the exact same stored value onto
a new sticker. A "Reprint label" action on the Book Detail screen
(`ui_layer_design.md` §3) just re-displays/re-renders the existing
`book_copies.barcode` value; it doesn't touch `catalog_service` at all.
This resolves what was originally an open question about "reissuing" a
barcode — there's nothing to reissue, since the identifier never
changes, only its physical printout does.

## 7. Resolved

- **Damaged sticker vs. damaged book, confirmed as two different
  things**: a damaged/unreadable physical *label* is a reprint (§6),
  not a status change or a new barcode value. A damaged *book* goes
  through `mark_copy` as `damaged`, then later `disposed` once the
  school actually disposes of it — two separate steps, both logged in
  `book_copy_status_log`, with `disposed` requiring a reason. Full
  detail on this status split is in `application_layer_design.md` §11.
- **`PREFIX` confirmed as `"SMTE"`** — Science, Mathematics, Technology,
  and Environment, the program this collection belongs to. One thing
  worth flagging on scope, since it was mentioned directly: the current
  collection is ม.1–3 only, not yet ม.4–6. **Recommendation: keep the
  prefix flat as `"SMTE"`, don't bake `"M1-3"` into it.** A barcode
  format is painful to change once physical stickers exist on real
  books — if ม.4–6 titles get added later under the same system, they
  just continue the same `book_id` sequence with no scheme change
  needed. The grade-range distinction (M1-3 vs. M4-6) belongs in the
  `categories` table (`database_layer_design.md` §5) as book metadata
  instead — e.g. two categories under the same collection — since
  category assignment is easy to add or adjust later, while a barcode
  already printed on a physical sticker isn't.
- **Label printing, confirmed simple**: no specialized label printer —
  the school prints on a normal inkjet, onto A4 paper. So "printing
  labels" is really **exporting a PDF laid out for A4**, which the
  school prints themselves; the app never talks to a printer directly.

## 8. Label sheet PDF — implementation approach

- **Barcode symbology: Code128.** It handles the full character set our
  format actually uses — letters, digits, and the dash in
  `SMTE-00042-01` — and is readable by any standard USB barcode scanner,
  including the inexpensive ones a school library is likely to have.
- **Layout: a grid of label cells per A4 page**, each cell containing
  the rendered barcode image plus the human-readable code underneath it
  (so a label is still identifiable by eye if a scanner isn't handy).
  **Confirmed: plain A4 paper, cut by hand** — not a pre-cut adhesive
  product, consistent with how a government school actually works day
  to day. That means the PDF should print light dashed cut-guide lines
  around each cell (a common convention for hand-cut label sheets) and
  leave a little extra spacing between cells for scissors room, rather
  than packing labels edge-to-edge the way a die-cut product could.
  Default grid — 3 columns × 8 rows (24 labels/page) — stays a reasonable
  starting point now that the paper stock itself is confirmed, not just
  assumed.
- **Tooling**: Python's `reportlab` for the PDF layout and `python-barcode`
  for rendering the Code128 images — both lightweight, pure-Python-ish
  libraries with no heavy runtime dependency, consistent with keeping
  this app light on old hardware (`design_doc.md` §2). PDF generation
  only happens when staff explicitly export labels, not on any hot path.
- **Trigger points**: the confirmation screen after adding a book/copies
  (§6) gets an "Export Labels (PDF)" action for the just-generated
  copies; the Book Detail screen (`ui_layer_design.md` §3) gets the same
  action for selecting existing copies to (re)print later.
- **Multi-page**: if more labels are requested than fit one page's grid,
  the export spans multiple pages automatically — nothing for staff to
  configure per export.

```python
def export_label_sheet_pdf(copies: list[tuple[int, str]], output_path: str,
                            cols: int = 3, rows: int = 8) -> None:
    # copies: [(copy_id, barcode), ...]
    # renders each barcode via python-barcode (Code128), lays them out
    # in a cols x rows grid per page via reportlab, paginating as needed
    ...
```

## 9. Resolved — no open items remain

Plain A4 paper, hand-cut, confirmed — §8 now reflects that directly
rather than hedging on paper stock.

