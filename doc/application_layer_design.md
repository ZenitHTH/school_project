# Application Layer Design — Student Manager + Library Management

This document covers the application layer in detail, now that the scope
has grown from "student records" to "student records + school library
management." It assumes the overall architecture and project structure
already defined in `design_doc.md`; this doc goes one level deeper on the
layer that will carry most of the new complexity.

## 1. Why this needs its own doc

The application layer is where every business rule lives (loan limits,
fines, who's allowed to borrow). It's also the layer that has to stay
Qt-free and testable as the app grows. Library management adds real
state machines (a loan has a lifecycle; a reservation has a lifecycle) and
cross-domain rules (a student's status affects their library privileges).
Getting the shape of this layer right now avoids a rewrite later.

## 2. Domain split

Two domains share one application layer, one database:

- **Student domain** (existing): students, enrollments, transfers, leave,
  retentions.
- **Library domain** (new): books, copies, loans, reservations, fines.

They're not independent — a loan references a student and must respect
that student's status. Model this as one domain *depending on* the other,
not two silos glued together in the UI.

```
core/
├── student/
│   ├── models.py
│   └── services/
│       ├── student_service.py
│       ├── enrollment_service.py
│       └── history_service.py
├── library/
│   ├── models.py
│   └── services/
│       ├── catalog_service.py
│       ├── loan_service.py
│       ├── reservation_service.py
│       └── fine_service.py
├── importers/
│   ├── xlsx_validator.py
│   └── build_db.py
└── shared/
    ├── result.py        # Result/Outcome type, see §7
    └── errors.py         # domain error types
```

`library/` is allowed to import from `student/` (e.g. `loan_service` calls
`student_service.get_status(student_id)`). `student/` never imports from
`library/` — the dependency runs one direction only.

## 3. Student domain services (detail)

The original doc left this domain as a one-line list — worth detailing
now, since search/status/ID/classroom changes are exactly the operations
a librarian or registrar will use daily, and a couple of them (status,
student ID) have real business-rule and data-integrity weight.

### `student_service.py`

- **`search(query)`** — searches across `student_id`, `national_id`, and
  name fields (first/last/full, partial match, Thai text). Backs the
  student list's search box. Returns paginated results (see
  `database_layer_design.md` §6 on pagination), not the full table.
- **`get(student_id)`** — one student record with current enrollment
  joined in, for the detail screen.
- **`update_status(student_id, new_status, reason=None)`** — the single
  choke point for status changes; nothing else in the app flips
  `students.status` directly. Not a free-for-all field edit — enforce
  which transitions are legal and what each one writes:

  | From → To | Also writes |
  |---|---|
  | `active` → `on_leave` | new row in `leave_of_absence` (reason, date) |
  | `active` → `transferred_out` | new row in `transfers_out` |
  | `on_leave` → `active` | closes the open `leave_of_absence` row (return date) |
  | `on_leave` → `transferred_out` | new row in `transfers_out` |
  | `transferred_out` → `active` | new row in `transfers_in` (reason, date) — **confirmed real, super-rare** rather than disallowed |

  Confirmed with the school: `transferred_out → active` does happen, just
  rarely, so it's allowed — a direct status flip that logs to
  `transfers_in`, not a separate re-admission pipeline with a new student
  record. It's the same student, same `student_id`, coming back.

  Reject any transition not in this table with a typed failure (§7), not
  a silent no-op.

  This is also *the* place the cross-domain rule in §9 is enforced: since
  every status change funnels through here, `loan_service` only ever
  needs to read the current status, never guess whether some other code
  path changed it correctly.

- **`change_student_id(old_id, new_id, reason)`** — renumbering a
  student's ID. Flagged separately from the rest because `student_id` is
  the primary key and is referenced by every other table (`enrollments`,
  `room_changes`, `transfers_out/in`, `leave_of_absence`, `retentions`,
  and the library tables `loans`/`reservations`). Treat this as a rare,
  deliberate operation, not a routine edit:

  1. Validate `new_id` isn't already in use.
  2. Requires a schema change first: add `ON UPDATE CASCADE` to every
     foreign key that currently points at `students(student_id)` (none
     of them specify it today — see `database_layer_design.md` §2 for
     where this becomes a migration). With that in place, updating
     `students.student_id` once lets SQLite propagate the new value to
     every child table automatically, instead of the application having
     to hand-update seven tables inside one transaction and risk missing
     one.
  3. One transaction: the `UPDATE students SET student_id = ?` plus an
     insert into a new small audit table:
     ```sql
     CREATE TABLE student_id_changes (
         id          INTEGER PRIMARY KEY AUTOINCREMENT,
         old_id      INTEGER NOT NULL,
         new_id      INTEGER NOT NULL,
         reason      TEXT,
         changed_at  TEXT NOT NULL
     );
     ```
     Kept separate from the general history tables — a PK change is a
     different kind of event (a correction to the record's identity
     itself) from a status/room change, and worth its own trail if
     anyone ever asks "wait, why did this student's ID change?"

- **`update_name(student_id, prefix, first_name, last_name, reason=None)`**
  — much lower-risk than `change_student_id` since no other table
  references a student by name, only by `student_id`. Still worth doing
  properly rather than as a bare field edit:
  1. Recompute and store `full_name` from the parts (`prefix +
     first_name + last_name`) rather than letting it drift out of sync
     with the individual fields — it's a derived/display column, not
     independently editable.
  2. Log the change to a small audit table, same reasoning as
     `student_id_changes` — a name correction (misspelling, legal name
     change, prefix change on marital status, etc.) is worth a trail
     separate from the day-to-day status/room history:
     ```sql
     CREATE TABLE student_name_changes (
         id          INTEGER PRIMARY KEY AUTOINCREMENT,
         student_id  INTEGER NOT NULL REFERENCES students(student_id) ON UPDATE CASCADE,
         old_full_name TEXT NOT NULL,
         new_full_name TEXT NOT NULL,
         reason      TEXT,
         changed_at  TEXT NOT NULL
     );
     ```
  3. No cascade concerns and no uniqueness check needed (unlike
     `student_id`) — this can run as a single-table update plus the
     audit insert, no multi-table transaction required.

### `enrollment_service.py`

- **`current_enrollment(student_id)`** — active grade/room for the
  current year/semester.
- **`change_classroom(student_id, new_room, reason=None)`** — moves a
  student to a different room *within the same academic period*.
  Confirmed real trigger: when a student unexpectedly leaves the school
  mid-year (`update_status` → `transferred_out`), the remaining students
  in that room sometimes get reshuffled across rooms to keep class sizes
  balanced — that reshuffling is a series of `change_classroom` calls,
  one per affected student, not a special case of its own.
  1. `UPDATE` (not insert) the student's current `enrollments` row for
     the active year/semester — this is a correction to an
     already-open enrollment period, not a new one.
  2. Insert a row into `room_changes` (old_room, new_room, date,
     reason) — that table already exists in the current schema for
     exactly this.

  Confirmed single-student by design (§12): staff are fine calling this
  one-by-one, even for rebalancing — no bulk "rebalance this room" helper
  planned.
- **`enroll_next_period(student_id, year, semester, grade_level, room)`**
  — the normal year-to-year progression. This is a *new* `enrollments`
  row, deliberately kept separate from `change_classroom`: moving a
  student from room 3 to room 4 in the middle of March is a correction;
  moving them from ม.1 to ม.2 next year is a new period. Conflating the
  two under one "change classroom" function would make it unclear which
  rows are supposed to be inserts vs. updates. If a grade-level change is
  requested via `change_classroom`, treat that as a signal it should
  have gone through this function instead, and say so rather than
  silently doing something a report will later contradict.

  **Trigger, corrected**: this isn't invoked from a standalone bulk UI
  action. Yearly promotion happens via the xlsx diff-import
  (`design_doc.md` §6a) — the import's apply step calls this once per
  student whose grade/room changed, inside one outer transaction, same
  reasoning as any other multi-row operation in this design (a partial
  promotion is a worse failure state than a partial single-student
  change).

## 4. New data model (library domain)

Additions to the schema built by `build_db.py` (student tables stay as-is,
aside from the `ON UPDATE CASCADE` addition and new `student_id_changes`
table from §3):

```sql
CREATE TABLE books (
    book_id       INTEGER PRIMARY KEY,
    isbn          TEXT,
    title         TEXT NOT NULL,
    author        TEXT,
    publisher     TEXT,
    category      TEXT,
    shelf_location TEXT,
    total_copies  INTEGER NOT NULL DEFAULT 1,
    active        INTEGER NOT NULL DEFAULT 1   -- soft delete, keep loan history intact
);

CREATE TABLE book_copies (
    copy_id     INTEGER PRIMARY KEY,
    book_id     INTEGER NOT NULL REFERENCES books(book_id),
    barcode     TEXT UNIQUE,
    status      TEXT NOT NULL DEFAULT 'available'
                CHECK (status IN ('available','on_loan','lost','damaged','retired','disposed'))
);

CREATE TABLE loans (
    loan_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    copy_id      INTEGER NOT NULL REFERENCES book_copies(copy_id),
    student_id   INTEGER NOT NULL REFERENCES students(student_id) ON UPDATE CASCADE,
    borrowed_at  TEXT NOT NULL,
    due_at       TEXT NOT NULL,
    returned_at  TEXT,
    status       TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active','returned','overdue','lost'))
);

CREATE TABLE reservations (
    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id        INTEGER NOT NULL REFERENCES books(book_id),
    student_id     INTEGER NOT NULL REFERENCES students(student_id) ON UPDATE CASCADE,
    reserved_at    TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'waiting'
                CHECK (status IN ('waiting','ready','fulfilled','cancelled','expired'))
);

CREATE TABLE fines (
    fine_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_id     INTEGER NOT NULL REFERENCES loans(loan_id),
    amount      REAL NOT NULL,
    reason      TEXT NOT NULL,          -- 'overdue', 'lost', 'damaged'
    paid        INTEGER NOT NULL DEFAULT 0,
    paid_at     TEXT
);

CREATE INDEX idx_copies_book ON book_copies(book_id);
CREATE INDEX idx_loans_student ON loans(student_id);
CREATE INDEX idx_loans_copy ON loans(copy_id);
CREATE INDEX idx_reservations_book ON reservations(book_id);
CREATE INDEX idx_fines_loan ON fines(loan_id);
```

**Individual copies, not just a count**: tracking `book_copies` separately
from `books` (rather than a single `available_copies` counter) is worth
the extra table — it lets you know *which physical copy* is out, mark one
copy lost without touching the others, and use barcodes later without a
schema change.

## 5. Services and responsibilities (library domain)

### `catalog_service.py`
- `add_book(...)`, `update_book(...)`, `retire_book(book_id)` (soft
  delete — never hard-delete a book with loan history)
- `add_copies(book_id, count)`, `mark_copy(copy_id, status)`
- `search(query, category=None)` — catalog browse/search
- `available_copy_for(book_id)` — returns one available copy or `None`

### `loan_service.py`
- `checkout(student_id, book_id)` — the core state-changing operation:
  1. Check student status via `student_service` — must be `active`
  2. Check student's outstanding fines and current loan count against
     policy limits (see §6)
  3. Find an available copy via `catalog_service`
  4. If all checks pass: create `loans` row, flip copy to `on_loan`
  5. If any check fails: return a typed failure (§7), never raise for
     expected business conditions
- `return_book(loan_id)` — marks `returned_at`, flips copy back to
  `available`, computes overdue fine via `fine_service` if late, and
  fulfills the next waiting reservation for that book if one exists
- `renew(loan_id)` — extends `due_at` by policy period, refuses if the
  book has a waiting reservation
- `overdue_loans()` — for the "books overdue" report/dashboard

### `reservation_service.py`
- `reserve(student_id, book_id)` — only allowed when no copy is currently
  available; queued FIFO
- `cancel(reservation_id)`
- `promote_next(book_id)` — called by `loan_service.return_book`, moves
  the next `waiting` reservation to `ready` (called internally, not
  exposed as a standalone user action beyond viewing status)

### `fine_service.py`
- `assess_overdue(loan_id)` — computed at return time (see §6 for rate)
- `record_payment(fine_id)`
- `outstanding_for(student_id)` — used by `loan_service.checkout` to
  block new loans if unpaid fines exceed policy threshold

Every service function that changes state returns a `Result` (§7), not a
raw bool or a raised exception, so the UI can show *why* something failed.
The same pattern applies to `student_service`/`enrollment_service` in §3
— `update_status` rejecting an illegal transition, or `change_student_id`
rejecting a `new_id` already in use, are exactly this kind of expected
failure, not an exception.

## 6. Business rules (make these config, not hardcoded)

Put these in one `core/library/policy.py` (or a `policies` table if the
school wants to tune them without a code change):

| Rule | Suggested default |
|---|---|
| Loan duration | 14 days |
| Max active loans per student | 3 |
| Renewal limit | 1 renewal per loan |
| Overdue fine rate | per-day amount, capped at a max |
| Borrowing blocked if | student status ≠ `active`, OR unpaid fines above threshold, OR at max active loans |
| Lost book | fixed replacement fee, loan closed as `lost` |

These are guesses to be confirmed with the school, not final numbers —
flagged again in §12, alongside the student-status transition table in §3.

## 7. Error handling pattern

Business-rule failures (book unavailable, student over their limit,
unpaid fines, an illegal status transition) are **not** exceptions —
they're expected outcomes the UI needs to display. Use a small `Result`
type shared across all services:

```python
@dataclass
class Result:
    ok: bool
    error: str | None = None
    data: object | None = None
```

Reserve real exceptions for actual bugs/integrity problems (a `book_id`
that doesn't exist when it should, a DB constraint violation) — those are
allowed to propagate and get logged, not silently swallowed.

## 8. Cross-domain rule: student status affects library privileges

Explicit dependency, called out because it's easy to miss:

- A student with status `transferred_out` should not be able to check out
  new books. Existing open loans stay in the system (history), but
  `loan_service.checkout` must query `student_service` for status before
  approving.
- Because `student_service.update_status` (§3) is the only place status
  changes happen, this check is a simple current-value read — there's no
  second code path that could have changed status without going through
  the transition rules.
- Open question: when a student is marked `transferred_out` or
  `on_leave` *while they have an active loan*, does the app auto-flag
  it for the librarian ("student left with book X still out"), or leave
  it to manual review? Recommend a report/dashboard item rather than an
  automatic action — don't silently do anything to a physical book's
  status without a human confirming it.

## 9. UI boundary

The application layer stays plain Python — no `QObject` in `core/`.
Confirmed structure: **three separate applications**, not sections of
one app — Student Management, Librarian Management, and the self-service
booth (`design_doc.md` §8), each with its own database file
(`database_layer_design.md` §12). `core/` and `data/` are shared code,
but each app's `data/db.py` points at a different local database, which
is what actually separates them — not a permissions layer inside one
process.

- **`apps/student_management_app/adapters/student_admin_adapter.py`** —
  the full `student_service` and `enrollment_service` surface: search,
  get, `update_status`, `change_student_id`, `update_name`,
  `change_classroom`, `enroll_next_period`. Runs against `student.sqlite`.
- **`apps/librarian_management_app/adapters/librarian_admin_adapter.py`**
  — `catalog_service` (add/retire books, `mark_copy`), `loan_service`
  (checkout/return, current loans, `overdue_loans`), `reservation_service`,
  `fine_service`, plus **read-only** `student_service.search`/`get` for
  borrowing-history lookups. Runs against `library.sqlite`, whose
  `students`/`enrollments` tables are a periodically-synced mirror, not
  the live source — this adapter simply never imports
  `student_service`'s write functions, since there's nowhere sensible
  for them to write on this side.
- **`apps/booth_app/adapters/booth_adapter.py`** — a wholly separate
  application, so this is its own small Python entry point. Wraps only
  `student_service.search` (the built-in mini search) and
  `loan_service.checkout`/`return_book`. Which database it points at is
  still open (`database_layer_design.md` §13) — same `library.sqlite` as
  Librarian Management if they share a PC/LAN, or its own synced copy if
  not.

Every adapter translates `Result` into Qt signals/properties the UI can
bind to. This keeps `core/student` and `core/library` unit testable
without booting Qt at all, in any of the three apps.

## 10. Testing

Pure-Python services mean pure-Python tests, no Qt/UI needed:

- `test_student_service.py`: search matches on partial name/ID, each
  legal status transition writes the right history row, each illegal
  transition is rejected, `change_student_id` cascades correctly and
  rejects a duplicate `new_id`
- `test_enrollment_service.py`: `change_classroom` updates the existing
  row and logs to `room_changes`, `enroll_next_period` inserts a new row
  rather than updating
- `test_loan_service.py`: checkout succeeds/fails on each policy rule
  (over limit, unpaid fines, inactive student, no copies available),
  return computes correct fine, return fulfills a waiting reservation
- `test_reservation_service.py`: FIFO ordering, cancel, promote-next
- `test_fine_service.py`: rate calculation, payment recording

One assertion-based check per rule is enough at this stage — this doesn't
need a full test framework yet, just enough to catch a regression when a
policy value or transition rule changes.

## 11. Audit & activity logging system

Two kinds of logging live in this app, serving different purposes — worth
keeping them distinct rather than merging into one giant table:

### Domain-specific audit tables (already designed)

Structured, one purpose each, easy to build a specific report from:
`student_id_changes`, `student_name_changes`, `leave_of_absence`,
`transfers_out`, `transfers_in`, `room_changes`, `retentions`. Each
answers a specific question well ("list every transfer this semester")
because its columns are shaped for exactly that question.

One gap in this set, closed now given how much the school emphasized
accounting for every physical item (§12): a copy going `lost` or
`damaged` *outside* an active loan (found during a shelf check, not a
return) currently has nowhere to leave a record. Adding it:

```sql
CREATE TABLE book_copy_status_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    copy_id     INTEGER NOT NULL REFERENCES book_copies(copy_id),
    old_status  TEXT NOT NULL,
    new_status  TEXT NOT NULL,
    reason      TEXT,
    changed_at  TEXT NOT NULL
);
```

`catalog_service.mark_copy(copy_id, status, reason=None)` writes this in
the same transaction as the status update — one function, one place a
copy's status ever changes, one full trail from acquired to
disposed/lost.

**Confirmed workflow for a damaged physical book**: `damaged` and
`disposed` are two separate steps, not one. A damaged copy is first
marked `damaged` (a report — the book still physically exists, pending a
decision), and separately, once the school actually disposes of it,
marked `disposed` (the terminal state, reason required — this is the
one government schools typically need a documented reason for, given
the accountability emphasis already established). `book_copy_status_log`
captures both transitions with their own timestamp and reason, so the
full lifecycle (`available` → `damaged` → `disposed`) is visible, not
collapsed into a single event. **This is distinct from a barcode
sticker being physically damaged or unreadable** — that's not a status
change at all, just a label reprint (`book_barcode_generation.md` §6),
since the barcode value itself doesn't change.

### General activity log (new — the "log system" itself)

The domain tables above only exist for events someone already thought to
model specifically. A general, cross-cutting log fills the rest: loan
checkouts/returns, fine payments, catalog additions/edits, migrations
run, PIN unlock attempts — anything state-changing that doesn't have its
own dedicated table, plus a unified "what happened recently" view across
everything that does.

```sql
CREATE TABLE activity_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_at   TEXT NOT NULL,
    actor       TEXT,             -- see the open question below
    action      TEXT NOT NULL,    -- e.g. 'student.update_status', 'loan.checkout'
    entity_type TEXT NOT NULL,    -- 'student', 'book', 'loan', ...
    entity_id   TEXT NOT NULL,
    detail      TEXT              -- short human-readable summary
);
CREATE INDEX idx_activity_log_entity ON activity_log(entity_type, entity_id);
CREATE INDEX idx_activity_log_time ON activity_log(logged_at);
```

`detail` is a short one-line summary ("status: active → on_leave"), not a
raw dump of every column — the domain tables already hold the structured
before/after values where that level of detail matters; this table is
for browsing and searching, not for reconstructing exact field values.

**One choke point, same pattern as `update_status`**: a single
`core/shared/log_service.py` with one function —
`record(action, entity_type, entity_id, detail=None)` — called by every
service alongside the actual change, inside the *same* transaction
(updates the transaction table in `database_layer_design.md` §6: every
row there gains "+ `activity_log` insert"). Nothing writes to
`activity_log` except through this one function, so there's never a
second code path that forgot to log something.

**Deliberately not logging reads** — viewing a student's record isn't
logged, only changes. Keeps the table growth bounded to actual activity
and avoids turning this into a surveillance log of who looked at what.
Flagged as an explicit choice in §12, since some government data-handling
rules do require read-access logging for sensitive personal data (
national ID, etc.) — worth a direct answer, not an assumption, given
everything else confirmed so far about how seriously this school treats
accountability.

**Retention: don't auto-delete.** Given the accountability requirement
already confirmed (§12), the default is to keep `activity_log` forever,
not prune it — a "we can't tell you what happened 3 years ago" gap would
undercut the entire point of building this. If the table's size ever
becomes a real performance concern (unlikely at school scale, but
`EXPLAIN QUERY PLAN` per `database_layer_design.md` §9 will show it), the
fix is archiving older rows to a separate file, not deleting them.

**UI**: a simple activity log screen — filter by entity type, date range,
free-text search in `detail` — for a "what's happened recently" and
"show me everything about this book/student" view.

## 12. Open questions

**Student domain — resolved this round:**
- ~~Is "transferred back in" a distinct re-admission flow?~~ Confirmed:
  rare but real, handled as a direct `transferred_out → active` flip
  logged to `transfers_in` (§3).
- ~~Does `change_classroom` vs `enroll_next_period` match how staff
  think about it?~~ Confirmed: `change_classroom` is for unplanned
  mid-year moves (most commonly rebalancing after a student leaves),
  `enroll_next_period` is the normal yearly progression. Matches the
  original design.
- ~~Is one-by-one room rebalancing acceptable, or is a bulk helper
  worth building?~~ Confirmed: one-by-one is fine — `change_classroom`
  itself is called far more often than `change_student_id` is, but the
  *rebalancing scenario specifically* is rare enough not to need a bulk
  action. No bulk "rebalance this room" operation planned.
- ~~How often does `student_id` actually need to change?~~ Confirmed:
  very rare, almost always a typo correction. Keeping the
  `ON UPDATE CASCADE` + `student_id_changes` audit approach from §3 as
  designed — a stable-ID-plus-display-code redesign isn't worth it for
  something this infrequent.
- ~~How often does a name change happen?~~ Confirmed: also very rare,
  same typo-correction pattern as student ID. `update_name` in §3 stays
  as designed — no need for a structured reason-code field beyond the
  free-text `reason` already in `student_name_changes`.

**Library domain — resolved this round:**
- ~~Copy count expectations — barcode-level or simple count?~~
  Confirmed emphatically: individual copy tracking, matching
  `database_layer_design.md` §5's two-barcode design. This is a
  government school — every physical item has to be accounted for on
  paper, and a lost/unaccounted-for book is a real problem, not a minor
  inconvenience. Directly motivated the logging system in §11.
- ~~Should reservations notify students?~~ Confirmed: not in the first
  build — no in-app notification, no printed slip. Librarian handles it
  manually for now. `reservation_service.reserve`/`cancel` (§5) stays as
  designed; a notification step can be added later without changing the
  underlying reservation state machine.
- ~~Does the app need a distinct "librarian" role?~~ Confirmed, and more
  specific than a simple yes/no: **three GUI surfaces**, not two roles —
  student search, a student-facing self-service checkout booth, and
  librarian admin (`design_doc.md` §8, `application_layer_design.md`
  §9). The self-service booth in particular changes the earlier "one
  operator or role-based access" framing: it's not staff at all, it's
  students operating the app directly, which is why its adapter (§9) is
  scoped down structurally rather than just hidden by UI.

**Library domain — still open:**
- Fine amounts and loan duration — real numbers from the school, not the
  placeholders in §6.

**New, from the logging system (§11):**
- **`activity_log.actor`** is now partly answered by the three-surface
  decision above: on the self-service booth, the student identifies
  themselves to check a book out, so `actor` can genuinely be their
  `student_id` for those events. On the librarian admin surface, the
  plan is still a single shared 6-digit PIN (`database_layer_design.md`
  §2 & §12), which unlocks the app but can't say *which staff member*
  performed a given action. If "which librarian did this" matters for
  accountability, that's a vote for per-user staff logins — worth
  deciding together with that still-open question rather than
  separately. Self-service actions don't have this gap; staff actions
  still do.
- Does the school's data-handling policy require logging *reads* of
  sensitive fields (national ID, etc.), not just writes? §11 assumes
  writes-only by default; confirm before treating that as settled.
