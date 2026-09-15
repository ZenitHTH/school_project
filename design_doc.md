# Student Manager — Design Doc

## 1. Goal

A desktop application for managing student records (roster, enrollment,
transfers, leave, retention history) that runs well on school PCs, many of
which are 8+ years old, across a mix of Windows and Linux machines. The UI
must adapt to different screen resolutions and support adding new UI
components over time without rework.

## 2. Constraints

- **Hardware**: mixed fleet, many low-spec (8+ year old) PCs. Rules out
  Electron/web-view-based UI frameworks — too much memory/CPU overhead.
- **OS**: mix of Windows and Linux. Needs one codebase, compiled per OS.
- **UI**: must look modern ("beautiful"), and must resize/reflow across
  resolutions and let new screens/components be added without rewriting
  layout code.
- **Data**: source of truth today is a hand-maintained xlsx roster. Already
  converted to SQLite via `build_db.py` — this becomes the app's database.

## 3. Stack

| Layer | Choice | Why |
|---|---|---|
| UI | PySide6 + Qt Quick (QML) | Native-compiled widgets (light on old hardware), anchor/layout system built for resolution independence, modern look out of the box |
| App logic | Plain Python classes | No framework needed for CRUD + validation at this scale |
| Data | SQLite (already built) | Zero-install embedded DB, fine for a single school's data volume |
| Packaging | PyInstaller (or Nuitka if size/speed matters later) | Produces a standalone binary per OS, no Python install needed on target PCs |

## 4. Architecture

```
┌─────────────────────────────────────────────┐
│                Student manager                │
│                                               │
│  ┌─────────────────────────────────────────┐ │
│  │  UI layer (QML)                          │ │
│  │  Screens, adaptive layout, no DB access  │ │
│  └───────────────────┬───────────────────────┘ │
│                      ↓                        │
│  ┌─────────────────────────────────────────┐ │
│  │  Application layer (Python)              │ │
│  │  StudentService, EnrollmentService, etc. │ │
│  │  validation + business rules             │ │
│  └───────────────────┬───────────────────────┘ │
│                      ↓                        │
│  ┌─────────────────────────────────────────┐ │
│  │  Data layer                              │ │
│  │  school.sqlite (already built)           │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
        ↑
   xlsx roster → build_db.py (one-time / on re-import)
```

**Rule**: QML never touches SQLite directly. It calls into Python service
objects exposed via `QObject`/`Property`/`Slot`. This keeps the DB swappable
and the UI testable without a real database.

## 5. Data model (as built by `build_db.py`)

The xlsx-to-SQLite conversion is done and working (verified: 2,807 students,
2,648 enrollments imported). Tables:

- **students** — one row per student: `student_id` (PK), `national_id`,
  `prefix`, `first_name`, `last_name`, `full_name`, `gender`, `status`
  (`active` / `on_leave` / `transferred_out`).
- **enrollments** — which grade/room/track a student is in per
  academic year + semester. Unique per `(student_id, year, semester,
  grade_level, room)`.
- **room_changes**, **transfers_out**, **transfers_in**,
  **leave_of_absence**, **retentions** — history/event tables, each
  referencing `students.student_id`.
- **v_class_statistics** (view) — male/female/total counts per
  year/semester/grade/room/track, computed live instead of hand-typed.

This schema is the contract the application layer is built against. No
changes needed here to start on the app layer — flag now if fields are
missing (e.g. contact info, address, guardian) so the schema is amended
before code is built on top of it.

## 6. File import & validation

The app doesn't assume a fixed file location — the user opens a file via a
picker, and the app decides what to do based on what's actually in it.

**Flow:**

1. User opens a file (`.xlsx` or `.sqlite`).
2. **If `.sqlite`**: validate schema before opening as the working
   database — check that the expected tables exist (`students`,
   `enrollments`, `room_changes`, `transfers_out`, `transfers_in`,
   `leave_of_absence`, `retentions`) with their key columns
   (e.g. `students.student_id`, `students.full_name`). If any required
   table/column is missing → **refuse**, show a warning ("This database
   doesn't match the expected student database — missing table(s):
   ..."), and don't open it. If it matches → open it directly, skip
   import.
3. **If `.xlsx`**: validate structure before touching anything:
   - Required sheet names present (`ม.1`–`ม.6`, etc. per `GRADE_SHEETS`
     in `build_db.py`)
   - Expected header markers found in at least one grade sheet (the `ที่`
     block marker `build_db.py` already looks for)
   - If validation fails → **refuse**, show a clear warning ("This doesn't
     look like a student roster file — no recognizable class sheets
     found"), and do not run `build_db.py`. Never guess or partially import
     an unrecognized file.
   - If validation passes → **check whether this would be a re-import
     into a database that already has live app data** (any row in
     `activity_log`, or any `book`/`loan` data at all — see below). If
     so, show an explicit warning before proceeding: re-running
     `build_db.py` wipes and rebuilds the student tables from scratch
     (§5), which would silently erase any status/name/ID changes made
     through the app since the last import, since SQLite is the source
     of truth from here on (§11). Require an explicit confirmation,
     not a default "yes."
   - Otherwise (first-time setup, empty/fresh database) → run
     `build_db.py` against it to build the working `school.sqlite`, then
     open that.
4. **Any other file type** → refuse immediately, no validation attempt.

This validation is a lightweight pre-check — required tables/columns for
sqlite, required sheet names + one structural marker for xlsx — not a full
parse. It exists to stop someone from pointing the app at an unrelated
file, not to catch every malformed roster. Genuinely malformed *roster*
files (right sheets, bad rows) surface as row-level errors during the
actual `build_db.py` run, reported back to the user rather than silently
skipped. Sqlite schema checks use `PRAGMA table_info` / `sqlite_master`,
not a full read of the data.

**Confirmed: xlsx import is a one-time/initial-setup operation, not a
recurring sync.** Once the app is in use, `school.sqlite` is the source
of truth (§11) — student edits happen through the app's own screens, not
by editing the spreadsheet and re-importing. The guard above exists
specifically because the same `build_db.py` script is still useful for
the very first setup and for a genuine "start over from a spreadsheet"
scenario, but must never run silently against a database that already
has real app history in it.

## 7. Application layer (next to build)

One service class per table family, e.g.:

- `StudentService` — get/search/create/update student, change status
- `EnrollmentService` — current class list per room, enroll/re-enroll
- `HistoryService` — transfers, leave, retentions (read-mostly, mostly for
  reporting)

Each service owns its SQL and validation; nothing above it writes raw SQL.

## 8. UI layer — three separate apps, not one with sections

**Confirmed structure**: Student Management, Librarian Management, and
the self-service checkout booth are **three separate applications** —
each its own build, own executable, own database file, deployed to
different PCs. There is no launcher joining them; each opens directly
into its own screens. Full detail on Student Management's and Librarian
Management's screens lives in `ui_layer_design.md`; this section stays a
summary, and the two-database sync design lives in
`database_layer_design.md` §12.

- **Student Management** — student search, student detail
  (profile/enrollment/history), the sensitive edit actions
  (`update_status`, `change_classroom`, `change_student_id`,
  `update_name`, plus a bulk "promote students" flow for the yearly
  grade progression), and the xlsx import/re-import screen (§6). Owns
  `student.sqlite`, the source of truth for student data.
- **Librarian Management** — catalog, checkout/return (staff-operated,
  distinct from the booth), current loans, per-student and per-book
  borrowing history, reservations, fines, and category management. Owns
  `library.sqlite` (the library domain), plus a read-only mirror of
  student data refreshed from Student Management on a periodic/on-demand
  sync (`database_layer_design.md` §12) — not live, confirmed acceptable.
- **Self-service booth** — students checking books out themselves.
  Separate build; its database relationship to Librarian Management
  (same file/live vs. its own periodic sync) is still an open question
  (`database_layer_design.md` §13).

Each app gets its own thin adapter (`application_layer_design.md` §9)
exposing only the service calls it needs — the booth's is the narrowest,
since it's the one surface a student operates directly rather than staff.

Built with QML `Layouts`/anchors (not fixed x/y), so screens reflow across
resolutions from old 1366×768 laptops up.

## 9. Project structure

This is a new project, and the intent is for it to grow into a large app
over time — so the layout is organized by *layer first, domain second* from
day one, rather than one flat folder of scripts. Easy to read: anyone can
guess which folder a file lives in from its job. Easy to write: adding a
new feature means adding a folder, not touching existing ones.

```
student_manager/
├── apps/
│   ├── student_management_app/   # owns student.sqlite (§8)
│   │   ├── main.py
│   │   └── qml/
│   ├── librarian_management_app/ # owns library.sqlite + student mirror
│   │   ├── main.py               #   (§8, database_layer_design.md §12)
│   │   └── qml/
│   └── booth_app/                 # separate self-service checkout build
│       ├── main.py
│       └── qml/
├── core/                    # application layer — no Qt imports here,
│   ├── student/               #   shared by all apps above; which
│   │   └── services/          #   local db each app's data/db.py points
│   │       ├── student_service.py   #   at is what actually differs
│   │       └── enrollment_service.py
│   ├── library/
│   │   └── services/
│   │       ├── catalog_service.py
│   │       ├── loan_service.py
│   │       ├── reservation_service.py
│   │       └── fine_service.py
│   ├── importers/
│   │   ├── xlsx_validator.py   # sheet/structure pre-check
│   │   └── build_db.py         # existing import script, moved in as-is
│   └── shared/
│       ├── result.py
│       ├── errors.py
│       └── log_service.py       # activity_log writer
├── data/
│   ├── db.py                # connection + key + PRAGMAs
│   ├── migrate.py
│   ├── migrations/
│   ├── sync/                 # diff.py (compare, no writes) + apply.py
│   │                          #   (the actual transaction), §12
│   └── repositories/
├── resources/               # icons, fonts, default sqlite template
├── tests/
│   ├── test_services/
│   └── test_importers/
├── packaging/
│   ├── student_management_windows.spec
│   ├── student_management_linux.spec
│   ├── librarian_management_windows.spec
│   ├── librarian_management_linux.spec
│   ├── booth_app_windows.spec
│   └── booth_app_linux.spec
└── requirements.txt
```

**Rules that keep this from rotting as it grows:**
- `core/` never imports from `apps/` — logic must run and be testable
  without Qt at all, and must work identically whichever app calls it.
- `apps/*/qml/` never writes SQL — only calls `core/` through its app's
  adapter.
- One file per screen, one file per service. When a service file gets big,
  split by sub-feature, not by arbitrary line count.
- `build_db.py` moves into `core/importers/` unchanged at first — refactor
  it once the app layer actually needs to call into it (e.g. return a
  structured result instead of `print()`-ing a report), not before.

## 10. Packaging

Three separate apps means **six build artifacts**: `student_management`,
`librarian_management`, and `booth_app`, each for Windows and Linux.
`PyInstaller` builds run separately on a Windows machine and a Linux
machine (cross-compiling isn't reliable) per app. Test each packaged
build on actual old hardware before rollout — the booth app in
particular is meant to be lightweight enough to run on whatever
spare/dedicated PC ends up at the checkout desk, so it's worth confirming
it's genuinely lighter than the other two, not just smaller in screen
count.

## 11. Open questions

- ~~Does the xlsx get re-imported periodically, or is SQLite the new
  source of truth going forward?~~ **Resolved: SQLite is the source of
  truth from launch onward.** Student edits happen only through the
  app's own screens (§6, §8) — xlsx import is a one-time/initial-setup
  operation, not a recurring sync. See the guard added to §6 to stop a
  well-meaning re-import from wiping out app-made edits.
- **Deferred, not in the first build**: an export-to-xlsx feature (the
  reverse direction — pulling data *out* of the app back into a
  spreadsheet) was raised as something the school might want later.
  Noted here so it isn't forgotten, not scheduled yet.
- ~~Any fields needed beyond what's in the current schema (contact info,
  guardian, address, photo)?~~ **Resolved: no, the current fields are
  enough.** The `students` table stays as-is — no guardian/contact,
  address, or photo storage needed.
- ~~Single-user or multiple PCs sharing one database?~~ **Superseded by
  a more specific answer**: it turned out Student Management and
  Librarian Management are two separate PCs *from launch*, not a future
  concern — see §8 and `database_layer_design.md` §12 for the
  periodic-sync design this led to. True *live* multi-PC access (two
  people editing the same live data simultaneously) is still deferred,
  per `database_layer_design.md` §11.
