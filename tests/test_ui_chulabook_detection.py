"""
tests/test_ui_chulabook_detection.py
Covers:
  - BookCatalogView chulabook detection button existence
  - Detect flow: status line, results dialog, flagged row content
  - Dialog close behavior
  - Error path (service failure -> status, dialog stays closed)
All providers monkeypatched — no network in tests.
"""
import os
import sys

import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from data.db import get_connection
from data.migrate import apply_migrations
from data.repositories import book_repo
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter


@pytest.fixture(scope="session")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    return app


@pytest.fixture
def lib_ui(qapp, tmp_path):
    conn = get_connection(str(tmp_path / "ui_library.sqlite"), pin="123456")
    apply_migrations(conn)
    book_repo.add_book(conn, title="หนังสือ CB", isbn="9786160000001", author="A1")
    book_repo.add_book(conn, title="หนังสือ แคช", isbn="9786160000002", author="A2")
    book_repo.add_book(conn, title="หนังสือ NLT", isbn="9786160000003", author="A3")
    adapter = LibrarianAdminAdapter(conn)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("librarianAdmin", adapter)
    engine.addImportPath(os.path.abspath("apps"))
    engine.load("apps/librarian_management_app/qml/Main.qml")
    window = engine.rootObjects()[0]

    yield {"app": qapp, "engine": engine, "window": window, "adapter": adapter, "conn": conn}
    conn.close()


@pytest.fixture
def patch_providers(lib_ui, monkeypatch):
    """...001 -> chulabook-only, ...002 -> in isbn_cache, ...003 -> NLT hit."""
    from core.library.services import chulabook_service as svc

    conn = lib_ui["conn"]
    conn.execute(
        "CREATE TABLE IF NOT EXISTS isbn_cache ("
        "isbn TEXT PRIMARY KEY, title TEXT NOT NULL, author TEXT, "
        "publisher TEXT, published_year TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.execute("INSERT OR IGNORE INTO isbn_cache (isbn, title) VALUES ('9786160000002', 'cached')")
    conn.commit()

    monkeypatch.setattr(
        svc, "_fetch_chulabook",
        lambda i, t: {"isbn": i, "title": "CB", "author": "x", "publisher": ""} if i == "9786160000001" else None
    )
    monkeypatch.setattr(
        svc, "_fetch_primo",
        lambda i, t: {"isbn": i, "title": "NLT", "author": "y", "publisher": "p"} if i == "9786160000003" else None
    )
    monkeypatch.setattr(svc, "_fetch_seed", lambda i, t: None)
    monkeypatch.setattr(svc, "_fetch_openlibrary", lambda i, t: None)


def find_child(root, name):
    return root.findChild(object, name)


def process_events(app):
    for _ in range(5):
        app.processEvents()


def test_button_exists(lib_ui):
    assert find_child(lib_ui["window"], "btnDetectChulabook") is not None


def test_detect_flow_flags_one_book(lib_ui, patch_providers):
    window = lib_ui["window"]
    find_child(window, "btnDetectChulabook").clicked.emit()
    process_events(lib_ui["app"])

    view = find_child(window, "bookCatalogView")
    assert view.property("chulabookStatus") == "พบ 1 เล่มที่พบเฉพาะใน Chulabook"
    assert view.property("chulabookDialogOpen") is True
    model = find_child(window, "chulabookResultsModel")
    assert model.rowCount() == 1
    books = view.property("chulabookBooks").toVariant()
    assert books[0]["isbn"] == "9786160000001"


def test_close_dialog(lib_ui, patch_providers):
    window = lib_ui["window"]
    find_child(window, "btnDetectChulabook").clicked.emit()
    process_events(lib_ui["app"])
    find_child(window, "btnCloseChulabookDialog").clicked.emit()
    process_events(lib_ui["app"])
    assert find_child(window, "bookCatalogView").property("chulabookDialogOpen") is False


def test_error_status_on_service_failure(lib_ui, patch_providers, monkeypatch):
    from core.shared.result import Err

    monkeypatch.setattr(
        "apps.librarian_management_app.adapters.librarian_admin_adapter.detect_chulabook_books",
        lambda conn, timeout=5.0, workers=8: Err("boom"),
    )
    window = lib_ui["window"]
    find_child(window, "btnDetectChulabook").clicked.emit()
    process_events(lib_ui["app"])
    view = find_child(window, "bookCatalogView")
    assert str(view.property("chulabookStatus")).startswith("✗")
    assert view.property("chulabookDialogOpen") is False
