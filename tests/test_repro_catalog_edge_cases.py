"""
tests/test_repro_catalog_edge_cases.py
Deterministic regression and diagnostic test suite for the catalog search,
double-enter key dispatch, long metadata layout, and copy breakdown.
"""

import os
import sys
import json
import pytest

from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject, Qt, QEvent, QCoreApplication

from data.db import get_connection
from data.migrate import apply_migrations
from data.repositories import book_repo
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp_instance():
    """Ensure a singleton QGuiApplication is running."""
    app = QGuiApplication.instance()
    if app is None:
        QQuickStyle.setStyle("Fusion")
        app = QGuiApplication(sys.argv)
    return app


@pytest.fixture
def catalog_fixture(qapp_instance, tmp_path):
    """Setup an isolated database and QML environment with long metadata."""
    db_file = str(tmp_path / "test_catalog.sqlite")
    conn = get_connection(db_file, pin="123456")
    apply_migrations(conn)

    # Seed book with long author name matching user's Book 59
    long_author = (
        "ปิยวัฒน์ เลิศสิริภัทรจิตร , ศุภสุตา วงศ์ดามา ,  วิศลย์ เรืองเศรษฐกิจ , "
        "ศุภิสรา วงค์ดามา , ชยาพัทธ์ วรรณวงศ์ธิกุล ,สุธี หิรัญวิภาส , วรุตม์ ต.ศรีษ์"
    )
    b_id = book_repo.add_book(
        conn,
        title="พิฆาตคณิตศาสตร์ ม.ต้น",
        author=long_author,
        isbn="9786163749178",
        shelf_location="A-2",
    )
    book_repo.add_copies(conn, b_id, barcodes=["SMTE-00059-01"])

    adapter = LibrarianAdminAdapter(conn)
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.addImportPath(os.path.abspath("apps"))
    engine.rootContext().setContextProperty("librarianAdmin", adapter)

    qml_path = os.path.abspath("apps/librarian_management_app/qml/Main.qml")
    engine.load(qml_path)
    assert len(engine.rootObjects()) > 0, "Failed to load Main.qml"
    window = engine.rootObjects()[0]
    qapp_instance.processEvents()

    yield {
        "app": qapp_instance,
        "conn": conn,
        "adapter": adapter,
        "window": window,
        "book_id": b_id,
        "engine": engine,
    }

    conn.close()
    engine.deleteLater()
    qapp_instance.processEvents()


def _dispatch_return_key(window: QObject) -> None:
    """Helper to dispatch a Key_Return event to the window."""
    ev = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier, "\r")
    QCoreApplication.sendEvent(window, ev)


def test_search_repeated_enter_does_not_crash(catalog_fixture):
    """Verify pressing Enter multiple times in catalogSearchInput is safe."""
    window = catalog_fixture["window"]
    app = catalog_fixture["app"]
    search_input = window.findChild(QObject, "catalogSearchInput")
    catalog_model = window.findChild(QObject, "catalogModel")

    search_input.forceActiveFocus()
    search_input.setProperty("text", "คณิตศาสตร์")
    app.processEvents()

    # Dispatch Return twice consecutively
    _dispatch_return_key(window)
    app.processEvents()
    _dispatch_return_key(window)
    app.processEvents()

    assert catalog_model.property("count") == 1
    first_item = catalog_model.get(0)
    assert first_item.property("title").toString() == "พิฆาตคณิตศาสตร์ ม.ต้น"


def test_copy_breakdown_with_standard_row_factory(catalog_fixture):
    """Verify get_book_copy_breakdown handles row factory contract cleanly."""
    conn = catalog_fixture["conn"]
    book_id = catalog_fixture["book_id"]

    breakdown = book_repo.get_book_copy_breakdown(conn, book_id)
    assert breakdown["total_copies"] == 1
    assert breakdown["available_copies"] == 1
    assert breakdown["on_loan_copies"] == 0
    assert len(breakdown["copies"]) == 1
    assert breakdown["copies"][0]["can_remove"] is True


def test_copy_breakdown_with_tuple_row_factory(catalog_fixture):
    """Verify get_book_copy_breakdown handles tuple rows (row_factory=None) without TypeError."""
    conn = catalog_fixture["conn"]
    book_id = catalog_fixture["book_id"]

    orig_factory = conn.row_factory
    try:
        conn.row_factory = None
        breakdown = book_repo.get_book_copy_breakdown(conn, book_id)
        assert breakdown["total_copies"] == 1
        assert breakdown["available_copies"] == 1
        assert breakdown["on_loan_copies"] == 0
        assert len(breakdown["copies"]) == 1
        assert breakdown["copies"][0]["can_remove"] is True
    finally:
        conn.row_factory = orig_factory


def test_add_copies_double_execution_debounced(catalog_fixture):
    """Verify addCopiesDialog guards duplicate rapid submission."""
    window = catalog_fixture["window"]
    app = catalog_fixture["app"]
    conn = catalog_fixture["conn"]
    book_id = catalog_fixture["book_id"]

    initial_breakdown = book_repo.get_book_copy_breakdown(conn, book_id)
    initial_count = initial_breakdown["total_copies"]

    window.openAddCopiesDialog(book_id, "พิฆาตคณิตศาสตร์ ม.ต้น")
    app.processEvents()

    add_dialog = window.findChild(QObject, "addCopiesDialog")
    assert add_dialog is not None
    assert add_dialog.property("visible") is True
    assert add_dialog.property("isSubmitting") is False

    count_input = window.findChild(QObject, "addCopiesCountInput")
    assert count_input is not None
    count_input.setProperty("text", "2")

    # Call executeAddCopies twice consecutively (simulating rapid double-Enter/click)
    add_dialog.executeAddCopies()
    add_dialog.executeAddCopies()
    app.processEvents()

    # Verify against the database that copies were only added once
    updated_breakdown = book_repo.get_book_copy_breakdown(conn, book_id)
    assert updated_breakdown["total_copies"] == initial_count + 2


def test_catalog_view_layout_bounds_prevent_explosion(catalog_fixture):
    """Verify BookCatalogView delegate enforces layout bounds and text elision."""
    window = catalog_fixture["window"]
    engine = catalog_fixture["engine"]

    catalog_list = window.findChild(QObject, "catalogList")
    assert catalog_list is not None

    del_comp = catalog_list.property("delegate")
    assert del_comp is not None

    del_item = del_comp.create(engine.rootContext())
    assert del_item is not None

    col_layout = [c for c in del_item.findChildren(QObject) if c.metaObject().className() == "QQuickColumnLayout"][0]
    layout_attached = [c for c in col_layout.children() if "LayoutAttached" in c.metaObject().className()][0]

    assert layout_attached.property("fillWidth") is True
    assert layout_attached.property("minimumWidth") == 280.0
    assert layout_attached.property("preferredWidth") == 380.0

    texts = [c for c in col_layout.findChildren(QObject) if "Text" in c.metaObject().className()]
    assert len(texts) == 2
    for t in texts:
        assert t.property("maximumLineCount") == 1
        t_attached = [c for c in t.children() if "LayoutAttached" in c.metaObject().className()][0]
        assert t_attached.property("fillWidth") is True


def test_open_dialogs_twice_is_idempotent(catalog_fixture):
    """Verify opening edit dialog twice rapidly does not crash or corrupt state."""
    window = catalog_fixture["window"]
    app = catalog_fixture["app"]
    book_id = catalog_fixture["book_id"]

    # Open edit dialog consecutively
    window.openEditBookDialog(book_id, "พิฆาตคณิตศาสตร์ ม.ต้น", "author", "9786163749178", 0, "A-2", 1)
    app.processEvents()
    window.openEditBookDialog(book_id, "พิฆาตคณิตศาสตร์ ม.ต้น", "author", "9786163749178", 0, "A-2", 1)
    app.processEvents()

    edit_dialog = window.findChild(QObject, "editBookDialog")
    assert edit_dialog.property("visible") is True
