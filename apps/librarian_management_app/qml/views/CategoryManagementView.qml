import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: barcodePrintScreen
    objectName: "categoryScreen"
    color: "#f8fafc"

    property string lastPdfExported: ""

    property alias barcodePrintSearchInput: barcodePrintSearchInput
    property alias btnSelectAllBooks: btnSelectAllBooks
    property alias btnPrintSelectedPdf: btnPrintSelectedPdf
    property alias btnExportPdfSheet: btnExportPdfSheet
    property alias genBarcodesList: genBarcodesList
    property alias genBarcodesModel: genBarcodesModel
    property alias genPdfStatusText: genPdfStatusText

    signal addCopiesRequested(int bookId, string title)

    function loadPrintableBooks(query) {
        genBarcodesModel.clear()
        try {
            var q = (typeof query === "string") ? query : ""
            var raw = librarianAdmin.getBooksWithBarcodes(q)
            var books = JSON.parse(raw)
            for (var i = 0; i < books.length; i++) {
                var b = books[i]
                if (b.barcodes && b.barcodes.length > 0) {
                    var previewStr = ""
                    if (b.barcodes.length <= 5) {
                        previewStr = b.barcodes.join(", ")
                    } else {
                        previewStr = b.barcodes.slice(0, 3).join(", ") + " ... " + b.barcodes[b.barcodes.length - 1] + " (รวม " + b.barcodes.length + " เล่ม)"
                    }
                    genBarcodesModel.append({
                        "book_id": b.book_id,
                        "title": b.title || "",
                        "author": b.author || "",
                        "category_name": b.category_name || "ทั่วไป",
                        "copy_count": b.barcodes.length,
                        "barcodes_json": JSON.stringify(b.barcodes),
                        "barcode_preview": previewStr,
                        "selected": true
                    })
                }
            }
        } catch (e) {
            console.error("Failed to load printable books: " + e)
        }
    }

    function deselectAllPrintableBooks() {
        for (var i = 0; i < genBarcodesModel.count; i++) {
            genBarcodesModel.setProperty(i, "selected", false)
        }
    }

    function selectAllPrintableBooks() {
        for (var i = 0; i < genBarcodesModel.count; i++) {
            genBarcodesModel.setProperty(i, "selected", true)
        }
    }

    function toggleSelectAllPrintableBooks() {
        var allSelected = true
        for (var i = 0; i < genBarcodesModel.count; i++) {
            if (!genBarcodesModel.get(i).selected) {
                allSelected = false
                break
            }
        }
        if (allSelected) {
            deselectAllPrintableBooks()
        } else {
            selectAllPrintableBooks()
        }
    }

    function setPrintableBookSelected(index, isSelected) {
        if (index >= 0 && index < genBarcodesModel.count) {
            genBarcodesModel.setProperty(index, "selected", isSelected)
        }
    }

    function exportSelectedBooksPdf() {
        var barcodes = []
        for (var i = 0; i < genBarcodesModel.count; i++) {
            var item = genBarcodesModel.get(i)
            if (item.selected) {
                try {
                    var list = JSON.parse(item.barcodes_json)
                    for (var j = 0; j < list.length; j++) {
                        barcodes.push(list[j])
                    }
                } catch (e) {}
            }
        }
        if (barcodes.length === 0) {
            genPdfStatusText.text = "✗ กรุณาเลือกหนังสืออย่างน้อย 1 รายการเพื่อพิมพ์บาร์โค้ด"
            return
        }
        var outPath = "/tmp/library_selected_labels_" + Date.now() + ".pdf"
        var res = JSON.parse(librarianAdmin.exportLabelsPdf(JSON.stringify(barcodes), outPath))
        if (res.ok) {
            barcodePrintScreen.lastPdfExported = res.data.output_path
            genPdfStatusText.text = "✓ บันทึกแผ่นพิมพ์สติกเกอร์ PDF A4 สำเร็จที่: " + res.data.output_path
        } else {
            genPdfStatusText.text = "✗ ข้อผิดพลาดในการส่งออก PDF: " + res.error
        }
    }

    function exportAllBooksPdf() {
        var barcodes = []
        for (var i = 0; i < genBarcodesModel.count; i++) {
            var item = genBarcodesModel.get(i)
            try {
                var list = JSON.parse(item.barcodes_json)
                for (var j = 0; j < list.length; j++) {
                    barcodes.push(list[j])
                }
            } catch (e) {}
        }
        if (barcodes.length === 0) {
            genPdfStatusText.text = "✗ ไม่พบบาร์โค้ดสำหรับพิมพ์"
            return
        }
        var outPath = "/tmp/library_all_labels_" + Date.now() + ".pdf"
        var res = JSON.parse(librarianAdmin.exportLabelsPdf(JSON.stringify(barcodes), outPath))
        if (res.ok) {
            barcodePrintScreen.lastPdfExported = res.data.output_path
            genPdfStatusText.text = "✓ บันทึกแผ่นพิมพ์สติกเกอร์ PDF A4 สำเร็จที่: " + res.data.output_path
        } else {
            genPdfStatusText.text = "✗ ข้อผิดพลาดในการส่งออก PDF: " + res.error
        }
    }

    function exportGenPdf() {
        exportAllBooksPdf()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        // Header
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                spacing: 4
                Layout.fillWidth: true
                Text {
                    text: "🏷️ พิมพ์สติกเกอร์บาร์โค้ดหนังสือ (Barcode Printout Generator)"
                    font.bold: true
                    font.pixelSize: 22
                    color: "#1e293b"
                }
                Text {
                    text: "เลือกพิมพ์บาร์โค้ดประจำเล่มลงแผ่นสติกเกอร์ PDF A4 (3x8) เลือกเฉพาะหนังสือที่ต้องการหรือพิมพ์ทั้งหมด"
                    font.pixelSize: 13
                    color: "#64748b"
                }
            }
            Button {
                text: "🔄 รีเฟรชรายการ"
                flat: true
                onClicked: barcodePrintScreen.loadPrintableBooks(barcodePrintSearchInput.text)
            }
        }

        // Toolbar Card
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 72
            color: "#ffffff"
            radius: 8
            border.color: "#e2e8f0"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 12

                TextField {
                    id: barcodePrintSearchInput
                    objectName: "barcodePrintSearchInput"
                    placeholderText: "🔍 ค้นหาหนังสือ (ชื่อ, ผู้แต่ง)..."
                    Layout.fillWidth: true
                    font.pixelSize: 13
                    selectByMouse: true
                    padding: 8
                    background: Rectangle { border.color: parent.activeFocus ? "#2563eb" : "#cbd5e1"; radius: 4; color: "#ffffff" }
                    onTextChanged: barcodePrintScreen.loadPrintableBooks(text)
                }

                Button {
                    id: btnSelectAllBooks
                    objectName: "btnSelectAllBooks"
                    text: "☑️ เลือกทั้งหมด / ยกเลิก"
                    onClicked: barcodePrintScreen.toggleSelectAllPrintableBooks()
                }

                Button {
                    id: btnPrintSelectedPdf
                    objectName: "btnPrintSelectedPdf"
                    text: "📄 พิมพ์เฉพาะหนังสือที่เลือก (PDF A4)"
                    highlighted: true
                    enabled: genBarcodesModel.count > 0
                    onClicked: barcodePrintScreen.exportSelectedBooksPdf()
                }

                Button {
                    id: btnExportPdfSheet
                    objectName: "btnExportPdfSheet"
                    text: "🖨️ พิมพ์บาร์โค้ดทั้งหมด (PDF A4)"
                    enabled: genBarcodesModel.count > 0
                    onClicked: barcodePrintScreen.exportAllBooksPdf()
                }
            }
        }

        // Barcode List Card
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#ffffff"
            radius: 8
            border.color: "#e2e8f0"
            border.width: 1
            clip: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "📋 รายการหนังสือและรหัสบาร์โค้ดที่มีในระบบ"
                        font.bold: true
                        font.pixelSize: 15
                        color: "#1e293b"
                    }
                    Text {
                        text: "(" + genBarcodesModel.count + " รายการ)"
                        font.pixelSize: 13
                        color: "#64748b"
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: "#e2e8f0" }

                // Empty state
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 120
                    color: "#f8fafc"
                    border.color: "#e2e8f0"
                    radius: 6
                    visible: genBarcodesModel.count === 0

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 6
                        Text {
                            text: "📂 ไม่พบรายการหนังสือที่มีบาร์โค้ดพร้อมพิมพ์"
                            font.pixelSize: 14
                            font.bold: true
                            color: "#64748b"
                            Layout.alignment: Qt.AlignHCenter
                        }
                        Text {
                            text: "ไปที่หน้า '📚 เพิ่มหนังสือ / หมวดหมู่' เพื่อลงทะเบียนหนังสือและสร้างบาร์โค้ด"
                            font.pixelSize: 12
                            color: "#94a3b8"
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                }

                ListView {
                    id: genBarcodesList
                    objectName: "genBarcodesList"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 8
                    visible: genBarcodesModel.count > 0
                    model: ListModel { id: genBarcodesModel; objectName: "genBarcodesModel" }

                    delegate: Rectangle {
                        width: genBarcodesList.width
                        height: 58
                        color: model.selected ? "#f0fdf4" : "#f8fafc"
                        border.color: model.selected ? "#86efac" : "#cbd5e1"
                        border.width: 1
                        radius: 6

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            anchors.topMargin: 6
                            anchors.bottomMargin: 6
                            spacing: 12

                            CheckBox {
                                checked: model.selected
                                onClicked: genBarcodesModel.setProperty(index, "selected", checked)
                            }

                            Rectangle {
                                width: 32
                                height: 32
                                radius: 16
                                color: "#e0f2fe"
                                Text {
                                    anchors.centerIn: parent
                                    text: "📖"
                                    font.pixelSize: 16
                                }
                            }

                            ColumnLayout {
                                spacing: 2
                                Layout.fillWidth: true
                                RowLayout {
                                    spacing: 8
                                    Text {
                                        text: model.title
                                        font.bold: true
                                        font.pixelSize: 14
                                        color: "#0f172a"
                                    }
                                    Rectangle {
                                        height: 18
                                        width: catBadgeText.contentWidth + 10
                                        radius: 4
                                        color: "#e2e8f0"
                                        Text {
                                            id: catBadgeText
                                            anchors.centerIn: parent
                                            text: model.category_name
                                            font.pixelSize: 10
                                            color: "#475569"
                                        }
                                    }
                                    Rectangle {
                                        height: 18
                                        width: copyBadgeText.contentWidth + 10
                                        radius: 4
                                        color: "#dcfce7"
                                        Text {
                                            id: copyBadgeText
                                            anchors.centerIn: parent
                                            text: model.copy_count + " เล่ม"
                                            font.pixelSize: 10
                                            font.bold: true
                                            color: "#166534"
                                        }
                                    }
                                }
                                Text {
                                    text: (model.author ? ("ผู้แต่ง: " + model.author + " | ") : "") + "รหัสบาร์โค้ด: " + model.barcode_preview
                                    font.pixelSize: 11
                                    font.family: "monospace"
                                    color: "#0f766e"
                                }
                            }

                            Button {
                                text: "+ เพิ่มเล่ม"
                                flat: true
                                font.pixelSize: 12
                                Layout.alignment: Qt.AlignRight
                                onClicked: barcodePrintScreen.addCopiesRequested(model.book_id, model.title)
                            }
                        }
                    }
                }
            }
        }

        // PDF Result Status Banner
        Rectangle {
            Layout.fillWidth: true
            height: 48
            radius: 6
            color: "#f1f5f9"
            border.color: "#e2e8f0"
            visible: genPdfStatusText.text !== ""

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10
                Text {
                    id: genPdfStatusText
                    objectName: "genPdfStatusText"
                    text: ""
                    font.pixelSize: 12
                    font.bold: true
                    color: text.indexOf("✗") !== -1 ? "#ef4444" : "#0f766e"
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                Button {
                    text: "📂 เปิดไฟล์ PDF"
                    visible: barcodePrintScreen.lastPdfExported !== ""
                    onClicked: {
                        Qt.openUrlExternally("file://" + barcodePrintScreen.lastPdfExported)
                    }
                }
            }
        }
    }
}
