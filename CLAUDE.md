# Instructions for Claude Code (LLM Wiki Schema)

## 1. Quick Orientation
- **Domain**: School student registry, library circulation desk, and self-service kiosk system.
- **Tech Stack**: Python 3.14, PySide6 (Qt Quick/QML), SQLite with FTS5 trigram, OpenPyXL, ReportLab.
- **Wiki Index**: `wiki/index.md`

## 2. Token-Saving Rule
- **Read `wiki/` first**: When answering questions or planning changes, consult `wiki/` instead of reading entire source directories.
- **Surgical edits**: Inspect raw code files only when making specific code modifications.

## 3. Key Invariants
- Use `Result[T, E]`, `Ok`, and `Err` from `core.shared.result`.
- Use `_sanitize_for_qml` before serializing data to QML.
- Use shared components from `apps/common_qml/`.
- Verify with `.venv/bin/pytest tests/`.
