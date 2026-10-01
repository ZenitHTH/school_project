import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent

    property var rootWindow: null

    property alias addBookDialog: addBookDialog
    property alias newBookTitle: newBookTitle
    property alias newBookIsbn: newBookIsbn
    property alias newBookAuthor: newBookAuthor
    property alias newBookBarcodes: newBookBarcodes

    property alias addCopiesDialog: addCopiesDialog
    property alias addCopiesCountInput: addCopiesCountInput

    property alias barcodeConfirmDialog: barcodeConfirmDialog
    property alias barcodeConfirmList: barcodeConfirmList
    property alias barcodeConfirmModel: barcodeConfirmModel
    property alias pdfExportStatusText: pdfExportStatusText

    property alias editBookDialog: editBookDialog
    property alias editBookTitleInput: editBookTitleInput
    property alias editBookAuthorInput: editBookAuthorInput
    property alias editBookIsbnInput: editBookIsbnInput
    property alias editBookCategoryCombo: editBookCategoryCombo
    property alias editBookCategoryModel: editBookCategoryModel
    property alias editBookShelfInput: editBookShelfInput
    property alias editBookStatusText: editBookStatusText

    property alias deleteBookDialog: deleteBookDialog
    property alias deleteBookConfirmText: deleteBookConfirmText
    property alias btnConfirmDeleteBook: btnConfirmDeleteBook

    function openAddCopiesDialog(bookId, title) {
        if (rootWindow) {
            rootWindow.selectedBookId = bookId
            rootWindow.selectedBookTitle = title
        }
        addCopiesCountInput.text = "1"
        addCopiesDialog.open()
    }

    function openEditBookDialog(bookId, title, author, isbn, categoryId, shelf) {
        editBookDialog.targetBookId = bookId
        editBookTitleInput.text = title
        editBookAuthorInput.text = author
        editBookIsbnInput.text = isbn
        editBookShelfInput.text = shelf
        editBookStatusText.text = ""

        editBookCategoryModel.clear()
        editBookCategoryModel.append({ "category_id": 0, "name": "-- ไม่ระบุหมวดหมู่ --" })
        var selectedIndex = 0
        try {
            var cats = JSON.parse(librarianAdmin.getCategories())
            for (var i = 0; i < cats.length; i++) {
                editBookCategoryModel.append(cats[i])
                if (cats[i].category_id === categoryId) selectedIndex = i + 1
            }
        } catch (e) {}
        editBookCategoryCombo.currentIndex = selectedIndex
        editBookDialog.open()
    }

    function submitEditBook() {
        var title = editBookTitleInput.text.trim()
        if (!title) {
            editBookStatusText.text = "✗ กรุณาระบุชื่อหนังสือ"
            return
        }
        var catId = ""
        if (editBookCategoryCombo.currentIndex > 0) {
            catId = editBookCategoryModel.get(editBookCategoryCombo.currentIndex).category_id.toString()
        }
        var res = JSON.parse(librarianAdmin.updateBook(
            editBookDialog.targetBookId,
            title,
            editBookIsbnInput.text.trim(),
            editBookAuthorInput.text.trim(),
            catId,
            editBookShelfInput.text.trim()
        ))
        if (res.ok) {
            editBookDialog.close()
            if (rootWindow) {
                rootWindow.searchBooks()
                rootWindow.loadBooksForExistingSelector()
            }
        } else {
            editBookStatusText.text = "✗ " + (res.error || "แก้ไขไม่สำเร็จ")
        }
    }

    function openDeleteBookDialog(bookId, title) {
        deleteBookDialog.targetBookId = bookId
        deleteBookDialog.targetBookTitle = title
        deleteBookConfirmText.text = "ต้องการลบหนังสือ '" + title + "' หรือไม่?"
        deleteBookDialog.open()
    }

    function executeDeleteBook() {
        var res = JSON.parse(librarianAdmin.deleteBook(deleteBookDialog.targetBookId))
        if (res.ok) {
            deleteBookDialog.close()
            if (rootWindow) {
                rootWindow.searchBooks()
                rootWindow.loadBooksForExistingSelector()
            }
        } else {
            deleteBookConfirmText.text = "✗ " + (res.error || "ลบหนังสือไม่สำเร็จ")
        }
    }

    // 1. Add Book Dialog
    Dialog {
        id: addBookDialog
        objectName: "addBookDialog"
        title: "เพิ่มหนังสือใหม่และสร้างบาร์โค้ด"
        modal: true
        closePolicy: Popup.CloseOnEscape
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: parent
        width: Math.min(480, rootWindow ? rootWindow.width - 40 : 450)

        ColumnLayout {
            TextField { id: newBookTitle; objectName: "newBookTitle"; placeholderText: "ชื่อหนังสือ" }
            TextField { id: newBookIsbn; objectName: "newBookIsbn"; placeholderText: "ISBN (บาร์โค้ดจากสำนักพิมพ์)" }
            TextField { id: newBookAuthor; objectName: "newBookAuthor"; placeholderText: "ผู้แต่ง" }
            TextField { id: newBookBarcodes; objectName: "newBookBarcodes"; placeholderText: "จำนวนเล่ม (เช่น 2) หรือระบุบาร์โค้ดคั่นด้วยจุลภาค" }
        }

        onAccepted: {
            if (newBookTitle.text) {
                var res = JSON.parse(librarianAdmin.addBook(newBookTitle.text, newBookIsbn.text, newBookAuthor.text, "", "", "", newBookBarcodes.text))
                if (res.ok && res.data && res.data.barcodes && res.data.barcodes.length > 0) {
                    barcodeConfirmModel.clear()
                    if (rootWindow) rootWindow.lastGeneratedBarcodes = res.data.barcodes
                    for (var i = 0; i < res.data.barcodes.length; i++) {
                        barcodeConfirmModel.append({ "barcode": res.data.barcodes[i] })
                    }
                    pdfExportStatusText.text = ""
                    barcodeConfirmDialog.open()
                }
                if (rootWindow) rootWindow.searchBooks()
            }
        }
    }

    // 2. Add Copies Dialog
    Dialog {
        id: addCopiesDialog
        objectName: "addCopiesDialog"
        title: "เพิ่มเล่มหนังสือ: " + (rootWindow ? rootWindow.selectedBookTitle : "")
        modal: true
        closePolicy: Popup.CloseOnEscape
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: parent
        width: Math.min(450, rootWindow ? rootWindow.width - 40 : 420)

        ColumnLayout {
            spacing: 8
            Text { text: "ระบุจำนวนเล่มที่ต้องการสร้างบาร์โค้ดเพิ่ม:"; color: "#475569" }
            TextField {
                id: addCopiesCountInput
                objectName: "addCopiesCountInput"
                placeholderText: "จำนวนเล่ม (เช่น 2) หรือระบุบาร์โค้ดคั่นด้วยจุลภาค"
                text: "1"
            }
        }

        onAccepted: {
            var raw = addCopiesCountInput.text.trim()
            var count = parseInt(raw) || 0
            var res
            var bookId = rootWindow ? rootWindow.selectedBookId : 0
            if (count > 0 && !isNaN(Number(raw))) {
                res = JSON.parse(librarianAdmin.addCopies(bookId, count))
            } else {
                res = JSON.parse(librarianAdmin.addCopies(bookId, raw))
            }
            if (res.ok && res.data && res.data.barcodes && res.data.barcodes.length > 0) {
                barcodeConfirmModel.clear()
                if (rootWindow) rootWindow.lastGeneratedBarcodes = res.data.barcodes
                for (var i = 0; i < res.data.barcodes.length; i++) {
                    barcodeConfirmModel.append({ "barcode": res.data.barcodes[i] })
                }
                pdfExportStatusText.text = ""
                barcodeConfirmDialog.open()
            }
            if (rootWindow) rootWindow.searchBooks()
        }
    }

    // 3. Barcode Confirm Dialog
    Dialog {
        id: barcodeConfirmDialog
        objectName: "barcodeConfirmDialog"
        title: "สร้างบาร์โค้ดประจำเล่มสำเร็จ"
        modal: true
        closePolicy: Popup.CloseOnEscape
        standardButtons: Dialog.Close
        width: Math.min(460, rootWindow ? rootWindow.width - 40 : 440)
        anchors.centerIn: parent

        ColumnLayout {
            spacing: 12
            Text {
                text: "ระบบสร้างบาร์โค้ดประจำเล่มเรียบร้อยแล้ว (" + barcodeConfirmModel.count + " เล่ม):"
                font.bold: true
            }
            ListView {
                id: barcodeConfirmList
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(180, barcodeConfirmModel.count * 34)
                clip: true
                model: ListModel { id: barcodeConfirmModel }
                delegate: Rectangle {
                    width: barcodeConfirmList.width
                    height: 30
                    color: index % 2 === 0 ? "#f8fafc" : "#ffffff"
                    border.color: "#e2e8f0"
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 6
                        Text { text: "• เล่มที่ " + (index + 1) + ": "; font.bold: true }
                        Text { text: model.barcode; font.family: "Monospace"; color: "#0f766e" }
                    }
                }
            }
            Button {
                text: "📄 ส่งออกสติกเกอร์บาร์โค้ด (PDF A4)"
                highlighted: true
                Layout.alignment: Qt.AlignRight
                onClicked: {
                    var outPath = "/tmp/library_labels_" + Date.now() + ".pdf"
                    var barcodes = (rootWindow && rootWindow.lastGeneratedBarcodes) ? rootWindow.lastGeneratedBarcodes : []
                    var res = JSON.parse(librarianAdmin.exportLabelsPdf(JSON.stringify(barcodes), outPath))
                    if (res.ok) {
                        pdfExportStatusText.text = "✓ บันทึกไฟล์ PDF สำเร็จที่: " + res.data.output_path
                    } else {
                        pdfExportStatusText.text = "✗ ข้อผิดพลาด: " + res.error
                    }
                }
            }
            Text {
                id: pdfExportStatusText
                color: "#059669"
                font.pixelSize: 12
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
        }
    }

    // 4. Edit Book Dialog
    Dialog {
        id: editBookDialog
        objectName: "editBookDialog"
        title: "✏️ แก้ไขข้อมูลหนังสือ"
        modal: true
        closePolicy: Popup.CloseOnEscape
        anchors.centerIn: parent
        width: Math.min(460, rootWindow ? rootWindow.width - 40 : 440)
        standardButtons: Dialog.NoButton
        property int targetBookId: 0

        ColumnLayout {
            anchors.fill: parent
            spacing: 10

            Text { text: "ชื่อหนังสือ (Title) *"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
            TextField {
                id: editBookTitleInput
                objectName: "editBookTitleInput"
                Layout.fillWidth: true
                selectByMouse: true
                padding: 8
                background: Rectangle { border.color: parent.activeFocus ? "#2563eb" : "#cbd5e1"; radius: 4; color: "#ffffff" }
            }

            Text { text: "ผู้แต่ง (Author)"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
            TextField {
                id: editBookAuthorInput
                objectName: "editBookAuthorInput"
                Layout.fillWidth: true
                selectByMouse: true
                padding: 8
                background: Rectangle { border.color: parent.activeFocus ? "#2563eb" : "#cbd5e1"; radius: 4; color: "#ffffff" }
            }

            Text { text: "ISBN"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
            TextField {
                id: editBookIsbnInput
                objectName: "editBookIsbnInput"
                Layout.fillWidth: true
                selectByMouse: true
                padding: 8
                background: Rectangle { border.color: parent.activeFocus ? "#2563eb" : "#cbd5e1"; radius: 4; color: "#ffffff" }
            }

            Text { text: "หมวดหมู่"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
            ComboBox {
                id: editBookCategoryCombo
                objectName: "editBookCategoryCombo"
                Layout.fillWidth: true
                textRole: "name"
                model: ListModel { id: editBookCategoryModel }
                background: Rectangle {
                    color: "#ffffff"
                    border.color: editBookCategoryCombo.activeFocus ? "#2563eb" : "#cbd5e1"
                    radius: 4
                }
                contentItem: Text {
                    leftPadding: 8
                    text: editBookCategoryCombo.displayText
                    color: "#1e293b"
                    font.pixelSize: 13
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }
            }

            Text { text: "ตำแหน่งชั้นวาง"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
            TextField {
                id: editBookShelfInput
                objectName: "editBookShelfInput"
                Layout.fillWidth: true
                selectByMouse: true
                padding: 8
                background: Rectangle { border.color: parent.activeFocus ? "#2563eb" : "#cbd5e1"; radius: 4; color: "#ffffff" }
            }

            Text {
                id: editBookStatusText
                objectName: "editBookStatusText"
                Layout.fillWidth: true
                text: ""
                font.pixelSize: 12
                wrapMode: Text.Wrap
                color: text.indexOf("✗") !== -1 ? "#ef4444" : "#10b981"
                visible: text !== ""
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button { text: "ยกเลิก"; onClicked: editBookDialog.close() }
                Button {
                    text: "💾 บันทึก"
                    highlighted: true
                    onClicked: submitEditBook()
                }
            }
        }
    }

    // 5. Delete Book Confirm Dialog
    Dialog {
        id: deleteBookDialog
        objectName: "deleteBookDialog"
        title: "🗑️ ยืนยันการลบหนังสือ"
        modal: true
        closePolicy: Popup.CloseOnEscape
        anchors.centerIn: parent
        width: Math.min(420, rootWindow ? rootWindow.width - 40 : 400)
        standardButtons: Dialog.NoButton
        property int targetBookId: 0
        property string targetBookTitle: ""

        ColumnLayout {
            anchors.fill: parent
            spacing: 16

            Text {
                id: deleteBookConfirmText
                objectName: "deleteBookConfirmText"
                text: "ต้องการลบหนังสือนี้หรือไม่?"
                font.pixelSize: 13
                color: "#1e293b"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Text {
                text: "⚠️ การลบจะปิดใช้งานหนังสือและบาร์โค้ดทั้งหมดของเล่มนี้"
                font.pixelSize: 12
                color: "#b45309"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button { text: "ยกเลิก"; onClicked: deleteBookDialog.close() }
                Button {
                    id: btnConfirmDeleteBook
                    objectName: "btnConfirmDeleteBook"
                    text: "ยืนยันการลบ"
                    contentItem: Text {
                        text: btnConfirmDeleteBook.text
                        color: "white"
                        font.pixelSize: 12
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: btnConfirmDeleteBook.pressed ? "#be123c" : "#e11d48"
                        radius: 4
                    }
                    onClicked: executeDeleteBook()
                }
            }
        }
    }
}
