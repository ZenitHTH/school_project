# Student Search Algorithm & FTS5 Trigram (`core/student/services/search_parser.py` & `data/repositories/student_repo.py`)

## 1. Search Query Parsing
Search inputs can match students by:
1. **Grade / Room shorthand**: E.g. `"ม.1/2"`, `"1/2"`, `"m.1/2"` -> Parsed as `grade_level="ม.1", room=2`.
2. **Numeric suffix**: E.g. `"582"` -> Matches `student_id LIKE '%582'`.
3. **Full Name keywords**: E.g. `"สมชาย"`, `"กติกา"` -> Trigram FTS5 full-text search.
4. **National ID Exclusion**: Search queries never match `national_id` to prevent privacy leaks through broad numeric searches.

---

## 2. FTS5 Trigram Indexing
SQLite's `trigram` tokenizer indexes 3-character substrings, enabling substring queries inside Thai words without word-segmentation dictionaries:

```sql
CREATE VIRTUAL TABLE students_fts USING fts5(
    full_name,
    content='students',
    content_rowid='student_id',
    tokenize='trigram'
);
```

### Search SQL Execution Strategy:
- **Length < 3 chars**: Fallback to `s.full_name LIKE ?` with `%query%`.
- **Length >= 3 chars**: `students_fts MATCH ?` with relevance rank ordering:
  ```sql
  ORDER BY CASE
      WHEN s.student_id IN (SELECT rowid FROM students_fts WHERE students_fts MATCH ?)
      THEN (SELECT rank FROM students_fts WHERE students_fts MATCH ? AND rowid = s.student_id)
      ELSE 999 END ASC, s.student_id ASC
  ```
- **Pagination**: Standard `LIMIT ? OFFSET ?` via `StudentService.search(query, limit=50, offset=offset)`.
- **Total Count**: `StudentService.count(query)` counts matching records for the UI `PaginationBar`.
