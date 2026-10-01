import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: barcodeGenScreen
    objectName: "barcodeGenScreen"
    color: "#f8fafc"

    property int currentGenMode: 0 // 0: New Book, 1: Add Copies to Existing
    property var previewedBarcodes: []
    property int previewedBookId: 0
    property string lastPdfExported: ""

    property alias btnModeNewBook: btnModeNewBook
    property alias btnModeAddCopies: btnModeAddCopies
    property alias genBookTitle: genBookTitle
    property alias genBookAuthor: genBookAuthor
    property alias genBookIsbn: genBookIsbn
    property alias genCategoryCombo: genCategoryCombo
    property alias genCategoryModel: genCategoryModel
    property alias genShelfLocation: genShelfLocation
    property alias genExistingBookCombo: genExistingBookCombo
    property alias genExistingBooksModel: genExistingBooksModel
    property alias genCopyCountInput: genCopyCountInput
    property alias btnRefreshPreview: btnRefreshPreview
    property alias btnExecuteGenerate: btnExecuteGenerate
    property alias genStatusMessage: genStatusMessage
    property alias btnExportPdfSheet: btnExportPdfSheet
    property alias genBarcodesList: genBarcodesList
    property alias genBarcodesModel: genBarcodesModel
    property alias genPdfStatusText: genPdfStatusText

    signal backToCatalogRequested()
    signal bookSaved()

    function initGeneratorPage() {
        genCategoryModel.clear()
        genCategoryModel.append({ "category_id": 0, "name": "-- ไม่ระบุหมวดหมู่ --" })
        try {
            var cats = JSON.parse(librarianAdmin.getCategories())
            for (var i = 0; i < cats.length; i++) {
                genCategoryModel.append(cats[i])
            }
        } catch (e) {}
        loadBooksForExistingSelector()
        updateGenPreview()
    }

    function loadBooksForExistingSelector() {
        genExistingBooksModel.clear()
        try {
            var books = JSON.parse(librarianAdmin.searchBooks(""))
            for (var i = 0; i < books.length; i++) {
                var b = books[i]
                genExistingBooksModel.append({
                    "book_id": b.book_id,
                    "title": b.title,
                    "author": b.author || "",
                    "total_copies": b.total_copies,
                    "display": b.title + " (มีอยู่ " + b.total_copies + " เล่ม)"
                })
            }
        } catch (e) {}
    }

    function updateGenPreview() {
        var count = parseInt(genCopyCountInput.text) || 1
        var targetBookId = 0
        var currentTitle = ""
        if (barcodeGenScreen.currentGenMode === 0) {
            targetBookId = 0
            currentTitle = genBookTitle.text.trim() || "(หนังสือใหม่)"
        } else {
            if (genExistingBooksModel.count > 0 && genExistingBookCombo.currentIndex >= 0 && genExistingBookCombo.currentIndex < genExistingBooksModel.count) {
                var selected = genExistingBooksModel.get(genExistingBookCombo.currentIndex)
                targetBookId = selected.book_id
                currentTitle = selected.title
                existingBookInfoText.text = "หนังสือ: " + selected.title + " | ปัจจุบันมี: " + selected.total_copies + " เล่ม"
            }
        }

        try {
            var res = JSON.parse(librarianAdmin.previewBarcodes(targetBookId, count))
            if (res.ok && res.barcodes) {
                genBarcodesModel.clear()
                for (var j = 0; j < res.barcodes.length; j++) {
                    genBarcodesModel.append({
                        "barcode": res.barcodes[j],
                        "title": currentTitle,
                        "seq": (j + 1) + " จาก " + res.barcodes.length,
                        "is_committed": false
                    })
                }
                genSummaryLabel.text = "พร้อมสร้าง: " + res.barcodes.length + " เล่ม (รหัสเริ่มต้น: " + res.barcodes[0] + ")"
            }
        } catch (e) {}
    }

    function executeGenerateAndSave() {
        var count = parseInt(genCopyCountInput.text) || 1
        var res
        if (barcodeGenScreen.currentGenMode === 0) {
            var title = genBookTitle.text.trim()
            if (!title) {
                genStatusMessage.text = "✗ กรุณาระบุชื่อหนังสือ"
                return
            }
            var isbn = genBookIsbn.text.trim()
            var author = genBookAuthor.text.trim()
            var catId = ""
            if (genCategoryCombo.currentIndex > 0) {
                catId = genCategoryModel.get(genCategoryCombo.currentIndex).category_id.toString()
            }
            var shelf = genShelfLocation.text.trim()
            res = JSON.parse(librarianAdmin.addBook(title, isbn, author, catId, shelf, "", count.toString()))
            if (res.ok) {
                genStatusMessage.text = "✓ บันทึกหนังสือ '" + title + "' และสร้างบาร์โค้ดสำเร็จ " + res.data.barcodes.length + " เล่ม"
                barcodeGenScreen.previewedBarcodes = res.data.barcodes
                genBarcodesModel.clear()
                for (var i = 0; i < res.data.barcodes.length; i++) {
                    genBarcodesModel.append({
                        "barcode": res.data.barcodes[i],
                        "title": title,
                        "seq": (i + 1) + " จาก " + res.data.barcodes.length,
                        "is_committed": true
                    })
                }
                genSummaryLabel.text = "✓ บันทึกและสร้างบาร์โค้ดเรียบร้อย (" + res.data.barcodes.length + " เล่ม)"
                barcodeGenScreen.bookSaved()
                loadBooksForExistingSelector()
            } else {
                genStatusMessage.text = "✗ เกิดข้อผิดพลาด: " + res.error
            }
        } else {
            if (genExistingBooksModel.count === 0 || genExistingBookCombo.currentIndex < 0) {
                genStatusMessage.text = "✗ กรุณาเลือกหนังสือเดิมในระบบ"
                return
            }
            var selBook = genExistingBooksModel.get(genExistingBookCombo.currentIndex)
            res = JSON.parse(librarianAdmin.addCopies(selBook.book_id, count))
            if (res.ok) {
                genStatusMessage.text = "✓ เพิ่มเล่มหนังสือ '" + selBook.title + "' และสร้างบาร์โค้ดสำเร็จ " + res.data.barcodes.length + " เล่ม"
                barcodeGenScreen.previewedBarcodes = res.data.barcodes
                genBarcodesModel.clear()
                for (var k = 0; k < res.data.barcodes.length; k++) {
                    genBarcodesModel.append({
                        "barcode": res.data.barcodes[k],
                        "title": selBook.title,
                        "seq": (k + 1) + " จาก " + res.data.barcodes.length,
                        "is_committed": true
                    })
                }
                genSummaryLabel.text = "✓ บันทึกและสร้างบาร์โค้ดเรียบร้อย (" + res.data.barcodes.length + " เล่ม)"
                barcodeGenScreen.bookSaved()
                loadBooksForExistingSelector()
            } else {
                genStatusMessage.text = "✗ เกิดข้อผิดพลาด: " + res.error
            }
        }
    }

    function exportGenPdf() {
        var barcodes = []
        for (var i = 0; i < genBarcodesModel.count; i++) {
            barcodes.push(genBarcodesModel.get(i).barcode)
        }
        if (barcodes.length === 0) return
        var outPath = "/tmp/library_labels_" + Date.now() + ".pdf"
        var res = JSON.parse(librarianAdmin.exportLabelsPdf(JSON.stringify(barcodes), outPath))
        if (res.ok) {
            barcodeGenScreen.lastPdfExported = res.data.output_path
            genPdfStatusText.text = "✓ บันทึกแผ่นพิมพ์สติกเกอร์ PDF A4 สำเร็จที่: " + res.data.output_path
        } else {
            genPdfStatusText.text = "✗ ข้อผิดพลาดในการส่งออก PDF: " + res.error
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 14

        // Header
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text {
                    text: "🏷️ เครื่องมือเพิ่มหนังสือและสร้างบาร์โค้ดประจำเล่ม"
                    font.bold: true
                    font.pixelSize: 20
                    color: "#0f172a"
                }
                Text {
                    text: "ระบบสร้างรหัสบาร์โค้ดติดตามประจำเล่มแบบกำหนดได้ (SMTE-xxxxx-xx) ตามมาตรฐาน Code128 พร้อมพิมพ์สติกเกอร์ A4 (3x8)"
                    font.pixelSize: 12
                    color: "#64748b"
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }
            }
            Button {
                text: "📖 กลับแคตตาล็อก"
                onClicked: barcodeGenScreen.backToCatalogRequested()
            }
        }

        // Main split cards
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

            // Left Card: Form
            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: 380
                Layout.maximumWidth: 410
                Layout.minimumWidth: 330
                color: "#ffffff"
                radius: 8
                border.color: "#e2e8f0"

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 16
                    clip: true

                    ColumnLayout {
                        width: parent.width
                        spacing: 12

                        // Mode Switch
                        RowLayout {
                            Layout.fillWidth: true
                            Button {
                                id: btnModeNewBook
                                objectName: "btnModeNewBook"
                                text: "🆕 เพิ่มหนังสือใหม่"
                                Layout.fillWidth: true
                                highlighted: barcodeGenScreen.currentGenMode === 0
                                onClicked: {
                                    barcodeGenScreen.currentGenMode = 0
                                    barcodeGenScreen.updateGenPreview()
                                }
                            }
                            Button {
                                id: btnModeAddCopies
                                objectName: "btnModeAddCopies"
                                text: "➕ เพิ่มเล่มหนังสือเดิม"
                                Layout.fillWidth: true
                                highlighted: barcodeGenScreen.currentGenMode === 1
                                onClicked: {
                                    barcodeGenScreen.currentGenMode = 1
                                    barcodeGenScreen.loadBooksForExistingSelector()
                                    barcodeGenScreen.updateGenPreview()
                                }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: "#e2e8f0" }

                        // Form fields for New Book
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            visible: barcodeGenScreen.currentGenMode === 0

                            Text { text: "ชื่อหนังสือ (Title) *"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
                            TextField {
                                id: genBookTitle
                                objectName: "genBookTitle"
                                Layout.fillWidth: true
                                placeholderText: "เช่น ฟิสิกส์พื้นฐาน ม.1"
                                selectByMouse: true
                                padding: 8
                                background: Rectangle { border.color: parent.activeFocus ? "#2563eb" : "#cbd5e1"; radius: 4; color: "#ffffff" }
                                onTextChanged: barcodeGenScreen.updateGenPreview()
                            }

                            Text { text: "ผู้แต่ง (Author)"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
                            TextField {
                                id: genBookAuthor
                                objectName: "genBookAuthor"
                                Layout.fillWidth: true
                                placeholderText: "ชื่อผู้แต่ง / คณะผู้จัดทำ"
                                selectByMouse: true
                                padding: 8
                                background: Rectangle { border.color: parent.activeFocus ? "#2563eb" : "#cbd5e1"; radius: 4; color: "#ffffff" }
                            }

                            Text { text: "ISBN จากสำนักพิมพ์"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
                            TextField {
                                id: genBookIsbn
                                objectName: "genBookIsbn"
                                Layout.fillWidth: true
                                placeholderText: "เช่น 978-616-00-1234-5"
                                selectByMouse: true
                                padding: 8
                                background: Rectangle { border.color: parent.activeFocus ? "#2563eb" : "#cbd5e1"; radius: 4; color: "#ffffff" }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Text { text: "หมวดหมู่"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
                                    ComboBox {
                                        id: genCategoryCombo
                                        objectName: "genCategoryCombo"
                                        Layout.fillWidth: true
                                        textRole: "name"
                                        model: ListModel { id: genCategoryModel }
                                        background: Rectangle {
                                            color: "#ffffff"
                                            border.color: genCategoryCombo.activeFocus ? "#2563eb" : "#cbd5e1"
                                            radius: 4
                                        }
                                        contentItem: Text {
                                            leftPadding: 8
                                            text: genCategoryCombo.displayText
                                            color: "#1e293b"
                                            font.pixelSize: 13
                                            verticalAlignment: Text.AlignVCenter
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Text { text: "ตำแหน่งชั้นวาง"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
                                    TextField {
                                        id: genShelfLocation
                                        objectName: "genShelfLocation"
                                        Layout.fillWidth: true
                                        placeholderText: "เช่น ชั้น A-01"
                                        selectByMouse: true
                                        padding: 8
                                        background: Rectangle { border.color: parent.activeFocus ? "#2563eb" : "#cbd5e1"; radius: 4; color: "#ffffff" }
                                    }
                                }
                            }
                        }

                        // Form fields for Existing Book
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            visible: barcodeGenScreen.currentGenMode === 1

                            Text { text: "เลือกหนังสือเดิมในระบบ *"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
                            ComboBox {
                                id: genExistingBookCombo
                                objectName: "genExistingBookCombo"
                                Layout.fillWidth: true
                                textRole: "display"
                                model: ListModel { id: genExistingBooksModel }
                                onCurrentIndexChanged: barcodeGenScreen.updateGenPreview()
                                background: Rectangle {
                                    color: "#ffffff"
                                    border.color: genExistingBookCombo.activeFocus ? "#2563eb" : "#cbd5e1"
                                    radius: 4
                                }
                                contentItem: Text {
                                    leftPadding: 8
                                    text: genExistingBookCombo.displayText
                                    color: "#1e293b"
                                    font.pixelSize: 13
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }
                            }
                            Text {
                                id: existingBookInfoText
                                text: ""
                                color: "#0284c7"
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }
                        }

                        // Common: Copy count
                        Text { text: "จำนวนเล่มที่ต้องการสร้าง (Copy Count) *"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            TextField {
                                id: genCopyCountInput
                                objectName: "genCopyCountInput"
                                text: "1"
                                Layout.preferredWidth: 90
                                validator: IntValidator { bottom: 1; top: 99 }
                                selectByMouse: true
                                padding: 8
                                background: Rectangle { border.color: parent.activeFocus ? "#2563eb" : "#cbd5e1"; radius: 4; color: "#ffffff" }
                                onTextChanged: barcodeGenScreen.updateGenPreview()
                            }
                            Item { Layout.fillWidth: true }
                            Button { text: "-1"; Layout.preferredWidth: 44; onClicked: { var c = Math.max(1, (parseInt(genCopyCountInput.text) || 1) - 1); genCopyCountInput.text = c.toString(); } }
                            Button { text: "+1"; Layout.preferredWidth: 44; onClicked: { var c = Math.min(99, (parseInt(genCopyCountInput.text) || 1) + 1); genCopyCountInput.text = c.toString(); } }
                            Button { text: "+5"; Layout.preferredWidth: 44; onClicked: { var c = Math.min(99, (parseInt(genCopyCountInput.text) || 1) + 5); genCopyCountInput.text = c.toString(); } }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: "#e2e8f0" }

                        // Submit & Action buttons
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Button {
                                id: btnRefreshPreview
                                objectName: "btnRefreshPreview"
                                text: "🔄 จำลองรหัส"
                                onClicked: barcodeGenScreen.updateGenPreview()
                            }

                            Button {
                                id: btnExecuteGenerate
                                objectName: "btnExecuteGenerate"
                                text: "💾 บันทึกและสร้างบาร์โค้ด"
                                highlighted: true
                                Layout.fillWidth: true
                                onClicked: barcodeGenScreen.executeGenerateAndSave()
                            }
                        }

                        Text {
                            id: genStatusMessage
                            objectName: "genStatusMessage"
                            text: ""
                            font.pixelSize: 12
                            font.bold: true
                            wrapMode: Text.Wrap
                            color: text.indexOf("✗") !== -1 ? "#ef4444" : "#10b981"
                            visible: text !== ""
                            Layout.fillWidth: true
                            Layout.preferredWidth: 320
                        }
                    }
                }
            }

            // Right Card: Barcode Live Generator Preview & PDF Export
            Rectangle {
                Layout.fillHeight: true
                Layout.fillWidth: true
                Layout.minimumWidth: 360
                color: "#ffffff"
                radius: 8
                border.color: "#e2e8f0"
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: "ตัวอย่างบาร์โค้ดประจำเล่ม"
                                font.bold: true
                                font.pixelSize: 16
                                color: "#1e293b"
                            }
                            Text {
                                id: genSummaryLabel
                                text: "พร้อมสร้าง: 1 เล่ม"
                                color: "#64748b"
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }
                        }
                        Button {
                            id: btnExportPdfSheet
                            objectName: "btnExportPdfSheet"
                            text: "📄 พิมพ์สติกเกอร์ PDF (A4)"
                            highlighted: true
                            enabled: genBarcodesModel.count > 0
                            onClicked: barcodeGenScreen.exportGenPdf()
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: "#e2e8f0" }

                    // List of generated or previewed barcodes
                    ListView {
                        id: genBarcodesList
                        objectName: "genBarcodesList"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 8
                        model: ListModel { id: genBarcodesModel; objectName: "genBarcodesModel" }

                        delegate: Rectangle {
                            width: genBarcodesList.width
                            height: 56
                            radius: 6
                            color: model.is_committed ? "#f0fdf4" : "#f8fafc"
                            border.color: model.is_committed ? "#86efac" : "#cbd5e1"
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                anchors.topMargin: 6
                                anchors.bottomMargin: 6
                                spacing: 10

                                Rectangle {
                                    width: 32
                                    height: 32
                                    radius: 16
                                    color: model.is_committed ? "#dcfce7" : "#e2e8f0"
                                    Text {
                                        anchors.centerIn: parent
                                        text: "🏷️"
                                        font.pixelSize: 15
                                    }
                                }

                                ColumnLayout {
                                    spacing: 2
                                    Layout.fillWidth: true
                                    RowLayout {
                                        spacing: 8
                                        Text {
                                            text: model.barcode
                                            font.bold: true
                                            font.family: "Monospace"
                                            font.pixelSize: 14
                                            color: "#0f766e"
                                        }
                                        Rectangle {
                                            height: 18
                                            width: statusText.contentWidth + 10
                                            radius: 9
                                            color: model.is_committed ? "#bbf7d0" : "#fed7aa"
                                            Text {
                                                id: statusText
                                                anchors.centerIn: parent
                                                text: model.is_committed ? "บันทึกแล้ว" : "จำลอง"
                                                font.pixelSize: 10
                                                font.bold: true
                                                color: model.is_committed ? "#15803d" : "#c2410c"
                                            }
                                        }
                                    }
                                    Text {
                                        text: (model.title || "-") + " | " + model.seq
                                        font.pixelSize: 11
                                        color: "#64748b"
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                }

                                Text {
                                    text: "Code128"
                                    font.pixelSize: 10
                                    color: "#94a3b8"
                                    Layout.alignment: Qt.AlignRight
                                }
                            }
                        }
                    }

                    // PDF Result feedback footer
                    Rectangle {
                        Layout.fillWidth: true
                        height: 44
                        radius: 6
                        color: "#f1f5f9"
                        border.color: "#e2e8f0"
                        visible: genPdfStatusText.text !== ""

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 8
                            Text {
                                id: genPdfStatusText
                                objectName: "genPdfStatusText"
                                text: ""
                                font.pixelSize: 11
                                color: text.indexOf("✗") !== -1 ? "#ef4444" : "#0f766e"
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                            }
                            Button {
                                text: "📂 เปิดไฟล์ PDF"
                                visible: barcodeGenScreen.lastPdfExported !== ""
                                onClicked: {
                                    Qt.openUrlExternally("file://" + barcodeGenScreen.lastPdfExported)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
