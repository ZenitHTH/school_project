# Wiki Revision Log

All architectural updates, refactorings, and knowledge ingestions are tracked here.

## [2026-10-01] init | Wiki created
- Scaffolding of LLM Wiki for School Project.
- Cataloged modular QML components (`apps/common_qml`).
- Documented Rust-style `Result[T, E]` type and warning propagation in core importers/adapters.
- Documented SQLite schema, FTS5 trigram search, and air-gapped snapshot sync.

## [2026-10-01] fix | QML Dialog Centering & Modal Bounds
- Fixed dialog centering in `apps/librarian_management_app/qml/dialogs/` (`BookActionDialogs.qml`, `CategoryActionDialogs.qml`) and `StudentActionDialogs.qml` by adding `anchors.fill: parent` to root items.
- Added `modal: true`, `closePolicy: Popup.CloseOnEscape`, and responsive width constraints across all modal dialogs.
- Verified 0 undefined-to-bool warnings across all apps.

