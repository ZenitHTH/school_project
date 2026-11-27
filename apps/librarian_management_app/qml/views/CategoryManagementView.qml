import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../../common_qml"
import "../../../common_qml/Typography.js" as Typography

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

    property bool _reloadingFilter: false

    Timer {
        id: printSearchDebounce
        interval: 180
        repeat: false
        onTriggered: barcodePrintScreen.loadPrintableBooks(barcodePrintSearchInput.text, true)
    }

    function reloadCategoryFilter() {
        var prevName = (barcodeCategoryFilterCombo && barcodeCategoryFilterCombo.currentIndex > 0 && barcodeCategoryFilterCombo.currentIndex < barcodeCategoryFilterModel.count)
            ? barcodeCategoryFilterModel.get(barcodeCategoryFilterCombo.currentIndex).name
            : ""
        _reloadingFilter = true
        barcodeCategoryFilterModel.clear()
        barcodeCategoryFilterModel.append({ "category_id": 0, "name": "📚 ทุกหมวดหมู่" })
        var targetIndex = 0
        try {
            var raw = librarianAdmin.listCategories()
            var cats = JSON.parse(raw)
            for (var i = 0; i < cats.length; i++) {
                barcodeCategoryFilterModel.append(cats[i])
                if (prevName && cats[i].name === prevName) {
                    targetIndex = i + 1
                }
            }
        } catch (e) {}
        if (barcodeCategoryFilterCombo) {
            barcodeCategoryFilterCombo.currentIndex = targetIndex
        }
        _reloadingFilter = false
    }

    function loadPrintableBooks(query, skipCategoryReload) {
        if (!skipCategoryReload) {
            reloadCategoryFilter()
        }
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
        var res = JSON.parse(librarianAdmin.exportLabelsPdf(JSON.stringify(barcodes), ""))
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
        var res = JSON.parse(librarianAdmin.exportLabelsPdf(JSON.stringify(barcodes), ""))
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
            StyledButton {
                variant: StyledButton.Ghost
                text: "🔄 รีเฟรชรายการ"
                onClicked: barcodePrintScreen.loadPrintableBooks()
            }
        }

        // Live Selection Metric Cards
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: Math.max(52, Math.round(metricRow1.implicitHeight + 16))
                color: "#ffffff"
                radius: 6
                border.color: "#e2e8f0"
                clip: true
                RowLayout {
                    id: metricRow1
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8
                    Text { text: "📚"; font.pixelSize: 18 }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        Text { text: "หนังสือที่เลือกพิมพ์"; font.pixelSize: 10; color: "#64748b"; Layout.fillWidth: true; elide: Text.ElideRight }
                        Text {
                            id: selectedBooksCountText
                            objectName: "selectedBooksCountText"
                            text: "0 เรื่อง"
                            font.bold: true
                            font.pixelSize: 14
                            color: "#0f172a"
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: Math.max(52, Math.round(metricRow2.implicitHeight + 16))
                color: "#ffffff"
                radius: 6
                border.color: "#86efac"
                clip: true
                RowLayout {
                    id: metricRow2
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8
                    Text { text: "🏷️"; font.pixelSize: 18 }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        Text { text: "สติกเกอร์บาร์โค้ดรวม"; font.pixelSize: 10; color: "#166534"; Layout.fillWidth: true; elide: Text.ElideRight }
                        Text {
                            id: selectedStickersCountText
                            objectName: "selectedStickersCountText"
                            text: "0 ดวง"
                            font.bold: true
                            font.pixelSize: 14
                            color: "#166534"
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: Math.max(52, Math.round(metricRow3.implicitHeight + 16))
                color: "#ffffff"
                radius: 6
                border.color: "#93c5fd"
                clip: true
                RowLayout {
                    id: metricRow3
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8
                    Text { text: "📄"; font.pixelSize: 18 }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        Text { text: "ประมาณการกระดาษ A4"; font.pixelSize: 10; color: "#1d4ed8"; Layout.fillWidth: true; elide: Text.ElideRight }
                        Text {
                            id: estimatedPagesText
                            objectName: "estimatedPagesText"
                            text: "0 แผ่น (A4 3x8)"
                            font.bold: true
                            font.pixelSize: 14
                            color: "#1d4ed8"
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        // Toolbar Card (Search, Filter & Actions)
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: Math.max(60, Math.round(toolbarRow.implicitHeight + 20))
            color: "#ffffff"
            radius: 8
            border.color: "#e2e8f0"
            clip: true

            Flow {
                id: toolbarRow
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 10
                spacing: 10

                StyledTextInput {
                    id: barcodePrintSearchInput
                    objectName: "barcodePrintSearchInput"
                    placeholderText: "🔍 ค้นหาชื่อหนังสือ / ผู้แต่ง..."
                    width: Math.max(180, Math.min(320, toolbarRow.width))
                    font.pixelSize: 12
                    selectByMouse: true
                    onTextEdited: printSearchDebounce.restart()
                    onTextChanged: if (!activeFocus) barcodePrintScreen.loadPrintableBooks(text, true)
                    onAccepted: {
                        printSearchDebounce.stop()
                        barcodePrintScreen.loadPrintableBooks(text, true)
                    }
                }

                StyledComboBox {
                    id: barcodeCategoryFilterCombo
                    objectName: "barcodeCategoryFilterCombo"
                    width: Math.max(160, Math.min(toolbarRow.width, Math.round(170 * (window.fontScale || 1.0))))
                    textRole: "name"
                    model: ListModel { id: barcodeCategoryFilterModel; objectName: "barcodeCategoryFilterModel" }
                    onCurrentIndexChanged: {
                        if (!barcodePrintScreen._reloadingFilter) {
                            barcodePrintScreen.loadPrintableBooks(barcodePrintSearchInput.text, true)
                        }
                    }
                }

                StyledButton {
                    variant: StyledButton.Primary
                    id: btnSelectAllBooks
                    objectName: "btnSelectAllBooks"
                    text: "☑️ เลือกทั้งหมด"
                    onClicked: barcodePrintScreen.toggleSelectAllPrintableBooks()
                }

                StyledButton {
                    variant: StyledButton.Primary
                    id: btnPrintSelectedPdf
                    objectName: "btnPrintSelectedPdf"
                    text: "📄 พิมพ์เฉพาะที่เลือก"
                    enabled: genBarcodesModel.count > 0
                    onClicked: barcodePrintScreen.exportSelectedBooksPdf()
                }

                StyledButton {
                    variant: StyledButton.Primary
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
            implicitHeight: Math.max(32, Math.round(catHeaderRow.implicitHeight + 8))
            Layout.preferredHeight: implicitHeight
            clip: true
            color: "#f1f5f9"
            border.color: "#cbd5e1"
            radius: 4

            RowLayout {
                id: catHeaderRow
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8
                Text { text: "เลือก"; font.bold: true; font.pixelSize: Math.max(11, Math.round(12 * (window.fontScale || 1.0))); color: "#475569"; Layout.minimumWidth: 32; Layout.preferredWidth: Math.round(40 * (window.fontScale || 1.0)); elide: Text.ElideRight }
                Text { text: "ID"; font.bold: true; font.pixelSize: Math.max(11, Math.round(12 * (window.fontScale || 1.0))); color: "#475569"; Layout.minimumWidth: 32; Layout.preferredWidth: Math.round(40 * (window.fontScale || 1.0)); elide: Text.ElideRight }
                Text { text: "ชื่อหนังสือ / ผู้แต่ง"; font.bold: true; font.pixelSize: Math.max(11, Math.round(12 * (window.fontScale || 1.0))); color: "#475569"; Layout.fillWidth: true; Layout.minimumWidth: 100; elide: Text.ElideRight }
                Text { text: "หมวดหมู่"; font.bold: true; font.pixelSize: Math.max(11, Math.round(12 * (window.fontScale || 1.0))); color: "#475569"; Layout.minimumWidth: 55; Layout.preferredWidth: Math.round(85 * (window.fontScale || 1.0)); elide: Text.ElideRight }
                Text { text: "จำนวน"; font.bold: true; font.pixelSize: Math.max(11, Math.round(12 * (window.fontScale || 1.0))); color: "#475569"; Layout.minimumWidth: 44; Layout.preferredWidth: Math.round(58 * (window.fontScale || 1.0)); elide: Text.ElideRight }
                Text { text: "รหัสบาร์โค้ดประจำเล่ม"; font.bold: true; font.pixelSize: Math.max(11, Math.round(12 * (window.fontScale || 1.0))); color: "#475569"; Layout.minimumWidth: 90; Layout.preferredWidth: Math.round(160 * (window.fontScale || 1.0)); elide: Text.ElideRight }
                Text { text: "จัดการ"; font.bold: true; font.pixelSize: Math.max(11, Math.round(12 * (window.fontScale || 1.0))); color: "#475569"; Layout.minimumWidth: 55; Layout.preferredWidth: Math.round(68 * (window.fontScale || 1.0)); horizontalAlignment: Text.AlignRight; elide: Text.ElideRight }
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
                id: catRowDelegate
                width: genBarcodesList.width
                implicitHeight: Math.max(50, Math.round(barcodesRow.implicitHeight + 14))
                height: implicitHeight
                clip: true
                color: model.selected ? "#f0fdf4" : (index % 2 === 0 ? "#ffffff" : "#f8fafc")
                border.color: model.selected ? "#86efac" : "#e2e8f0"
                border.width: model.selected ? 1.5 : 1
                radius: 4

                Component.onCompleted: Typography.applyToItem(this)

                RowLayout {
                    id: barcodesRow
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 8

                    CheckBox {
                        checked: model.selected
                        Layout.minimumWidth: 32
                        Layout.preferredWidth: Math.round(40 * (window.fontScale || 1.0))
                        onClicked: {
                            genBarcodesModel.setProperty(index, "selected", checked)
                            barcodePrintScreen.recalculateSelectionStats()
                        }
                    }

                    Text {
                        text: "#" + model.book_id
                        font.bold: true
                        font.pixelSize: Math.max(10, Math.round(11 * (window.fontScale || 1.0)))
                        color: "#0284c7"
                        Layout.minimumWidth: 32
                        Layout.preferredWidth: Math.round(40 * (window.fontScale || 1.0))
                        elide: Text.ElideRight
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 100
                        spacing: 1
                        Text {
                            id: catBookTitleText
                            objectName: "catBookTitleText"
                            text: model.title
                            font.bold: true
                            font.pixelSize: Math.max(11, Math.round(13 * (window.fontScale || 1.0)))
                            color: "#0f172a"
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        Text {
                            text: model.author ? ("ผู้แต่ง: " + model.author) : ""
                            font.pixelSize: Math.max(10, Math.round(11 * (window.fontScale || 1.0)))
                            color: "#64748b"
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            visible: text !== ""
                        }
                    }

                    Rectangle {
                        id: categoryPillRect
                        objectName: "categoryPillRect"
                        Layout.minimumWidth: 55
                        Layout.preferredWidth: Math.round(85 * (window.fontScale || 1.0))
                        implicitHeight: Math.max(24, Math.round(categoryPillText.implicitHeight + 6))
                        Layout.preferredHeight: implicitHeight
                        radius: 4
                        color: "#f1f5f9"
                        border.color: "#e2e8f0"
                        Text {
                            id: categoryPillText
                            objectName: "categoryPillText"
                            anchors.centerIn: parent
                            width: parent.width - 8
                            horizontalAlignment: Text.AlignHCenter
                            text: model.category_name
                            font.pixelSize: Math.max(10, Math.round(11 * (window.fontScale || 1.0)))
                            color: "#475569"
                            elide: Text.ElideRight
                        }
                    }

                    Rectangle {
                        id: copyCountPillRect
                        objectName: "copyCountPillRect"
                        Layout.minimumWidth: 44
                        Layout.preferredWidth: Math.round(58 * (window.fontScale || 1.0))
                        implicitHeight: Math.max(24, Math.round(copyCountPillText.implicitHeight + 6))
                        Layout.preferredHeight: implicitHeight
                        radius: 4
                        color: "#dcfce7"
                        Text {
                            id: copyCountPillText
                            objectName: "copyCountPillText"
                            anchors.centerIn: parent
                            width: parent.width - 6
                            horizontalAlignment: Text.AlignHCenter
                            text: model.copy_count + " เล่ม"
                            font.bold: true
                            font.pixelSize: Math.max(10, Math.round(11 * (window.fontScale || 1.0)))
                            color: "#166534"
                            elide: Text.ElideRight
                        }
                    }

                    Text {
                        text: model.barcode_preview
                        font.family: "monospace"
                        font.pixelSize: Math.max(10, Math.round(11 * (window.fontScale || 1.0)))
                        color: "#0f766e"
                        Layout.minimumWidth: 90
                        Layout.preferredWidth: Math.round(160 * (window.fontScale || 1.0))
                        elide: Text.ElideRight
                    }

                    StyledButton {
                        variant: StyledButton.Ghost
                        id: btnAddCopiesRow
                        objectName: "btnAddCopiesRow"
                        text: "+ เล่ม"
                        font.pixelSize: Math.max(10, Math.round(11 * (window.fontScale || 1.0)))
                        Layout.minimumWidth: 55
                        Layout.preferredWidth: Math.max(55, Math.round(contentItem.implicitWidth + 16))
                        implicitHeight: Math.max(28, Math.round(contentItem.implicitHeight + 12))
                        Layout.preferredHeight: implicitHeight
                        onClicked: barcodePrintScreen.addCopiesRequested(model.book_id, model.title)
                    }
                }
            }
        }

        // PDF Status Banner
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: Math.max(44, Math.round(pdfStatusRow.implicitHeight + 16))
            radius: 6
            color: "#f1f5f9"
            border.color: "#e2e8f0"
            visible: genPdfStatusText.text !== ""

            RowLayout {
                id: pdfStatusRow
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
                StyledButton {
                    variant: StyledButton.Primary
                    text: "📂 เปิดไฟล์ PDF"
                    visible: barcodePrintScreen.lastPdfExported !== ""
                    onClicked: librarianAdmin.openLocalFile(barcodePrintScreen.lastPdfExported)
                }
            }
        }
    }
}
