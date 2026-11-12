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
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
from PySide6.QtCore import QMetaObject, Qt, QObject, Q_ARG, QPoint
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
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
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.addImportPath(os.path.abspath("apps"))
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

    qapp.processEvents()
    conn.close()
    engine.deleteLater()
    qapp.processEvents()


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


def test_catalog_barcode_and_category_filter(lib_ui):
    window, app = lib_ui["window"], lib_ui["app"]
    adapter = lib_ui["adapter"]

    cat_a = json.loads(adapter.addCategory("หมวดฟิสกส"))["data"]["category_id"]
    adapter.addBook("ฟิสกส 101", "", "ผุ้แต่ง", "", str(cat_a), "", "FIS-01")
    cat_b = json.loads(adapter.addCategory("หมวดคณิศาสตร"))["data"]["category_id"]
    adapter.addBook("คณิศาสตร 101", "", "ผุ้แต่ง 2", "", str(cat_b), "", "MATH-01")

    # Refresh the category combo now that categories exist
    view = find(window, "bookCatalogView")
    assert view is not None
    QMetaObject.invokeMethod(view, "loadCategories", Qt.DirectConnection)
    process(app)

    combo = find(window, "catalogCategoryCombo")
    model = find(window, "catalogModel")

    # --- barcode sticker into the existing search field (all categories) ---
    find(window, "catalogSearchInput").setProperty("text", "SCI-01")
    invoke(window, "searchBooks")
    process(app)
    assert model.property("count") >= 1

    # --- category filter narrows to the single book in cat_a ---
    cat_model = find(window, "catalogCategoryModel")
    for i in range(cat_model.property("count")):
        combo.setProperty("currentIndex", i)
        process(app)
        if combo.property("displayText") == "หมวดฟิสกส":
            break
    find(window, "catalogSearchInput").setProperty("text", "")
    invoke(window, "searchBooks")
    process(app)
    assert model.property("count") == 1


def test_category_dropdown_renders_options(lib_ui):
    window, app = lib_ui["window"], lib_ui["app"]
    engine = lib_ui["engine"]
    adapter = lib_ui["adapter"]

    cat_name = "หมวดทดสอบ"
    json.loads(adapter.addCategory(cat_name))

    # Go to the add-book page and refresh the category combo
    QMetaObject.invokeMethod(find(window, "navBtnGenerator"), "clicked", Qt.DirectConnection)
    process(app)
    QMetaObject.invokeMethod(find(window, "barcodeGenScreen"), "loadCategoriesList", Qt.DirectConnection)
    process(app)

    combo = find(window, "genCategoryCombo")
    assert combo is not None

    # Open the dropdown with a real click on the combo
    itempos = combo.mapToGlobal(combo.width() * 0.9, combo.height() / 2)
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(int(itempos.x()), int(itempos.y())))
    process(app)
    process(app)

    # The dropdown popup must render its option rows (regression: empty 0px popup
    # caused by the StyledComboBox popup override dropping the options ListView).
    # Locate the options ListView: one row per model entry, hosted by the open popup.
    model = find(window, "genCategoryModel")
    lvs = [i for i in window.findChildren(QQuickItem)
          if i.metaObject().className() == "QQuickListView"
          and i.property("count") == model.property("count")
          and i.property("count") >= 2
          and i.parentItem() is not None
          and i.parentItem().metaObject().className() == "QQuickPopupItem"
          and i.parentItem().property("visible")]
    assert lvs, "options ListView not open in a visible popup"
    lv = lvs[0]
    popup = lv.parentItem()
    assert lv.height() > 50, "options ListView has no height (rows not rendered)"
    # Option rows must carry their text (regression: empty rows because the delegate
    # never bound model[control.textRole]). Delegates are not reachable via
    # findChildren (QML scene-graph parents differ from the QObject child tree),
    # so ask the options ListView for a row item directly.
    d = QQmlExpression(engine.rootContext(), lv, "itemAt(10, 54)").evaluate()
    d = d[0] if isinstance(d, tuple) and isinstance(d[0], QObject) else d
    assert d.property("text") == cat_name, "option text not bound to the delegate row"
    # The actually rendered Text (the delegate's contentItem) must carry the
    # value too — bare `text: text` inside contentItem does NOT resolve to the
    # delegate's text; it must reference the delegate through its id.
    ci = QQmlExpression(engine.rootContext(), d, "contentItem").evaluate()
    ci = ci[0] if isinstance(ci, tuple) and isinstance(ci[0], QObject) else ci
    assert ci is not None, "delegate has no contentItem"
    assert ci.property("text") == cat_name, "option text not rendered (contentItem text empty)"
    # Select the second option via a real click on its row
    row_y = 4 + 36 + 18  # popup padding + one row + half a row
    rowpos = popup.mapToGlobal(10, row_y)
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(int(rowpos.x()), int(rowpos.y())))
    process(app)
    process(app)
    assert combo.property("currentIndex") == 1  # index 0 is the default row


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
        "catalogCategoryCombo",
        "catalogCategoryModel",
        "bookCatalogView",
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
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.addImportPath(os.path.abspath("apps"))
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

    qapp.processEvents()
    conn.close()
    engine.deleteLater()
    qapp.processEvents()


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

    # Test input
    title_input = find(window, "genBookTitle")
    assert title_input is not None
    title_input.setProperty("text", "ชีววิทยาน่ารู้ ม.3")

    count_input = find(window, "genCopyCountInput")
    count_input.setProperty("text", "2")
    process(lib_ui["app"])

    # Save and commit (generates and saves barcodes into SQLite)
    save_btn = find(window, "btnExecuteGenerate")
    assert save_btn is not None
    save_btn.clicked.emit()
    process(lib_ui["app"])

    status_msg = find(window, "genStatusMessage")
    assert "✓" in status_msg.property("text")

    # Navigate to Dedicated Barcode Printout page (Page 7)
    find(window, "navBtnCategories").clicked.emit()
    process(lib_ui["app"])
    assert stack.property("currentIndex") == 7

    model = find(window, "genBarcodesModel")
    assert model is not None
    assert model.property("count") >= 1

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
    nav_btn = find(window, "navBtnGenerator")
    assert nav_btn is not None
    nav_btn.clicked.emit()
    process(lib_ui["app"])

    assert stack.property("currentIndex") == 6

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
    find(window, "navBtnGenerator").clicked.emit()
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


def test_book_and_grouping_split_page_saves_barcodes_and_manages_categories(lib_ui):
    window = lib_ui["window"]
    find(window, "navBtnGenerator").clicked.emit()
    process(lib_ui["app"])

    # Right side: add category and verify Left side genCategoryModel updates immediately
    cat_input = find(window, "categoryNameInput")
    add_cat_btn = find(window, "btnAddCategory")
    cat_input.setProperty("text", "หมวดคอมพิวเตอร์")
    add_cat_btn.clicked.emit()
    process(lib_ui["app"])
    assert find(window, "categoryListModel").property("count") >= 1
    assert find(window, "genCategoryModel").property("count") >= 2

    # Left side: add book and verify barcodes are generated and saved in database
    find(window, "genBookTitle").setProperty("text", "Python เบื้องต้น")
    find(window, "genCopyCountInput").setProperty("text", "3")
    find(window, "btnExecuteGenerate").clicked.emit()
    process(lib_ui["app"])

    assert "✓" in find(window, "genStatusMessage").property("text")
    books = json.loads(lib_ui["adapter"].getBooksWithBarcodes("Python"))
    assert len(books) == 1
    assert len(books[0]["barcodes"]) == 3


def test_barcode_printout_page_select_book_and_print_all(lib_ui):
    window = lib_ui["window"]
    # Add a second book so we can test printing selected vs printing all
    lib_ui["adapter"].addBook("เคมีอินทรีย์", "", "ดร.สมศรี", "", "", "", "2")

    # Navigate to Page 7 (Barcode Printout page)
    find(window, "navBtnCategories").clicked.emit()
    process(lib_ui["app"])

    model = find(window, "genBarcodesModel")
    assert model.property("count") >= 2

    # Validation: Deselect all and try printing selected -> error message
    invoke(window, "deselectAllPrintableBooks")
    find(window, "btnPrintSelectedPdf").clicked.emit()
    process(lib_ui["app"])
    assert "กรุณาเลือกหนังสืออย่างน้อย 1 รายการ" in find(window, "genPdfStatusText").property("text")

    # 1. Print Selected (select only first book)
    invoke(window, "setPrintableBookSelected", Q_ARG("QVariant", 0), Q_ARG("QVariant", True))
    find(window, "btnPrintSelectedPdf").clicked.emit()
    process(lib_ui["app"])
    assert "✓" in find(window, "genPdfStatusText").property("text")

    # 2. Print All
    find(window, "btnExportPdfSheet").clicked.emit()
    process(lib_ui["app"])
    assert "✓" in find(window, "genPdfStatusText").property("text")


def test_existing_book_selector_auto_selects_and_adds_copies_to_five(lib_ui):
    window = lib_ui["window"]
    find(window, "navBtnGenerator").clicked.emit()
    process(lib_ui["app"])

    # 1. Add book with 1 copy initially
    find(window, "genBookTitle").setProperty("text", "หัวใจคณิตศาสตร์ ม.ต้น")
    find(window, "genBookIsbn").setProperty("text", "9786164408500")
    find(window, "genBookAuthor").setProperty("text", "ณัฐอุดมพาณิชย์")
    find(window, "genCopyCountInput").setProperty("text", "1")
    find(window, "btnExecuteGenerate").clicked.emit()
    process(lib_ui["app"])

    # 2. Switch to Mode 1 (Add Copies to Existing) -> combo must auto-select (>= 0), height >= 32
    find(window, "btnModeAddCopies").clicked.emit()
    process(lib_ui["app"])
    combo = find(window, "genExistingBookCombo")
    assert combo.property("currentIndex") >= 0
    assert combo.property("displayText") != ""
    assert combo.property("height") >= 32

    # 3. Select the newly added book and add 4 copies -> total 5 barcodes in PDF
    model = find(window, "genExistingBooksModel")
    target_idx = 0
    for i in range(model.property("count")):
        item = model.get(i)
        t = item.property("title").toString() if hasattr(item.property("title"), "toString") else str(item.property("title"))
        if t == "หัวใจคณิตศาสตร์ ม.ต้น":
            target_idx = i
            break
    combo.setProperty("currentIndex", target_idx)
    find(window, "genCopyCountInput").setProperty("text", "4")
    find(window, "btnExecuteGenerate").clicked.emit()
    process(lib_ui["app"])

    books = json.loads(lib_ui["adapter"].getBooksWithBarcodes("หัวใจคณิตศาสตร์"))
    assert len(books) == 1
    assert len(books[0]["barcodes"]) == 5
    assert books[0]["barcodes"][0].endswith("-01")
    assert books[0]["barcodes"][4].endswith("-05")


def test_edit_book_dialog_increases_total_copies_and_syncs_printout(lib_ui):
    window = lib_ui["window"]
    res = json.loads(lib_ui["adapter"].addBook("ฟิสิกส์ ม.ต้น", "9786160001112", "อ.นิวตัน", "", "", "B-1", "1"))
    book_id = res["data"]["book_id"]

    invoke(
        window,
        "openEditBookDialog",
        Q_ARG("QVariant", book_id),
        Q_ARG("QVariant", "ฟิสิกส์ ม.ต้น"),
        Q_ARG("QVariant", "อ.นิวตัน"),
        Q_ARG("QVariant", "9786160001112"),
        Q_ARG("QVariant", 0),
        Q_ARG("QVariant", "B-1"),
        Q_ARG("QVariant", 1),
    )
    process(lib_ui["app"])

    copies_input = find(window, "editBookCopiesInput")
    assert copies_input is not None
    assert copies_input.property("text") == "1"
    copies_input.setProperty("text", "5")
    invoke(window, "submitEditBook")
    process(lib_ui["app"])

    books = json.loads(lib_ui["adapter"].getBooksWithBarcodes("ฟิสิกส์ ม.ต้น"))
    assert len(books) == 1
    assert len(books[0]["barcodes"]) == 5


def test_barcode_printout_exports_all_five_barcodes_to_pdf(lib_ui):
    import re
    window = lib_ui["window"]
    lib_ui["adapter"].addBook("เคมีคำนวณ ม.ต้น", "9786169990001", "อ.เคมี", "", "", "C-1", "5")

    find(window, "navBtnCategories").clicked.emit()
    process(lib_ui["app"])

    search_box = find(window, "barcodePrintSearchInput")
    search_box.setProperty("text", "เคมีคำนวณ")
    process(lib_ui["app"])

    model = find(window, "genBarcodesModel")
    assert model.property("count") == 1
    row0 = model.get(0)
    assert row0.property("copy_count").toInt() == 5
    preview_str = row0.property("barcode_preview").toString()
    assert "-01" in preview_str and "-05" in preview_str

    find(window, "btnPrintSelectedPdf").clicked.emit()
    process(lib_ui["app"])

    cat_screen = find(window, "categoryScreen")
    pdf_path = cat_screen.property("lastPdfExported")
    assert os.path.exists(pdf_path)
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    barcodes_in_pdf = re.findall(rb"\((SMTE-\d{5}-\d{2})\)", pdf_bytes)
    assert len(barcodes_in_pdf) == 5
    assert barcodes_in_pdf[0].endswith(b"-01")
    assert barcodes_in_pdf[4].endswith(b"-05")


def test_book_entry_page_shows_live_incoming_preview_and_current_inventory_grid(lib_ui):
    window = lib_ui["window"]
    stack = find(window, "librarianStack")

    # Open Book Entry & Management page (Tab 6)
    find(window, "navBtnGenerator").clicked.emit()
    process(lib_ui["app"])
    assert stack.property("currentIndex") == 6

    # Verify right-side current inventory grid displays existing seeded book(s)
    inv_model = find(window, "inventoryBooksModel")
    assert inv_model is not None
    initial_inv_count = inv_model.property("count")
    assert initial_inv_count >= 1

    # Type new book on the left -> verify right-side incoming preview updates live
    find(window, "genBookTitle").setProperty("text", "ดาราศาสตร์และอวกาศ ม.ปลาย")
    find(window, "genBookAuthor").setProperty("text", "ดร.เอกภพ")
    find(window, "genBookIsbn").setProperty("text", "978-616-111-222-3")
    find(window, "genShelfLocation").setProperty("text", "A-09")
    find(window, "genCopyCountInput").setProperty("text", "3")
    process(lib_ui["app"])

    inc_title = find(window, "incomingTitleText")
    inc_barcodes = find(window, "incomingBarcodePreviewText")
    assert inc_title is not None
    assert "ดาราศาสตร์และอวกาศ ม.ปลาย" in inc_title.property("text")
    assert "SMTE-" in inc_barcodes.property("text")
    assert "-01" in inc_barcodes.property("text")
    assert "-03" in inc_barcodes.property("text")

    # Save book -> verify it immediately appears in right-side current inventory grid
    find(window, "btnExecuteGenerate").clicked.emit()
    process(lib_ui["app"])
    assert inv_model.property("count") == initial_inv_count + 1


def test_dedicated_barcode_print_page_selection_metrics_and_navigation(lib_ui):
    window = lib_ui["window"]
    stack = find(window, "librarianStack")

    # Add two books in different categories
    cat_res = json.loads(lib_ui["adapter"].addCategory("วิทยาศาสตร์"))
    cat_id = str(cat_res["data"]["category_id"])
    lib_ui["adapter"].addBook("ฟิสิกส์นิวเคลียร์", "978111", "อ.สมชาย", "", cat_id, "S-1", "3")
    lib_ui["adapter"].addBook("ประวัติศาสตร์ไทย", "978222", "อ.สมหญิง", "", "", "H-1", "2")

    # Navigate from Book Entry page (Tab 6) to Dedicated Print page (Tab 7) via btnGoToPrintPage
    find(window, "navBtnGenerator").clicked.emit()
    process(lib_ui["app"])
    go_print_btn = find(window, "btnGoToPrintPage")
    assert go_print_btn is not None
    go_print_btn.clicked.emit()
    process(lib_ui["app"])
    assert stack.property("currentIndex") == 7

    # Verify live selection metrics (books selected & total barcode stickers)
    stickers_text = find(window, "selectedStickersCountText")
    assert stickers_text is not None
    assert "ดวง" in stickers_text.property("text")

    # Deselect all -> 0 stickers selected
    invoke(window, "deselectAllPrintableBooks")
    process(lib_ui["app"])
    assert "0" in stickers_text.property("text")

    # Select first book -> sticker count updates to match first book's copy_count
    invoke(window, "setPrintableBookSelected", Q_ARG("QVariant", 0), Q_ARG("QVariant", True))
    process(lib_ui["app"])
    row0_copies = find(window, "genBarcodesModel").get(0).property("copy_count").toInt()
    assert str(row0_copies) in stickers_text.property("text")

    # Filter by category ("วิทยาศาสตร์") -> preserves currentIndex and filters rows
    cat_combo = find(window, "barcodeCategoryFilterCombo")
    cat_combo.setProperty("currentIndex", 1)
    process(lib_ui["app"])
    assert cat_combo.property("currentIndex") == 1
    assert find(window, "genBarcodesModel").property("count") == 1


def test_edit_book_reduce_mistakenly_entered_copies(lib_ui):
    window = lib_ui["window"]
    find(window, "navBtnGenerator").clicked.emit()
    process(lib_ui["app"])

    # Register book with 5 copies by mistake
    res = json.loads(lib_ui["adapter"].addBook("ดาราศาสตร์เบื้องต้น", "9786161234567", "ดร.ดาว", "", "", "D-1", "5"))
    assert res["ok"] is True
    book_id = res["data"]["book_id"]

    # Open edit book dialog
    invoke(
        window,
        "openEditBookDialog",
        Q_ARG("QVariant", book_id),
        Q_ARG("QVariant", "ดาราศาสตร์เบื้องต้น"),
        Q_ARG("QVariant", "ดร.ดาว"),
        Q_ARG("QVariant", "9786161234567"),
        Q_ARG("QVariant", 0),
        Q_ARG("QVariant", "D-1"),
        Q_ARG("QVariant", 5),
    )
    process(lib_ui["app"])

    copies_input = find(window, "editBookCopiesInput")
    assert copies_input is not None
    assert copies_input.property("text") == "5"

    # Librarian entered 5 by mistake, corrects it to 2 copies
    copies_input.setProperty("text", "2")
    invoke(window, "submitEditBook")
    process(lib_ui["app"])

    # Verify database, barcode listing, and Tab 6 inventory grid all reflect 2 copies
    books = json.loads(lib_ui["adapter"].getBooksWithBarcodes("ดาราศาสตร์"))
    assert len(books) == 1
    assert len(books[0]["barcodes"]) == 2
    inv_model = find(window, "inventoryBooksModel")
    assert inv_model.get(0).property("total_copies").toInt() == 2


def test_isbn_autofill_overwrite_and_options(lib_ui, monkeypatch):
    win = lib_ui["window"]
    adapter = lib_ui["adapter"]
    from PySide6.QtCore import QObject

    # Seed cache for 9786162137792
    adapter.isbn_svc.save_cache("9786162137792", "รวมสูตรคณิต", "สกายบุ๊กส์")

    barcode_view = win.findChild(QObject, "barcodeGenScreen")
    assert barcode_view is not None

    title_input = win.findChild(QObject, "genBookTitle")
    author_input = win.findChild(QObject, "genBookAuthor")
    isbn_input = win.findChild(QObject, "genBookIsbn")
    status_msg = win.findChild(QObject, "genStatusMessage")
    chk_auto = win.findChild(QObject, "chkAutoFetchIsbn")

    # 4. Verify chkAutoFetchIsbn exists and is checked by default
    assert chk_auto is not None
    assert chk_auto.property("checked") is True

    # 1. Both blank -> fills both
    title_input.setProperty("text", "")
    author_input.setProperty("text", "")
    isbn_input.setProperty("text", "9786162137792")
    barcode_view.fetchIsbnAndAutofill()
    assert title_input.property("text") == "รวมสูตรคณิต"
    assert author_input.property("text") == "สกายบุ๊กส์"

    # 2. Existing text -> deletes and replaces with matching database metadata
    title_input.setProperty("text", "ชื่อที่พิมพ์เองเก่า")
    author_input.setProperty("text", "ผู้แต่งเดิม")
    barcode_view.fetchIsbnAndAutofill()
    assert title_input.property("text") == "รวมสูตรคณิต"
    assert author_input.property("text") == "สกายบุ๊กส์"

    # 3. Unknown ISBN -> preserves existing text, shows cannot fetch data
    monkeypatch.setattr("core.library.services.isbn_service.fetch_remote_providers", lambda *a, **k: None)
    isbn_input.setProperty("text", "9786167082493")
    barcode_view.fetchIsbnAndAutofill()
    assert title_input.property("text") == "รวมสูตรคณิต"
    assert author_input.property("text") == "สกายบุ๊กส์"
    assert "cannot fetch data" in status_msg.property("text")


def test_dialog_isbn_autofill_overwrite_and_options(lib_ui, monkeypatch):
    win = lib_ui["window"]
    adapter = lib_ui["adapter"]
    from PySide6.QtCore import QObject

    adapter.isbn_svc.save_cache("9786162137792", "รวมสูตรคณิต", "สกายบุ๊กส์")

    dialog_root = win.findChild(QObject, "bookDialogs")
    assert dialog_root is not None

    title_input = win.findChild(QObject, "newBookTitle")
    author_input = win.findChild(QObject, "newBookAuthor")
    isbn_input = win.findChild(QObject, "newBookIsbn")
    status_text = win.findChild(QObject, "addBookStatusText")
    chk_auto = win.findChild(QObject, "chkDialogAutoFetchIsbn")

    # 4. Verify chkDialogAutoFetchIsbn exists and is checked by default
    assert chk_auto is not None
    assert chk_auto.property("checked") is True

    # 1. Blank fields -> filled
    title_input.setProperty("text", "")
    author_input.setProperty("text", "")
    isbn_input.setProperty("text", "9786162137792")
    dialog_root.fetchDialogIsbnAndAutofill()
    assert title_input.property("text") == "รวมสูตรคณิต"
    assert author_input.property("text") == "สกายบุ๊กส์"
    assert "ดึงข้อมูลสำเร็จ" in status_text.property("text")

    # 2. Existing text -> deletes and replaces with matching database metadata
    title_input.setProperty("text", "พิมพ์เองในไดอะล็อก")
    author_input.setProperty("text", "ผู้แต่งในไดอะล็อก")
    dialog_root.fetchDialogIsbnAndAutofill()
    assert title_input.property("text") == "รวมสูตรคณิต"
    assert author_input.property("text") == "สกายบุ๊กส์"

    # 3. Unknown ISBN -> preserves and reports error
    title_input.setProperty("text", "พิมพ์ใหม่ก่อนลอง")
    author_input.setProperty("text", "ผู้แต่งใหม่ก่อนลอง")
    monkeypatch.setattr("core.library.services.isbn_service.fetch_remote_providers", lambda *a, **k: None)
    isbn_input.setProperty("text", "9786167082493")
    dialog_root.fetchDialogIsbnAndAutofill()
    assert title_input.property("text") == "พิมพ์ใหม่ก่อนลอง"
    assert author_input.property("text") == "ผู้แต่งใหม่ก่อนลอง"
    assert "cannot fetch data" in status_text.property("text")


def test_isbn_thai_keyboard_warning(lib_ui, monkeypatch):
    win = lib_ui["window"]
    from PySide6.QtCore import QObject

    barcode_view = win.findChild(QObject, "barcodeGenScreen")
    assert barcode_view is not None

    isbn_input = win.findChild(QObject, "genBookIsbn")
    status_msg = win.findChild(QObject, "genStatusMessage")

    isbn_input.setProperty("text", "ตึคภุภ")
    assert status_msg.property("text") == "✗ ลืมเปลี่ยนภาษา"

    called_remote = False
    monkeypatch.setattr(
        "core.library.services.isbn_service.fetch_remote_providers",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not be called")),
    )
    barcode_view.fetchIsbnAndAutofill()
    assert status_msg.property("text") == "✗ ลืมเปลี่ยนภาษา"

    isbn_input.setProperty("text", "")
    assert status_msg.property("text") == ""


def test_dialog_isbn_thai_keyboard_warning(lib_ui, monkeypatch):
    win = lib_ui["window"]
    from PySide6.QtCore import QObject

    dialog_root = win.findChild(QObject, "bookDialogs")
    assert dialog_root is not None

    isbn_input = win.findChild(QObject, "newBookIsbn")
    status_text = win.findChild(QObject, "addBookStatusText")

    isbn_input.setProperty("text", "ตึคภุภ")
    assert status_text.property("text") == "✗ ลืมเปลี่ยนภาษา"

    monkeypatch.setattr(
        "core.library.services.isbn_service.fetch_remote_providers",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not be called")),
    )
    dialog_root.fetchDialogIsbnAndAutofill()
    assert status_text.property("text") == "✗ ลืมเปลี่ยนภาษา"

    isbn_input.setProperty("text", "")
    assert status_text.property("text") == ""


def test_checkbox_labels_survive_startup_typography(lib_ui):
    """Regression: the startup Typography pass must not pin plain CheckBox
    implicit heights to a transient (pre-layout) value, which squashed the
    template label to height 0 and hid checkbox text (e.g. the
    auto-fetch + No-ISBN checkboxes on the barcode-generator page)."""
    from PySide6.QtCore import QObject
    win = lib_ui["window"]
    app = lib_ui["app"]
    stacks = [o for o in win.findChildren(QObject) if o.metaObject().className() == "QQuickStackLayout"]
    stacks[0].setProperty("currentIndex", 6)
    app.processEvents()
    for name in ["chkAutoFetchIsbn", "chkNoIsbnGen"]:
        chk = win.findChild(QObject, name)
        assert chk is not None, f"{name} not found on generator page"
        ci = chk.property("contentItem")
        assert ci.property("height") > 10, (
            f"{name} label squashed by typography: height={ci.property('height')}"
        )

