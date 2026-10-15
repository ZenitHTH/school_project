# SDD ledger — plan: .superpowers/plans/barcode-fix-repo-cleanup-sqlite-optimization.md

Pre-flight:
- Task 1 -> Task 2: Task 1 touches label_service.py, adapter, book_repo. Task 2 deletes dead files. No conflicts.
- Task 2 -> Task 3: Task 2 removes core/library/models.py, core/shared/errors.py. Task 3 modifies core/shared/mock_qt.py. No conflicts.
- Task 3 -> Task 4: Task 3 modifies adapters. Task 4 modifies data/repositories/student_repo.py. No conflicts.
- Task 4 -> Task 5: Task 4 touches student_repo.py. Task 5 touches data/sync/apply.py and migrations. No conflicts.

Task 1: complete (commits 125c466..539c105, tests: pytest tests/test_barcode_and_disposed.py -> 6 passed)

