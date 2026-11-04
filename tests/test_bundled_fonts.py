"""
tests/test_bundled_fonts.py
Tests bundled font assets, QFontDatabase registration, QML FontLoader, and packaging specs.
"""
import os
import sys
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtGui import QGuiApplication, QFont
from PySide6.QtQml import QQmlApplicationEngine
from core.shared.mock_qt import get_bundled_fonts_dir, register_bundled_fonts


@pytest.fixture(scope="session")
def qapp():
    return QGuiApplication.instance() or QGuiApplication(sys.argv)


def test_bundled_fonts_directory_contains_font_files():
    font_dir = get_bundled_fonts_dir()
    assert os.path.isdir(font_dir)
    files = os.listdir(font_dir)
    required = ["NotoSansThai-Regular.ttf", "NotoSansThai-Bold.ttf", "THSarabunNew.ttf", "Tahoma.ttf"]
    for req in required:
        assert req in files, f"Missing required font: {req}"


def test_register_bundled_fonts_loads_families(qapp):
    families = register_bundled_fonts()
    assert len(families) > 0
    assert any("Noto Sans Thai" in f for f in families)
    assert any("TH Sarabun New" in f for f in families)
    noto_sub = [s.lower() for s in QFont.substitutes("Noto Sans")]
    assert any("noto sans thai" in s for s in noto_sub)


def test_bundled_fonts_qml_loads(qapp):
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.abspath("apps"))
    engine.addImportPath(os.path.abspath("apps/common_qml"))
    engine.load(os.path.abspath("apps/common_qml/BundledFonts.qml"))
    assert len(engine.rootObjects()) > 0


def test_packaging_specs_include_fonts_and_scripts():
    specs = [
        "packaging/librarian_management.spec",
        "packaging/student_management.spec",
        "packaging/booth_app.spec",
    ]
    for spec in specs:
        with open(spec, "r", encoding="utf-8") as f:
            content = f.read()
        assert "apps/common_qml/fonts" in content, f"Missing fonts in {spec}"
        assert "apps/common_qml/*.js" in content, f"Missing js in {spec}"
