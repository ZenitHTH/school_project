# File Locations — Windows, Linux, macOS

Where each app keeps its files on the three OS families. **Assumption to
confirm**: "3 OS family" is read as Windows, Linux, and macOS — earlier
docs only planned for Windows and Linux (`design_doc.md` §2, §10). If
macOS is genuinely in scope, see §6 for what it adds.

## 1. Files each app creates

| File | Purpose |
|---|---|
| `student.sqlite` / `library.sqlite` | The encrypted database (`database_layer_design.md` §12) |
| `*-wal`, `*-shm` | SQLite sidecar files created by WAL mode (§1 of the database doc) — **must stay in the same folder as the database** |
| `*.salt` + lockout counter | PIN key-derivation salt and failed-attempt count (`database_layer_design.md` §2) |
| `backups/` | Pre-migration / pre-import copies (`database_layer_design.md` §10) |
| `config` | Last-opened database path, library barcode prefix (`SMTE`), policy settings |
| `logs/` | Technical error/crash logs — **not** the `activity_log` table, which lives inside the database |
| Exports | Student snapshot for LINE, label-sheet PDFs — user-chosen, see §4 |

## 2. Default locations

Don't hand-build these paths. Use the `platformdirs` Python library
(small, pure Python, fine for old hardware) so each OS's own convention
is followed:

| | Windows | Linux | macOS |
|---|---|---|---|
| Database, salt, backups, config | `%LOCALAPPDATA%\<app>\` | `~/.local/share/<app>/` | `~/Library/Application Support/<app>/` |
| Logs | under the same `%LOCALAPPDATA%\<app>\` tree | `~/.local/state/<app>/` | `~/Library/Logs/<app>/` |

`<app>` is a per-app folder name — `SMTE-StudentManagement`,
`SMTE-LibrarianManagement`, `SMTE-Booth` — so two apps installed on the
same PC never write to each other's files. Exact log subfolders are
whatever `platformdirs` returns; the point is to call the library, not
copy this table into code.

## 3. Rules that avoid real problems

- **Never write next to the executable.** `Program Files` (Windows) and
  system install folders are read-only for normal users. Worse,
  PyInstaller's single-file builds unpack to a temporary folder on every
  launch and delete it afterward — a database saved there would silently
  vanish. Data always goes to the user-data folder above.
- **Location must be configurable, not only derived.** The app already
  opens databases through a file picker (`design_doc.md` §6), so the
  default is just where the picker starts and what gets remembered in
  `config`. This matters for one open question: if the Booth app ends up
  sharing `library.sqlite` on the same PC as Librarian Management
  (`database_layer_design.md` §13), it needs to *point at* that file, not
  create its own copy under its own `<app>` folder.
- **Per-user by default, and that has a catch.** `%LOCALAPPDATA%` and its
  Linux/macOS equivalents belong to one OS user account. If several
  staff log into the same PC under different accounts, each would get a
  separate, empty database. Fine for one shared login; if that's not how
  the school works, pick one shared folder on first run through the same
  picker instead.
- **Keep the database and its sidecar files together** (§1) — moving or
  backing up only the `.sqlite` file while the app is open can lose
  recent writes. Backup procedure is in `database_layer_design.md` §10.
- **Test with a Thai-named user folder.** Thai staff may well have Thai
  characters in their OS username, so paths like
  `C:\Users\<Thai name>\AppData\...` are realistic. Python handles this
  fine in general, but SQLCipher is a native library bundled into the
  packaged build, so it's worth one explicit test on a real Windows
  machine rather than assuming.
- Build paths with `pathlib`, never string-concatenated separators.

## 4. User-chosen locations (exports)

- **Import Student Snapshot** (received over LINE): open the file dialog
  at the user's Downloads folder first — where a received file most
  likely landed — and remember the last folder used afterward.
- **Export Student Snapshot** and **label-sheet PDFs**: default the save
  dialog to the user's Documents folder; the person prints or sends from
  there.

## 5. Updating and removing (portable archive)

Distribution is a portable archive first (`design_doc.md` §10b), so
there's no installer and no uninstaller. Because data lives in the
user-data folder, not the program folder:

- **Updating** = replace the program folder with the new version; the
  database is untouched, which is the behavior wanted.
- **Removing** = delete the program folder. **That does not delete
  student data** — it stays in the user-data folder. If the school ever
  needs a PC wiped of it, that's a deliberate manual step, worth stating
  in the rollout notes given to staff.
- The program folder can be anywhere, including a USB stick, but the
  database will not follow it (§3's note on per-PC data).

## 6. What macOS adds, if it's in scope

- Build artifacts go from six to **nine** (three apps × three OS,
  `design_doc.md` §10), and macOS builds have to be made on a Mac —
  PyInstaller can't cross-compile.
- Unsigned apps trigger Gatekeeper warnings on first launch; decide
  whether staff are told to right-click → Open, or whether the school
  wants signed builds (an Apple developer account and recurring cost —
  probably not worth it for a first launch).
- SQLCipher's native library has to be bundled for macOS too, tested the
  same way as on Windows and Linux (`database_layer_design.md` §1).

## 7. Open questions

- Is macOS actually in scope, or does "3 OS family" mean something else
  (for example Windows 7/10/11, or Linux distributions)? Changes §6
  entirely.
- Do multiple staff share one OS login on each PC, or does each have
  their own account? Decides whether per-user folders (§3) are fine or
  a shared location is needed.
