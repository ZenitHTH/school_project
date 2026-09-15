# UI Layer Design — Student Management & Librarian Management (separate apps)

Covers the UI layer of **Student Management** and **Librarian
Management** — two separate applications, each its own build and
executable, running on separate PCs (`design_doc.md` §8,
`database_layer_design.md` §12). The self-service checkout booth is a
third, separate application, out of scope here for the same reason as
before — it doesn't share a UI with either of these.

## 1. App shell & flow

No launcher — these are two separate installed programs, each opening
directly into its own screens:

```
Student Management app                Librarian Management app
        │                                       │
        ▼                                       ▼
   PIN entry                               PIN entry
   (unlocks student.sqlite)                (unlocks library.sqlite)
        │                                       │
        ▼                                       ▼
   Student List / Search              Catalog Browse / Search
   (§2 below)                          (§3 below)
```

PIN entry happens before anything else in both apps, since neither can
read its database without the derived key
(`database_layer_design.md` §2). Each app has its own PIN/encryption
setup — they're independent databases, so there's no reason the same PIN
has to unlock both.

## 2. Student Management

| Screen | Purpose |
|---|---|
| Student List / Search | FTS-backed search (`application_layer_design.md` §4) across ID, national ID, name. Filter by class/room/status. |
| Student Detail | Tabs: **Profile** (name, national ID, gender, status badge), **Enrollment** (current class/room + enrollment history), **History** (transfers, leave, retentions, room changes, and the ID/name-change audit trail — read-only views of the audit tables). |
| Promote Students (year-end) | **Bulk** operation — the one exception to "everything is one-by-one" (`application_layer_design.md` §3's confirmed answer was about *room rebalancing*, not this). Grade promotion genuinely happens to the whole school at once every year, so this gets its own screen: pick the academic year/semester, confirm the grade-mapping rule (each room moves up one grade, rooms reassigned per the school's usual random-room process), review a summary, commit. Calls `enrollment_service.enroll_next_period` once per affected student inside one outer transaction — a partial promotion (half the school moved up, half not) is a much worse failure state than a partial room-rebalance ever was. |
| Import / Re-import Data | Wraps `build_db.py`, including the re-import safeguard (`design_doc.md` §6) — refuses to run silently against a database that already has live app history. |
| Activity Log | Shared component (§4) — shows this app's own local log only (`student.sqlite`'s `activity_log`), not Librarian Management's. |

Quick edit actions (Update Status, Change Classroom, Change Student ID,
Update Name) open as **dialogs from Student Detail**, not their own full
screens — they're short forms with a reason field, not multi-step flows.
Change Student ID is the one exception worth a slightly heavier dialog:
given it's a primary-key change with cascading effects
(`application_layer_design.md` §3), require the new ID to be typed twice
(new value + confirmation) rather than a single-click confirm, matching
how consequential the operation actually is.

## 3. Librarian Management

| Screen | Purpose |
|---|---|
| Catalog Browse / Search | FTS-backed search, filter by category (dropdown from `categories`, §5 of `database_layer_design.md` — never free text). |
| Sync Student Data | Import a snapshot file from Student Management (`database_layer_design.md` §12). Shows a **diff preview** first — new students, changed fields (old → new, status changes visually flagged), any student missing from the snapshot, and any ID renumbering — before an explicit "Apply" commits it. Never a silent overwrite. |
| Book Detail | Title/author/ISBN/category/shelf location; list of copies with each copy's tracking barcode and status; "add copies" action; "mark copy status" action (lost/damaged/retired) with a reason field, writing to `book_copy_status_log`. |
| Checkout / Return | Staff-operated manual version — librarian scans/enters a copy's tracking barcode and looks up the student via the embedded mini search (§4). Distinct from the booth app, but calls the same `loan_service.checkout`/`return_book`. |
| Current Loans | Live table of every active loan — who has what, due date, overdue rows visually flagged. |
| Student Borrowing History | Mini student search (§4) → that student's full loan history. |
| Book Borrow History | Per book/copy — everyone who's ever had this specific copy, directly serving the accountability requirement that drove the two-barcode design in the first place. |
| Reservations | Waiting list per book; manual "mark ready" action since automated notification isn't in the v1 plan. |
| Fines | Outstanding fines list; record-payment action. |
| Categories | Manage the `categories` lookup table — add a new one when genuinely needed. |
| Activity Log | Shared component (§4) — shows this app's own local log only (`library.sqlite`'s `activity_log`), not Student Management's. |

## 4. Shared components (used across both apps)

- **Mini student search** — one component, backed by
  `student_service.search`, embedded two ways: as the *main* screen in
  Student Management (live source-of-truth data), and as a lookup widget
  inside Librarian Management's Checkout/Return and Student Borrowing
  History screens (the periodically-synced local mirror,
  `database_layer_design.md` §12 — same component, same adapter call,
  just pointed at a different local database depending on which app it's
  built into).
- **Activity Log viewer** — same reusable component built into both
  apps, but each shows only **its own local log** — `student.sqlite`'s
  in Student Management, `library.sqlite`'s in Librarian Management.
  These are separate databases on separate PCs now (not sections of one
  app), so there's no cross-app view unless the two logs are explicitly
  merged — which is exactly the open "unified activity log" question in
  `database_layer_design.md` §13, not solved here. Don't design this
  screen as if it can show the other app's history; it can't, as things
  stand.

## 5. Adapters (from `application_layer_design.md` §9)

| App | Adapter | Wraps |
|---|---|---|
| Student Management | `student_admin_adapter.py` (in `apps/student_management_app/`) | `student_service` (full — search, get, `update_status`, `change_student_id`, `update_name`) + `enrollment_service` (full — `current_enrollment`, `change_classroom`, `enroll_next_period`) |
| Librarian Management | `librarian_admin_adapter.py` (in `apps/librarian_management_app/`) | `catalog_service`, `loan_service`, `reservation_service`, `fine_service`, plus read-only `student_service.search`/`get` for history lookups |

Each adapter lives inside its own app's folder, not a shared one — they
translate `Result` into Qt signals/properties, and neither is reachable
from the booth app, which is a fully separate application with its own
adapter (`application_layer_design.md` §9).

## 6. Open questions

- **Promote Students, per-room override**: is "everyone up one grade,
  rooms reassigned per the usual process, review, commit" enough, or
  does staff need to override specific students' next room *before*
  committing (rather than fixing exceptions afterward with individual
  `change_classroom` calls)? Affects whether §2's bulk screen needs an
  editable preview table or just a summary + confirm.
- **Home-screen quick-stats**: each app currently opens straight into
  its main list/search screen with no dashboard numbers. Worth adding
  at-a-glance stats (total students, books currently out) to either
  app's landing screen later, or is that unnecessary?
- **Activity Log cross-app visibility** (§4): confirmed each app only
  shows its own local log for now — is that acceptable, or does the
  unified view flagged as open in `database_layer_design.md` §13 need to
  happen sooner rather than later?
