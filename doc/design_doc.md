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
| UI | Qt Quick (QML) via PySide — **version depends on Windows 7 support, see §10a** | Native-compiled widgets (light on old hardware), anchor/layout system built for resolution independence, modern look out of the box |
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
   - If validation passes → run through the **diff-preview import** in
     §6a, not a blind rebuild — this is the corrected flow, replacing the
     earlier one-time-only assumption below.
4. **Any other file type** → refuse immediately, no validation attempt.

This validation is a lightweight pre-check — required tables/columns for
sqlite, required sheet names + one structural marker for xlsx — not a full
parse. It exists to stop someone from pointing the app at an unrelated
file, not to catch every malformed roster. Genuinely malformed *roster*
files (right sheets, bad rows) surface as row-level errors during the
actual import run, reported back to the user rather than silently
skipped. Sqlite schema checks use `PRAGMA table_info` / `sqlite_master`,
not a full read of the data.

## 6a. Corrected: xlsx re-import is a recurring, expected operation

**Superseded decision, worth stating plainly**: §11 previously confirmed
xlsx import as one-time/initial-setup only, with SQLite as the source of
truth from launch onward. That turned out to be wrong for one specific
case — **yearly grade/classroom promotion happens by re-importing a new
xlsx**, not through an in-app bulk action. This is a normal, expected,
recurring event (once a year), not the rare "start over from scratch"
scenario the original safeguard assumed.

That matters because `build_db.py`'s current behavior — drop and rebuild
the student tables from scratch, straight from the xlsx — would silently
**erase** any status change, name correction, or student ID fix made
through the app during the year, if the new xlsx doesn't happen to
reflect that same change. A blind rebuild was never safe for a recurring
operation; it was only ever safe for a true first-time import.

**Fix: reuse the same diff-preview pattern already designed for the
cross-app student data sync** (`database_layer_design.md` §12), rather
than inventing a second mechanism for what's structurally the same
problem — reconciling an external file against live local data:

1. **Parse** the new xlsx (same logic `build_db.py` already has for
   reading sheets into structured rows) without writing anything yet.
2. **Diff** against the current `students`/`enrollments`, same
   categories as §12's sync preview:
   - **New students** (in the xlsx, not yet in the database) → will be
     added.
   - **Grade/room changed** (the normal case for nearly every returning
     student each year) → will be applied via `enroll_next_period`
     (`application_layer_design.md` §3) — a genuinely new enrollment
     period, not an overwrite of history, exactly as that function was
     always meant to work.
   - **Missing from the new xlsx** (in the database, not in the file —
     e.g. already graduated or transferred out) → flagged, never
     auto-deleted, consistent with the rest of this design.
   - **Identity fields differ** (name or status differs between the
     xlsx and the current database) → flagged for explicit review,
     specifically because the app may have already corrected exactly
     this through `update_name`/`update_status` — the xlsx's version
     doesn't automatically win.
3. **Review and confirm** — staff see the categorized diff before
   anything is written, same screen pattern as the Librarian
   Management sync preview.
4. **Apply**, all inside one transaction — every affected student's
   `enroll_next_period` call (or new-student insert) succeeds or none
   do, matching the "a half-completed promotion is worse than a
   half-completed room rebalance" reasoning this design already used
   once before.

**This also removes a screen, not just a bug**: with promotion driven by
re-importing the new xlsx, the standalone "Promote Students" bulk screen
originally planned for Advanced Student Management isn't needed —
importing the file *is* the promotion. One less screen to build, and one
less place the same operation could be triggered two different ways.

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

**Bundle as a one-folder build, not one file.** Ship the exe together
with its library folder (Python, Qt, SQLCipher) as a portable archive (§10b),
so staff can't separate them. Single-file builds unpack to a temp folder
on every launch, which is slow on old PCs and fails if temp is locked
down.

## 10a. Windows 7 compatibility (decision needed)

**Confirmed**: the school's PCs run a mix of Windows 7, 10, and 11. That
conflicts with the stack in §3 as written: Qt 6 (PySide6) targets
Windows 10 and newer, and Python 3.9+ no longer runs on Windows 7
(verify both against current PySide6/Python docs before committing).

| Option | What it means | Cost |
|---|---|---|
| **A. Single Qt 5.15 / PySide2 / Python 3.8 baseline** (recommended if any Windows 7 PC will run these apps) | One codebase, one build per OS, runs on Windows 7, 10, and 11 | Older, end-of-life toolchain; pin every dependency (`reportlab`, `python-barcode`, `openpyxl`, `platformdirs`, SQLCipher binding) to versions that still support Python 3.8; QML imports must be versioned (`import QtQuick 2.15`) |
| B. Two builds: Qt 6 for Windows 10/11 + Qt 5 legacy build for Windows 7 | Modern stack where possible | Doubles the packaging and test matrix; PySide2/PySide6 API differences need a compatibility layer |
| C. Retire or upgrade the Windows 7 PCs | Simplest software, one modern stack | Not the software's decision; Windows 7 is also long out of security support |

For an offline school desktop app, an older pinned toolchain is a
smaller risk than a machine that can't run the app at all — so A is the
default recommendation, with the door open to move to Qt 6 once the
last Windows 7 PC is gone.

**Two checks either way**: (1) Windows 7 needs its Universal C Runtime
update installed for Python 3.8 builds to start — confirm on a real
Windows 7 PC, not assumed. (2) FTS5's `trigram` tokenizer needs SQLite
3.34+ (`student_search_algorithm.md` §2) and the categories migration
wants 3.35+ for `DROP COLUMN` (`database_layer_design.md` §5) — confirm
the SQLite version bundled inside whichever SQLCipher build ends up
available for Python 3.8, since older builds may bundle an older SQLite.

**What would narrow this**: which of the three apps will actually run
on a Windows 7 machine. If none of the Student Management or Librarian
Management PCs is on Windows 7, only the Booth app's PC matters — and
that could be the one place to solve it.

## 10b. Distribution: portable archive first

**Decision**: v1 ships as a portable archive per app per OS — no
installer yet. The one-folder build from §10 is archived as-is; staff
extract it and run the exe. Installers (Inno Setup for Windows,
`.deb`/AppImage for Linux, `.dmg` for macOS) are deferred, not dropped:
the freeze step is identical either way, so nothing is redone later.

Freeze (per app, per OS, driven by the `.spec` files in `packaging/`):
`pyinstaller --noconfirm --onedir --windowed --name SMTE-StudentManagement apps/student_management_app/main.py`
— built with **Python 3.8** for the Windows 7-capable build (§10a).

**Portable means the program, not the data.** The database stays in the
user-data folder (`file_locations_design.md` §2), so running the app
from a USB stick on another PC starts with an empty database on that PC.

**Rules for a portable archive**
- **Format**: `.zip` on Windows; `.tar.gz` on Linux and macOS. Zip does
  not reliably keep the executable permission on those systems, so the
  app could fail with "permission denied" until someone runs `chmod +x`.
- **Extract to a short path, ideally without Thai characters** (for
  example `C:\SMTE\StudentManagement\`). Windows 7 has a 260-character
  path limit and the library folder is deeply nested; Thai characters in
  the path are one more thing to test, not assume.
- **Windows "Unblock"**: an archive received over LINE or downloaded is
  marked as coming from the internet, and Windows may show SmartScreen
  warnings for the extracted exe. Right-click the `.zip` → Properties →
  **Unblock** *before* extracting.
- **No shortcut is created**: the README tells staff to right-click the
  exe → Send to → Desktop (create shortcut).
- **Windows 7 prerequisites are now manual**: with no installer script
  to check for them, the Universal C Runtime update and Visual C++
  runtime have to be listed in the README and confirmed on a real
  Windows 7 PC.
- **Updating**: delete the old folder and extract the new version fresh
  (extracting on top can leave stale files behind). Data is untouched;
  migrations run on first start, with a backup first
  (`database_layer_design.md` §10).
- **Removing**: delete the folder. Data stays in the user-data folder.
- **Version visible**: put the version in the archive name
  (`SMTE-StudentManagement-1.0.0-win.zip`) and on an About/footer line in
  the app, since there's no installer record of what's installed — staff
  need a way to tell you which build they're running.
- **Unsigned executables** may trigger SmartScreen and some antivirus
  products; plan a short "More info → Run anyway" note in the README
  and test with the school's real antivirus (§10).

**Deliverables**: one archive per app per OS — six, or nine if macOS is
confirmed (`file_locations_design.md` §6).

## 11. Open questions

- ~~Does the xlsx get re-imported periodically, or is SQLite the new
  source of truth going forward?~~ **Corrected, this was answered wrong
  the first time**: it's **both**, split by field. Day-to-day student
  edits (status, name, ID corrections) happen through the app (§6, §8) —
  SQLite is the source of truth for those. But **grade/classroom
  assignment specifically is driven by a yearly xlsx re-import** (§6a),
  which is a real, recurring, expected operation, not a one-time setup
  step. The original safeguard treated re-import as a rare emergency;
  §6a replaces it with a proper diff-preview flow instead, and removes
  the need for a separate in-app "Promote Students" bulk action.
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
