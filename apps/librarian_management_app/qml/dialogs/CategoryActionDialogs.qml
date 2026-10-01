import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var rootWindow: null

    property alias renameCategoryDialog: renameCategoryDialog
    property alias renameCategoryInput: renameCategoryInput
    property alias renameStatusText: renameStatusText
    property alias btnSubmitRename: btnSubmitRename

    property alias reassignCategoryDialog: reassignCategoryDialog
    property alias reassignWarningText: reassignWarningText
    property alias reassignBooksList: reassignBooksList
    property alias reassignBooksModel: reassignBooksModel
    property alias targetCategoryCombo: targetCategoryCombo
    property alias targetCategoryComboModel: targetCategoryComboModel
    property alias btnConfirmReassignDelete: btnConfirmReassignDelete

    property alias simpleDeleteCategoryDialog: simpleDeleteCategoryDialog
    property alias simpleDeleteConfirmText: simpleDeleteConfirmText
    property alias btnConfirmSimpleDelete: btnConfirmSimpleDelete

    function openRenameCategoryDialog(catId, catName) {
        renameCategoryDialog.targetCatId = catId
        renameCategoryInput.text = catName
        renameStatusText.text = ""
        renameCategoryDialog.open()
    }

    function submitRenameCategory() {
        var newName = renameCategoryInput.text.trim()
        if (!newName) {
            renameStatusText.text = "⚠️ กรุณากรอกชื่อหมวดหมู่"
            return
        }
        var res = JSON.parse(librarianAdmin.renameCategory(renameCategoryDialog.targetCatId, newName))
        if (res.ok) {
            renameCategoryDialog.close()
            if (rootWindow) {
                rootWindow.categoryStatusText.text = "✓ แก้ไขชื่อเป็น '" + newName + "' สำเร็จ"
                rootWindow.categoryStatusText.color = "#10b981"
                rootWindow.loadCategoriesList()
                rootWindow.initGeneratorPage()
            }
        } else {
            renameStatusText.text = "✗ " + (res.error || "ไม่สามารถแก้ไขชื่อได้")
        }
    }

    function requestDeleteCategory(catId, catName) {
        var rawBooks = librarianAdmin.getBooksInCategory(catId)
        var books = JSON.parse(rawBooks)
        if (books && books.length > 0) {
            reassignCategoryDialog.targetCatId = catId
            reassignCategoryDialog.targetCatName = catName
            reassignWarningText.text = "พบหนังสือ " + books.length + " เล่มในหมวดหมู่ '" + catName + "' กรุณาเลือกหมวดหมู่ใหม่ที่จะย้ายไปก่อนลบ"
            reassignBooksModel.clear()
            for (var i = 0; i < books.length; i++) {
                reassignBooksModel.append({
                    "book_id": books[i].book_id,
                    "title": books[i].title,
                    "author": books[i].author || "",
                    "isbn": books[i].isbn || ""
                })
            }
            targetCategoryComboModel.clear()
            targetCategoryComboModel.append({ "category_id": 0, "name": "-- ไม่ระบุหมวดหมู่ (ว่าง) --" })
            var rawCats = librarianAdmin.listCategories()
            var cats = JSON.parse(rawCats)
            for (var j = 0; j < cats.length; j++) {
                if (cats[j].category_id !== catId) {
                    targetCategoryComboModel.append(cats[j])
                }
            }
            targetCategoryCombo.currentIndex = 0
            reassignCategoryDialog.open()
        } else {
            simpleDeleteCategoryDialog.targetCatId = catId
            simpleDeleteCategoryDialog.targetCatName = catName
            simpleDeleteConfirmText.text = "ยืนยันการลบหมวดหมู่ '" + catName + "' (ไม่มีหนังสือผูกอยู่) หรือไม่?"
            simpleDeleteCategoryDialog.open()
        }
    }

    function executeReassignAndDelete() {
        var targetCatId = ""
        if (targetCategoryCombo.currentIndex > 0) {
            targetCatId = targetCategoryComboModel.get(targetCategoryCombo.currentIndex).category_id.toString()
        }
        var res = JSON.parse(librarianAdmin.deleteCategory(reassignCategoryDialog.targetCatId, targetCatId))
        if (res.ok) {
            reassignCategoryDialog.close()
            if (rootWindow) {
                rootWindow.categoryStatusText.text = "✓ ลบหมวดหมู่และย้ายหนังสือเรียบร้อยแล้ว"
                rootWindow.categoryStatusText.color = "#10b981"
                rootWindow.loadCategoriesList()
                rootWindow.initGeneratorPage()
                rootWindow.searchBooks()
            }
        } else {
            if (rootWindow) {
                rootWindow.categoryStatusText.text = "✗ " + (res.error || "ลบหมวดหมู่ไม่สำเร็จ")
                rootWindow.categoryStatusText.color = "#ef4444"
            }
        }
    }

    function executeDirectDelete() {
        var res = JSON.parse(librarianAdmin.deleteCategory(simpleDeleteCategoryDialog.targetCatId, ""))
        if (res.ok) {
            simpleDeleteCategoryDialog.close()
            if (rootWindow) {
                rootWindow.categoryStatusText.text = "✓ ลบหมวดหมู่เรียบร้อยแล้ว"
                rootWindow.categoryStatusText.color = "#10b981"
                rootWindow.loadCategoriesList()
                rootWindow.initGeneratorPage()
                rootWindow.searchBooks()
            }
        } else {
            if (rootWindow) {
                rootWindow.categoryStatusText.text = "✗ " + (res.error || "ลบหมวดหมู่ไม่สำเร็จ")
                rootWindow.categoryStatusText.color = "#ef4444"
            }
        }
    }

    // 1. Rename Category Dialog
    Dialog {
        id: renameCategoryDialog
        objectName: "renameCategoryDialog"
        title: "✏️ แก้ไขชื่อหมวดหมู่"
        modal: true
        anchors.centerIn: parent
        width: 380
        standardButtons: Dialog.NoButton
        property int targetCatId: 0

        ColumnLayout {
            anchors.fill: parent
            spacing: 12

            Text {
                text: "ระบุชื่อหมวดหมู่ใหม่:"
                font.pixelSize: 13
                color: "#475569"
            }

            TextField {
                id: renameCategoryInput
                objectName: "renameCategoryInput"
                Layout.fillWidth: true
                font.pixelSize: 13
                selectByMouse: true
                onAccepted: submitRenameCategory()
            }

            Text {
                id: renameStatusText
                objectName: "renameStatusText"
                Layout.fillWidth: true
                text: ""
                font.pixelSize: 11
                color: "#ef4444"
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button {
                    text: "ยกเลิก"
                    onClicked: renameCategoryDialog.close()
                }
                Button {
                    id: btnSubmitRename
                    objectName: "btnSubmitRename"
                    text: "บันทึก"
                    highlighted: true
                    onClicked: submitRenameCategory()
                }
            }
        }
    }

    // 2. Reassign Category Dialog
    Dialog {
        id: reassignCategoryDialog
        objectName: "reassignCategoryDialog"
        title: "⚠️ จัดการหนังสือและลบหมวดหมู่"
        modal: true
        anchors.centerIn: parent
        width: 520
        standardButtons: Dialog.NoButton
        property int targetCatId: 0
        property string targetCatName: ""

        ColumnLayout {
            anchors.fill: parent
            spacing: 12

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: reassignWarningLayout.implicitHeight + 16
                color: "#fff1f2"
                border.color: "#fecdd3"
                radius: 6
                RowLayout {
                    id: reassignWarningLayout
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8
                    Text {
                        id: reassignWarningText
                        objectName: "reassignWarningText"
                        text: "พบหนังสือในหมวดหมู่นี้ กรุณาเลือกหมวดหมู่ใหม่ที่จะย้ายไปก่อนลบ"
                        color: "#e11d48"
                        font.pixelSize: 12
                        font.bold: true
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            Text {
                text: "รายชื่อหนังสือที่ได้รับผลกระทบ:"
                font.bold: true
                font.pixelSize: 13
                color: "#1e293b"
            }

            Rectangle {
                Layout.fillWidth: true
                height: 140
                color: "#f8fafc"
                border.color: "#e2e8f0"
                radius: 6

                ListView {
                    id: reassignBooksList
                    objectName: "reassignBooksList"
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    spacing: 6
                    model: ListModel { id: reassignBooksModel; objectName: "reassignBooksModel" }
                    delegate: RowLayout {
                        width: reassignBooksList.width
                        spacing: 8
                        Text { text: "📖"; font.pixelSize: 12 }
                        Text {
                            text: model.title
                            font.bold: true
                            font.pixelSize: 12
                            color: "#1e293b"
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: model.author ? ("โดย " + model.author) : ""
                            font.pixelSize: 11
                            color: "#64748b"
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text {
                    text: "ย้ายหนังสือทั้งหมดไปยังหมวดหมู่:"
                    font.pixelSize: 12
                    font.bold: true
                    color: "#334155"
                }
                ComboBox {
                    id: targetCategoryCombo
                    objectName: "targetCategoryCombo"
                    Layout.fillWidth: true
                    textRole: "name"
                    model: ListModel { id: targetCategoryComboModel; objectName: "targetCategoryComboModel" }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button {
                    text: "ยกเลิก"
                    onClicked: reassignCategoryDialog.close()
                }
                Button {
                    id: btnConfirmReassignDelete
                    objectName: "btnConfirmReassignDelete"
                    text: "ย้ายหนังสือและยืนยันการลบ"
                    contentItem: Text {
                        text: btnConfirmReassignDelete.text
                        color: "white"
                        font.pixelSize: 12
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: btnConfirmReassignDelete.pressed ? "#be123c" : "#e11d48"
                        radius: 4
                    }
                    onClicked: executeReassignAndDelete()
                }
            }
        }
    }

    // 3. Simple Delete Category Dialog
    Dialog {
        id: simpleDeleteCategoryDialog
        objectName: "simpleDeleteCategoryDialog"
        title: "🗑️ ยืนยันการลบหมวดหมู่"
        modal: true
        anchors.centerIn: parent
        width: 380
        standardButtons: Dialog.NoButton
        property int targetCatId: 0
        property string targetCatName: ""

        ColumnLayout {
            anchors.fill: parent
            spacing: 16

            Text {
                id: simpleDeleteConfirmText
                objectName: "simpleDeleteConfirmText"
                text: "ต้องการลบหมวดหมู่นี้หรือไม่?"
                font.pixelSize: 13
                color: "#1e293b"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button {
                    text: "ยกเลิก"
                    onClicked: simpleDeleteCategoryDialog.close()
                }
                Button {
                    id: btnConfirmSimpleDelete
                    objectName: "btnConfirmSimpleDelete"
                    text: "ยืนยันการลบ"
                    contentItem: Text {
                        text: btnConfirmSimpleDelete.text
                        color: "white"
                        font.pixelSize: 12
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: btnConfirmSimpleDelete.pressed ? "#be123c" : "#e11d48"
                        radius: 4
                    }
                    onClicked: executeDirectDelete()
                }
            }
        }
    }
}
