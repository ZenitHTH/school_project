"""
tests/test_ui_librarian.py
UI-level tests for Librarian Management App.

Coverage:
  - Initial screen state (catalog screen index 0, initial books loaded)
  - Navigation across all 6 screens
  - Catalog search and book list filtering
  - Add Book Dialog: input title/author/barcodes -> accept -> book added and listed
  - Desk Student Lookup: lookup by ID/name -> updates currentCheckoutStudent and UI label
  - Desk Checkout: validation errors + successful checkout -> updates deskStatusText
  - Desk Return: validation errors + successful return -> updates deskStatusText
  - Active Loans screen: loadActiveLoans populates activeLoanModel
  - Student Sync screen: previewDiff updates summary text & diffModel, applySync updates status
  - Fines screen: loadFines populates fineModel
  - Audit Log screen: loadLogs populates logModel
  - Structural integrity: all required objectNames exist
"""
import os
import sys
import json
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QMetaObject, Qt, QObject, Q_ARG
from data.db import get_connection
from data.migrate import apply_migrations
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter
from data.sync.export import export_snapshot


@pytest.fixture(scope="session")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    return app


@pytest.fixture
def lib_ui(qapp, tmp_path):
    db_file = str(tmp_path / "ui_library.sqlite")
    conn = get_connection(db_file, pin="123456")
    apply_migrations(conn)

    # Seed students
    conn.execute(
        "INSERT INTO students (student_id, full_name, status) VALUES "
        "(2001, 'สมเกียรติ ยืมดี', 'active'), "
        "(2002, 'สมใจ ลาออก', 'transferred_out')"
    )
    conn.commit()

    # Seed initial book
    from data.repositories import book_repo
    b_id = book_repo.add_book(conn, title="วิทยาศาสตร์น่ารู้", author="ดร.สมชาย", isbn="978-001")
    book_repo.add_copies(conn, b_id, barcodes=["SCI-01", "SCI-02"])

    adapter = LibrarianAdminAdapter(conn)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("librarianAdmin", adapter)

    qml_path = os.path.abspath("apps/librarian_management_app/qml/Main.qml")
    engine.load(qml_path)
    assert len(engine.rootObjects()) > 0, "Librarian QML failed to load"

    window = engine.rootObjects()[0]
    qapp.processEvents()

    yield {
        "app": qapp,
        "window": window,
        "engine": engine,
        "conn": conn,
        "adapter": adapter,
        "tmp_path": tmp_path,
    }

    conn.close()
    engine.deleteLater()


def find(window, name):
    return window.findChild(QObject, name)


def invoke(window, method, *args):
    if args:
        QMetaObject.invokeMethod(window, method, Qt.DirectConnection, *args)
    else:
        QMetaObject.invokeMethod(window, method, Qt.DirectConnection)


def process(app):
    app.processEvents()


# ---------------------------------------------------------------------------
# 1. Initial State & Navigation
# ---------------------------------------------------------------------------

def test_librarian_initial_screen_is_catalog(lib_ui):
    stack = find(lib_ui["window"], "librarianStack")
    assert stack is not None
    assert stack.property("currentIndex") == 0


def test_librarian_initial_catalog_loaded(lib_ui):
    model = find(lib_ui["window"], "catalogModel")
    assert model is not None
    assert model.property("count") >= 1


def test_librarian_screen_navigation(lib_ui):
    stack = find(lib_ui["window"], "librarianStack")
    for idx in range(6):
        stack.setProperty("currentIndex", idx)
        process(lib_ui["app"])
        assert stack.property("currentIndex") == idx


# ---------------------------------------------------------------------------
# 2. Catalog Search & Add Book Dialog
# ---------------------------------------------------------------------------

def test_catalog_search_filtering(lib_ui):
    window = lib_ui["window"]
    search_input = find(window, "catalogSearchInput")
    search_input.setProperty("text", "วิทยาศาสตร์")
    invoke(window, "searchBooks")
    process(lib_ui["app"])

    model = find(window, "catalogModel")
    assert model.property("count") >= 1

    search_input.setProperty("text", "NOTEXIST999")
    invoke(window, "searchBooks")
    process(lib_ui["app"])
    assert model.property("count") == 0


def test_add_book_dialog_execution(lib_ui):
    window = lib_ui["window"]
    dialog = find(window, "addBookDialog")
    assert dialog is not None

    find(window, "newBookTitle").setProperty("text", "คณิตศาสตร์ ม.ปลาย")
    find(window, "newBookIsbn").setProperty("text", "978-002")
    find(window, "newBookAuthor").setProperty("text", "อาจารย์สมศักดิ์")
    find(window, "newBookBarcodes").setProperty("text", "MATH-01,MATH-02")
    dialog.accept()
    process(lib_ui["app"])

    # Search and verify new book exists in catalogModel
    find(window, "catalogSearchInput").setProperty("text", "คณิตศาสตร์")
    invoke(window, "searchBooks")
    process(lib_ui["app"])

    model = find(window, "catalogModel")
    assert model.property("count") >= 1


# ---------------------------------------------------------------------------
# 3. Desk Checkout & Return
# ---------------------------------------------------------------------------

def test_desk_student_lookup_found(lib_ui):
    window = lib_ui["window"]
    find(window, "studentLookupInput").setProperty("text", "2001")
    invoke(window, "lookupStudent")
    process(lib_ui["app"])

    name_label = find(window, "checkoutStudentName")
    assert "สมเกียรติ ยืมดี" in name_label.property("text")
    assert window.property("currentCheckoutStudent") is not None


def test_desk_student_lookup_not_found(lib_ui):
    window = lib_ui["window"]
    find(window, "studentLookupInput").setProperty("text", "99999")
    invoke(window, "lookupStudent")
    process(lib_ui["app"])

    status = find(window, "deskStatusText")
    assert "ไม่พบ" in status.property("text")


def test_desk_checkout_without_student_fails(lib_ui):
    window = lib_ui["window"]
    window.setProperty("currentCheckoutStudent", None)
    find(window, "barcodeInput").setProperty("text", "SCI-01")
    invoke(window, "doCheckout")
    process(lib_ui["app"])

    status = find(window, "deskStatusText")
    assert "กรุณาเลือกนักเรียน" in status.property("text")


def test_desk_checkout_success(lib_ui):
    window = lib_ui["window"]
    # 1. Lookup student
    find(window, "studentLookupInput").setProperty("text", "2001")
    invoke(window, "lookupStudent")
    process(lib_ui["app"])

    # 2. Scan barcode & checkout
    find(window, "barcodeInput").setProperty("text", "SCI-01")
    invoke(window, "doCheckout")
    process(lib_ui["app"])

    status = find(window, "deskStatusText")
    assert "ยืมหนังสือสำเร็จ" in status.property("text")


def test_desk_checkout_already_loaned_fails(lib_ui):
    window = lib_ui["window"]
    find(window, "studentLookupInput").setProperty("text", "2001")
    invoke(window, "lookupStudent")
    process(lib_ui["app"])

    # 1. First checkout succeeds
    find(window, "barcodeInput").setProperty("text", "SCI-01")
    invoke(window, "doCheckout")
    process(lib_ui["app"])

    # 2. Second checkout of same copy must fail
    find(window, "barcodeInput").setProperty("text", "SCI-01")
    invoke(window, "doCheckout")
    process(lib_ui["app"])

    status = find(window, "deskStatusText")
    assert "ไม่สามารถยืมได้" in status.property("text")


def test_desk_return_success(lib_ui):
    window = lib_ui["window"]
    # Checkout first
    find(window, "studentLookupInput").setProperty("text", "2001")
    invoke(window, "lookupStudent")
    find(window, "barcodeInput").setProperty("text", "SCI-01")
    invoke(window, "doCheckout")
    process(lib_ui["app"])

    # Now return
    find(window, "barcodeInput").setProperty("text", "SCI-01")
    invoke(window, "doReturn")
    process(lib_ui["app"])

    status = find(window, "deskStatusText")
    assert "คืนหนังสือสำเร็จเรียบร้อย" in status.property("text")


def test_desk_return_unloaned_barcode(lib_ui):
    window = lib_ui["window"]
    find(window, "barcodeInput").setProperty("text", "SCI-02")  # on shelf, not loaned
    invoke(window, "doReturn")
    process(lib_ui["app"])

    status = find(window, "deskStatusText")
    assert "ไม่พบรายการยืม" in status.property("text")


# ---------------------------------------------------------------------------
# 4. Active Loans Screen
# ---------------------------------------------------------------------------

def test_load_active_loans_populates_model(lib_ui):
    window = lib_ui["window"]
    # Checkout a book first
    find(window, "studentLookupInput").setProperty("text", "2001")
    invoke(window, "lookupStudent")
    find(window, "barcodeInput").setProperty("text", "SCI-02")
    invoke(window, "doCheckout")
    process(lib_ui["app"])

    invoke(window, "loadActiveLoans")
    process(lib_ui["app"])

    model = find(window, "activeLoanModel")
    assert model.property("count") >= 1


# ---------------------------------------------------------------------------
# 5. Student Sync Screen
# ---------------------------------------------------------------------------

def test_sync_preview_and_apply(lib_ui):
    window = lib_ui["window"]
    tmp = lib_ui["tmp_path"]

    # Create a dummy student DB and export snapshot
    source_db_file = str(tmp / "source_student.sqlite")
    s_conn = get_connection(source_db_file, pin="123456")
    apply_migrations(s_conn)
    s_conn.execute("INSERT INTO students (student_id, full_name, status) VALUES (5555, 'นักเรียนใหม่ ซิงค์', 'active')")
    s_conn.commit()

    snap_file = str(tmp / "test_snapshot.sqlite")
    export_snapshot(s_conn, snap_file)
    s_conn.close()

    # In UI: set path, preview diff
    find(window, "snapshotPathInput").setProperty("text", snap_file)
    invoke(window, "previewDiff")
    process(lib_ui["app"])

    summary_text = find(window, "diffSummaryText")
    assert "ผลการตรวจสอบ" in summary_text.property("text")

    apply_btn = find(window, "applySyncBtn")
    assert apply_btn.property("enabled") is True

    # Apply sync
    invoke(window, "applySync")
    process(lib_ui["app"])
    assert "สำเร็จเรียบร้อย" in summary_text.property("text")


# ---------------------------------------------------------------------------
# 6. Fines & Logs Screens
# ---------------------------------------------------------------------------

def test_load_fines_and_logs(lib_ui):
    window = lib_ui["window"]

    invoke(window, "loadFines")
    process(lib_ui["app"])
    fines_model = find(window, "fineModel")
    assert fines_model is not None

    invoke(window, "loadLogs")
    process(lib_ui["app"])
    logs_model = find(window, "logModel")
    assert logs_model is not None
    assert logs_model.property("count") >= 1


# ---------------------------------------------------------------------------
# 7. Structural Integrity
# ---------------------------------------------------------------------------

def test_librarian_all_objectnames_present(lib_ui):
    window = lib_ui["window"]
    required = [
        "librarianStack",
        "catalogSearchInput",
        "catalogList",
        "catalogModel",
        "btnOpenGeneratorPage",
        "addBookDialog",
        "newBookTitle",
        "newBookIsbn",
        "newBookAuthor",
        "newBookBarcodes",
        "studentLookupInput",
        "btnLookupStudent",
        "checkoutStudentName",
        "barcodeInput",
        "btnCheckout",
        "btnReturn",
        "deskStatusText",
        "activeLoanList",
        "activeLoanModel",
        "snapshotPathInput",
        "btnPreviewDiff",
        "applySyncBtn",
        "diffSummaryText",
        "diffDetailsList",
        "diffModel",
        "fineList",
        "fineModel",
        "logList",
        "logModel",
        "openWizardBtn",
        "firstLaunchDialog",
    ]
    missing = [name for name in required if find(window, name) is None]
    assert not missing, f"Missing objectNames in Librarian QML: {missing}"


def test_librarian_first_launch_dialog_opens_on_blank_db(qapp, tmp_path):
    """When librarian app opens with empty DB, firstLaunchDialog opens automatically."""
    db_file = str(tmp_path / "first_launch_lib_ui.sqlite")
    conn = get_connection(db_file, pin="123456")
    apply_migrations(conn)

    adapter = LibrarianAdminAdapter(conn)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("librarianAdmin", adapter)

    qml_path = os.path.abspath("apps/librarian_management_app/qml/Main.qml")
    engine.load(qml_path)
    qapp.processEvents()

    window = engine.rootObjects()[0]
    dlg = find(window, "firstLaunchDialog")
    assert dlg is not None, "firstLaunchDialog not found"
    assert dlg.property("visible") is True, "firstLaunchDialog should open on blank DB"

    # Click create blank database button
    blank_btn = find(window, "firstLaunchBlankBtn")
    assert blank_btn is not None
    blank_btn.clicked.emit()
    qapp.processEvents()

    assert dlg.property("visible") is False, "Dialog should close after blank db init"

    # Verify state saved
    cur = conn.cursor()
    cur.execute("SELECT value FROM sync_state WHERE key = 'library_first_launch_done';")
    assert cur.fetchone()[0] == "1"

    conn.close()
    engine.deleteLater()


def test_librarian_manual_open_wizard_button(lib_ui):
    """Clicking openWizardBtn opens the first launch wizard manually."""
    window = lib_ui["window"]
    btn = find(window, "openWizardBtn")
    assert btn is not None
    btn.clicked.emit()
    process(lib_ui["app"])

    dlg = find(window, "firstLaunchDialog")
    assert dlg is not None
    assert dlg.property("visible") is True


def test_barcode_generator_page_preview_and_save(lib_ui):
    """Test dedicated barcode generator GUI page: preview and save new book with deterministic barcodes."""
    window = lib_ui["window"]
    stack = find(window, "librarianStack")
    nav_btn = find(window, "navBtnGenerator")
    assert nav_btn is not None
    nav_btn.clicked.emit()
    process(lib_ui["app"])

    assert stack.property("currentIndex") == 6

    # Test previewing
    title_input = find(window, "genBookTitle")
    assert title_input is not None
    title_input.setProperty("text", "ชีววิทยาน่ารู้ ม.3")

    count_input = find(window, "genCopyCountInput")
    count_input.setProperty("text", "2")
    process(lib_ui["app"])

    model = find(window, "genBarcodesModel")
    assert model is not None
    assert model.property("count") == 2

    # Save and commit
    save_btn = find(window, "btnExecuteGenerate")
    assert save_btn is not None
    save_btn.clicked.emit()
    process(lib_ui["app"])

    status_msg = find(window, "genStatusMessage")
    assert "✓" in status_msg.property("text")

    # Export PDF
    pdf_btn = find(window, "btnExportPdfSheet")
    assert pdf_btn is not None
    assert pdf_btn.property("enabled") is True
    pdf_btn.clicked.emit()
    process(lib_ui["app"])

    pdf_status = find(window, "genPdfStatusText")
    assert "✓" in pdf_status.property("text")


def test_category_management_screen(lib_ui):
    window = lib_ui["window"]
    stack = find(window, "librarianStack")
    nav_btn = find(window, "navBtnCategories")
    assert nav_btn is not None
    nav_btn.clicked.emit()
    process(lib_ui["app"])

    assert stack.property("currentIndex") == 7

    cat_input = find(window, "categoryNameInput")
    add_btn = find(window, "btnAddCategory")
    status_text = find(window, "categoryStatusText")
    cat_model = find(window, "categoryListModel")

    assert cat_input is not None
    assert add_btn is not None
    assert cat_model is not None

    # Empty validation
    cat_input.setProperty("text", "")
    add_btn.clicked.emit()
    process(lib_ui["app"])
    assert "กรุณากรอกชื่อหมวดหมู่" in status_text.property("text")

    # Add valid category
    cat_input.setProperty("text", "จิตวิทยาและการพัฒนาตนเอง")
    add_btn.clicked.emit()
    process(lib_ui["app"])

    assert "เพิ่มหมวดหมู่สำเร็จ" in status_text.property("text") or "✓" in status_text.property("text")
    assert cat_input.property("text") == ""
    assert cat_model.property("count") >= 1


def test_category_rename_and_delete_with_reassign(lib_ui):
    window = lib_ui["window"]
    find(window, "navBtnCategories").clicked.emit()
    process(lib_ui["app"])

    # 1. Add two test categories
    invoke(window, "addNewCategory")  # empty
    cat_input = find(window, "categoryNameInput")
    add_btn = find(window, "btnAddCategory")

    cat_input.setProperty("text", "หมวดทดสอบ 1")
    add_btn.clicked.emit()
    process(lib_ui["app"])

    cat_input.setProperty("text", "หมวดทดสอบ 2")
    add_btn.clicked.emit()
    process(lib_ui["app"])

    # 2. Test Rename
    cat_model = find(window, "categoryListModel")
    assert cat_model.property("count") >= 2
    first_cat = cat_model.get(0)
    cat_id = first_cat.property("category_id").toInt()

    invoke(window, "openRenameCategoryDialog", Q_ARG("QVariant", cat_id), Q_ARG("QVariant", "หมวดทดสอบ 1 ที่แก้ไขแล้ว"))
    process(lib_ui["app"])

    rename_input = find(window, "renameCategoryInput")
    assert rename_input.property("text") == "หมวดทดสอบ 1 ที่แก้ไขแล้ว"
    find(window, "btnSubmitRename").clicked.emit()
    process(lib_ui["app"])

    # 3. Test Delete Empty Category (Simple Delete Dialog)
    invoke(window, "requestDeleteCategory", Q_ARG("QVariant", cat_id), Q_ARG("QVariant", "หมวดทดสอบ 1 ที่แก้ไขแล้ว"))
    process(lib_ui["app"])

    simple_dlg = find(window, "simpleDeleteCategoryDialog")
    assert simple_dlg.property("visible") is True
    find(window, "btnConfirmSimpleDelete").clicked.emit()
    process(lib_ui["app"])
    assert simple_dlg.property("visible") is False

    # 4. Test Delete Category with Books Assigned (Reassign Dialog)
    # Assign a book to the remaining test category
    second_cat = cat_model.get(0)
    cat_id_2 = second_cat.property("category_id").toInt()
    conn = lib_ui["conn"]
    conn.execute("UPDATE books SET category_id = ? WHERE book_id = 1", (cat_id_2,))
    conn.commit()

    invoke(window, "requestDeleteCategory", Q_ARG("QVariant", cat_id_2), Q_ARG("QVariant", "หมวดทดสอบ 2"))
    process(lib_ui["app"])

    reassign_dlg = find(window, "reassignCategoryDialog")
    assert reassign_dlg.property("visible") is True
    find(window, "btnConfirmReassignDelete").clicked.emit()
    process(lib_ui["app"])
    assert reassign_dlg.property("visible") is False




