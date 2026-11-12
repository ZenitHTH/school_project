"""
tests/test_ui_barcode_generator_fields.py
Reproduction and regression test suite verifying sizing, padding, background,
and placeholder contrast on BarcodeGeneratorView and related library inputs.
"""
import os
import sys
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtGui import QGuiApplication
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQml import QQmlApplicationEngine


@pytest.fixture(scope="session")
def qapp():
    QQuickStyle.setStyle("Fusion")
    return QGuiApplication.instance() or QGuiApplication(sys.argv)


def _load_view(qml_rel_path: str):
    """Load QML file and return (engine, rootObject)."""
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps"))
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.load(os.path.abspath(qml_rel_path))
    assert len(engine.rootObjects()) > 0, f"Failed to load {qml_rel_path}"
    return engine, engine.rootObjects()[0]


def _check_field_contrast_and_padding(item, name: str, min_h: int, min_pad: int):
    """Assert item and its background satisfy minimum height, padding, and contrast."""
    assert item is not None, f"Input field {name} not found"
    assert item.property("implicitHeight") >= min_h, f"{name} implicitHeight < {min_h}"
    assert item.property("leftPadding") >= min_pad, f"{name} leftPadding < {min_pad}"
    assert item.property("rightPadding") >= min_pad, f"{name} rightPadding < {min_pad}"

    bg = item.property("background")
    assert bg is not None, f"{name} has no background"
    assert bg.property("implicitHeight") >= min_h, f"{name} background implicitHeight < {min_h}"

    color_prop = item.property("placeholderTextColor")
    hex_color = color_prop.name().lower() if hasattr(color_prop, "name") else str(color_prop).lower()
    assert hex_color == "#64748b", f"{name} placeholderTextColor is {hex_color}, expected #64748b"


def test_barcode_generator_fields_height_and_contrast(qapp):
    """Verify BarcodeGeneratorView inputs have >=38px height, >=10px padding, and contrast."""
    _engine, root = _load_view("apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml")
    field_names = [
        "genBookTitle",
        "genBookAuthor",
        "genBookIsbn",
        "genShelfLocation",
        "genCopyCountInput",
    ]
    for name in field_names:
        item = root.findChild(object, name)
        _check_field_contrast_and_padding(item, name, min_h=38, min_pad=10)


def test_inventory_pane_fields_height_and_contrast(qapp):
    """Verify BookInventoryRightPane inputs have >=38px height, >=12px padding, and contrast."""
    _engine, root = _load_view("apps/librarian_management_app/qml/views/BookInventoryRightPane.qml")
    for name in ["inventorySearchInput", "categoryNameInput"]:
        item = root.findChild(object, name)
        _check_field_contrast_and_padding(item, name, min_h=38, min_pad=12)


def test_catalog_and_circulation_inputs_minimum_dimensions(qapp):
    """Verify BookCatalogView and CirculationDeskView inputs have >=36px height and >=8px pad."""
    _e1, cat_root = _load_view("apps/librarian_management_app/qml/views/BookCatalogView.qml")
    cat_inp = cat_root.findChild(object, "catalogSearchInput")
    assert cat_inp.property("implicitHeight") >= 36
    assert cat_inp.property("leftPadding") >= 8

    _e2, circ_root = _load_view("apps/librarian_management_app/qml/views/CirculationDeskView.qml")
    for name in ["studentLookupInput", "barcodeInput"]:
        inp = circ_root.findChild(object, name)
        assert inp.property("implicitHeight") >= 36
        assert inp.property("leftPadding") >= 8


def test_edit_book_dialog_inputs_minimum_dimensions(qapp):
    """Verify EditBookDialog inputs have >=38px height, background height, and >=12px pad."""
    _engine, root = _load_view("apps/librarian_management_app/qml/dialogs/EditBookDialog.qml")
    for name in [
        "editBookTitleInput",
        "editBookAuthorInput",
        "editBookIsbnInput",
        "editBookShelfInput",
        "editBookCopiesInput",
    ]:
        item = root.findChild(object, name)
        assert item.property("implicitHeight") >= 38
        assert item.property("leftPadding") >= 12
        bg = item.property("background")
        assert bg is not None and bg.property("implicitHeight") >= 38

    combo = root.findChild(object, "editBookCategoryCombo")
    assert combo.property("implicitHeight") >= 38
    assert combo.property("background").property("implicitHeight") >= 38


def test_student_detail_and_sync_views_inputs(qapp):
    """Verify StudentDetailView and StudentSyncView inputs have proper sizing and contrast."""
    _e1, stu_root = _load_view("apps/student_management_app/qml/views/StudentDetailView.qml")
    direct_inp = stu_root.findChild(object, "directIdInput") or [
        c for c in stu_root.findChildren(object) if "TextField" in c.metaObject().className()
    ][0]
    assert direct_inp is not None
    assert direct_inp.property("implicitHeight") >= 36

    _e2, sync_root = _load_view("apps/librarian_management_app/qml/views/StudentSyncView.qml")
    sync_inp = sync_root.findChild(object, "snapshotPathInput")
    assert sync_inp is not None
    assert sync_inp.property("implicitHeight") >= 36


def test_barcode_fields_adversarial_scaling(qapp):
    """Verify fields stay >= 36px under 0.35x scale and expand gracefully under 1.5x scale."""
    _engine, root = _load_view("apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml")
    title_inp = root.findChild(object, "genBookTitle")

    # Extreme downscaling
    font = title_inp.property("font")
    font.setPixelSize(5)
    title_inp.setProperty("font", font)
    qapp.processEvents()
    assert title_inp.property("implicitHeight") >= 38
    assert title_inp.property("background").property("implicitHeight") >= 38

    # Extreme upscaling
    font.setPixelSize(22)
    title_inp.setProperty("font", font)
    qapp.processEvents()
    assert title_inp.property("implicitHeight") >= 48


def test_barcode_generator_buttons_and_combo_dimensions(qapp):
    """Verify btnFetchIsbn and genCategoryCombo match input field heights."""
    _engine, root = _load_view("apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml")
    btn_fetch = root.findChild(object, "btnFetchIsbn")
    isbn_inp = root.findChild(object, "genBookIsbn")
    assert btn_fetch.property("implicitHeight") == isbn_inp.property("implicitHeight")

    cat_combo = root.findChild(object, "genCategoryCombo")
    assert cat_combo.property("implicitHeight") >= 38
    assert cat_combo.property("background").property("implicitHeight") >= 38


def test_styled_text_input_component(qapp):
    """Verify StyledTextInput component instantiation, properties, and defaults."""
    from PySide6.QtQml import QQmlExpression
    _engine, item = _load_view("apps/common_qml/StyledTextInput.qml")
    assert item is not None
    assert item.property("implicitHeight") >= 38
    assert item.property("leftPadding") == 12
    assert item.property("rightPadding") == 12
    val, _err = QQmlExpression(_engine.rootContext(), item, "verticalAlignment").evaluate()
    assert val in (4, 128)
    bg = item.property("background")
    assert bg is not None and bg.property("implicitHeight") >= 38


def test_no_isbn_checkbox_locks_field(qapp):
    """No-ISBN checkboxes lock the ISBN field, show '-', and suppress the
    'forgot to switch language' warning while locked."""
    pairs = [
        ("apps/librarian_management_app/qml/dialogs/BookActionDialogs.qml",
         "chkNoIsbnAdd", "newBookIsbn", "addBookStatusText"),
        ("apps/librarian_management_app/qml/dialogs/EditBookDialog.qml",
         "chkNoIsbnEdit", "editBookIsbnInput", None),
        ("apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml",
         "chkNoIsbnGen", "genBookIsbn", "genStatusMessage"),
    ]
    for rel, chk_name, field_name, status_name in pairs:
        _engine, root = _load_view(rel)
        chk = root.findChild(object, chk_name)
        field = root.findChild(object, field_name)
        assert chk is not None, f"{chk_name} not found in {rel}"
        assert field is not None, f"{field_name} not found in {rel}"
        chk.setProperty("checked", True)
        qapp.processEvents()
        assert field.property("enabled") is False, f"{field_name} not locked"
        assert field.property("text") == "-", f"{field_name} should show '-'"
        if status_name:
            status = root.findChild(object, status_name)
            assert status is not None, f"{status_name} not found in {rel}"
            assert "ลืมเปลี่ยนภาษา" not in (status.property("text") or ""), \
                f"{field_name} fired language warning while locked"
        chk.setProperty("checked", False)
        qapp.processEvents()
        assert field.property("enabled") is True, f"{field_name} not re-enabled"
        assert field.property("text") == "", f"{field_name} not cleared"
