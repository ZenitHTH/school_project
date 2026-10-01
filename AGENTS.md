# Configuration Document for AI Agents (LLM Wiki Schema)

This file instructs AI coding assistants on how to navigate, maintain, and contribute to the **School Project (SMTE)** codebase and its internal knowledge base.

---

## 1. Project Context
- **Domain**: School student registry, library circulation desk, and self-service kiosk system.
- **Tech Stack**: Python 3.14, PySide6 (Qt Quick/QML), SQLite with FTS5 trigram, OpenPyXL, ReportLab.
- **Root Wiki**: All high-level architectures, schemas, and API references reside in `wiki/index.md`.

---

## 2. Reading Rule: Query Wiki First
**To avoid excessive token usage and long delays:**
- When asked about system architecture, schemas, search algorithms, or UI components, **read the corresponding page in `wiki/` first** instead of scanning hundreds of lines across `apps/`, `core/`, or `data/`.
- Only inspect raw code files when you need to make surgical edits or write unit tests.

---

## 3. Architecture Rules & Invariants
1. **Result Type**: Use `Result[T, E]`, `Ok`, and `Err` from `core.shared.result`. Never raise unhandled exceptions across service boundaries.
2. **QML Sanitization**: Always run database dictionaries through `_sanitize_for_qml` before serializing to JSON for QML to prevent null-role crashes.
3. **Common QML**: Always reuse components from `apps/common_qml/` (`StyledSearchField`, `PaginationBar`, `AuditLogView`, `ActionFeedbackBanner`, `FirstLaunchDialog`) rather than reinventing ad-hoc inputs or buttons.
4. **Air-Gapped Sync**: Student records are authoritative in Student Management and sync via `snapshot.sqlite` diffs to Library Management.
5. **Testing**: Maintain 100% test coverage. Always run `.venv/bin/pytest tests/` after modifying services or adapters.

---

## 4. Ingest & Maintenance Workflow
When new features or architectural modifications are made:
1. Implement and verify code via pytest.
2. Update the relevant markdown page in `wiki/`.
3. Append a short summary entry to `wiki/log.md`.
