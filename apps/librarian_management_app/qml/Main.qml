import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs

ApplicationWindow {
    id: window
    visible: true
    width: 1200
    height: 800
    minimumWidth: 900
    minimumHeight: 600
    title: "ระบบจัดการห้องสมุด (Librarian Management)"
    color: "#f8fafc"

    property var currentCheckoutStudent: null

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

                Button {
                    text: "📖 แคตตาล็อกหนังสือ"
                    Layout.fillWidth: true
                    onClicked: stackLayout.currentIndex = 0
                }

                Button {
                    text: "🔄 เคาน์เตอร์ ยืม-คืน"
                    Layout.fillWidth: true
                    onClicked: stackLayout.currentIndex = 1
                }

                Button {
                    text: "📋 รายการที่กำลังยืมอยู่"
                    Layout.fillWidth: true
                    onClicked: {
                        loadActiveLoans()
                        stackLayout.currentIndex = 2
                    }
                }

                Button {
                    text: "📥 Sync ข้อมูลนักเรียน"
                    Layout.fillWidth: true
                    onClicked: stackLayout.currentIndex = 3
                }

                Button {
                    text: "💰 ค่าปรับและการชำระ"
                    Layout.fillWidth: true
                    onClicked: {
                        loadFines()
                        stackLayout.currentIndex = 4
                    }
                }

                Button {
                    text: "📜 ประวัติกิจกรรม (Audit Log)"
                    Layout.fillWidth: true
                    onClicked: {
                        loadLogs()
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

            // 1. Catalog Screen
            Rectangle {
                color: "#ffffff"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 16

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "แคตตาล็อกหนังสือ (Book Catalog)"; font.bold: true; font.pixelSize: 22 }
                        Item { Layout.fillWidth: true }
                        Button {
                            objectName: "btnAddBookDialog"
                            text: "+ เพิ่มหนังสือใหม่"
                            highlighted: true
                            onClicked: addBookDialog.open()
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        TextField {
                            id: catalogSearchInput
                            objectName: "catalogSearchInput"
                            placeholderText: "ค้นหาชื่อหนังสือ, ผู้แต่ง, ISBN..."
                            Layout.fillWidth: true
                            onAccepted: searchBooks()
                        }
                        Button { objectName: "btnSearchBooks"; text: "ค้นหา"; onClicked: searchBooks() }
                    }

                    ListView {
                        id: catalogList
                        objectName: "catalogList"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: ListModel { id: catalogModel; objectName: "catalogModel" }
                        delegate: Rectangle {
                            width: catalogList.width
                            height: 64
                            border.color: "#e2e8f0"
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                ColumnLayout {
                                    Layout.preferredWidth: 350
                                    Text { text: model.title; font.bold: true; font.pixelSize: 15 }
                                    Text { text: "ผู้แต่ง: " + (model.author || "-") + " | ISBN: " + (model.isbn || "-"); color: "#64748b"; font.pixelSize: 12 }
                                }
                                Text { text: "หมวดหมู่: " + (model.category_name || "-"); color: "#475569"; Layout.preferredWidth: 150 }
                                Text { text: "มีทั้งหมด: " + model.total_copies + " เล่ม (พร้อมยืม: " + model.available_copies + ")"; color: "#059669"; font.bold: true; Layout.fillWidth: true }
                            }
                        }
                    }
                }
            }

            // 2. Checkout & Return Desk Screen
            Rectangle {
                color: "#ffffff"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 16

                    Text { text: "เคาน์เตอร์ ยืม-คืน หนังสือ (Desk Checkout/Return)"; font.bold: true; font.pixelSize: 22 }

                    // Student lookup section
                    Rectangle {
                        Layout.fillWidth: true
                        height: 120
                        color: "#f1f5f9"
                        radius: 8
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 8
                            Text { text: "1. ระบุนักเรียนผู้ยืม:"; font.bold: true }
                            RowLayout {
                                TextField {
                                    id: studentLookupInput
                                    objectName: "studentLookupInput"
                                    placeholderText: "พิมพ์รหัสนักเรียน หรือชื่อ..."
                                    Layout.preferredWidth: 260
                                    onAccepted: lookupStudent()
                                }
                                Button { objectName: "btnLookupStudent"; text: "ค้นหา"; onClicked: lookupStudent() }
                                Text {
                                    id: checkoutStudentName
                                    objectName: "checkoutStudentName"
                                    text: window.currentCheckoutStudent ? ("ผู้ยืม: " + window.currentCheckoutStudent.full_name + " (รหัส " + window.currentCheckoutStudent.student_id + " - สถานะ " + window.currentCheckoutStudent.status + ")") : "ยังไม่ได้เลือกนักเรียน"
                                    font.bold: true
                                    color: window.currentCheckoutStudent ? "#0f766e" : "#64748b"
                                }
                            }
                        }
                    }

                    // Barcode scan section
                    Rectangle {
                        Layout.fillWidth: true
                        height: 140
                        color: "#f8fafc"
                        border.color: "#cbd5e1"
                        radius: 8
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 8
                            Text { text: "2. สแกนบาร์โค้ดประจำเล่มหนังสือ (Tracking Barcode):"; font.bold: true }
                            RowLayout {
                                TextField {
                                    id: barcodeInput
                                    objectName: "barcodeInput"
                                    placeholderText: "สแกนบาร์โค้ด..."
                                    Layout.preferredWidth: 260
                                    font.pixelSize: 16
                                }
                                Button {
                                    objectName: "btnCheckout"
                                    text: "ยืมหนังสือ (Checkout)"
                                    highlighted: true
                                    onClicked: doCheckout()
                                }
                                Button {
                                    objectName: "btnReturn"
                                    text: "คืนหนังสือ (Return)"
                                    onClicked: doReturn()
                                }
                            }
                            Text {
                                id: deskStatusText
                                objectName: "deskStatusText"
                                font.pixelSize: 14
                                color: "#2563eb"
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // 3. Active Loans Screen
            Rectangle {
                color: "#ffffff"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 16

                    Text { text: "รายการหนังสือที่กำลังยืมอยู่ทั้งหมด"; font.bold: true; font.pixelSize: 22 }

                    ListView {
                        id: activeLoanList
                        objectName: "activeLoanList"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: ListModel { id: activeLoanModel; objectName: "activeLoanModel" }
                        delegate: Rectangle {
                            width: activeLoanList.width
                            height: 54
                            border.color: "#e2e8f0"
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                Text { text: model.barcode; font.bold: true; Layout.preferredWidth: 120 }
                                Text { text: model.title; font.pixelSize: 14; Layout.preferredWidth: 280 }
                                Text { text: model.full_name + " (" + model.student_id + ")"; Layout.preferredWidth: 200 }
                                Text { text: "กำหนดคืน: " + model.due_at.substring(0, 10); color: "#dc2626"; Layout.fillWidth: true }
                            }
                        }
                    }
                }
            }

            // 4. Student Data Sync Screen
            Rectangle {
                color: "#ffffff"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 16

                    Text { text: "Sync ข้อมูลนักเรียนจากฝ่ายทะเบียน (LINE Snapshot)"; font.bold: true; font.pixelSize: 22 }

                    RowLayout {
                        TextField {
                            id: snapshotPathInput
                            objectName: "snapshotPathInput"
                            text: "snapshot.sqlite"
                            placeholderText: "path ของไฟล์ snapshot.sqlite"
                            Layout.preferredWidth: 320
                        }
                        Button {
                            objectName: "btnPreviewDiff"
                            text: "ตรวจสอบความเปลี่ยนแปลง (Preview Diff)"
                            highlighted: true
                            onClicked: previewDiff()
                        }
                        Button {
                            id: applySyncBtn
                            objectName: "applySyncBtn"
                            text: "ยืนยันนำเข้าข้อมูล (Apply Sync)"
                            enabled: false
                            onClicked: applySync()
                        }
                    }

                    // Diff Preview card
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#f8fafc"
                        border.color: "#e2e8f0"
                        radius: 6
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8
                            Text {
                                id: diffSummaryText
                                objectName: "diffSummaryText"
                                text: "กด 'ตรวจสอบความเปลี่ยนแปลง' เพื่อดูรายการก่อนนำเข้า"
                                font.bold: true
                                font.pixelSize: 16
                            }
                            ListView {
                                id: diffDetailsList
                                objectName: "diffDetailsList"
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                model: ListModel { id: diffModel; objectName: "diffModel" }
                                delegate: Text {
                                    text: model.desc
                                    color: model.is_status ? "#b91c1c" : "#1e293b"
                                    font.bold: model.is_status
                                }
                            }
                        }
                    }
                }
            }

            // 5. Fines Screen
            Rectangle {
                color: "#ffffff"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 16

                    Text { text: "ค่าปรับค้างชำระและการบันทึกการชำระ"; font.bold: true; font.pixelSize: 22 }

                    ListView {
                        id: fineList
                        objectName: "fineList"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: ListModel { id: fineModel; objectName: "fineModel" }
                        delegate: Rectangle {
                            width: fineList.width
                            height: 54
                            border.color: "#e2e8f0"
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                Text { text: model.full_name; font.bold: true; Layout.preferredWidth: 180 }
                                Text { text: model.title; Layout.preferredWidth: 260 }
                                Text { text: model.amount + " บาท (" + model.reason + ")"; color: "#dc2626"; font.bold: true; Layout.preferredWidth: 160 }
                                Text { text: model.paid ? "ชำระแล้ว" : "ค้างชำระ"; color: model.paid ? "#166534" : "#991b1b"; Layout.fillWidth: true }
                                Button {
                                    text: "บันทึกการชำระ"
                                    visible: !model.paid
                                    onClicked: {
                                        librarianAdmin.payFine(model.fine_id)
                                        loadFines()
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // 6. Audit Log Screen
            Rectangle {
                color: "#ffffff"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 16

                    Text { text: "ประวัติกิจกรรมห้องสมุด (Audit Log)"; font.bold: true; font.pixelSize: 22 }

                    ListView {
                        id: logList
                        objectName: "logList"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: ListModel { id: logModel; objectName: "logModel" }
                        delegate: Rectangle {
                            width: logList.width
                            height: 48
                            border.color: "#e2e8f0"
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                Text { text: model.logged_at.substring(0, 19); color: "#64748b"; Layout.preferredWidth: 150 }
                                Text { text: model.action; font.bold: true; Layout.preferredWidth: 160 }
                                Text { text: model.detail; Layout.fillWidth: true }
                            }
                        }
                    }
                }
            }
        }
    }

    // Dialogs
    Dialog {
        id: addBookDialog
        objectName: "addBookDialog"
        title: "เพิ่มหนังสือใหม่และบาร์โค้ด"
        standardButtons: Dialog.Ok | Dialog.Cancel
        ColumnLayout {
            TextField { id: newBookTitle; objectName: "newBookTitle"; placeholderText: "ชื่อหนังสือ" }
            TextField { id: newBookIsbn; objectName: "newBookIsbn"; placeholderText: "ISBN (บาร์โค้ดจากสำนักพิมพ์)" }
            TextField { id: newBookAuthor; objectName: "newBookAuthor"; placeholderText: "ผู้แต่ง" }
            TextField { id: newBookBarcodes; objectName: "newBookBarcodes"; placeholderText: "บาร์โค้ดประจำเล่ม (คั่นด้วยจุลภาค เช่น SCI-01,SCI-02)" }
        }
        onAccepted: {
            if (newBookTitle.text) {
                librarianAdmin.addBook(newBookTitle.text, newBookIsbn.text, newBookAuthor.text, "", "", "", newBookBarcodes.text)
                searchBooks()
            }
        }
    }

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
            firstLaunchStatusText.text = "กำลังนำเข้าข้อมูลจาก: " + path + "..."
            var res = JSON.parse(librarianAdmin.importRoster(path, "Librarian"))
            if (res.ok) {
                firstLaunchStatusText.text = "✓ นำเข้าข้อมูลนักเรียนสำเร็จเรียบร้อยแล้ว"
                searchBooks()
                firstLaunchTimer.start()
            } else {
                firstLaunchStatusText.text = "✗ เกิดข้อผิดพลาด: " + res.error
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

    Dialog {
        id: firstLaunchDialog
        objectName: "firstLaunchDialog"
        title: "🎉 เริ่มต้นใช้งานระบบห้องสมุด (Library Setup Wizard)"
        modal: true
        anchors.centerIn: parent
        width: 520
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape

        ColumnLayout {
            spacing: 16
            width: parent.width

            Rectangle {
                Layout.fillWidth: true
                height: 70
                color: "#eff6ff"
                radius: 8
                border.color: "#bfdbfe"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 12
                    Text {
                        text: "📚"
                        font.pixelSize: 32
                    }
                    ColumnLayout {
                        spacing: 4
                        Text {
                            text: "ยินดีต้อนรับสู่ระบบห้องสมุดโรงเรียน"
                            font.bold: true
                            font.pixelSize: 15
                            color: "#1e3a8a"
                        }
                        Text {
                            text: "ยังไม่พบข้อมูลในระบบห้องสมุด หรือเป็นการเริ่มต้นใช้งานครั้งแรก"
                            font.pixelSize: 12
                            color: "#3b82f6"
                        }
                    }
                }
            }

            Text {
                text: "คุณมีไฟล์ข้อมูลนักเรียนเพื่อนำเข้าหรือไม่?"
                font.bold: true
                font.pixelSize: 14
                color: "#1e293b"
            }

            Text {
                text: "• หากมีไฟล์ Snapshot / Excel: ระบบจะซิงค์บัญชีรายชื่อนักเรียนเพื่อเริ่มระบบยืม-คืนทันที\n• หากไม่มีไฟล์: ระบบจะสร้างฐานข้อมูลเปล่าตามกฎตาราง เพื่อให้พร้อมจัดการแคตตาล็อกหนังสือ"
                font.pixelSize: 12
                color: "#64748b"
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }

            Text {
                id: firstLaunchStatusText
                objectName: "firstLaunchStatusText"
                text: ""
                font.pixelSize: 12
                color: text.indexOf("✗") !== -1 ? "#ef4444" : "#10b981"
                wrapMode: Text.Wrap
                Layout.fillWidth: true
                visible: text !== ""
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Button {
                    id: firstLaunchImportBtn
                    objectName: "firstLaunchImportBtn"
                    Layout.fillWidth: true
                    text: "📥 มีไฟล์ Snapshot / Excel — เลือกไฟล์นำเข้า"
                    highlighted: true
                    onClicked: {
                        firstLaunchFileDialog.open()
                    }
                }

                Button {
                    id: firstLaunchBlankBtn
                    objectName: "firstLaunchBlankBtn"
                    Layout.fillWidth: true
                    text: "🆕 ไม่มีไฟล์ — สร้างฐานข้อมูลเปล่า"
                    onClicked: {
                        var res = JSON.parse(librarianAdmin.initializeBlankDatabase("Librarian"))
                        firstLaunchDialog.close()
                        searchBooks()
                    }
                }
            }
        }
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
