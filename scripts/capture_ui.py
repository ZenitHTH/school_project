#!/usr/bin/env python3
"""Capture UI screenshots for visual inspection."""

import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtGui import QGuiApplication
import PySide6.QtQuick
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QMetaObject, Qt, Q_ARG

from data.db import get_connection
from data.migrate import apply_migrations
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter
from data.repositories import book_repo


def main():
    app = QGuiApplication(sys.argv)
    conn = get_connection(":memory:", pin="123456")
    apply_migrations(conn)

    # Seed some sample data
    b1 = book_repo.add_book(conn, title="คู่มือวิทยาศาสตร์ ม.1 เล่ม 1", author="ดร.สมชาย สมหวัง", isbn="978-616-01-0011-2")
    book_repo.add_copies(conn, b1, barcodes=["SMTE-00001-01", "SMTE-00001-02"])
    b2 = book_repo.add_book(conn, title="คณิตศาสตร์เสริมประสบการณ์ ม.3", author="อ.วรรณา ก้าวหน้า", isbn="978-616-02-0022-3")
    book_repo.add_copies(conn, b2, barcodes=["SMTE-00002-01"])

    adapter = LibrarianAdminAdapter(conn)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("librarianAdmin", adapter)

    qml_path = str(PROJECT_ROOT / "apps" / "librarian_management_app" / "qml" / "Main.qml")
    engine.load(qml_path)
    app.processEvents()

    window = engine.rootObjects()[0]
    out_dir = PROJECT_ROOT / "ui_screenshots"
    out_dir.mkdir(exist_ok=True)

    from PySide6.QtCore import QObject
    def find(obj, name):
        return obj.findChild(QObject, name)

    # 1. Catalog Screen (Index 0)
    stack = find(window, "librarianStack")
    stack.setProperty("currentIndex", 0)
    app.processEvents()
    img_catalog = window.grabWindow()
    img_catalog.save(str(out_dir / "01_catalog_screen.png"))
    print("Saved 01_catalog_screen.png")

    # 2. Generator Screen (Index 6) - New Book preview
    stack.setProperty("currentIndex", 6)
    app.processEvents()
    QMetaObject.invokeMethod(window, "initGeneratorPage")
    app.processEvents()

    title_input = find(window, "genBookTitle")
    if title_input:
        title_input.setProperty("text", "เคมีพื้นฐานและห้องทดลอง ม.2")
    author_input = find(window, "genBookAuthor")
    if author_input:
        author_input.setProperty("text", "ผศ.ดร.วิชัย นวัตกรรม")
    isbn_input = find(window, "genBookIsbn")
    if isbn_input:
        isbn_input.setProperty("text", "978-616-09-9876-5")
    shelf_input = find(window, "genShelfLocation")
    if shelf_input:
        shelf_input.setProperty("text", "SCI-B03")
    count_input = find(window, "genCopyCountInput")
    if count_input:
        count_input.setProperty("text", "3")

    QMetaObject.invokeMethod(window, "updateGenPreview")
    app.processEvents()

    img_gen_new = window.grabWindow()
    img_gen_new.save(str(out_dir / "02_generator_new_book.png"))
    print("Saved 02_generator_new_book.png")

    # Commit the new book
    QMetaObject.invokeMethod(window, "executeGenerateAndSave")
    app.processEvents()
    img_gen_committed = window.grabWindow()
    img_gen_committed.save(str(out_dir / "03_generator_committed.png"))
    print("Saved 03_generator_committed.png")

    # 3. Generator Screen (Index 6) - Add Copies to Existing Book mode
    btn_add_copies = find(window, "btnModeAddCopies")
    if btn_add_copies:
        btn_add_copies.clicked.emit()
    app.processEvents()
    img_gen_existing = window.grabWindow()
    img_gen_existing.save(str(out_dir / "04_generator_add_copies.png"))
    print("Saved 04_generator_add_copies.png")

    # 4. Desk Checkout Screen (Index 1)
    stack.setProperty("currentIndex", 1)
    app.processEvents()
    img_desk = window.grabWindow()
    img_desk.save(str(out_dir / "05_desk_checkout.png"))
    print("Saved 05_desk_checkout.png")

    # 5. Category Management Screen (Index 7)
    cat1_id = book_repo.add_category(conn, "วิทยาศาสตร์และเทคโนโลยี")
    book_repo.add_category(conn, "วรรณกรรมเยาวชน")
    book_repo.add_category(conn, "ประวัติศาสตร์และสังคม")

    # Link books b1 and b2 to category 1
    conn.execute("UPDATE books SET category_id = ?, category = 'วิทยาศาสตร์และเทคโนโลยี' WHERE book_id IN (?, ?)", (cat1_id, b1, b2))

    stack.setProperty("currentIndex", 7)
    app.processEvents()
    QMetaObject.invokeMethod(window, "loadCategoriesList")
    app.processEvents()

    cat_input = find(window, "categoryNameInput")
    if cat_input:
        cat_input.setProperty("text", "คอมพิวเตอร์และปัญญาประดิษฐ์")
    app.processEvents()

    img_cat = window.grabWindow()
    img_cat.save(str(out_dir / "06_category_management.png"))
    print("Saved 06_category_management.png")

    # 6. Rename Dialog Preview
    QMetaObject.invokeMethod(window, "openRenameCategoryDialog", Q_ARG("QVariant", cat1_id), Q_ARG("QVariant", "วิทยาศาสตร์และนวัตกรรมใหม่"))
    app.processEvents()
    img_rename = window.grabWindow()
    img_rename.save(str(out_dir / "07_rename_category_dialog.png"))
    print("Saved 07_rename_category_dialog.png")
    rename_dlg = find(window, "renameCategoryDialog")
    if rename_dlg:
        rename_dlg.close()
    app.processEvents()

    # 7. Reassign & Delete Dialog Preview (with books b1 and b2)
    QMetaObject.invokeMethod(window, "requestDeleteCategory", Q_ARG("QVariant", cat1_id), Q_ARG("QVariant", "วิทยาศาสตร์และเทคโนโลยี"))
    app.processEvents()
    img_reassign = window.grabWindow()
    img_reassign.save(str(out_dir / "08_reassign_delete_dialog.png"))
    print("Saved 08_reassign_delete_dialog.png")


if __name__ == "__main__":
    main()
