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
                        initGeneratorPage()
                        stackLayout.currentIndex = 6
                    }
                }

                NavBtn {
                    id: navBtnCategories
                    objectName: "navBtnCategories"
                    text: "📁 จัดการหมวดหมู่"
                    active: stackLayout.currentIndex === 7
                    onClicked: {
                        loadCategoriesList()
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
                        loadActiveLoans()
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
                        loadFines()
                        stackLayout.currentIndex = 4
                    }
                }

                NavBtn {
                    text: "📜 ประวัติกิจกรรม (Audit Log)"
                    active: stackLayout.currentIndex === 5
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
                            id: btnOpenGeneratorPage
                            objectName: "btnOpenGeneratorPage"
                            text: "🏷️ สร้างบาร์โค้ดและเพิ่มหนังสือ"
                            highlighted: true
                            onClicked: {
                                initGeneratorPage()
                                stackLayout.currentIndex = 6
                            }
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
                                Text { text: "หมวดหมู่: " + (model.category_name || "-"); color: "#475569"; Layout.preferredWidth: 130 }
                                Text { text: "มีทั้งหมด: " + model.total_copies + " เล่ม (พร้อมยืม: " + model.available_copies + ")"; color: "#059669"; font.bold: true; Layout.fillWidth: true }
                                Button {
                                    text: "+ เพิ่มเล่ม"
                                    onClicked: {
                                        window.selectedBookId = model.book_id
                                        window.selectedBookTitle = model.title
                                        addCopiesCountInput.text = "1"
                                        addCopiesDialog.open()
                                    }
                                }
                                Button {
                                    text: "✏️ แก้ไข"
                                    flat: true
                                    font.pixelSize: 12
                                    onClicked: openEditBookDialog(model.book_id, model.title, model.author || "", model.isbn || "", model.category_id || 0, model.shelf_location || "")
                                }
                                Button {
                                    text: "🗑️ ลบ"
                                    flat: true
                                    font.pixelSize: 12
                                    contentItem: Text {
                                        text: "🗑️ ลบ"
                                        font.pixelSize: 12
                                        color: "#ef4444"
                                        verticalAlignment: Text.AlignVCenter
                                        horizontalAlignment: Text.AlignHCenter
                                    }
                                    onClicked: openDeleteBookDialog(model.book_id, model.title)
                                }
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

            // 7. Book Adding & Barcode Generator Screen (index 6)
            Rectangle {
                id: barcodeGenScreen
                objectName: "barcodeGenScreen"
                color: "#f8fafc"

                property int currentGenMode: 0 // 0: New Book, 1: Add Copies to Existing
                property var previewedBarcodes: []
                property int previewedBookId: 0
                property string lastPdfExported: ""

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
                            onClicked: stackLayout.currentIndex = 0
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
                                                updateGenPreview()
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
                                                loadBooksForExistingSelector()
                                                updateGenPreview()
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
                                            onTextChanged: updateGenPreview()
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
                                            onCurrentIndexChanged: updateGenPreview()
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
                                            onTextChanged: updateGenPreview()
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
                                            onClicked: updateGenPreview()
                                        }

                                        Button {
                                            id: btnExecuteGenerate
                                            objectName: "btnExecuteGenerate"
                                            text: "💾 บันทึกและสร้างบาร์โค้ด"
                                            highlighted: true
                                            Layout.fillWidth: true
                                            onClicked: executeGenerateAndSave()
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
                                        onClicked: exportGenPdf()
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

            // 8. Category Management Screen (index 7)
            Rectangle {
                id: categoryScreen
                objectName: "categoryScreen"
                color: "#ffffff"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 16

                    // Header
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            spacing: 4
                            Text {
                                text: "📁 จัดการหมวดหมู่หนังสือ (Category Management)"
                                font.bold: true
                                font.pixelSize: 22
                                color: "#1e293b"
                            }
                            Text {
                                text: "เพิ่มและตรวจสอบรายการหมวดหมู่สำหรับจัดหมวดหมู่หนังสือในระบบห้องสมุด"
                                font.pixelSize: 13
                                color: "#64748b"
                            }
                        }
                        Item { Layout.fillWidth: true }
                        Button {
                            text: "🔄 รีเฟรช"
                            flat: true
                            onClicked: loadCategoriesList()
                        }
                    }

                    // Input Card
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 96
                        color: "#f8fafc"
                        radius: 8
                        border.color: "#e2e8f0"
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                TextField {
                                    id: categoryNameInput
                                    objectName: "categoryNameInput"
                                    placeholderText: "ระบุชื่อหมวดหมู่ใหม่..."
                                    Layout.fillWidth: true
                                    font.pixelSize: 13
                                    selectByMouse: true
                                    onAccepted: addNewCategory()
                                }
                                Button {
                                    id: btnAddCategory
                                    objectName: "btnAddCategory"
                                    text: "+ เพิ่มหมวดหมู่"
                                    highlighted: true
                                    Layout.preferredWidth: 140
                                    onClicked: addNewCategory()
                                }
                            }

                            Text {
                                id: categoryStatusText
                                objectName: "categoryStatusText"
                                Layout.fillWidth: true
                                text: ""
                                font.pixelSize: 12
                            }
                        }
                    }

                    // Categories List
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "📋 รายการหมวดหมู่ทั้งหมด"
                                font.bold: true
                                font.pixelSize: 16
                                color: "#1e293b"
                            }
                            Text {
                                text: "(" + categoryListModel.count + " หมวดหมู่)"
                                font.pixelSize: 13
                                color: "#64748b"
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 120
                            color: "#f8fafc"
                            border.color: "#e2e8f0"
                            radius: 8
                            visible: categoryListModel.count === 0
                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 8
                                Text {
                                    text: "📂 ยังไม่มีหมวดหมู่ในระบบ"
                                    font.pixelSize: 15
                                    font.bold: true
                                    color: "#64748b"
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                Text {
                                    text: "พิมพ์ชื่อหมวดหมู่ในช่องด้านบน แล้วกด '+ เพิ่มหมวดหมู่' เพื่อเริ่มต้น"
                                    font.pixelSize: 13
                                    color: "#94a3b8"
                                    Layout.alignment: Qt.AlignHCenter
                                }
                            }
                        }

                        ListView {
                            id: categoryListView
                            objectName: "categoryListView"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 8
                            visible: categoryListModel.count > 0
                            model: categoryListModel

                            delegate: Rectangle {
                                width: categoryListView.width
                                height: 50
                                color: "#ffffff"
                                border.color: "#e2e8f0"
                                radius: 6

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 12

                                    Rectangle {
                                        width: 36
                                        height: 26
                                        radius: 4
                                        color: "#e0f2fe"
                                        border.color: "#38bdf8"
                                        Text {
                                            anchors.centerIn: parent
                                            text: "#" + model.category_id
                                            font.bold: true
                                            color: "#0284c7"
                                            font.pixelSize: 11
                                        }
                                    }

                                    Text {
                                        text: model.name
                                        font.pixelSize: 14
                                        font.bold: true
                                        color: "#1e293b"
                                        Layout.fillWidth: true
                                    }

                                    Button {
                                        id: btnEditCategory
                                        text: "✏️ แก้ไข"
                                        font.pixelSize: 11
                                        flat: true
                                        onClicked: openRenameCategoryDialog(model.category_id, model.name)
                                    }

                                    Button {
                                        id: btnDeleteCategory
                                        text: "🗑️ ลบ"
                                        font.pixelSize: 11
                                        flat: true
                                        contentItem: Text {
                                            text: "🗑️ ลบ"
                                            font.pixelSize: 11
                                            color: "#ef4444"
                                            verticalAlignment: Text.AlignVCenter
                                            horizontalAlignment: Text.AlignHCenter
                                        }
                                        onClicked: requestDeleteCategory(model.category_id, model.name)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Dialogs
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
    Dialog {
        id: addBookDialog
        objectName: "addBookDialog"
        title: "เพิ่มหนังสือใหม่และสร้างบาร์โค้ด"
        standardButtons: Dialog.Ok | Dialog.Cancel
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
                    window.lastGeneratedBarcodes = res.data.barcodes
                    for (var i = 0; i < res.data.barcodes.length; i++) {
                        barcodeConfirmModel.append({ "barcode": res.data.barcodes[i] })
                    }
                    pdfExportStatusText.text = ""
                    barcodeConfirmDialog.open()
                }
                searchBooks()
            }
        }
    }

    Dialog {
        id: addCopiesDialog
        objectName: "addCopiesDialog"
        title: "เพิ่มเล่มหนังสือ: " + window.selectedBookTitle
        standardButtons: Dialog.Ok | Dialog.Cancel
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
            if (count > 0 && !isNaN(Number(raw))) {
                res = JSON.parse(librarianAdmin.addCopies(window.selectedBookId, count))
            } else {
                res = JSON.parse(librarianAdmin.addCopies(window.selectedBookId, raw))
            }
            if (res.ok && res.data && res.data.barcodes && res.data.barcodes.length > 0) {
                barcodeConfirmModel.clear()
                window.lastGeneratedBarcodes = res.data.barcodes
                for (var i = 0; i < res.data.barcodes.length; i++) {
                    barcodeConfirmModel.append({ "barcode": res.data.barcodes[i] })
                }
                pdfExportStatusText.text = ""
                barcodeConfirmDialog.open()
            }
            searchBooks()
        }
    }

    Dialog {
        id: barcodeConfirmDialog
        objectName: "barcodeConfirmDialog"
        title: "สร้างบาร์โค้ดประจำเล่มสำเร็จ"
        standardButtons: Dialog.Close
        width: 460
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
                    var res = JSON.parse(librarianAdmin.exportLabelsPdf(JSON.stringify(window.lastGeneratedBarcodes), outPath))
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
    // Edit Book Dialog
    Dialog {
        id: editBookDialog
        objectName: "editBookDialog"
        title: "✏️ แก้ไขข้อมูลหนังสือ"
        modal: true
        anchors.centerIn: parent
        width: 440
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

    // Delete Book Confirm Dialog
    Dialog {
        id: deleteBookDialog
        objectName: "deleteBookDialog"
        title: "🗑️ ยืนยันการลบหนังสือ"
        modal: true
        anchors.centerIn: parent
        width: 400
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
                searchBooks()
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
                searchBooks()
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

    ListModel {
        id: categoryListModel
        objectName: "categoryListModel"
    }

    function loadCategoriesList() {
        categoryListModel.clear()
        try {
            var raw = librarianAdmin.listCategories()
            var cats = JSON.parse(raw)
            for (var i = 0; i < cats.length; i++) {
                categoryListModel.append({
                    "category_id": cats[i].category_id,
                    "name": cats[i].name
                })
            }
        } catch (e) {
            console.error("Failed to load categories: " + e)
        }
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
                loadCategoriesList()
                initGeneratorPage()
            } else {
                categoryStatusText.text = "✗ " + (res.error || "เกิดข้อผิดพลาดในการเพิ่มหมวดหมู่")
                categoryStatusText.color = "#ef4444"
            }
        } catch (e) {
            categoryStatusText.text = "✗ เกิดข้อผิดพลาดในการเชื่อมต่อ: " + e
            categoryStatusText.color = "#ef4444"
        }
    }

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
            categoryStatusText.text = "✓ แก้ไขชื่อเป็น '" + newName + "' สำเร็จ"
            categoryStatusText.color = "#10b981"
            loadCategoriesList()
            initGeneratorPage()
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
            categoryStatusText.text = "✓ ลบหมวดหมู่และย้ายหนังสือเรียบร้อยแล้ว"
            categoryStatusText.color = "#10b981"
            loadCategoriesList()
            initGeneratorPage()
            searchBooks()
        } else {
            categoryStatusText.text = "✗ " + (res.error || "ลบหมวดหมู่ไม่สำเร็จ")
            categoryStatusText.color = "#ef4444"
        }
    }

    function executeDirectDelete() {
        var res = JSON.parse(librarianAdmin.deleteCategory(simpleDeleteCategoryDialog.targetCatId, ""))
        if (res.ok) {
            simpleDeleteCategoryDialog.close()
            categoryStatusText.text = "✓ ลบหมวดหมู่เรียบร้อยแล้ว"
            categoryStatusText.color = "#10b981"
            loadCategoriesList()
            initGeneratorPage()
            searchBooks()
        } else {
            categoryStatusText.text = "✗ " + (res.error || "ลบหมวดหมู่ไม่สำเร็จ")
            categoryStatusText.color = "#ef4444"
        }
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
            searchBooks()
            loadBooksForExistingSelector()
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
            searchBooks()
            loadBooksForExistingSelector()
        } else {
            deleteBookConfirmText.text = "✗ " + (res.error || "ลบหนังสือไม่สำเร็จ")
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
