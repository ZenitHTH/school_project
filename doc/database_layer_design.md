# Database Layer Design — Library Management

Covers `data/` specifically: connection handling, encryption, schema
versioning, transaction boundaries, and integrity rules for the library
tables and the latest student-domain features added in
`application_layer_design.md`. Read that doc first for *why* the schema
looks the way it does — this doc is about *how the app talks to the
database safely and quickly* as it grows.

## 1. File & connection management

- **One database file**: `school.sqlite`, path resolved via the file
  import/open flow already defined (`design_doc.md` §6) — encrypted at
  rest from first launch (§2).
- Because encryption is required, the app uses **SQLCipher**
  (`sqlcipher3-binary` or `pysqlcipher3`) as a near drop-in replacement
  for the stdlib `sqlite3` module — same API surface, but every
  connection must run `PRAGMA key` as the very first statement, before
  anything else, or every later query fails:
  ```python
  import sqlcipher3.dbapi2 as sqlite3   # drop-in replacement, same API

  conn = sqlite3.connect(db_path)
  conn.execute("PRAGMA key = ?;", (derived_key,))    # must be first — unlocks the file
  conn.execute("PRAGMA foreign_keys = ON;")           # enforce FKs at runtime
  conn.execute("PRAGMA journal_mode = WAL;")          # SQLCipher supports WAL
  conn.row_factory = sqlite3.Row
  ```
- **Foreign keys ON at runtime, OFF during import**: `build_db.py`
  deliberately runs with `PRAGMA foreign_keys = OFF` because it
  drops/recreates tables in a specific order. That's correct for a bulk
  rebuild but must never be the setting the running app uses.
- **One connection, owned by `data/db.py`**, not one per service. If a
  background thread is ever needed (e.g. import running off the UI
  thread so the window doesn't freeze), that thread opens its own
  connection and re-supplies the key — SQLCipher connections aren't
  safely shared across threads any more than plain SQLite ones are.
- **Packaging note**: SQLCipher is a native library, not pure Python —
  bundling it with PyInstaller/Nuitka (`design_doc.md`'s packaging plan)
  means the sqlcipher shared library (a Windows DLL, a Linux `.so`) has
  to actually end up in the packaged build. A working dev environment
  with the pip package installed doesn't guarantee PyInstaller picks up
  the native lib automatically — this needs an explicit test on the
  packaged binary, not just the dev environment, per the same "test on
  actual old hardware" habit from `design_doc.md`'s build plan.

## 2. Encryption & PIN access (first launch)

Confirmed: v1 ships with the whole database file encrypted at rest,
unlocked by a 6-digit PIN entered at app launch — not open file
permissions, not a documented warning. This directly answers the earlier
concern about someone opening `school.sqlite` in a random SQLite GUI
tool: without the key, the file is unreadable noise to any other tool.

- **PIN → key, never PIN as key**: run the 6-digit PIN through a
  key-derivation function (PBKDF2-HMAC-SHA256, tens of thousands of
  iterations) combined with a random per-install salt stored alongside
  the database (`school.sqlite.salt` — the salt itself isn't secret,
  salts never need to be). A handful of lines, and it meaningfully slows
  down offline brute-force attempts compared to using the raw PIN.
- **Honest trade-off, stated plainly**: a 6-digit PIN has only about a
  million possible values. Key derivation slows down *each* guess but
  doesn't shrink the total keyspace — someone with the file and
  unlimited offline attempts will eventually get in. Acceptable for a
  first launch as long as it's a known trade-off, not a surprise — see
  §12 for the natural next step once the school's ICT is involved.
- **Verifying the PIN**: SQLCipher has no "check this key" call —
  standard pattern is open with the derived key, then run a cheap query
  (`SELECT count(*) FROM sqlite_master;`). A wrong key makes SQLCipher
  raise a "file is not a database" error rather than returning garbage,
  so a wrong PIN fails loudly and immediately.
- **Lockout**: track failed attempts locally (a small counter, e.g. next
  to the salt file) and add a short delay after a few wrong tries.
  Doesn't need to be sophisticated for v1 — a few seconds' backoff after
  3 failures makes casual guessing impractical without real friction for
  someone who just mistyped their PIN.
- **`build_db.py` compatibility**: it currently opens its own raw
  `sqlite3.connect()`, which stops working once the database is
  encrypted unless it also sets the key first. When the import flow
  (`design_doc.md` §6) runs it against an already-unlocked database,
  pass in the already-open, already-keyed connection rather than letting
  it open a fresh unkeyed one.
- **Backups stay encrypted for free**: a backup (§10) is a plain file
  copy of `school.sqlite`, already encrypted at rest — no extra step
  needed to keep backups secure. It does mean losing the PIN loses every
  backup too (flagged in §12).

## 3. Schema versioning & migrations

The schema will keep changing. Track this explicitly instead of hoping
`build_db.py`'s DROP+CREATE stays in sync everywhere:

- Use SQLite's built-in `PRAGMA user_version` as a schema version number.
- `data/migrations/000N_description.sql` — one file per change, numbered,
  never edited after merging. Current plan:

  | # | Migration | Content |
  |---|---|---|
  | 0001 | `initial` | student tables, exactly `build_db.py`'s current `SCHEMA` |
  | 0002 | `library_tables` | `books`, `book_copies`, `loans`, `reservations`, `fines` |
  | 0003 | `student_fk_cascade_and_audit` | rebuilds every table with a FK to `students` to add `ON UPDATE CASCADE`; adds `student_id_changes`, `student_name_changes` |
  | 0004 | `search_fts` | `books_fts`, `students_fts` virtual tables + sync triggers (§4) |
  | 0005 | `categories` | `categories` table; `books.category` (TEXT) replaced with `books.category_id` (FK) (§5) |
  | 0006 | `activity_logging` | `activity_log`, `book_copy_status_log` (`application_layer_design.md` §11) |

- `data/migrate.py`: on app startup, reads `PRAGMA user_version`, applies
  any migration files numbered higher than it in order, bumps the
  version after each. Runs against the already-keyed connection (§2) —
  it never opens its own separate unkeyed connection.
- **Reconciling with `build_db.py`**: going forward, schema changes are
  added as new migration files — `build_db.py` becomes purely an
  *importer* that assumes the schema already exists and only
  inserts/updates rows. Its `DROP TABLE IF EXISTS` + rebuild approach is
  fine for student tables re-imported from xlsx, but must **never** run
  against the library tables or the audit tables — those hold data the
  app itself creates.

### 3a. Adding `ON UPDATE CASCADE` in SQLite (the table-rebuild pattern)

SQLite can't `ALTER TABLE ... ADD CONSTRAINT` after the fact — adding
`ON UPDATE CASCADE` means rebuilding the table: create a new one with the
constraint, copy the data across, drop the old one, rename. Applies to
every table referencing `students(student_id)`: `enrollments`,
`room_changes`, `transfers_out`, `transfers_in`, `leave_of_absence`,
`retentions`, `loans`, `reservations` — eight tables, all in migration
`0003`.

Pattern for one of them (`enrollments`; repeat per table):

```sql
PRAGMA foreign_keys = OFF;  -- required while rebuilding, restored after

CREATE TABLE enrollments_new (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id   INTEGER NOT NULL REFERENCES students(student_id) ON UPDATE CASCADE,
    year         INTEGER NOT NULL,
    semester     INTEGER NOT NULL,
    grade_level  TEXT NOT NULL,
    room         INTEGER NOT NULL
    -- ...remaining columns unchanged
);

INSERT INTO enrollments_new SELECT * FROM enrollments;
DROP TABLE enrollments;
ALTER TABLE enrollments_new RENAME TO enrollments;
CREATE INDEX idx_enrollments_student ON enrollments(student_id);

PRAGMA foreign_keys = ON;
```

Run the whole migration (all eight tables) inside one transaction, and
**always back up first** (§10) — this is the single riskiest migration in
the plan. Check the `INSERT ... SELECT *` column list against
`PRAGMA table_info(<table>)` before it ships, not from memory.

## 4. Search performance: FTS5 for books and students

Both `catalog_service.search` and `student_service.search`
(`application_layer_design.md`) are free-text search — exactly what
SQLite's FTS5 extension is for, and considerably faster than
`LIKE '%term%'` table scans, which can't use a normal index at all with a
leading wildcard.

```sql
CREATE VIRTUAL TABLE books_fts USING fts5(
    title, author, isbn, content='books', content_rowid='book_id',
    tokenize='trigram'
);
CREATE TRIGGER books_ai AFTER INSERT ON books BEGIN
    INSERT INTO books_fts(rowid, title, author, isbn)
    VALUES (new.book_id, new.title, new.author, new.isbn);
END;
CREATE TRIGGER books_ad AFTER DELETE ON books BEGIN
    INSERT INTO books_fts(books_fts, rowid, title, author, isbn)
    VALUES ('delete', old.book_id, old.title, old.author, old.isbn);
END;
CREATE TRIGGER books_au AFTER UPDATE ON books BEGIN
    INSERT INTO books_fts(books_fts, rowid, title, author, isbn)
    VALUES ('delete', old.book_id, old.title, old.author, old.isbn);
    INSERT INTO books_fts(rowid, title, author, isbn)
    VALUES (new.book_id, new.title, new.author, new.isbn);
END;

CREATE VIRTUAL TABLE students_fts USING fts5(
    full_name, content='students', content_rowid='student_id',
    tokenize='trigram'
);
-- + matching AFTER INSERT/UPDATE/DELETE triggers, same shape as above
-- national_id is deliberately NOT indexed here — confirmed out of
-- search scope entirely (student_search_algorithm.md §1)
```

**`tokenize='trigram'`, not the FTS5 default**: Thai script doesn't put
spaces between words, so the default `unicode61` word-boundary tokenizer
would badly fragment names and titles, breaking substring search. The
trigram tokenizer indexes overlapping 3-character windows instead, which
works regardless of script or word boundaries — full detail and the
query-side algorithm that goes with it in `student_search_algorithm.md`.

Because the triggers live in the schema, `catalog_repo.search()` and
`student_repo.search()` just query the FTS tables (`MATCH`) and join back
to the base table — no repository code has to remember to keep the index
updated on every write path.

Trade-off: FTS5 roughly doubles storage for the indexed columns (small
strings, not a real concern at school scale), a trigram index specifically
is somewhat larger than a word-based one, and adds slightly more work
per insert/update — an easy trade given writes here are "add a book" /
"edit a student," not a high-frequency path.

## 5. Book catalog schema — two barcodes per copy, and categories

**Two barcodes, confirmed**: individual copy tracking is wanted, and
every physical book actually carries two distinct barcodes — which the
existing schema (`application_layer_design.md` §4) already separates
correctly across two tables:

- **`books.isbn`** — the printed shop/manufacturer barcode on the book
  itself. Used for fast physical inventory counts against the school's
  government asset register (scan every book on a shelf, tally against
  records). Same value across every physical copy of a title, which is
  exactly why it belongs on `books`, not `book_copies`.
- **`book_copies.barcode`** — the library's own sticker/tag on each
  individual physical copy, scanned at checkout/return to identify
  *which specific copy* a student has. Unique per copy, already enforced
  by the existing `UNIQUE` constraint.

No schema change needed — worth a one-line comment in the schema itself
so a future reader doesn't wonder why there are two barcode-looking
columns:

```sql
-- books.isbn: printed shop/manufacturer barcode, shared across every
--             copy of a title — used for government asset-count audits
-- book_copies.barcode: the library's own per-copy tracking barcode,
--                       used for checkout/return
```

**Categories, confirmed**: create the lookup table now, and the catalog
UI only ever lets staff pick a category from it — no free-text category
field anywhere, so `"Novel"` / `"novel"` / `"Novels"` can't happen in the
first place.

```sql
CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE
);

-- books.category (TEXT) becomes books.category_id (INTEGER, FK)
ALTER TABLE books ADD COLUMN category_id INTEGER REFERENCES categories(category_id);
-- books.category itself is dropped in a follow-up step once category_id
-- is populated (SQLite's ALTER TABLE can add a column but not drop one
-- pre-3.35 — confirm the SQLite version bundled with the app before
-- deciding whether DROP COLUMN or a table-rebuild, §3a-style, is needed)
```

`catalog_service.add_book` (`application_layer_design.md` §5) takes a
`category_id` selected from a dropdown backed by `categories`, plus an
"add new category" action for when a genuinely new one is needed —
adding a category is still easy, it's just a deliberate action instead
of a typo.

## 6. Transaction boundaries

Every operation touching more than one table must be one transaction — a
crash mid-way must not leave a copy marked `on_loan` with no matching
`loans` row, or a student's ID changed in `students` but not everywhere
that referenced it.

| Operation | Tables touched | Transaction |
|---|---|---|
| Checkout | `loans` insert, `book_copies` status update, `activity_log` insert | atomic |
| Return | `loans` update, `book_copies` status update, `fines` insert (if late), `reservations` promote, `activity_log` insert | atomic |
| Retire a book | `books` soft-delete flag, `book_copies` status → `retired` for all its copies, `activity_log` insert | atomic |
| `change_student_id` | `students` update (cascades via §3a), `student_id_changes` insert, `activity_log` insert | atomic |
| `update_name` | `students` update, `student_name_changes` insert, `activity_log` insert | atomic |
| `update_status` transition | `students` update, plus a row in `leave_of_absence` / `transfers_out` / `transfers_in`, `activity_log` insert | atomic |
| `change_classroom` | `enrollments` update, `room_changes` insert, `activity_log` insert | atomic, per student |
| `mark_copy` (lost/damaged/etc.) | `book_copies` status update, `book_copy_status_log` insert, `activity_log` insert | atomic |
| xlsx import | full `build_db.py` run (against the keyed connection, §2) | atomic — commit only at the end |

Every state-changing operation now carries one extra insert into
`activity_log` (`application_layer_design.md` §11), written by the same
`log_service.record(...)` call every service makes — one more row in the
same transaction, not a separate step that could be forgotten.

In `sqlite3`/SQLCipher, atomicity means explicit `with conn:` blocks, not
a bare series of `execute()` calls with a stray `commit()` elsewhere.

## 7. Integrity rules encoded in the schema

- `CHECK` constraints on every status column — invalid states are
  rejected by the database itself, not just application code.
- `UNIQUE` on `book_copies.barcode` (§5) and `categories.name` (§5) — no
  duplicate physical-copy tags, no duplicate category spellings (and
  categories can only be selected, not typed, so this is enforced twice
  over — at the schema level and at the UI level).
- Soft delete on `books.active`; students are never deleted, only
  transitioned to `transferred_out` — every history table stays intact.
- `ON UPDATE CASCADE` (§3a) on every FK referencing `students(student_id)`
  — after migration `0003`, `change_student_id` is safe by construction.
- All library foreign keys point at `students.student_id` and
  `books.book_id` / `book_copies.copy_id` — with `PRAGMA foreign_keys =
  ON` (§1), the database refuses a loan for a student or book that
  doesn't exist.

## 8. Repository layer (between services and raw SQL)

Parameterized queries live in `data/repositories/`; services (`core/`)
call these instead of writing SQL inline — see
`application_layer_design.md` §5 for why this split exists.

```
data/
├── db.py                    # connection + key + PRAGMAs, §1–2
├── migrate.py                # migration runner, §3
├── migrations/
│   ├── 0001_initial.sql
│   ├── 0002_library_tables.sql
│   ├── 0003_student_fk_cascade_and_audit.sql
│   ├── 0004_search_fts.sql
│   ├── 0005_categories.sql
│   └── 0006_activity_logging.sql
└── repositories/
    ├── student_repo.py       # search (students_fts), CRUD,
    │                          #   update_status/update_name/change_id
    │                          #   incl. their audit-table inserts
    ├── enrollment_repo.py     # current_enrollment, change_classroom,
    │                          #   enroll_next_period, room_changes
    ├── book_repo.py           # catalog CRUD, search (books_fts),
    │                          #   mark_copy + book_copy_status_log insert
    ├── loan_repo.py
    ├── reservation_repo.py
    ├── fine_repo.py
    └── log_repo.py            # activity_log insert, called by
                                 #   core/shared/log_service.py from
                                 #   every other service
```

**Always parameterized queries** (`?` placeholders), never
string-formatted SQL — a one-line habit that also happens to be the only
safe way to handle apostrophes, Thai text, etc. correctly.

## 9. Performance on old hardware

- Indices on every FK lookup column, plus FTS5 (§4) instead of `LIKE`.
- WAL mode (§1) matters more on old spinning-disk hardware than SSD — it
  avoids the writer blocking readers.
- Paginate list views (student list, catalog) at the query level rather
  than loading the full table into the UI.
- Check `EXPLAIN QUERY PLAN` on the catalog search, student search, and
  overdue-loans queries once real data volume is in.

## 10. Backup & data safety

For this first launch: a plain file copy, no retention policy or
automated schedule yet. A fuller backup strategy (automated schedule,
network backup, retention count) is deferred to a conversation with the
school's central ICT staff about what infrastructure they can actually
support, rather than guessed at here.

What's still worth doing at this minimal stage:
- Before running any migration (§3, especially §3a's table rebuild) or
  an xlsx re-import, copy the current `school.sqlite` **and its
  `.salt` file** (§2) to a timestamped backup before touching either —
  cheap, no dependency, no ICT involvement needed. **One correction to
  "plain file copy"**: WAL mode (§1) keeps recent writes in `-wal` and
  `-shm` sidecar files next to the database, so copying only the main
  file while the app has it open can produce an incomplete backup. Run
  `PRAGMA wal_checkpoint(TRUNCATE)` first (or use SQLite's backup API —
  confirm it works through SQLCipher) so the main file is complete, then
  copy. Where these files live per OS is in `file_locations_design.md`.
  This is a local
  safety net against the app's own operations, not a substitute for real
  backup infrastructure — it protects against a bad migration, not a
  dead hard drive. Worth flagging that distinction explicitly when the
  ICT conversation happens.

## 11. Concurrency / live multi-PC (still deferred)

The earlier "eventually, not yet" answer about multiple PCs **live**
sharing one database still stands — that's specifically about
synchronous, real-time shared access (e.g. two people editing the exact
same live data at the same moment). The right move when *that* becomes
real is still not a network share — SQLite/SQLCipher over SMB/NFS is a
known corruption source — but a small local network service (§ as
before). Not building this now. §12 below is a different, narrower thing
that **is** needed now: two separate apps on two separate PCs, one of
which only needs an occasionally-refreshed *copy* of the other's data,
not live access to it.

## 12. Two-database architecture & student data sync

**Confirmed structure**: Student Management and Librarian Management are
two separate applications on two separate PCs (`design_doc.md` §8) —
not two sections of one app. Each owns its own local, encrypted database
file:

- **`student.sqlite`** (Student Management PC) — the full student
  domain: `students`, `enrollments`, `room_changes`, `transfers_out/in`,
  `leave_of_absence`, `retentions`, `student_id_changes`,
  `student_name_changes`, plus its own `activity_log`. This is the
  source of truth for student data.
- **`library.sqlite`** (Librarian Management PC) — the full library
  domain (`books`, `book_copies`, `loans`, `reservations`, `fines`,
  `categories`, `book_copy_status_log`), its own `activity_log`, **plus
  a read-only mirror** of just `students` (and current `enrollments`) —
  enough to search for a borrower and validate their status, nothing
  more. Confirmed: Librarian Management doesn't need or get the
  library-irrelevant student history tables (room changes, transfers,
  etc.) — those stay on the Student Management side only.

Both apps still share the same `core/` and `data/` codebase
(`design_doc.md` §9) — what differs between them is which local database
file `data/db.py` connects to and which tables exist in it, not the
Python code itself. `core/student/services/student_service.py`'s
`search`/`get` functions run the same way in both apps; Librarian
Management's adapter (`application_layer_design.md` §9) simply never
imports the *write* functions (`update_status`, `change_student_id`,
`update_name`) — there's nothing to protect against, since those
functions have nowhere sensible to write on a mirror table anyway.

### The sync mechanism

Confirmed acceptable: periodic or on-demand sync, not live. Concretely:

1. **Export (Student Management)**: an "Export Student Snapshot" action
   writes a timestamped file (a small SQLite file containing just
   `students` + current-period `enrollments`, or a JSON export — SQLite
   file is simpler since both sides already speak SQLite). **Confirmed
   transport for v1: sent manually through LINE chat** — staff export
   the file and send it to whoever operates Librarian Management the
   same way they'd share any other file. File size isn't a concern
   (roughly 2,800 students' worth of name/ID/enrollment data is a tiny
   file, well under any chat app's limits).

   **Worth flagging, not just accepting silently**: this snapshot
   carries the same sensitive data the main app goes to real lengths to
   protect (SQLCipher + PIN, `database_layer_design.md` §2) — national
   IDs, full names, enrollment status — and LINE is a third-party
   consumer app the data now passes through, outside the app's own
   security boundary entirely. Recommend the exported snapshot file
   itself be encrypted before sending (reuse the same key-derivation
   approach as §2, with a separate export password rather than the
   app's own PIN, so the file is meaningless if it ends up somewhere
   unintended) rather than leaving a plain-text SQLite file to travel
   over chat. This is a recommendation to confirm, not yet built —
   flagged in §13.
2. **Preview the diff (Librarian Management)** — before writing
   anything, compare the incoming snapshot's `students`/`enrollments`
   rows against the local mirror's current rows, keyed by `student_id`:
   - **New** — in the snapshot, not yet in the local mirror.
   - **Changed** — same `student_id`, one or more fields differ (name,
     status, room/grade). Show old → new per field, not just "this
     student changed." **Status changes get visually flagged** more
     prominently than a name/room change, since a status change (e.g.
     → `transferred_out`) directly affects whether that student should
     still be able to borrow — the one diff category a librarian
     genuinely needs to notice, not just acknowledge.
   - **Missing from the snapshot** — a `student_id` the local mirror has
     that the new snapshot doesn't include. Flagged as unusual (students
     are never actually deleted upstream, per `application_layer_design.md`
     §3), not silently removed — this case most likely means a bad
     export, and is worth surfacing rather than acting on automatically.
   - **ID renumbering** — surfaced explicitly as its own line ("ID
     renumbered: 32635 → 32999"), not folded into "changed," since it's
     a different kind of event (§3 point below) from an ordinary field
     edit.

   This turns the sync from "trust and rebuild" into "review and apply"
   — the librarian sees exactly what's about to change before it does,
   rather than a silent table replace.
3. **Apply (Librarian Management)** — only after confirming the diff,
   replace the local mirror tables in one transaction — same idempotent
   drop-and-rebuild pattern `build_db.py` already uses, just for a much
   smaller table set. Records a `last_synced_at` timestamp in a small
   `sync_state` table (`ui_layer_design.md` §4's "last synced" note), and
   writes one summary row to `library.sqlite`'s own `activity_log`
   (`application_layer_design.md` §11) — e.g. "sync.import: 3 new, 5
   updated, 1 ID renumbered" — so the sync itself is part of the
   accountability trail, not invisible to it.
4. **Handling `student_id` changes across the sync boundary**: since
   `student_id` is the primary key and *can* (rarely) change on the
   Student Management side, a plain table replace would silently orphan
   any `loans`/`reservations` on the Librarian side still pointing at the
   old ID. The export includes any `student_id_changes` rows since the
   last sync; applying those to `library.sqlite`'s own
   `loans.student_id` / `reservations.student_id` happens as part of step
   3, *before* refreshing the mirror tables — one more place
   `student_id_changes` (§3a) pays for itself beyond its original audit
   purpose, and exactly what step 2's "ID renumbering" line is showing
   in advance.
5. **Checkout against an unsynced student**: if Librarian Management
   tries to check a book out to a `student_id` that isn't in its local
   mirror yet (e.g. a brand-new student added today, not yet synced),
   `loan_service.checkout` fails with a clear message ("student not
   found locally — try syncing student data") rather than a raw
   foreign-key error.

Diff computation lives in `data/sync/diff.py` (comparison logic, no
writes), separate from `data/sync/apply.py` (the actual transaction in
step 3) — the same "read vs. write" separation the repository layer
already follows elsewhere in this design.

### What this doesn't solve (yet)

- **Staleness is real and visible, not hidden.** Between syncs, a
  student marked `transferred_out` on the Student Management side can
  still show as borrowable on the Librarian side. The "last synced"
  indicator (§ above) is the mitigation for v1 — not a fix, a visibility
  aid so staff know to check when it matters.
- **The Booth app's database relationship is unresolved.** If it runs on
  the same PC/LAN as Librarian Management and needs to see loan/copy
  changes the moment they happen (a book checked out at the booth must
  immediately show as unavailable in Librarian Management, and vice
  versa), that's the *live* multi-PC case from §11, not the periodic-sync
  case here — flagged as an open question in §13, not assumed either way.
- **Cross-database activity log**: `activity_log` now exists separately
  in `student.sqlite` and `library.sqlite`, each capturing only its own
  app's actions. Whether a unified view across both matters enough to
  build (e.g. folding recent `activity_log` rows into the same export/
  import as student data) is also an open question in §13, not decided
  here.

## 13. Open questions

**Resolved this round:**
- ~~Individual copy tracking?~~ Confirmed — two barcodes per book,
  already matches the existing schema (§5), no change needed.
- ~~Backup retention/location?~~ Deferred: plain SQLite plus a cheap
  pre-migration local copy for now; full strategy to be scoped with the
  school's central ICT team.
- ~~Protecting the file from outside tools?~~ Resolved by encryption
  (§2) rather than a warning — SQLCipher + 6-digit PIN from first
  launch.
- ~~Categories normalization?~~ Confirmed — create `categories` now
  (§5), catalog UI only allows selecting from it, no free text.
- ~~Same PC or different PCs for Student/Librarian Management?~~
  Confirmed different PCs, periodic sync acceptable — designed in §12.
- ~~Sync transport?~~ Confirmed — manual transfer via LINE chat for
  first launch (§12).

**New, from the two-database decision (§12):**
- **Booth app's database**: does it share `library.sqlite` directly
  (same PC/LAN, needs live consistency with Librarian Management), or
  does it also work off a periodic snapshot like the Librarian side does
  for student data? This decides whether the booth needs the live
  network-service approach from §11 or can reuse the simpler pattern
  from §12.
- **Unified activity log**: is a combined view across
  `student.sqlite`'s and `library.sqlite`'s separate `activity_log`
  tables worth building (e.g. via the same export/import mechanism), or
  is "each app shows its own log" acceptable given how the accountability
  requirement has been framed so far?
- **Snapshot encryption**: since the snapshot now travels through a
  third-party consumer app (LINE) rather than staying inside the app's
  own encrypted boundary, should the exported file itself be encrypted
  before sending (§12's recommendation), or is that unnecessary given
  everything else already decided about how this school handles risk
  trade-offs for a first launch?

**New, from the encryption decision:**
- **Lost-PIN recovery**: if the PIN is forgotten, is the data
  unrecoverable by design (no backdoor), or should there be a recovery
  mechanism — e.g. a longer recovery code generated at setup and kept
  physically secure by the school? Worth deciding deliberately now
  rather than discovering the answer is "unrecoverable" the first time
  someone forgets it.
- **Single PIN or per-user**: one PIN shared by whoever operates the app
  (librarian, registrar), or does each person need their own? Changes
  whether this is purely encryption or also a lightweight login system.
- **Lockout tuning**: is a few seconds' delay after failed attempts (§2)
  enough friction, or does the school want something stricter, given how
  seriously government-tracked assets are treated here?

**Still open from before:**
- None outstanding from the schema/backup/encryption side right now —
  remaining open items are in `application_layer_design.md` §12 (fine
  amounts, reservation notifications, librarian role, and two new ones
  from the logging system: whether `activity_log` needs per-user actor
  identity, and whether reads of sensitive fields need logging too).
