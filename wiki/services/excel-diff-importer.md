# Excel Diff Importer Architecture (`core/importers/xlsx_diff_importer.py`)

## 1. Overview
The Excel Diff Importer handles recurring annual roster imports (e.g. at the start of a new academic year). Instead of wiping existing data or causing primary key duplicate errors, it calculates a structural diff against the database and executes promotions non-destructively.

---

## 2. Key Phases

### 2.1 Fast Read-Only Streaming (`parse_roster_sheets`)
- Opens `.xlsx` using `openpyxl.load_workbook(file_path, read_only=True, data_only=True)`.
- Scans grade sheets (`ม.1` through `ม.6`).
- Extracts header title metadata using regex (`TITLE_RE`, `YEAR_RE`, `SEM_RE`).
- Cleans and splits full names into prefix, first name, last name, and gender via `split_name(c)`.

### 2.2 Diff Calculation (`calculate_xlsx_diff`)
Returns a `Result[dict, str]` containing:
1. `new_students`: Students in Excel file whose IDs do not exist in the database.
2. `grade_room_changes`: Existing students moving to a new grade level or room (promotions).
3. `missing_students`: Active students in DB not present in the current Excel roster.
4. `identity_conflicts`: Students whose registered names differ between the file and database.
5. **Warnings**: Attached via `.with_warning(...)` when conflicts or missing records are flagged.

### 2.3 Atomic Application (`apply_xlsx_diff`)
- Executed inside a single SQLite transaction `with conn:`.
- Inserts new students into `students` table.
- Appends new term enrollment records into `enrollments` table without modifying historical enrollments from previous years.
- Records activity in `activity_logs`.
