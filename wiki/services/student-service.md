# Student & Enrollment Services (`core/student/services/`)

## 1. Overview
The Student domain is the authoritative source of truth for student records, enrollment history, and status lifecycles across the entire system.

---

## 2. Student Service (`core.student.services.student_service`)
Encapsulates CRUD, search parsing, and identification lookups.

### Methods & Signatures:
- `search(query, grade_level, room, status, limit=50, offset=0) -> Result[List[Dict], str]`
  - Parses shorthand classroom queries (e.g. `"ม.1/2"`) into separate `grade_level="ม.1"` and `room=2` filters.
  - Queries `student_repo.search_students` using SQLite FTS5 trigram full text indexing.
- `count(query, grade_level, room, status) -> Result[int, str]`
- `get_by_id(student_id: int) -> Result[Dict, str]`
- `get_status(student_id: int) -> Optional[str]`
- `update_status(student_id: int, new_status: str, reason: Optional[str] = None, actor: Optional[str] = None) -> Result[Dict, str]`
  - Validates legal status transitions before updating.
- `change_student_id(old_id: int, new_id: int, reason: Optional[str] = None, actor: Optional[str] = None) -> Result[Dict, str]`
  - Executes atomic transaction cascading across `enrollments`, `loans`, `fines`, and `audit_log`.

---

## 3. Student Lifecycle & State Machine
Enforced via `LEGAL_STATUS_TRANSITIONS`:
- Allowed Transitions:
  - `active` ↔ `on_leave`
  - `active` → `transferred_out`
  - `on_leave` → `transferred_out`
  - `transferred_out` → `active`
- Inactive students (`on_leave`, `transferred_out`, `graduated`) are blocked from checking out library books.

---

## 4. Enrollment Service (`core.student.services.enrollment_service`)
Tracks historical and current class assignments by academic year and semester.

### Key Workflows:
1. **Classroom Movement (`change_classroom`)**:
   - Updates student room within current period and logs audit trail.
2. **Sequential Promotion (`promote_students`)**:
   - Promotes students sequentially using `GRADE_MAP` (`ม.1` → `ม.2` ... `ม.5` → `ม.6`).
   - Grade 6 students are moved to `graduated` status.
3. **Yearly Roster Rollover (`enroll_next_period`)**:
   - Enrolls active students into next academic year/semester while maintaining historical records.
