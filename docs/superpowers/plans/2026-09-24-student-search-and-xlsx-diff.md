# Student Search Algorithm & XLSX Diff-Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Thai-capable trigram FTS5 search algorithm without `national_id` and the non-destructive recurring XLSX diff-preview promotion importer matching updated software design docs.

**Architecture:** 
1. Database migration creates `students_fts` using `tokenize='trigram'` on `full_name` only.
2. `search_parser.py` cleans input and routes queries across grade/room regexes, digit suffix matches, length <3 LIKE fallbacks, and trigram FTS5 queries.
3. `xlsx_diff_importer.py` parses yearly school roster files, calculates structural diffs (new, changed room/grade, missing, conflict), and applies changes atomically.

**Tech Stack:** Python 3.12+, SQLite 3.34+ (FTS5 trigram), openpyxl, pytest.

**Spec:**
- [doc/student_search_algorithm.md](file:///Users/zenithth/Workspace/school_project/doc/student_search_algorithm.md)
- [doc/design_doc.md](file:///Users/zenithth/Workspace/school_project/doc/design_doc.md) §6a
- [doc/application_layer_design.md](file:///Users/zenithth/Workspace/school_project/doc/application_layer_design.md) §3

## Global Constraints
- Do NOT search or index `national_id` in student search.
- ID matching must be suffix-based (`LIKE '%' || query`), not prefix-based.
- Grade/room parser must support: `"ม.1"`, `"ม1"`, `"ม.1/2"`, `"ม1/2"`, `"ม.1.2"`, `"ม1.2"`, `"1/2"`, `"1.2"`.
- XLSX re-import must never blindly wipe tables; it must diff and require confirmation before atomic commit.

---

### Task 1: Migration 0005 — Trigram FTS5 for Students

**Files:**
- Create: `data/migrations/0005_trigram_fts.sql`
- Test: `tests/test_trigram_migration.py`

**Interfaces:**
- Produces: `students_fts` table with `tokenize='trigram'` containing only `full_name`.

- [ ] **Step 1: Write the failing test for 0005 migration**
```python
# tests/test_trigram_migration.py
import sqlite3
from data.migrate import run_migrations

def test_trigram_students_fts_creation():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    
    # Insert Thai student
    conn.execute("INSERT INTO students (student_id, full_name, status) VALUES (1001, 'นายเจษฎา งาคชสาร', 'active')")
    
    # Substring search in middle of first name should match with trigram
    cur = conn.execute("SELECT rowid FROM students_fts WHERE students_fts MATCH 'ษฎา'")
    rows = cur.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 1001
```

- [ ] **Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_trigram_migration.py -v`
Expected: FAIL (either migration doesn't exist or substring match fails).

- [ ] **Step 3: Write migration SQL**
Create `data/migrations/0005_trigram_fts.sql`:
```sql
-- Migration 0005: Recreate students_fts with trigram tokenizer on full_name only
DROP TRIGGER IF EXISTS students_ai;
DROP TRIGGER IF EXISTS students_ad;
DROP TRIGGER IF EXISTS students_au;
DROP TABLE IF EXISTS students_fts;

CREATE VIRTUAL TABLE students_fts USING fts5(
    full_name,
    content='students',
    content_rowid='student_id',
    tokenize='trigram'
);

CREATE TRIGGER students_ai AFTER INSERT ON students BEGIN
    INSERT INTO students_fts(rowid, full_name)
    VALUES (new.student_id, new.full_name);
END;

CREATE TRIGGER students_ad AFTER DELETE ON students BEGIN
    INSERT INTO students_fts(students_fts, rowid, full_name)
    VALUES ('delete', old.student_id, old.full_name);
END;

CREATE TRIGGER students_au AFTER UPDATE ON students BEGIN
    INSERT INTO students_fts(students_fts, rowid, full_name)
    VALUES ('delete', old.student_id, old.full_name);
    INSERT INTO students_fts(rowid, full_name)
    VALUES (new.student_id, new.full_name);
END;

INSERT INTO students_fts(rowid, full_name)
SELECT student_id, full_name FROM students;
```

- [ ] **Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_trigram_migration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add data/migrations/0005_trigram_fts.sql tests/test_trigram_migration.py
git commit -m "feat(db): migrate students_fts to trigram tokenizer on full_name"
```

---

### Task 2: Student Search Query Parser & Routing

**Files:**
- Create: `core/student/services/search_parser.py`
- Modify: `data/repositories/student_repo.py`
- Modify: `core/student/services/student_service.py`
- Test: `tests/test_search_algorithm.py`

**Interfaces:**
- Consumes: `parse_grade_room(query)`, `search_students(conn, query, ...)`
- Produces: Ranked student results following `doc/student_search_algorithm.md`.

- [ ] **Step 1: Write comprehensive failing tests for search pipeline**
```python
# tests/test_search_algorithm.py
import pytest
import sqlite3
from data.migrate import run_migrations
from core.student.services.student_service import StudentService

@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    run_migrations(c)
    # Seed test records
    c.execute("INSERT INTO students (student_id, national_id, full_name, first_name, last_name, status) VALUES (54321, '1234567890123', 'นายสมชาย เข็มกลัด', 'สมชาย', 'เข็มกลัด', 'active')")
    c.execute("INSERT INTO students (student_id, national_id, full_name, first_name, last_name, status) VALUES (94321, '9999999999999', 'นางสาวสมหญิง จริงใจ', 'สมหญิง', 'จริงใจ', 'active')")
    c.execute("INSERT INTO enrollments (id, student_id, academic_year, semester, grade_level, room) VALUES (1, 54321, 2567, 1, 'ม.1', 2)")
    c.execute("INSERT INTO enrollments (id, student_id, academic_year, semester, grade_level, room) VALUES (2, 94321, 2567, 1, 'ม.1', 3)")
    c.commit()
    return c

def test_national_id_excluded(conn):
    svc = StudentService(conn)
    res = svc.search("1234567890123")
    assert res.ok
    assert len(res.data) == 0  # national_id is strictly excluded

def test_id_suffix_match(conn):
    svc = StudentService(conn)
    res = svc.search("4321")
    assert res.ok
    assert len(res.data) == 2  # matches 54321 and 94321

def test_grade_room_queries(conn):
    svc = StudentService(conn)
    for q in ["ม.1/2", "ม1/2", "ม.1.2", "1/2"]:
        res = svc.search(q)
        assert res.ok, f"Failed for query {q}"
        assert len(res.data) == 1
        assert res.data[0]["student_id"] == 54321

def test_thai_middle_substring(conn):
    svc = StudentService(conn)
    res = svc.search("เข็ม")
    assert res.ok
    assert len(res.data) == 1
    assert res.data[0]["student_id"] == 54321

def test_short_query_fallback(conn):
    svc = StudentService(conn)
    res = svc.search("สม")
    assert res.ok
    assert len(res.data) == 2
```

- [ ] **Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_search_algorithm.py -v`
Expected: FAIL

- [ ] **Step 3: Implement query parser and repository methods**
Create `core/student/services/search_parser.py`:
```python
import re
from typing import Optional, Tuple

GRADE_WITH_PREFIX_RE = re.compile(r"^ม\.?(\d)(?:[./](\d+))?$")
GRADE_NO_PREFIX_RE = re.compile(r"^(\d)[./](\d+)$")

def clean_query(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()

def parse_grade_room(query: str) -> Optional[Tuple[str, Optional[int]]]:
    clean = clean_query(query)
    m = GRADE_WITH_PREFIX_RE.match(clean) or GRADE_NO_PREFIX_RE.match(clean)
    if not m:
        return None
    grade, room = m.groups()
    return f"ม.{grade}", int(room) if room else None
```
Update `student_repo.py` to support trigram FTS5 ranking (`ORDER BY rank`), ID suffix matching (`LIKE '%' || ?`), and clean routing. Update `student_service.py` to route through `search_parser`.

- [ ] **Step 4: Run tests to verify they pass**
Run: `uv run pytest tests/test_search_algorithm.py -v`
Expected: PASS

- [ ] **Step 5: Run existing repo/service tests**
Run: `uv run pytest tests/test_student_service.py tests/test_repositories.py -v`
Expected: PASS

- [ ] **Step 6: Commit**
```bash
git add core/student/services/search_parser.py data/repositories/student_repo.py core/student/services/student_service.py tests/test_search_algorithm.py
git commit -m "feat(search): implement trigram fts5 and grade/room search pipeline"
```

---

### Task 3: XLSX Diff-Preview Importer Engine

**Files:**
- Create: `core/importers/xlsx_diff_importer.py`
- Test: `tests/test_xlsx_diff_importer.py`

**Interfaces:**
- `calculate_xlsx_diff(conn, file_path, academic_year, semester) -> Result`
  Returns categorized diff:
  - `new_students`: list of student dicts
  - `grade_room_changes`: list of `{student_id, old_grade, old_room, new_grade, new_room}`
  - `missing_students`: list of existing active students absent from file
  - `identity_conflicts`: list of `{student_id, current_name, file_name}`
- `apply_xlsx_diff(conn, diff_data, academic_year, semester, actor) -> Result`
  Applies all changes in single atomic transaction.

- [ ] **Step 1: Write failing test for xlsx diff calculation and application**
```python
# tests/test_xlsx_diff_importer.py
import pytest
import sqlite3
from unittest.mock import patch
from data.migrate import run_migrations
from core.importers.xlsx_diff_importer import calculate_xlsx_diff, apply_xlsx_diff

def test_xlsx_diff_categorization_and_atomic_apply(tmp_path):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    # Seed current student
    conn.execute("INSERT INTO students (student_id, national_id, full_name, status) VALUES (101, '111', 'นายเดิม แท้', 'active')")
    conn.execute("INSERT INTO enrollments (id, student_id, academic_year, semester, grade_level, room) VALUES (1, 101, 2566, 2, 'ม.1', 1)")
    conn.commit()

    # Mock parsed rows from file
    parsed_rows = [
        {"student_id": 101, "national_id": "111", "prefix": "นาย", "first_name": "เดิม", "last_name": "แท้", "full_name": "นายเดิม แท้", "gender": "ชาย", "grade_level": "ม.2", "room": 1, "track": "วิทย์-คณิต"},
        {"student_id": 102, "national_id": "222", "prefix": "เด็กหญิง", "first_name": "ใหม่", "last_name": "สุข", "full_name": "เด็กหญิงใหม่ สุข", "gender": "หญิง", "grade_level": "ม.1", "room": 1, "track": None},
    ]

    with patch("core.importers.xlsx_diff_importer.parse_roster_sheets", return_value=parsed_rows):
        res = calculate_xlsx_diff(conn, "dummy.xlsx", academic_year=2567, semester=1)
        assert res.ok
        diff = res.data
        assert len(diff["new_students"]) == 1
        assert diff["new_students"][0]["student_id"] == 102
        assert len(diff["grade_room_changes"]) == 1
        assert diff["grade_room_changes"][0]["student_id"] == 101
        assert diff["grade_room_changes"][0]["new_grade"] == "ม.2"

        # Apply diff
        apply_res = apply_xlsx_diff(conn, diff, academic_year=2567, semester=1, actor="admin")
        assert apply_res.ok

        # Verify applied in DB
        s102 = conn.execute("SELECT * FROM students WHERE student_id = 102").fetchone()
        assert s102 is not None
        e101 = conn.execute("SELECT * FROM enrollments WHERE student_id = 101 AND academic_year = 2567").fetchone()
        assert e101["grade_level"] == "ม.2"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_xlsx_diff_importer.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `core/importers/xlsx_diff_importer.py`**
Implement sheet reading, diff calculation across existing `students` & `enrollments`, and atomic transaction execution with activity logging.

- [ ] **Step 4: Run tests to verify they pass**
Run: `uv run pytest tests/test_xlsx_diff_importer.py -v`
Expected: PASS

- [ ] **Step 5: Run full non-UI test suite**
Run: `uv run pytest -k "not ui and not qml and not clean" -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**
```bash
git add core/importers/xlsx_diff_importer.py tests/test_xlsx_diff_importer.py
git commit -m "feat(importer): implement recurring xlsx diff-preview and promotion importer"
```
