import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: barcodePrintScreen
    objectName: "categoryScreen"
    color: "#f8fafc"

    property string lastPdfExported: ""

    property alias barcodePrintSearchInput: barcodePrintSearchInput
    property alias barcodeCategoryFilterCombo: barcodeCategoryFilterCombo
    property alias barcodeCategoryFilterModel: barcodeCategoryFilterModel
    property alias btnSelectAllBooks: btnSelectAllBooks
    property alias btnPrintSelectedPdf: btnPrintSelectedPdf
    property alias btnExportPdfSheet: btnExportPdfSheet
    property alias genBarcodesList: genBarcodesList
    property alias genBarcodesModel: genBarcodesModel
    property alias genPdfStatusText: genPdfStatusText

    property alias selectedBooksCountText: selectedBooksCountText
    property alias selectedStickersCountText: selectedStickersCountText
    property alias estimatedPagesText: estimatedPagesText

    signal addCopiesRequested(int bookId, string title)

    function recalculateSelectionStats() {
        var books = 0
        var stickers = 0
        for (var i = 0; i < genBarcodesModel.count; i++) {
            var item = genBarcodesModel.get(i)
            if (item.selected) {
                books++
                stickers += item.copy_count
            }
        }
        selectedBooksCountText.text = books + " เรื่อง"
        selectedStickersCountText.text = stickers + " ดวง"
        var pages = Math.ceil(stickers / 24)
        estimatedPagesText.text = pages + " แผ่น (A4 3x8)"
    }

    function reloadCategoryFilter() {
        barcodeCategoryFilterModel.clear()
        barcodeCategoryFilterModel.append({ "category_id": 0, "name": "📚 ทุกหมวดหมู่" })
        try {
            var raw = librarianAdmin.listCategories()
            var cats = JSON.parse(raw)
            for (var i = 0; i < cats.length; i++) {
                barcodeCategoryFilterModel.append(cats[i])
            }
        } catch (e) {}
    }

    function loadPrintableBooks(query) {
        reloadCategoryFilter()
        genBarcodesModel.clear()
        try {
            var q = (typeof query === "string") ? query : barcodePrintSearchInput.text
            var raw = librarianAdmin.getBooksWithBarcodes(q)
            var books = JSON.parse(raw)

            var selectedCat = (barcodeCategoryFilterCombo && barcodeCategoryFilterCombo.currentIndex > 0)
                ? barcodeCategoryFilterModel.get(barcodeCategoryFilterCombo.currentIndex).name
                : ""

            for (var i = 0; i < books.length; i++) {
                var b = books[i]
                if (b.barcodes && b.barcodes.length > 0) {
                    var catName = b.category_name || "ทั่วไป"
                    if (selectedCat && catName !== selectedCat) {
                        continue
                    }

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
                        "category_name": catName,
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
        recalculateSelectionStats()
    }

    function deselectAllPrintableBooks() {
        for (var i = 0; i < genBarcodesModel.count; i++) {
            genBarcodesModel.setProperty(i, "selected", false)
        }
        recalculateSelectionStats()
    }

    function selectAllPrintableBooks() {
        for (var i = 0; i < genBarcodesModel.count; i++) {
            genBarcodesModel.setProperty(i, "selected", true)
        }
        recalculateSelectionStats()
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
            recalculateSelectionStats()
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
        anchors.margins: 20
        spacing: 14

        // Header
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                spacing: 2
                Layout.fillWidth: true
                Text {
                    text: "🏷️ พิมพ์สติกเกอร์บาร์โค้ดหนังสือ (Dedicated Barcode Print Studio)"
                    font.bold: true
                    font.pixelSize: 20
                    color: "#0f172a"
                }
                Text {
                    text: "เลือกติ๊กหนังสือที่ต้องการพิมพ์ แล้วสั่งพิมพ์ลงสติกเกอร์ PDF A4 (3x8 ดวง = 24 ดวง/แผ่น)"
                    font.pixelSize: 12
                    color: "#64748b"
                }
            }
            Button {
                text: "🔄 รีเฟรชรายการ"
                flat: true
                onClicked: barcodePrintScreen.loadPrintableBooks()
            }
        }

        // Live Selection Metric Cards
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Rectangle {
                Layout.fillWidth: true
                height: 52
                color: "#ffffff"
                radius: 6
                border.color: "#e2e8f0"
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8
                    Text { text: "📚"; font.pixelSize: 18 }
                    ColumnLayout {
                        spacing: 1
                        Text { text: "หนังสือที่เลือกพิมพ์"; font.pixelSize: 10; color: "#64748b" }
                        Text {
                            id: selectedBooksCountText
                            objectName: "selectedBooksCountText"
                            text: "0 เรื่อง"
                            font.bold: true
                            font.pixelSize: 14
                            color: "#0f172a"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 52
                color: "#ffffff"
                radius: 6
                border.color: "#86efac"
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8
                    Text { text: "🏷️"; font.pixelSize: 18 }
                    ColumnLayout {
                        spacing: 1
                        Text { text: "สติกเกอร์บาร์โค้ดรวม"; font.pixelSize: 10; color: "#166534" }
                        Text {
                            id: selectedStickersCountText
                            objectName: "selectedStickersCountText"
                            text: "0 ดวง"
                            font.bold: true
                            font.pixelSize: 14
                            color: "#166534"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 52
                color: "#ffffff"
                radius: 6
                border.color: "#93c5fd"
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8
                    Text { text: "📄"; font.pixelSize: 18 }
                    ColumnLayout {
                        spacing: 1
                        Text { text: "ประมาณการกระดาษ A4"; font.pixelSize: 10; color: "#1d4ed8" }
                        Text {
                            id: estimatedPagesText
                            objectName: "estimatedPagesText"
                            text: "0 แผ่น (A4 3x8)"
                            font.bold: true
                            font.pixelSize: 14
                            color: "#1d4ed8"
                        }
                    }
                }
            }
        }

        // Toolbar Card (Search, Filter & Actions)
        Rectangle {
            Layout.fillWidth: true
            height: 60
            color: "#ffffff"
            radius: 8
            border.color: "#e2e8f0"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10

                TextField {
                    id: barcodePrintSearchInput
                    objectName: "barcodePrintSearchInput"
                    placeholderText: "🔍 ค้นหาชื่อหนังสือ / ผู้แต่ง..."
                    Layout.fillWidth: true
                    font.pixelSize: 12
                    padding: 8
                    background: Rectangle { border.color: "#cbd5e1"; radius: 4 }
                    onTextChanged: barcodePrintScreen.loadPrintableBooks(text)
                }

                ComboBox {
                    id: barcodeCategoryFilterCombo
                    objectName: "barcodeCategoryFilterCombo"
                    Layout.preferredWidth: 150
                    implicitHeight: 34
                    textRole: "name"
                    model: ListModel { id: barcodeCategoryFilterModel; objectName: "barcodeCategoryFilterModel" }
                    onCurrentIndexChanged: barcodePrintScreen.loadPrintableBooks()
                }

                Button {
                    id: btnSelectAllBooks
                    objectName: "btnSelectAllBooks"
                    text: "☑️ เลือกทั้งหมด"
                    onClicked: barcodePrintScreen.toggleSelectAllPrintableBooks()
                }

                Button {
                    id: btnPrintSelectedPdf
                    objectName: "btnPrintSelectedPdf"
                    text: "📄 พิมพ์เฉพาะที่เลือก"
                    highlighted: true
                    enabled: genBarcodesModel.count > 0
                    onClicked: barcodePrintScreen.exportSelectedBooksPdf()
                }

                Button {
                    id: btnExportPdfSheet
                    objectName: "btnExportPdfSheet"
                    text: "🖨️ พิมพ์ทั้งหมด"
                    enabled: genBarcodesModel.count > 0
                    onClicked: barcodePrintScreen.exportAllBooksPdf()
                }
            }
        }

        // Bordered Grid Table Header
        Rectangle {
            Layout.fillWidth: true
            height: 30
            color: "#f1f5f9"
            border.color: "#cbd5e1"
            radius: 4

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8
                Text { text: "เลือก"; font.bold: true; font.pixelSize: 11; color: "#475569"; Layout.preferredWidth: 40 }
                Text { text: "ID"; font.bold: true; font.pixelSize: 11; color: "#475569"; Layout.preferredWidth: 40 }
                Text { text: "ชื่อหนังสือ / ผู้แต่ง"; font.bold: true; font.pixelSize: 11; color: "#475569"; Layout.fillWidth: true }
                Text { text: "หมวดหมู่"; font.bold: true; font.pixelSize: 11; color: "#475569"; Layout.preferredWidth: 100 }
                Text { text: "จำนวน"; font.bold: true; font.pixelSize: 11; color: "#475569"; Layout.preferredWidth: 60 }
                Text { text: "รหัสบาร์โค้ดประจำเล่ม"; font.bold: true; font.pixelSize: 11; color: "#475569"; Layout.preferredWidth: 260 }
                Text { text: "จัดการ"; font.bold: true; font.pixelSize: 11; color: "#475569"; Layout.preferredWidth: 65; horizontalAlignment: Text.AlignRight }
            }
        }

        // Bordered Table Rows (ListView)
        ListView {
            id: genBarcodesList
            objectName: "genBarcodesList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 4
            model: ListModel { id: genBarcodesModel; objectName: "genBarcodesModel" }

            delegate: Rectangle {
                width: genBarcodesList.width
                height: 48
                color: model.selected ? "#f0fdf4" : (index % 2 === 0 ? "#ffffff" : "#f8fafc")
                border.color: model.selected ? "#86efac" : "#e2e8f0"
                border.width: model.selected ? 1.5 : 1
                radius: 4

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 8

                    CheckBox {
                        checked: model.selected
                        Layout.preferredWidth: 40
                        onClicked: {
                            genBarcodesModel.setProperty(index, "selected", checked)
                            barcodePrintScreen.recalculateSelectionStats()
                        }
                    }

                    Text {
                        text: "#" + model.book_id
                        font.bold: true
                        font.pixelSize: 11
                        color: "#0284c7"
                        Layout.preferredWidth: 40
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        Text {
                            text: model.title
                            font.bold: true
                            font.pixelSize: 12
                            color: "#0f172a"
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        Text {
                            text: model.author ? ("ผู้แต่ง: " + model.author) : ""
                            font.pixelSize: 10
                            color: "#64748b"
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            visible: text !== ""
                        }
                    }

                    Rectangle {
                        Layout.preferredWidth: 100
                        height: 22
                        radius: 4
                        color: "#f1f5f9"
                        border.color: "#e2e8f0"
                        Text {
                            anchors.centerIn: parent
                            text: model.category_name
                            font.pixelSize: 10
                            color: "#475569"
                            elide: Text.ElideRight
                        }
                    }

                    Rectangle {
                        Layout.preferredWidth: 60
                        height: 22
                        radius: 4
                        color: "#dcfce7"
                        Text {
                            anchors.centerIn: parent
                            text: model.copy_count + " เล่ม"
                            font.bold: true
                            font.pixelSize: 10
                            color: "#166534"
                        }
                    }

                    Text {
                        text: model.barcode_preview
                        font.family: "monospace"
                        font.pixelSize: 11
                        color: "#0f766e"
                        Layout.preferredWidth: 260
                        elide: Text.ElideRight
                    }

                    Button {
                        text: "+ เล่ม"
                        font.pixelSize: 10
                        Layout.preferredWidth: 55
                        height: 26
                        flat: true
                        onClicked: barcodePrintScreen.addCopiesRequested(model.book_id, model.title)
                    }
                }
            }
        }

        // PDF Status Banner
        Rectangle {
            Layout.fillWidth: true
            height: 44
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
                    onClicked: Qt.openUrlExternally("file://" + barcodePrintScreen.lastPdfExported)
                }
            }
        }
    }
}
