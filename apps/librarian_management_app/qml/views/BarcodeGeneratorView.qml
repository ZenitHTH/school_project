import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../../common_qml"

Rectangle {
    id: barcodeGenScreen
    objectName: "barcodeGenScreen"
    color: "#f8fafc"

    property int currentGenMode: 0 // 0: New Book, 1: Add Copies to Existing
    property var duplicateBook: null
    onCurrentGenModeChanged: updateGenPreview()

    property alias btnModeNewBook: btnModeNewBook
    property alias btnModeAddCopies: btnModeAddCopies
    property alias genBookTitle: genBookTitle
    property alias genBookAuthor: genBookAuthor
    property alias genBookIsbn: genBookIsbn
    property alias btnFetchIsbn: btnFetchIsbn
    property alias chkAutoFetchIsbn: chkAutoFetchIsbn
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
            var raw = librarianAdmin.searchBooks(q, 0)
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
            var books = JSON.parse(librarianAdmin.searchBooks("", 0))
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
        var count = Math.max(1, parseInt(genCopyCountInput.text) || 1)
        if (barcodeGenScreen.currentGenMode === 1) {
            updateGenPreviewExistingMode(count)
            return
        }
        if (duplicateBook) {
            updateGenPreviewDuplicateBook(count)
            return
        }
        updateGenPreviewNewBook(count)
    }

    function updateGenPreviewDuplicateBook(count) {
        incomingTitleText.text = duplicateBook.title + " (พบหนังสือเดิมในระบบ - เพิ่มเล่ม)"
        incomingMetaText.text = "ผู้แต่ง: " + (duplicateBook.author || "-") + " | ISBN: " + (duplicateBook.isbn || "-") + " | มีอยู่แล้ว: " + duplicateBook.total_copies + " เล่ม"
        incomingLocationText.text = "รหัสหนังสือเดิม: #" + duplicateBook.book_id
        incomingCopyCountText.text = "เพิ่มเล่มใหม่: +" + count + " เล่ม"
        previewBarcodesForBook(duplicateBook.book_id, count)
    }

    function updateGenPreviewNewBook(count) {
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
        previewBarcodesForBook(0, count)
    }

    function updateGenPreviewExistingMode(count) {
        if (genExistingBooksModel.count <= 0 || genExistingBookCombo.currentIndex < 0) return
        var sel = genExistingBooksModel.get(genExistingBookCombo.currentIndex)
        incomingTitleText.text = sel.title + " (เพิ่มเล่มเดิม)"
        incomingMetaText.text = "ผู้แต่ง: " + (sel.author || "-") + " | มีอยู่แล้ว: " + sel.total_copies + " เล่ม"
        incomingLocationText.text = "รหัสหนังสือเดิม: #" + sel.book_id
        incomingCopyCountText.text = "เพิ่มเล่มใหม่: +" + count + " เล่ม"
        previewBarcodesForBook(sel.book_id, count)
    }

    function previewBarcodesForBook(bookId, count) {
        try {
            var res = JSON.parse(librarianAdmin.previewBarcodes(bookId, count))
            if (res.ok && res.barcodes && res.barcodes.length > 0) {
                var bcs = res.barcodes
                incomingBarcodePreviewText.text = (bcs.length <= 4)
                    ? bcs.join(", ")
                    : (bcs[0] + " ... " + bcs[bcs.length - 1] + " (รวม " + bcs.length + " เล่ม)")
            }
        } catch (e) {}
    }

    function checkIsbnDuplicate(rawIsbn) {
        if (!rawIsbn || !rawIsbn.trim() || !isArabicIsbn(rawIsbn)) {
            duplicateBook = null
            if (genStatusMessage.text.indexOf("⚠️ พบหนังสือเดิมในระบบ") !== -1) genStatusMessage.text = ""
            updateGenPreview()
            return
        }
        try {
            var res = JSON.parse(librarianAdmin.checkBookByIsbn(rawIsbn.trim()))
            if (res.ok && res.exists && res.book) {
                duplicateBook = res.book
                genStatusMessage.text = "⚠️ พบหนังสือเดิมในระบบ: '" + res.book.title + "' (มีอยู่แล้ว " + res.book.total_copies + " เล่ม) - จะเป็นการเพิ่มเล่มใหม่"
                if (!genBookTitle.text.trim() && res.book.title) genBookTitle.text = res.book.title
                if (!genBookAuthor.text.trim() && res.book.author) genBookAuthor.text = res.book.author
            } else {
                duplicateBook = null
                if (genStatusMessage.text.indexOf("⚠️ พบหนังสือเดิมในระบบ") !== -1) genStatusMessage.text = ""
            }
        } catch (e) {}
        updateGenPreview()
    }

    function isArabicIsbn(input) {
        if (!input || !input.trim()) return false
        var clean = input.replace(/[-\s]/g, "")
        if (!clean) return false
        return /^[0-9]+$/.test(clean) || (/^[0-9]{9}[xX]$/.test(clean))
    }

    function applyAutofillMetadata(data) {
        if (data.title) genBookTitle.text = data.title
        if (data.author !== undefined) genBookAuthor.text = data.author
        if (!duplicateBook) {
            genStatusMessage.text = "✓ ดึงข้อมูลสำเร็จ"
        }
        updateGenPreview()
    }

    function fetchIsbnAndAutofill() {
        if (isbnAutoFetchTimer.running) isbnAutoFetchTimer.stop()
        if (duplicateBook !== null) return
        var rawIsbn = genBookIsbn.text.trim()
        if (!rawIsbn) {
            genStatusMessage.text = "✗ cannot fetch data"
            return
        }
        if (!isArabicIsbn(rawIsbn)) {
            genStatusMessage.text = "✗ ลืมเปลี่ยนภาษา"
            return
        }
        executeIsbnFetch(rawIsbn)
    }

    function executeIsbnFetch(rawIsbn) {
        btnFetchIsbn.enabled = false
        btnExecuteGenerate.enabled = false
        genStatusMessage.text = "กำลังค้นหา..."
        try {
            var res = JSON.parse(librarianAdmin.fetchIsbnMetadata(rawIsbn))
            if (!res.ok || !res.data) {
                genStatusMessage.text = res.error === "ลืมเปลี่ยนภาษา" ? "✗ ลืมเปลี่ยนภาษา" : "✗ cannot fetch data"
                return
            }
            applyAutofillMetadata(res.data)
        } catch (e) {
            genStatusMessage.text = "✗ cannot fetch data"
        } finally {
            btnFetchIsbn.enabled = true
            btnExecuteGenerate.enabled = true
        }
    }

    Timer {
        id: isbnAutoFetchTimer
        interval: 300
        repeat: false
        onTriggered: {
            if (chkAutoFetchIsbn.checked && barcodeGenScreen.duplicateBook === null) {
                barcodeGenScreen.fetchIsbnAndAutofill()
            }
        }
    }

    Component.onDestruction: {
        if (isbnAutoFetchTimer.running) {
            isbnAutoFetchTimer.stop()
        }
    }

    function clearRegistrationForm(savedBookId) {
        genBookTitle.text = ""
        genBookAuthor.text = ""
        genBookIsbn.text = ""
        chkNoIsbnGen.checked = false
        genShelfLocation.text = ""
        genCopyCountInput.text = "1"
        genCategoryCombo.currentIndex = 0
        duplicateBook = null
        barcodeGenScreen.bookSaved()
        if (savedBookId) {
            loadBooksForExistingSelector(savedBookId)
        }
        loadInventoryGrid()
        updateGenPreview()
        genBookIsbn.forceActiveFocus()
    }

    function findExistingBookCandidate(isbn, title) {
        if (duplicateBook) return duplicateBook
        try {
            var q = isbn ? isbn : title
            var found = JSON.parse(librarianAdmin.searchBooks(q, 0))
            var norm = isbn ? isbn.replace(/[-\s]/g, "").toUpperCase() : ""
            for (var i = 0; i < found.length; i++) {
                var cIsbn = (found[i].isbn || "").replace(/[-\s]/g, "").toUpperCase()
                var match = norm ? (cIsbn === norm) : (found[i].title && found[i].title.trim() === title)
                if (match) return found[i]
            }
        } catch (e) {}
        return null
    }

    function saveExistingBookCopies(targetBook, count) {
        var res = JSON.parse(librarianAdmin.addCopies(targetBook.book_id, count.toString()))
        if (!res.ok) {
            genStatusMessage.text = "✗ เกิดข้อผิดพลาด: " + res.error
            return
        }
        genStatusMessage.text = "✓ เพิ่มเล่มหนังสือเดิม '" + targetBook.title + "' สำเร็จ (เพิ่ม " + count + " เล่ม)"
        clearRegistrationForm(targetBook.book_id)
    }

    function saveNewBook(bookData) {
        var catId = ""
        if (genCategoryCombo.currentIndex > 0 && genCategoryCombo.currentIndex < genCategoryModel.count) {
            catId = genCategoryModel.get(genCategoryCombo.currentIndex).category_id.toString()
        }
        var res = JSON.parse(librarianAdmin.addBook(
            bookData.title,
            bookData.isbn,
            bookData.author,
            "",
            catId,
            bookData.shelf,
            bookData.count.toString()
        ))
        if (!res.ok) {
            genStatusMessage.text = "✗ เกิดข้อผิดพลาด: " + res.error
            return
        }
        genStatusMessage.text = "✓ บันทึกหนังสือ '" + bookData.title + "' และสร้างบาร์โค้ดสำเร็จ " + res.data.barcodes.length + " เล่ม"
        clearRegistrationForm(res.data.book_id)
    }

    function executeGenerateAndSave() {
        var count = Math.max(1, parseInt(genCopyCountInput.text) || 1)
        if (barcodeGenScreen.currentGenMode === 1) {
            executeGenerateExistingMode(count)
            return
        }
        var title = genBookTitle.text.trim()
        var isbn = chkNoIsbnGen.checked ? "" : genBookIsbn.text.trim()
        var existingBook = findExistingBookCandidate(isbn, title)
        if (existingBook) {
            saveExistingBookCopies(existingBook, count)
            return
        }
        if (!title) {
            genStatusMessage.text = "✗ กรุณาระบุชื่อหนังสือ"
            return
        }
        saveNewBook({
            title: title,
            isbn: isbn,
            author: genBookAuthor.text.trim(),
            shelf: genShelfLocation.text.trim(),
            count: count
        })
    }

    function executeGenerateExistingMode(count) {
        if (genExistingBooksModel.count === 0 || genExistingBookCombo.currentIndex < 0) {
            genStatusMessage.text = "✗ กรุณาเลือกหนังสือเดิมในระบบ"
            return
        }
        var selBook = genExistingBooksModel.get(genExistingBookCombo.currentIndex)
        var res = JSON.parse(librarianAdmin.addCopies(selBook.book_id, count.toString()))
        if (!res.ok) {
            genStatusMessage.text = "✗ เกิดข้อผิดพลาด: " + res.error
            return
        }
        genStatusMessage.text = "✓ เพิ่มเล่มหนังสือ '" + selBook.title + "' และสร้างบาร์โค้ดสำเร็จ " + res.data.barcodes.length + " เล่ม"
        barcodeGenScreen.bookSaved()
        loadBooksForExistingSelector(selBook.book_id)
        loadInventoryGrid()
        updateGenPreview()
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
            StyledButton {
                variant: StyledButton.Primary
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
                            StyledButton {
                                variant: barcodeGenScreen.currentGenMode === 0 ? StyledButton.Primary : StyledButton.Neutral
                                id: btnModeNewBook
                                objectName: "btnModeNewBook"
                                text: "🆕 เพิ่มหนังสือใหม่"
                                Layout.fillWidth: true
                                onClicked: {
                                    barcodeGenScreen.currentGenMode = 0
                                }
                            }
                            StyledButton {
                                variant: barcodeGenScreen.currentGenMode === 1 ? StyledButton.Primary : StyledButton.Neutral
                                id: btnModeAddCopies
                                objectName: "btnModeAddCopies"
                                text: "➕ เพิ่มเล่มหนังสือเดิม"
                                Layout.fillWidth: true
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
                            StyledTextInput {
                                id: genBookTitle
                                objectName: "genBookTitle"
                                Layout.fillWidth: true
                                placeholderText: "เช่น ฟิสิกส์พื้นฐาน ม.1"
                                selectByMouse: true
                                onTextChanged: barcodeGenScreen.updateGenPreview()
                            }

                            Text { text: "ผู้แต่ง (Author)"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
                            StyledTextInput {
                                id: genBookAuthor
                                objectName: "genBookAuthor"
                                Layout.fillWidth: true
                                placeholderText: "ชื่อผู้แต่ง / คณะผู้จัดทำ"
                                selectByMouse: true
                                onTextChanged: barcodeGenScreen.updateGenPreview()
                            }

                            Text { text: "ISBN จากสำนักพิมพ์"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                StyledTextInput {
                                    id: genBookIsbn
                                    objectName: "genBookIsbn"
                                    Layout.fillWidth: true
                                    placeholderText: "เช่น 978-616-00-1234-5"
                                    selectByMouse: true
                                    enabled: !chkNoIsbnGen.checked
                                    onAccepted: {
                                        barcodeGenScreen.checkIsbnDuplicate(text.trim())
                                        if (chkAutoFetchIsbn.checked && barcodeGenScreen.duplicateBook === null) {
                                            barcodeGenScreen.fetchIsbnAndAutofill()
                                        }
                                    }
                                    onTextChanged: {
                                        if (chkNoIsbnGen.checked) {
                                            if (genStatusMessage.text === "✗ ลืมเปลี่ยนภาษา")
                                                genStatusMessage.text = ""
                                            return
                                        }
                                        if (text.trim() !== "" && !barcodeGenScreen.isArabicIsbn(text)) {
                                            genStatusMessage.text = "✗ ลืมเปลี่ยนภาษา"
                                            barcodeGenScreen.updateGenPreview()
                                            return
                                        }
                                        if (genStatusMessage.text === "✗ ลืมเปลี่ยนภาษา") {
                                            genStatusMessage.text = ""
                                        }
                                        var clean = text.replace(/[-\s]/g, "")
                                        if (clean.length >= 10) {
                                            barcodeGenScreen.checkIsbnDuplicate(text.trim())
                                        } else if (clean.length < 10 && barcodeGenScreen.duplicateBook !== null) {
                                            barcodeGenScreen.checkIsbnDuplicate("")
                                        } else {
                                            barcodeGenScreen.updateGenPreview()
                                        }
                                        if (chkAutoFetchIsbn.checked && clean.length === 13) {
                                            isbnAutoFetchTimer.restart()
                                        }
                                    }
                                }
                                StyledButton {
                                    variant: StyledButton.Primary
                                    id: btnFetchIsbn
                                    objectName: "btnFetchIsbn"
                                    text: "🔍 ดึงข้อมูล"
                                    implicitHeight: genBookIsbn.implicitHeight
                                    background: Rectangle {
                                        implicitHeight: parent.implicitHeight
                                        color: btnFetchIsbn.down ? "#1d4ed8" : (btnFetchIsbn.hovered ? "#2563eb" : "#3b82f6")
                                        radius: 6
                                    }
                                    contentItem: Text {
                                        text: btnFetchIsbn.text
                                        color: "#ffffff"
                                        font.bold: true
                                        font.pixelSize: 13
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                    onClicked: barcodeGenScreen.fetchIsbnAndAutofill()
                                }
                            }

                            CheckBox {
                                id: chkAutoFetchIsbn
                                objectName: "chkAutoFetchIsbn"
                                text: "ค้นหาอัตโนมัติเมื่อสแกน (Auto-fetch on scan)"
                                checked: true
                                font.pixelSize: 12
                            }

                            CheckBox {
                                id: chkNoIsbnGen
                                objectName: "chkNoIsbnGen"
                                text: "ไม่มี ISBN (No ISBN)"
                                font.pixelSize: 12
                                onCheckedChanged: {
                                    if (checked)
                                        genBookIsbn.text = "-"
                                    else if (genBookIsbn.text === "-")
                                        genBookIsbn.text = ""
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Text { text: "หมวดหมู่"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
                                    StyledComboBox {
                                        id: genCategoryCombo
                                        objectName: "genCategoryCombo"
                                        Layout.fillWidth: true
                                        textRole: "name"
                                        model: ListModel { id: genCategoryModel; objectName: "genCategoryModel" }
                                        onCurrentIndexChanged: barcodeGenScreen.updateGenPreview()
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Text { text: "ตำแหน่งชั้นวาง"; font.bold: true; color: "#1e293b"; font.pixelSize: 13 }
                                    StyledTextInput {
                                        id: genShelfLocation
                                        objectName: "genShelfLocation"
                                        Layout.fillWidth: true
                                        placeholderText: "เช่น ชั้น A-01"
                                        selectByMouse: true
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
                            StyledComboBox {
                                id: genExistingBookCombo
                                objectName: "genExistingBookCombo"
                                Layout.fillWidth: true
                                textRole: "display"
                                model: ListModel { id: genExistingBooksModel; objectName: "genExistingBooksModel" }
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
                            StyledTextInput {
                                id: genCopyCountInput
                                objectName: "genCopyCountInput"
                                text: "1"
                                Layout.preferredWidth: 90
                                validator: IntValidator { bottom: 1; top: 99 }
                                selectByMouse: true
                                onTextChanged: barcodeGenScreen.updateGenPreview()
                            }
                            Item { Layout.fillWidth: true }
                            StyledButton { variant: StyledButton.Primary; text: "-1"; Layout.preferredWidth: 44; implicitHeight: genCopyCountInput.implicitHeight; onClicked: { var c = Math.max(1, (parseInt(genCopyCountInput.text) || 1) - 1); genCopyCountInput.text = c.toString(); } }
                            StyledButton { variant: StyledButton.Primary; text: "+1"; Layout.preferredWidth: 44; implicitHeight: genCopyCountInput.implicitHeight; onClicked: { var c = Math.min(99, (parseInt(genCopyCountInput.text) || 1) + 1); genCopyCountInput.text = c.toString(); } }
                            StyledButton {
                                variant: StyledButton.Primary
                                text: "+5"
                                Layout.preferredWidth: 44
                                implicitHeight: genCopyCountInput.implicitHeight
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

                            StyledButton {
                                variant: StyledButton.Primary
                                id: btnRefreshPreview
                                objectName: "btnRefreshPreview"
                                text: "🔄 รีเฟรชข้อมูล"
                                onClicked: barcodeGenScreen.initGeneratorPage()
                            }

                            StyledButton {
                                variant: StyledButton.Primary
                                id: btnExecuteGenerate
                                objectName: "btnExecuteGenerate"
                                text: "💾 บันทึกและสร้างบาร์โค้ด"
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
                            color: text.indexOf("✗") !== -1 ? "#ef4444" : (text.indexOf("⚠️") !== -1 ? "#d97706" : "#10b981")
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
