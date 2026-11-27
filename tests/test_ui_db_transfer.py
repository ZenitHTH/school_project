"""UI component tests for reusable DatabaseTransferCard.qml."""

import os
import sys
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


@pytest.fixture(scope="session")
def qapp():
    return QGuiApplication.instance() or QGuiApplication(sys.argv)


def _load_card(qapp):
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda ws: warnings.extend([w.toString() for w in ws]))
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    qml = os.path.abspath("apps/common_qml/DatabaseTransferCard.qml")
    engine.load(qml)
    qapp.processEvents()
    assert len(engine.rootObjects()) > 0, f"Failed to load QML; warnings: {warnings}"
    root = engine.rootObjects()[0]
    return engine, root, warnings


def test_database_transfer_card_loads_and_exposes_controls(qapp):
    engine, root, warnings = _load_card(qapp)
    try:
        for name in (
            "btnExportDb",
            "btnPreviewImportDb",
            "btnApplyImportDb",
            "transferFormatCombo",
            "transferModeCombo",
            "diffSummaryText",
            "statusBanner",
        ):
            assert root.findChild(QObject, name) is not None, f"Missing objectName: {name}"

        apply_btn = root.findChild(QObject, "btnApplyImportDb")
        assert apply_btn.property("enabled") is False

        fmt_combo = root.findChild(QObject, "transferFormatCombo")
        mode_combo = root.findChild(QObject, "transferModeCombo")
        assert fmt_combo.property("currentValue") == "sqlite"
        assert mode_combo.property("currentValue") == "merge"

        # Responsive height derived from content (> 0)
        assert root.property("implicitHeight") > 120

        # No QML ReferenceError / TypeError warnings
        bad = [w for w in warnings if "ReferenceError" in w or "TypeError" in w]
        assert not bad, f"Unexpected QML errors: {bad}"
    finally:
        engine.deleteLater()
        qapp.processEvents()


def test_database_transfer_card_preview_gates_apply_and_resets_on_mode_change(qapp):
    engine, root, _warnings = _load_card(qapp)
    try:
        apply_btn = root.findChild(QObject, "btnApplyImportDb")
        summary = root.findChild(QObject, "diffSummaryText")
        banner = root.findChild(QObject, "statusBanner")
        mode_combo = root.findChild(QObject, "transferModeCombo")

        root.setProperty("selectedImportPath", "/tmp/books_bundle.sqlite")
        assert apply_btn.property("enabled") is False

        # Successful preview enables btnApplyImportDb and populates diffSummaryText
        QMetaObject.invokeMethod(
            root,
            "setPreviewResult",
            Qt.DirectConnection,
            Q_ARG("QVariant", {
                "ok": True,
                "data": {
                    "new_categories": 1,
                    "new_books": 3,
                    "updated_books": 1,
                    "new_copies": 5,
                    "skipped_locked_copies": 0,
                },
                "error": None,
            }),
        )
        qapp.processEvents()
        assert apply_btn.property("enabled") is True
        assert "3" in summary.property("text")
        assert "5" in summary.property("text")

        # Switching import mode disables apply until re-previewed
        mode_combo.setProperty("currentIndex", 1)
        qapp.processEvents()
        assert mode_combo.property("currentValue") == "replace"
        assert apply_btn.property("enabled") is False

        # Failed preview sets error banner and keeps apply disabled
        QMetaObject.invokeMethod(
            root,
            "setPreviewResult",
            Qt.DirectConnection,
            Q_ARG("QVariant", {"ok": False, "data": None, "error": "Checksum mismatch"}),
        )
        qapp.processEvents()
        assert apply_btn.property("enabled") is False
        assert banner.property("isError") is True
        assert "Checksum mismatch" in banner.property("text")

        # Export & import feedback update statusBanner cleanly
        QMetaObject.invokeMethod(
            root,
            "setExportResult",
            Qt.DirectConnection,
            Q_ARG("QVariant", {"ok": True, "data": {"output_path": "/tmp/out.xlsx"}, "error": None}),
        )
        qapp.processEvents()
        assert banner.property("isError") is False
        assert "/tmp/out.xlsx" in banner.property("text")
    finally:
        engine.deleteLater()
        qapp.processEvents()


def test_database_transfer_card_emits_signals_on_file_accept_and_apply(qapp):
    engine, root, _warnings = _load_card(qapp)
    try:
        events = []
        root.exportRequested.connect(lambda p, fmt: events.append(("export", p, fmt)))
        root.previewRequested.connect(lambda p, mode: events.append(("preview", p, mode)))
        root.importRequested.connect(lambda p, mode: events.append(("import", p, mode)))

        fmt_combo = root.findChild(QObject, "transferFormatCombo")
        fmt_combo.setProperty("currentIndex", 1)  # xlsx
        qapp.processEvents()

        QMetaObject.invokeMethod(
            root,
            "acceptExportPath",
            Qt.DirectConnection,
            Q_ARG("QVariant", "file:///tmp/books_export.xlsx"),
        )
        QMetaObject.invokeMethod(
            root,
            "acceptImportPath",
            Qt.DirectConnection,
            Q_ARG("QVariant", "file:///tmp/books_import.sqlite"),
        )
        QMetaObject.invokeMethod(
            root,
            "setPreviewResult",
            Qt.DirectConnection,
            Q_ARG("QVariant", {"ok": True, "data": {"new_books": 2, "new_copies": 4}, "error": None}),
        )
        qapp.processEvents()

        apply_btn = root.findChild(QObject, "btnApplyImportDb")
        assert apply_btn.property("enabled") is True
        apply_btn.clicked.emit()
        qapp.processEvents()

        assert events == [
            ("export", "file:///tmp/books_export.xlsx", "xlsx"),
            ("preview", "file:///tmp/books_import.sqlite", "merge"),
            ("import", "file:///tmp/books_import.sqlite", "merge"),
        ]
    finally:
        engine.deleteLater()
        qapp.processEvents()


def test_settings_view_toggles_and_forwards_book_transfer_card(qapp):
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda ws: warnings.extend([w.toString() for w in ws]))
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.load(os.path.abspath("apps/common_qml/SettingsView.qml"))
    qapp.processEvents()
    assert len(engine.rootObjects()) > 0
    root = engine.rootObjects()[0]
    try:
        card = root.findChild(QObject, "bookTransferCard")
        assert card is not None
        assert root.property("showBookTransferCard") is False
        assert card.property("visible") is False

        root.setProperty("showBookTransferCard", True)
        qapp.processEvents()
        assert card.property("visible") is True

        forwarded = []
        root.bookTransferExportRequested.connect(lambda p, fmt: forwarded.append(("export", p, fmt)))
        root.bookTransferPreviewRequested.connect(lambda p, mode: forwarded.append(("preview", p, mode)))
        root.bookTransferImportRequested.connect(lambda p, mode: forwarded.append(("import", p, mode)))

        QMetaObject.invokeMethod(card, "acceptExportPath", Qt.DirectConnection, Q_ARG("QVariant", "file:///tmp/out.sqlite"))
        QMetaObject.invokeMethod(card, "acceptImportPath", Qt.DirectConnection, Q_ARG("QVariant", "file:///tmp/in.sqlite"))
        QMetaObject.invokeMethod(card, "setPreviewResult", Qt.DirectConnection, Q_ARG("QVariant", {"ok": True, "data": {"new_books": 1}, "error": None}))
        card.findChild(QObject, "btnApplyImportDb").clicked.emit()
        qapp.processEvents()

        assert forwarded == [
            ("export", "file:///tmp/out.sqlite", "sqlite"),
            ("preview", "file:///tmp/in.sqlite", "merge"),
            ("import", "file:///tmp/in.sqlite", "merge"),
        ]
        bad = [w for w in warnings if "ReferenceError" in w or "TypeError" in w]
        assert not bad, f"Unexpected QML errors: {bad}"
    finally:
        engine.deleteLater()
        qapp.processEvents()


def test_librarian_main_wires_book_transfer_and_refreshes_catalog(qapp, tmp_path):
    import json
    from data.db import get_connection
    from data.migrate import apply_migrations
    from data.repositories import book_repo
    from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter

    src_conn = get_connection(str(tmp_path / "src_lib.sqlite"), pin="123456")
    apply_migrations(src_conn)
    cat_id = book_repo.add_category(src_conn, "ดาราศาสตร์")
    bid = book_repo.add_book(src_conn, title="ดวงดาวและการโคจร", author="อ.วิชัย", isbn="978-616-5555", category_id=cat_id)
    book_repo.add_copies(src_conn, bid, barcodes=["SMTE-00001-01"])
    src_conn.commit()
    src_adapter = LibrarianAdminAdapter(src_conn)
    bundle_path = tmp_path / "transfer_books.sqlite"
    assert json.loads(src_adapter.exportBooksDatabase(str(bundle_path), "sqlite", False))["ok"] is True
    src_conn.close()

    dst_conn = get_connection(str(tmp_path / "dst_lib.sqlite"), pin="123456")
    apply_migrations(dst_conn)
    dst_adapter = LibrarianAdminAdapter(dst_conn)

    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda ws: warnings.extend([w.toString() for w in ws]))
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.addImportPath(os.path.abspath("apps"))
    engine.rootContext().setContextProperty("librarianAdmin", dst_adapter)
    engine.load(os.path.abspath("apps/librarian_management_app/qml/Main.qml"))
    qapp.processEvents()
    assert len(engine.rootObjects()) > 0
    window = engine.rootObjects()[0]
    try:
        settings = window.findChild(QObject, "settingsView")
        card = window.findChild(QObject, "bookTransferCard")
        assert settings.property("showBookTransferCard") is True
        assert card is not None

        QMetaObject.invokeMethod(card, "acceptImportPath", Qt.DirectConnection, Q_ARG("QVariant", bundle_path.as_uri()))
        qapp.processEvents()
        apply_btn = card.findChild(QObject, "btnApplyImportDb")
        assert apply_btn.property("enabled") is True

        apply_btn.clicked.emit()
        qapp.processEvents()

        catalog_model = window.findChild(QObject, "catalogModel")
        assert catalog_model.property("count") == 1
        cat_model = window.findChild(QObject, "catalogCategoryModel")
        assert cat_model.property("count") >= 2
        bad = [w for w in warnings if "ReferenceError" in w or "TypeError" in w]
        assert not bad, f"Unexpected QML errors: {bad}"
    finally:
        engine.deleteLater()
        qapp.processEvents()
        dst_conn.close()
