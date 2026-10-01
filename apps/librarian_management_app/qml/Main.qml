import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../../common_qml"
import "views"
import "dialogs"

ApplicationWindow {
    id: window
    visible: true
    width: 1200
    height: 800
    minimumWidth: 900
    minimumHeight: 600
    title: "ระบบจัดการห้องสมุด (Librarian Management)"
    color: "#f8fafc"

    // Force light palette so TextFields/ComboBoxes always show dark text
    // regardless of system dark mode (Fusion style inherits system palette)
    palette.window: "#f8fafc"
    palette.windowText: "#1e293b"
    palette.base: "#ffffff"
    palette.text: "#1e293b"
    palette.button: "#e2e8f0"
    palette.buttonText: "#1e293b"
    palette.highlight: "#2563eb"
    palette.highlightedText: "#ffffff"
    palette.placeholderText: "#94a3b8"

    property var currentCheckoutStudent: null
    property var lastGeneratedBarcodes: []
    property int selectedBookId: 0
    property string selectedBookTitle: ""

    // View property aliases for script and test discovery
    property alias catalogSearchInput: catalogView.catalogSearchInput
    property alias btnSearchBooks: catalogView.btnSearchBooks
    property alias catalogList: catalogView.catalogList
    property alias catalogModel: catalogView.catalogModel
    property alias btnOpenGeneratorPage: catalogView.btnOpenGeneratorPage

    property alias studentLookupInput: deskView.studentLookupInput
    property alias btnLookupStudent: deskView.btnLookupStudent
    property alias checkoutStudentName: deskView.checkoutStudentName
    property alias barcodeInput: deskView.barcodeInput
    property alias btnCheckout: deskView.btnCheckout
    property alias btnReturn: deskView.btnReturn
    property alias deskStatusText: deskView.deskStatusText

    property alias activeLoanList: activeLoansView.activeLoanList
    property alias activeLoanModel: activeLoansView.activeLoanModel

    property alias snapshotPathInput: syncView.snapshotPathInput
    property alias btnPreviewDiff: syncView.btnPreviewDiff
    property alias applySyncBtn: syncView.applySyncBtn
    property alias diffSummaryText: syncView.diffSummaryText
    property alias diffDetailsList: syncView.diffDetailsList
    property alias diffModel: syncView.diffModel

    property alias fineList: finesView.fineList
    property alias fineModel: finesView.fineModel

    property alias logList: auditLogView.logList
    property alias logModel: auditLogView.logModel

    property alias barcodeGenScreen: barcodeGenView
    property alias btnModeNewBook: barcodeGenView.btnModeNewBook
    property alias btnModeAddCopies: barcodeGenView.btnModeAddCopies
    property alias genBookTitle: barcodeGenView.genBookTitle
    property alias genBookAuthor: barcodeGenView.genBookAuthor
    property alias genBookIsbn: barcodeGenView.genBookIsbn
    property alias genCategoryCombo: barcodeGenView.genCategoryCombo
    property alias genCategoryModel: barcodeGenView.genCategoryModel
    property alias genShelfLocation: barcodeGenView.genShelfLocation
    property alias genExistingBookCombo: barcodeGenView.genExistingBookCombo
    property alias genExistingBooksModel: barcodeGenView.genExistingBooksModel
    property alias genCopyCountInput: barcodeGenView.genCopyCountInput
    property alias btnRefreshPreview: barcodeGenView.btnRefreshPreview
    property alias btnExecuteGenerate: barcodeGenView.btnExecuteGenerate
    property alias genStatusMessage: barcodeGenView.genStatusMessage
    property alias btnExportPdfSheet: barcodeGenView.btnExportPdfSheet
    property alias genBarcodesList: barcodeGenView.genBarcodesList
    property alias genBarcodesModel: barcodeGenView.genBarcodesModel
    property alias genPdfStatusText: barcodeGenView.genPdfStatusText

    property alias categoryScreen: categoryView
    property alias categoryNameInput: categoryView.categoryNameInput
    property alias btnAddCategory: categoryView.btnAddCategory
    property alias categoryStatusText: categoryView.categoryStatusText
    property alias categoryListView: categoryView.categoryListView
    property alias categoryListModel: categoryView.categoryListModel

    // Dialog aliases
    property alias addBookDialog: bookDialogs.addBookDialog
    property alias newBookTitle: bookDialogs.newBookTitle
    property alias newBookIsbn: bookDialogs.newBookIsbn
    property alias newBookAuthor: bookDialogs.newBookAuthor
    property alias newBookBarcodes: bookDialogs.newBookBarcodes
    property alias addCopiesDialog: bookDialogs.addCopiesDialog
    property alias addCopiesCountInput: bookDialogs.addCopiesCountInput
    property alias barcodeConfirmDialog: bookDialogs.barcodeConfirmDialog
    property alias editBookDialog: bookDialogs.editBookDialog
    property alias editBookTitleInput: bookDialogs.editBookTitleInput
    property alias editBookAuthorInput: bookDialogs.editBookAuthorInput
    property alias editBookIsbnInput: bookDialogs.editBookIsbnInput
    property alias editBookCategoryCombo: bookDialogs.editBookCategoryCombo
    property alias editBookShelfInput: bookDialogs.editBookShelfInput
    property alias editBookStatusText: bookDialogs.editBookStatusText
    property alias deleteBookDialog: bookDialogs.deleteBookDialog
    property alias deleteBookConfirmText: bookDialogs.deleteBookConfirmText
    property alias btnConfirmDeleteBook: bookDialogs.btnConfirmDeleteBook

    property alias renameCategoryDialog: categoryDialogs.renameCategoryDialog
    property alias renameCategoryInput: categoryDialogs.renameCategoryInput
    property alias renameStatusText: categoryDialogs.renameStatusText
    property alias btnSubmitRename: categoryDialogs.btnSubmitRename
    property alias reassignCategoryDialog: categoryDialogs.reassignCategoryDialog
    property alias reassignWarningText: categoryDialogs.reassignWarningText
    property alias reassignBooksList: categoryDialogs.reassignBooksList
    property alias reassignBooksModel: categoryDialogs.reassignBooksModel
    property alias targetCategoryCombo: categoryDialogs.targetCategoryCombo
    property alias targetCategoryComboModel: categoryDialogs.targetCategoryComboModel
    property alias btnConfirmReassignDelete: categoryDialogs.btnConfirmReassignDelete
    property alias simpleDeleteCategoryDialog: categoryDialogs.simpleDeleteCategoryDialog
    property alias simpleDeleteConfirmText: categoryDialogs.simpleDeleteConfirmText
    property alias btnConfirmSimpleDelete: categoryDialogs.btnConfirmSimpleDelete

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Sidebar Navigation
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 240
            color: "#0f172a"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Text {
                    text: "📚 ห้องสมุดโรงเรียน"
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 18
                    Layout.alignment: Qt.AlignHCenter
                    Layout.topMargin: 10
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: "#334155"
                    Layout.bottomMargin: 10
                }

                component NavBtn: Button {
                    property bool active: false
                    Layout.fillWidth: true
                    height: 38
                    contentItem: Text {
                        text: parent.text
                        color: parent.active ? "#38bdf8" : (parent.hovered ? "#ffffff" : "#cbd5e1")
                        font.pixelSize: 13
                        font.bold: parent.active
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: 10
                    }
                    background: Rectangle {
                        color: parent.active ? "#1e293b" : (parent.hovered ? "#334155" : "transparent")
                        radius: 6
                        border.color: parent.active ? "#38bdf8" : "transparent"
                        border.width: parent.active ? 1 : 0
                    }
                }

                NavBtn {
                    text: "📖 แคตตาล็อกหนังสือ"
                    active: stackLayout.currentIndex === 0
                    onClicked: stackLayout.currentIndex = 0
                }

                NavBtn {
                    id: navBtnGenerator
                    objectName: "navBtnGenerator"
                    text: "🏷️ สร้างบาร์โค้ดและเพิ่มหนังสือ"
                    active: stackLayout.currentIndex === 6
                    onClicked: {
                        window.initGeneratorPage()
                        stackLayout.currentIndex = 6
                    }
                }

                NavBtn {
                    id: navBtnCategories
                    objectName: "navBtnCategories"
                    text: "📁 จัดการหมวดหมู่"
                    active: stackLayout.currentIndex === 7
                    onClicked: {
                        window.loadCategoriesList()
                        stackLayout.currentIndex = 7
                    }
                }

                NavBtn {
                    text: "🔄 เคาน์เตอร์ ยืม-คืน"
                    active: stackLayout.currentIndex === 1
                    onClicked: stackLayout.currentIndex = 1
                }

                NavBtn {
                    text: "📋 รายการที่กำลังยืมอยู่"
                    active: stackLayout.currentIndex === 2
                    onClicked: {
                        window.loadActiveLoans()
                        stackLayout.currentIndex = 2
                    }
                }

                NavBtn {
                    text: "📥 Sync ข้อมูลนักเรียน"
                    active: stackLayout.currentIndex === 3
                    onClicked: stackLayout.currentIndex = 3
                }

                NavBtn {
                    text: "💰 ค่าปรับและการชำระ"
                    active: stackLayout.currentIndex === 4
                    onClicked: {
                        window.loadFines()
                        stackLayout.currentIndex = 4
                    }
                }

                NavBtn {
                    text: "📜 ประวัติกิจกรรม (Audit Log)"
                    active: stackLayout.currentIndex === 5
                    onClicked: {
                        window.loadLogs()
                        stackLayout.currentIndex = 5
                    }
                }

                Item { Layout.fillHeight: true }

                Button {
                    id: openWizardBtn
                    objectName: "openWizardBtn"
                    Layout.fillWidth: true
                    text: "⚙️ ตัวช่วยสร้างฐานข้อมูล"
                    font.pixelSize: 11
                    flat: true
                    contentItem: Text {
                        text: openWizardBtn.text
                        font: openWizardBtn.font
                        color: "#94a3b8"
                        horizontalAlignment: Text.AlignHCenter
                    }
                    onClicked: firstLaunchDialog.open()
                }

                Text {
                    text: "สถานะ: ฐานข้อมูลพร้อมใช้งาน"
                    color: "#94a3b8"
                    font.pixelSize: 12
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }

        // Content Area
        StackLayout {
            id: stackLayout
            objectName: "librarianStack"
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: 0

            // 0. Book Catalog View
            BookCatalogView {
                id: catalogView
                onSearchRequested: window.searchBooks()
                onOpenGeneratorRequested: {
                    window.initGeneratorPage()
                    stackLayout.currentIndex = 6
                }
                onAddCopiesRequested: function(bookId, title) {
                    bookDialogs.openAddCopiesDialog(bookId, title)
                }
                onEditBookRequested: function(bookId, title, author, isbn, categoryId, shelf) {
                    bookDialogs.openEditBookDialog(bookId, title, author, isbn, categoryId, shelf)
                }
                onDeleteBookRequested: function(bookId, title) {
                    bookDialogs.openDeleteBookDialog(bookId, title)
                }
            }

            // 1. Circulation Desk View
            CirculationDeskView {
                id: deskView
                currentCheckoutStudent: window.currentCheckoutStudent
                onLookupStudentRequested: window.lookupStudent()
                onCheckoutRequested: window.doCheckout()
                onReturnRequested: window.doReturn()
            }

            // 2. Active Loans View
            ActiveLoansView {
                id: activeLoansView
            }

            // 3. Student Sync View
            StudentSyncView {
                id: syncView
                onPreviewDiffRequested: window.previewDiff()
                onApplySyncRequested: window.applySync()
            }

            // 4. Fines Management View
            FinesManagementView {
                id: finesView
                onLoadFinesRequested: window.loadFines()
            }

            // 5. Shared Audit Log View (from common_qml)
            AuditLogView {
                id: auditLogView
                title: "ประวัติกิจกรรมห้องสมุด (Audit Log)"
            }

            // 6. Barcode Generator View
            BarcodeGeneratorView {
                id: barcodeGenView
                onBackToCatalogRequested: stackLayout.currentIndex = 0
                onBookSaved: {
                    window.searchBooks()
                }
            }

            // 7. Category Management View
            CategoryManagementView {
                id: categoryView
                onEditCategoryRequested: function(catId, catName) {
                    categoryDialogs.openRenameCategoryDialog(catId, catName)
                }
                onDeleteCategoryRequested: function(catId, catName) {
                    categoryDialogs.requestDeleteCategory(catId, catName)
                }
                onCategoryAdded: {
                    window.initGeneratorPage()
                }
            }
        }
    }

    // Book Dialogs
    BookActionDialogs {
        id: bookDialogs
        rootWindow: window
    }

    // Category Dialogs
    CategoryActionDialogs {
        id: categoryDialogs
        rootWindow: window
    }

    // Setup Wizard Dialogs
    FileDialog {
        id: firstLaunchFileDialog
        objectName: "firstLaunchFileDialog"
        title: "เลือกไฟล์ข้อมูลนักเรียน (.sqlite Snapshot หรือ .xlsx Excel)"
        nameFilters: ["Student Data (*.sqlite *.xlsx *.xls *.db)", "All files (*)"]
        onAccepted: {
            var path = selectedFile.toString()
            if (path.indexOf("file://") === 0) {
                path = decodeURIComponent(path.substring(7))
            }
            firstLaunchDialog.statusText = "กำลังนำเข้าข้อมูลจาก: " + path + "..."
            var res = JSON.parse(librarianAdmin.importRoster(path, "Librarian"))
            if (res.ok) {
                firstLaunchDialog.statusText = "✓ นำเข้าข้อมูลนักเรียนสำเร็จเรียบร้อยแล้ว"
                searchBooks()
                firstLaunchTimer.start()
            } else {
                firstLaunchDialog.statusText = "✗ เกิดข้อผิดพลาด: " + res.error
            }
        }
    }

    Timer {
        id: firstLaunchTimer
        interval: 1200
        repeat: false
        onTriggered: {
            firstLaunchDialog.close()
        }
    }

    FirstLaunchDialog {
        id: firstLaunchDialog
        bannerIcon: "📚"
        bannerTitle: "ยินดีต้อนรับสู่ระบบห้องสมุดโรงเรียน"
        bannerSubtitle: "ยังไม่พบข้อมูลในระบบห้องสมุด หรือเป็นการเริ่มต้นใช้งานครั้งแรก"
        promptText: "คุณมีไฟล์ข้อมูลนักเรียนเพื่อนำเข้าหรือไม่?"
        explanationText: "• หากมีไฟล์ Snapshot / Excel: ระบบจะซิงค์บัญชีรายชื่อนักเรียนเพื่อเริ่มระบบยืม-คืนทันที\n• หากไม่มีไฟล์: ระบบจะสร้างฐานข้อมูลเปล่าตามกฎตาราง เพื่อให้พร้อมจัดการแคตตาล็อกหนังสือ"
        importButtonText: "📥 มีไฟล์ Snapshot / Excel — เลือกไฟล์นำเข้า"
        blankButtonText: "🆕 ไม่มีไฟล์ — สร้างฐานข้อมูลเปล่า"
        onImportClicked: firstLaunchFileDialog.open()
        onBlankClicked: {
            var res = JSON.parse(librarianAdmin.initializeBlankDatabase("Librarian"))
            firstLaunchDialog.close()
            searchBooks()
        }
    }

    // -------------------------------------------------------------
    // Controller & Orchestration Functions
    // -------------------------------------------------------------

    function searchBooks() {
        catalogModel.clear()
        var results = JSON.parse(librarianAdmin.searchBooks(catalogSearchInput.text))
        for (var i = 0; i < results.length; i++) catalogModel.append(results[i])
    }

    function lookupStudent() {
        var results = JSON.parse(librarianAdmin.searchStudents(studentLookupInput.text))
        if (results.length > 0) {
            window.currentCheckoutStudent = results[0]
        } else {
            deskStatusText.text = "ไม่พบข้อมูลนักเรียน"
        }
    }

    function doCheckout() {
        if (!window.currentCheckoutStudent) {
            deskStatusText.text = "กรุณาเลือกนักเรียนผู้ยืมก่อน"
            return
        }
        if (!barcodeInput.text) {
            deskStatusText.text = "กรุณากรอกหรือสแกนบาร์โค้ด"
            return
        }
        var res = JSON.parse(librarianAdmin.checkout(window.currentCheckoutStudent.student_id, barcodeInput.text))
        deskStatusText.text = res.ok ? "ยืมหนังสือสำเร็จ! กำหนดคืน: " + res.data.due_at.substring(0, 10) : "ไม่สามารถยืมได้: " + res.error
        barcodeInput.text = ""
    }

    function doReturn() {
        if (!barcodeInput.text) {
            deskStatusText.text = "กรุณากรอกหรือสแกนบาร์โค้ดเล่มที่ต้องการคืน"
            return
        }
        var copyRes = JSON.parse(librarianAdmin.getCopyByBarcode(barcodeInput.text))
        if (!copyRes.ok) {
            deskStatusText.text = copyRes.error
            return
        }
        var activeLoans = JSON.parse(librarianAdmin.getActiveLoans())
        var loanId = null
        for (var i = 0; i < activeLoans.length; i++) {
            if (activeLoans[i].copy_id === copyRes.data.copy_id) {
                loanId = activeLoans[i].loan_id
                break
            }
        }
        if (!loanId) {
            deskStatusText.text = "ไม่พบรายการยืมที่ค้างอยู่สำหรับบาร์โค้ดนี้"
            return
        }
        var retRes = JSON.parse(librarianAdmin.returnBook(loanId))
        deskStatusText.text = retRes.ok ? "คืนหนังสือสำเร็จเรียบร้อย" : ("คืนหนังสือไม่สำเร็จ: " + retRes.error)
        barcodeInput.text = ""
    }

    function loadActiveLoans() {
        activeLoanModel.clear()
        var loans = JSON.parse(librarianAdmin.getActiveLoans())
        for (var i = 0; i < loans.length; i++) activeLoanModel.append(loans[i])
    }

    function loadFines() {
        fineModel.clear()
        var fines = JSON.parse(librarianAdmin.listFines())
        for (var i = 0; i < fines.length; i++) fineModel.append(fines[i])
    }

    function loadLogs() {
        logModel.clear()
        var logs = JSON.parse(librarianAdmin.getActivityLogs())
        for (var i = 0; i < logs.length; i++) logModel.append(logs[i])
    }

    function previewDiff() {
        diffModel.clear()
        var res = JSON.parse(librarianAdmin.previewSync(snapshotPathInput.text))
        if (!res.ok) {
            diffSummaryText.text = "เกิดข้อผิดพลาด: " + res.error
            return
        }
        var s = res.data.summary
        diffSummaryText.text = "ผลการตรวจสอบ: นักเรียนใหม่ " + s.new_count + " คน, มีการเปลี่ยนแปลง " + s.changed_count + " คน (" + s.status_changes_count + " คนเปลี่ยนสถานะ), เปลี่ยนรหัส ID " + s.id_renumbered_count + " คน"
        applySyncBtn.enabled = true

        for (var i = 0; i < res.data.changed.length; i++) {
            var c = res.data.changed[i]
            diffModel.append({
                desc: "• เปลี่ยนแปลง: " + c.student_name + " (รหัส " + c.student_id + ") " + (c.status_changed ? "[สถานะเปลี่ยน!]" : ""),
                is_status: c.status_changed
            })
        }
        for (var j = 0; j < res.data.id_renumbered.length; j++) {
            var r = res.data.id_renumbered[j]
            diffModel.append({
                desc: "• เปลี่ยนรหัสนักเรียน: " + r.old_id + " -> " + r.new_id + " (" + r.student_name + ")",
                is_status: true
            })
        }
    }

    function applySync() {
        var res = JSON.parse(librarianAdmin.applySync(snapshotPathInput.text))
        diffSummaryText.text = res.ok ? "นำเข้าข้อมูลนักเรียนสำเร็จเรียบร้อย!" : ("เกิดข้อผิดพลาด: " + res.error)
        applySyncBtn.enabled = false
    }

    // Forwarding to Barcode Generator View
    function initGeneratorPage() {
        barcodeGenView.initGeneratorPage()
    }

    function loadBooksForExistingSelector() {
        barcodeGenView.loadBooksForExistingSelector()
    }

    function updateGenPreview() {
        barcodeGenView.updateGenPreview()
    }

    function executeGenerateAndSave() {
        barcodeGenView.executeGenerateAndSave()
    }

    function exportGenPdf() {
        barcodeGenView.exportGenPdf()
    }

    // Forwarding to Category Management View & Dialogs
    function loadCategoriesList() {
        categoryView.loadCategoriesList()
    }

    function addNewCategory() {
        categoryView.addNewCategory()
    }

    function openRenameCategoryDialog(catId, catName) {
        categoryDialogs.openRenameCategoryDialog(catId, catName)
    }

    function submitRenameCategory() {
        categoryDialogs.submitRenameCategory()
    }

    function requestDeleteCategory(catId, catName) {
        categoryDialogs.requestDeleteCategory(catId, catName)
    }

    function executeReassignAndDelete() {
        categoryDialogs.executeReassignAndDelete()
    }

    function executeDirectDelete() {
        categoryDialogs.executeDirectDelete()
    }

    // Forwarding to Book Dialogs
    function openEditBookDialog(bookId, title, author, isbn, categoryId, shelf) {
        bookDialogs.openEditBookDialog(bookId, title, author, isbn, categoryId, shelf)
    }

    function submitEditBook() {
        bookDialogs.submitEditBook()
    }

    function openDeleteBookDialog(bookId, title) {
        bookDialogs.openDeleteBookDialog(bookId, title)
    }

    function executeDeleteBook() {
        bookDialogs.executeDeleteBook()
    }

    Component.onCompleted: {
        if (typeof librarianAdmin !== "undefined" && librarianAdmin !== null) {
            searchBooks()
            if (librarianAdmin.isFirstLaunch()) {
                firstLaunchDialog.open()
            }
        }
    }
}
