"""
tests/test_ui_text_and_dropdown_alignment.py
Reproduction and regression test suite verifying left/vertical-center alignment
and padding across text inputs, Typography engine, and combo dropdowns.
"""
import os
import sys
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtGui import QGuiApplication
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlExpression
from PySide6.QtCore import QUrl

ALIGN_LEFT = 1       # TextInput.AlignLeft / Text.AlignLeft
ALIGN_VCENTER = 128  # TextInput.AlignVCenter / Text.AlignVCenter


@pytest.fixture(scope="session")
def qapp():
    QQuickStyle.setStyle("Fusion")
    return QGuiApplication.instance() or QGuiApplication(sys.argv)


def _load_view(rel_path: str):
    """Create QQmlApplicationEngine, load QML file, and return (engine, rootObject)."""
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps"))
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.load(os.path.abspath(rel_path))
    assert len(engine.rootObjects()) > 0, f"Failed to load {rel_path}"
    return engine, engine.rootObjects()[0]


def _eval_prop(engine, item, prop_expr: str):
    """Evaluate a QML expression on an item and return result."""
    expr = QQmlExpression(engine.rootContext(), item, prop_expr)
    val, err = expr.evaluate()
    assert not err, f"Failed evaluating {prop_expr}: {expr.error()}"
    return val


def test_styled_text_components_explicit_alignment(qapp):
    """Verify StyledTextInput and StyledSearchField explicitly declare left and v-center."""
    for rel_path in ("apps/common_qml/StyledTextInput.qml", "apps/common_qml/StyledSearchField.qml"):
        with open(os.path.abspath(rel_path), "r", encoding="utf-8") as f:
            src = f.read()
        assert "horizontalAlignment: TextInput.AlignLeft" in src, f"{rel_path} missing explicit horizontalAlignment"
        assert "verticalAlignment: TextInput.AlignVCenter" in src, f"{rel_path} missing explicit verticalAlignment"


def test_typography_engine_alignment_values(qapp):
    """Verify Typography.js sets verticalAlignment to 128 (not 4) and horizontalAlignment to 1."""
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps"))
    engine.addImportPath(os.path.abspath("apps/common_qml"))

    comp = QQmlComponent(engine)
    base_url = QUrl.fromLocalFile(os.path.abspath("apps/common_qml/harness.qml"))
    comp.setData(b"""
import QtQuick 2.15
import QtQuick.Controls 2.15
import common_qml 1.0
import "Typography.js" as Typography

Item {
    id: harness
    property alias input: testInput
    StyledTextInput { id: testInput; objectName: "testInput" }
    function applyTypo() {
        Typography.applyToNode(testInput, {family: "", factor: 1.0});
    }
}
""", base_url)
    root = comp.create()
    assert root is not None, f"Harness creation failed: {comp.errors()}"
    root.applyTypo()

    inp = root.findChild(object, "testInput")
    v_align = _eval_prop(engine, inp, "verticalAlignment")
    h_align = _eval_prop(engine, inp, "horizontalAlignment")
    assert v_align == ALIGN_VCENTER, f"Typography set verticalAlignment to {v_align}, expected 128 (not 4)"
    assert h_align == ALIGN_LEFT, f"Typography set horizontalAlignment to {h_align}, expected 1"


def test_settings_font_family_combo_alignment(qapp):
    """Verify fontFamilyCombo contentItem and delegate have leftPadding=12 and left/vcenter align."""
    engine, root = _load_view("apps/common_qml/SettingsControlsCard.qml")
    combo = root.findChild(object, "fontFamilyCombo")
    assert combo is not None

    ci = combo.property("contentItem")
    assert ci is not None, "fontFamilyCombo missing custom contentItem"
    assert ci.property("leftPadding") == 12, f"fontFamilyCombo contentItem leftPadding is {ci.property('leftPadding')}, expected 12"
    assert _eval_prop(engine, ci, "horizontalAlignment") == ALIGN_LEFT
    assert _eval_prop(engine, ci, "verticalAlignment") == ALIGN_VCENTER


def test_barcode_generator_inputs_and_combo_alignment(qapp):
    """Verify BarcodeGeneratorView inputs and genCategoryCombo alignments and padding."""
    engine, root = _load_view("apps/librarian_management_app/qml/views/BarcodeGeneratorView.qml")
    field_names = ["genBookTitle", "genBookAuthor", "genBookIsbn", "genShelfLocation", "genCopyCountInput"]

    for name in field_names:
        item = root.findChild(object, name)
        assert item is not None
        assert _eval_prop(engine, item, "horizontalAlignment") == ALIGN_LEFT
        assert _eval_prop(engine, item, "verticalAlignment") == ALIGN_VCENTER

    combo = root.findChild(object, "genCategoryCombo")
    ci = combo.property("contentItem")
    assert ci is not None
    assert ci.property("leftPadding") >= 12, f"genCategoryCombo leftPadding is {ci.property('leftPadding')}, expected >= 12"
    assert _eval_prop(engine, ci, "horizontalAlignment") == ALIGN_LEFT
    assert _eval_prop(engine, ci, "verticalAlignment") == ALIGN_VCENTER


def test_edit_book_dialog_combo_alignment(qapp):
    """Verify EditBookDialog categoryCombo has left-aligned contentItem with leftPadding 12."""
    engine, root = _load_view("apps/librarian_management_app/qml/dialogs/EditBookDialog.qml")
    combo = root.findChild(object, "editBookCategoryCombo")
    assert combo is not None

    ci = combo.property("contentItem")
    assert ci is not None
    assert ci.property("leftPadding") == 12
    assert _eval_prop(engine, ci, "horizontalAlignment") == ALIGN_LEFT
    assert _eval_prop(engine, ci, "verticalAlignment") == ALIGN_VCENTER
