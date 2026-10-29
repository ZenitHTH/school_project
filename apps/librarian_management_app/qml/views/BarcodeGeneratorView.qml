import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: barcodeGenScreen
    objectName: "barcodeGenScreen"
    color: "#f8fafc"

    property int currentGenMode: 0 // 0: New Book, 1: Add Copies to Existing
    onCurrentGenModeChanged: updateGenPreview()

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

    // Grouping / Category Management & Inventory aliases
    property alias categoryNameInput: rightInventoryPane.categoryNameInput
    property alias btnAddCategory: rightInventoryPane.btnAddCategory
    property alias categoryStatusText: rightInventoryPane.categoryStatusText
    property alias categoryListView: rightInventoryPane.categoryListView
    property alias categoryListModel: rightInventoryPane.categoryListModel

    property alias incomingBookPreviewCard: rightInventoryPane.incomingBookPreviewCard
    property alias incomingTitleText: rightInventoryPane.incomingTitleText
    property alias incomingMetaText: rightInventoryPane.incomingMetaText
    property alias incomingLocationText: rightInventoryPane.incomingLocationText
    property alias incomingCopyCountText: rightInventoryPane.incomingCopyCountText
    property alias incomingBarcodePreviewText: rightInventoryPane.incomingBarcodePreviewText
    property alias incomingBarcodesModel: rightInventoryPane.incomingBarcodesModel

    property alias inventorySearchInput: rightInventoryPane.inventorySearchInput
    property alias inventoryBooksList: rightInventoryPane.inventoryBooksList
    property alias inventoryBooksModel: rightInventoryPane.inventoryBooksModel
    property alias btnGoToPrintPage: rightInventoryPane.btnGoToPrintPage

    signal backToCatalogRequested()
    signal bookSaved()
    signal editCategoryRequested(int catId, string catName)
    signal deleteCategoryRequested(int catId, string catName)
    signal categoryAdded()
    signal goToPrintPageRequested()
    signal addCopiesRequested(int bookId, string title)
    signal editBookRequested(int bookId, string title, string author, string isbn, int categoryId, string shelf, int totalCopies)
    signal deleteBookRequested(int bookId, string title)

    function reloadCategories() {
        var prevCatId = 0
        if (genCategoryCombo.currentIndex > 0 && genCategoryCombo.currentIndex < genCategoryModel.count) {
            prevCatId = genCategoryModel.get(genCategoryCombo.currentIndex).category_id
        }
        genCategoryModel.clear()
        genCategoryModel.append({ "category_id": 0, "name": "-- ไม่ระบุหมวดหมู่ --" })
        categoryListModel.clear()
        try {
            var raw = librarianAdmin.listCategories()
            var cats = JSON.parse(raw)
            var newIndex = 0
            for (var i = 0; i < cats.length; i++) {
                genCategoryModel.append(cats[i])
                categoryListModel.append({
                    "category_id": cats[i].category_id,
                    "name": cats[i].name
                })
                if (cats[i].category_id === prevCatId) {
                    newIndex = i + 1
                }
            }
            genCategoryCombo.currentIndex = newIndex
        } catch (e) {}
    }

    function loadInventoryGrid(query) {
        inventoryBooksModel.clear()
        try {
            var q = (typeof query === "string") ? query : (inventorySearchInput ? inventorySearchInput.text : "")
            var raw = librarianAdmin.searchBooks(q)
            var books = JSON.parse(raw)
            for (var i = 0; i < books.length; i++) {
                inventoryBooksModel.append(books[i])
            }
        } catch (e) {}
    }

    function initGeneratorPage() {
        reloadCategories()
        loadBooksForExistingSelector()
        loadInventoryGrid()
        updateGenPreview()
    }

    function loadCategoriesList() {
        reloadCategories()
    }

    function addNewCategory() {
        var name = categoryNameInput.text.trim()
        if (!name) {
            categoryStatusText.text = "⚠️ กรุณากรอกชื่อหมวดหมู่"
            categoryStatusText.color = "#ef4444"
            return
        }

        try {
            var res = JSON.parse(librarianAdmin.addCategory(name))
            if (res.ok) {
                categoryStatusText.text = "✓ เพิ่มหมวดหมู่ '" + name + "' เรียบร้อยแล้ว"
                categoryStatusText.color = "#10b981"
                categoryNameInput.text = ""
                reloadCategories()
                barcodeGenScreen.categoryAdded()
            } else {
                categoryStatusText.text = "✗ " + (res.error || "เกิดข้อผิดพลาดในการเพิ่มหมวดหมู่")
                categoryStatusText.color = "#ef4444"
            }
        } catch (e) {
            categoryStatusText.text = "✗ เกิดข้อผิดพลาดในการเชื่อมต่อ: " + e
            categoryStatusText.color = "#ef4444"
        }
    }

    function loadBooksForExistingSelector(preferredBookId) {
        var prevId = (typeof preferredBookId === "number" && preferredBookId > 0)
            ? preferredBookId
            : (genExistingBookCombo.currentIndex >= 0 && genExistingBookCombo.currentIndex < genExistingBooksModel.count
                ? genExistingBooksModel.get(genExistingBookCombo.currentIndex).book_id
                : 0)

        genExistingBooksModel.clear()
        var selIdx = 0
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
                if (b.book_id === prevId) {
                    selIdx = i
                }
            }
        } catch (e) {}
        if (genExistingBooksModel.count > 0) {
            genExistingBookCombo.currentIndex = selIdx
            var cur = genExistingBooksModel.get(selIdx)
            existingBookInfoText.text = "หนังสือ: " + cur.title + " | ปัจจุบันมี: " + cur.total_copies + " เล่ม"
        } else {
            genExistingBookCombo.currentIndex = -1
            existingBookInfoText.text = ""
        }
    }

    function updateGenPreview() {
        var count = parseInt(genCopyCountInput.text) || 1
        if (count <= 0) count = 1

        if (barcodeGenScreen.currentGenMode === 0) {
            var t = genBookTitle.text.trim()
            incomingTitleText.text = t ? t : "(ยังไม่ได้ระบุชื่อหนังสือ)"
            var a = genBookAuthor.text.trim()
            var isbn = genBookIsbn.text.trim()
            incomingMetaText.text = "ผู้แต่ง: " + (a ? a : "-") + " | ISBN: " + (isbn ? isbn : "-")

            var catName = "-"
            if (genCategoryCombo.currentIndex > 0 && genCategoryCombo.currentIndex < genCategoryModel.count) {
                catName = genCategoryModel.get(genCategoryCombo.currentIndex).name
            }
            var shelf = genShelfLocation.text.trim()
            incomingLocationText.text = "หมวด: " + catName + " | ชั้นวาง: " + (shelf ? shelf : "-")
            incomingCopyCountText.text = "จำนวน: " + count + " เล่ม"

            try {
                var previewRes = JSON.parse(librarianAdmin.previewBarcodes(0, count))
                if (previewRes.ok && previewRes.barcodes && previewRes.barcodes.length > 0) {
                    var bcs = previewRes.barcodes
                    incomingBarcodePreviewText.text = (bcs.length <= 4)
                        ? bcs.join(", ")
                        : (bcs[0] + " ... " + bcs[bcs.length - 1] + " (รวม " + bcs.length + " เล่ม)")
                }
            } catch (e) {}
        } else {
            if (genExistingBooksModel.count > 0 && genExistingBookCombo.currentIndex >= 0) {
                var sel = genExistingBooksModel.get(genExistingBookCombo.currentIndex)
                incomingTitleText.text = sel.title + " (เพิ่มเล่มเดิม)"
                incomingMetaText.text = "ผู้แต่ง: " + (sel.author || "-") + " | มีอยู่แล้ว: " + sel.total_copies + " เล่ม"
                incomingLocationText.text = "รหัสหนังสือเดิม: #" + sel.book_id
                incomingCopyCountText.text = "เพิ่มเล่มใหม่: +" + count + " เล่ม"

                try {
                    var prevCopiesRes = JSON.parse(librarianAdmin.previewBarcodes(sel.book_id, count))
                    if (prevCopiesRes.ok && prevCopiesRes.barcodes && prevCopiesRes.barcodes.length > 0) {
                        var cbcs = prevCopiesRes.barcodes
                        incomingBarcodePreviewText.text = (cbcs.length <= 4)
                            ? cbcs.join(", ")
                            : (cbcs[0] + " ... " + cbcs[cbcs.length - 1] + " (รวม " + cbcs.length + " เล่ม)")
                    }
                } catch (e) {}
            }
        }
    }

    function executeGenerateAndSave() {
        var count = parseInt(genCopyCountInput.text) || 1
        if (count <= 0) count = 1

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
            if (genCategoryCombo.currentIndex > 0 && genCategoryCombo.currentIndex < genCategoryModel.count) {
                catId = genCategoryModel.get(genCategoryCombo.currentIndex).category_id.toString()
            }
            var shelf = genShelfLocation.text.trim()

            // Check if active book with identical title already exists
            var existingBook = null
            try {
                var found = JSON.parse(librarianAdmin.searchBooks(title))
                for (var fi = 0; fi < found.length; fi++) {
                    if (found[fi].title.trim() === title && (!isbn || found[fi].isbn === isbn)) {
                        existingBook = found[fi]
                        break
                    }
                }
            } catch (e) {}

            if (existingBook && existingBook.total_copies < count) {
                var diff = count - existingBook.total_copies
                res = JSON.parse(librarianAdmin.addCopies(existingBook.book_id, diff.toString()))
                if (res.ok) {
                    genStatusMessage.text = "✓ ปรับจำนวนเล่มหนังสือ '" + title + "' เป็น " + count + " เล่ม (สร้างบาร์โค้ดเพิ่ม " + diff + " เล่ม)"
                    barcodeGenScreen.bookSaved()
                    loadBooksForExistingSelector(existingBook.book_id)
                    loadInventoryGrid()
                    updateGenPreview()
                } else {
                    genStatusMessage.text = "✗ เกิดข้อผิดพลาด: " + res.error
                }
            } else {
                res = JSON.parse(librarianAdmin.addBook(title, isbn, author, "", catId, shelf, count.toString()))
                if (res.ok) {
                    genStatusMessage.text = "✓ บันทึกหนังสือ '" + title + "' และสร้างบาร์โค้ดสำเร็จ " + res.data.barcodes.length + " เล่ม"
                    barcodeGenScreen.bookSaved()
                    loadBooksForExistingSelector(res.data.book_id)
                    loadInventoryGrid()
                    updateGenPreview()
                } else {
                    genStatusMessage.text = "✗ เกิดข้อผิดพลาด: " + res.error
                }
            }
        } else {
            if (genExistingBooksModel.count === 0 || genExistingBookCombo.currentIndex < 0) {
                genStatusMessage.text = "✗ กรุณาเลือกหนังสือเดิมในระบบ"
                return
            }
            var selBook = genExistingBooksModel.get(genExistingBookCombo.currentIndex)
            res = JSON.parse(librarianAdmin.addCopies(selBook.book_id, count.toString()))
            if (res.ok) {
                genStatusMessage.text = "✓ เพิ่มเล่มหนังสือ '" + selBook.title + "' และสร้างบาร์โค้ดสำเร็จ " + res.data.barcodes.length + " เล่ม"
                barcodeGenScreen.bookSaved()
                loadBooksForExistingSelector(selBook.book_id)
                loadInventoryGrid()
                updateGenPreview()
            } else {
                genStatusMessage.text = "✗ เกิดข้อผิดพลาด: " + res.error
            }
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
                    text: "📚 เพิ่มหนังสือและจัดการหมวดหมู่ (Book Registration & Grouping)"
                    font.bold: true
                    font.pixelSize: 20
                    color: "#0f172a"
                }
                Text {
                    text: "ลงทะเบียนหนังสือใหม่/เพิ่มเล่มพร้อมสร้างบาร์โค้ดลงฐานข้อมูลทันที (ด้านซ้าย) และจัดการหมวดหมู่หนังสือ (ด้านขวา)"
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

        // Main 2-column split view
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

            // Left Card: Add Book / Add Copies Form
            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: 420
                Layout.maximumWidth: 460
                Layout.minimumWidth: 350
                color: "#ffffff"
                radius: 8
                border.color: "#e2e8f0"

                ScrollView {
                    id: leftFormScroll
                    anchors.fill: parent
                    anchors.margins: 16
                    clip: true

                    ColumnLayout {
                        width: leftFormScroll.availableWidth
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
                                onTextChanged: barcodeGenScreen.updateGenPreview()
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
                                onTextChanged: barcodeGenScreen.updateGenPreview()
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
                                        implicitHeight: 36
                                        textRole: "name"
                                        model: ListModel { id: genCategoryModel; objectName: "genCategoryModel" }
                                        onCurrentIndexChanged: barcodeGenScreen.updateGenPreview()
                                        background: Rectangle {
                                            implicitHeight: 36
                                            color: "#ffffff"
                                            border.color: genCategoryCombo.activeFocus ? "#2563eb" : "#cbd5e1"
                                            radius: 4
                                            Text {
                                                anchors.right: parent.right
                                                anchors.rightMargin: 10
                                                anchors.verticalCenter: parent.verticalCenter
                                                text: "▼"
                                                font.pixelSize: 10
                                                color: "#64748b"
                                            }
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
                                        onTextChanged: barcodeGenScreen.updateGenPreview()
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
                                implicitHeight: 36
                                textRole: "display"
                                model: ListModel { id: genExistingBooksModel; objectName: "genExistingBooksModel" }
                                background: Rectangle {
                                    implicitHeight: 36
                                    color: "#ffffff"
                                    border.color: genExistingBookCombo.activeFocus ? "#2563eb" : "#cbd5e1"
                                    radius: 4
                                    Text {
                                        anchors.right: parent.right
                                        anchors.rightMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "▼"
                                        font.pixelSize: 10
                                        color: "#64748b"
                                    }
                                }
                                contentItem: Text {
                                    leftPadding: 8
                                    text: genExistingBookCombo.displayText
                                    color: "#1e293b"
                                    font.pixelSize: 13
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }
                                onCurrentIndexChanged: {
                                    if (currentIndex >= 0 && currentIndex < genExistingBooksModel.count) {
                                        var sel = genExistingBooksModel.get(currentIndex)
                                        existingBookInfoText.text = "หนังสือ: " + sel.title + " | ปัจจุบันมี: " + sel.total_copies + " เล่ม"
                                    } else {
                                        existingBookInfoText.text = ""
                                    }
                                    barcodeGenScreen.updateGenPreview()
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
                        Text { text: "จำนวนเล่มที่ต้องการบันทึก (Copy Count) *"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
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
                            Button {
                                text: "+5"
                                Layout.preferredWidth: 44
                                onClicked: {
                                    var cur = parseInt(genCopyCountInput.text) || 1
                                    var c = (cur === 1) ? 5 : Math.min(99, cur + 5)
                                    genCopyCountInput.text = c.toString()
                                }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: "#e2e8f0" }

                        // Submit Button & Hidden Refresh
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Button {
                                id: btnRefreshPreview
                                objectName: "btnRefreshPreview"
                                text: "🔄 รีเฟรชข้อมูล"
                                onClicked: barcodeGenScreen.initGeneratorPage()
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
                        }
                    }
                }
            }

            // Right Card: Live Incoming Preview & Inventory Grid Table
            BookInventoryRightPane {
                id: rightInventoryPane
                Layout.fillHeight: true
                Layout.fillWidth: true
                Layout.minimumWidth: 400
                onAddNewCategoryRequested: barcodeGenScreen.addNewCategory()
                onEditCategoryRequested: function(catId, catName) { barcodeGenScreen.editCategoryRequested(catId, catName) }
                onDeleteCategoryRequested: function(catId, catName) { barcodeGenScreen.deleteCategoryRequested(catId, catName) }
                onRefreshInventoryRequested: barcodeGenScreen.loadInventoryGrid(inventorySearchInput.text)
                onAddCopiesRequested: function(bookId, title) { barcodeGenScreen.addCopiesRequested(bookId, title) }
                onEditBookRequested: function(bookId, title, author, isbn, categoryId, shelf, totalCopies) {
                    barcodeGenScreen.editBookRequested(bookId, title, author, isbn, categoryId, shelf, totalCopies)
                }
                onDeleteBookRequested: function(bookId, title) { barcodeGenScreen.deleteBookRequested(bookId, title) }
                onGoToPrintPageRequested: barcodeGenScreen.goToPrintPageRequested()
            }
        }
    }
}
