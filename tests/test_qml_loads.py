import os
import sys
import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from data.db import get_connection
from data.migrate import apply_migrations
from apps.student_management_app.adapters.student_admin_adapter import StudentAdminAdapter
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter
from apps.booth_app.adapters.booth_adapter import BoothAdapter


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


def test_student_qml_loads(qapp, tmp_path):
    db_file = str(tmp_path / "qml_student.sqlite")
    conn = get_connection(db_file, pin="123456")
    apply_migrations(conn)

    adapter = StudentAdminAdapter(conn)
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.addImportPath(os.path.abspath("apps"))
    engine.rootContext().setContextProperty("studentAdmin", adapter)

    qml_file = os.path.abspath("apps/student_management_app/qml/Main.qml")
    engine.load(qml_file)
    assert len(engine.rootObjects()) > 0, "Student Management Main.qml failed to load!"
    conn.close()


def test_librarian_qml_loads(qapp, tmp_path):
    db_file = str(tmp_path / "qml_library.sqlite")
    conn = get_connection(db_file, pin="123456")
    apply_migrations(conn)

    adapter = LibrarianAdminAdapter(conn)
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda ws: warnings.extend([w.toString() for w in ws]))
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.addImportPath(os.path.abspath("apps"))
    engine.rootContext().setContextProperty("librarianAdmin", adapter)

    qml_file = os.path.abspath("apps/librarian_management_app/qml/Main.qml")
    engine.load(qml_file)
    assert len(engine.rootObjects()) > 0, "Librarian Management Main.qml failed to load!"
    ref_errors = [w for w in warnings if "ReferenceError" in w or "TypeError" in w]
    assert not ref_errors, f"Unexpected QML errors: {ref_errors}"
    conn.close()


def test_booth_qml_loads(qapp, tmp_path):
    db_file = str(tmp_path / "qml_booth.sqlite")
    conn = get_connection(db_file, pin="123456")
    apply_migrations(conn)

    adapter = BoothAdapter(conn)
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.addImportPath(os.path.abspath("apps"))
    engine.rootContext().setContextProperty("boothAdapter", adapter)

    qml_file = os.path.abspath("apps/booth_app/qml/Main.qml")
    engine.load(qml_file)
    assert len(engine.rootObjects()) > 0, "Booth App Main.qml failed to load!"
    conn.close()


def test_common_qml_components_load(qapp):
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtQml import QQmlComponent
    QQuickStyle.setStyle("Fusion")

    engine = QQmlApplicationEngine()
    common_dir = os.path.abspath("apps/common_qml")
    engine.addImportPath(os.path.abspath("apps"))
    engine.addImportPath(common_dir)

    components = [
        "StyledSearchField.qml",
        "PaginationBar.qml",
        "ActionFeedbackBanner.qml",
        "AuditLogView.qml",
        "FirstLaunchDialog.qml",
        "SettingsView.qml",
        "BundledFonts.qml",
        "SettingsPreviewCard.qml",
        "SettingsControlsCard.qml",
        "SettingsHeader.qml",
        "SettingsFooter.qml",
        "StyledTextInput.qml",
        "StyledComboBox.qml",
        "StyledButton.qml",
        "StyledDialog.qml",
    ]

    for comp_name in components:
        comp_path = os.path.join(common_dir, comp_name)
        comp = QQmlComponent(engine, comp_path)
        assert not comp.isError(), f"{comp_name} errors: {[e.toString() for e in comp.errors()]}"
        obj = comp.create()
        assert obj is not None, f"Failed to instantiate {comp_name}"


def test_common_qml_module_import(qapp):
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtQml import QQmlComponent
    QQuickStyle.setStyle("Fusion")

    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps"))

    qml_text = """
    import QtQuick 2.15
    import QtQuick.Controls 2.15
    import common_qml 1.0

    ApplicationWindow {
        id: harnessWindow
        visible: true
        width: 600
        height: 600
        StyledSearchField { id: search }
        PaginationBar { id: pager }
        ActionFeedbackBanner { id: banner }
        AuditLogView { id: audit }
        FirstLaunchDialog { id: dialog }
        SettingsView { id: settings }
        BundledFonts { id: fonts }
        SettingsPreviewCard { id: preview }
        SettingsControlsCard { id: controls }
        SettingsHeader { id: header }
        SettingsFooter { id: footer }
        StyledTextInput { id: textInput }
        StyledComboBox { id: comboBox }
        StyledButton { id: button }
        StyledDialog { id: styledDialog; objectName: "styledDialog"; standardButtons: Dialog.Ok | Dialog.Cancel }
        StyledDialog { id: styledDialogNoButtons; objectName: "styledDialogNoButtons"; standardButtons: Dialog.NoButton }
    }
    """
    comp = QQmlComponent(engine)
    comp.setData(qml_text.encode("utf-8"), "")
    assert not comp.isError(), f"common_qml module import errors: {[e.toString() for e in comp.errors()]}"
    obj = comp.create()
    assert obj is not None, "Failed to instantiate root window with common_qml components"
    qapp.processEvents()

    from PySide6.QtQuick import QQuickItem
    from PySide6.QtCore import QObject

    styled = obj.findChild(QObject, "styledDialog")
    styled.open()
    qapp.processEvents()
    ok_btn = styled.findChild(QQuickItem, "dialogOkButton")
    cancel_btn = styled.findChild(QQuickItem, "dialogCancelButton")
    assert ok_btn is not None, "StyledDialog footer OK button (accepted wiring) missing"
    assert cancel_btn is not None, "StyledDialog footer Cancel button (rejected wiring) missing"
    assert bool(ok_btn.property("visible")) and bool(cancel_btn.property("visible")), \
        "Footer buttons should be visible for Ok|Cancel standardButtons"
    styled.close()
    qapp.processEvents()

    no_btn_dlg = obj.findChild(QObject, "styledDialogNoButtons")
    no_btn_dlg.open()
    qapp.processEvents()
    no_btn_ok = no_btn_dlg.findChild(QQuickItem, "dialogOkButton")
    assert not bool(no_btn_ok.property("visible")), "Footer must be hidden for NoButton standardButtons"
    no_btn_dlg.close()
    qapp.processEvents()
    obj.close()
    qapp.processEvents()

