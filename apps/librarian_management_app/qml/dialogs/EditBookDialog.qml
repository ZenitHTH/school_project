import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../../common_qml"

StyledDialog {
    id: editDialog
    objectName: "editBookDialog"
    title: ""
    width: Math.min(620, parent ? parent.width - 32 : 600)
    standardButtons: Dialog.NoButton
    padding: 0

    property int targetBookId: 0
    property int currentTotalCopies: 1
    property int availableCopies: 1
    property int onLoanCopies: 0
    property int minAllowedCopies: 1
    property var rootWindow: null

    property alias editBookTitleInput: titleInput
    property alias editBookAuthorInput: authorInput
    property alias editBookIsbnInput: isbnInput
    property alias editBookCategoryCombo: categoryCombo
    property alias editBookCategoryModel: categoryModel
    property alias editBookShelfInput: shelfInput
    property alias editBookCopiesInput: copiesInput
    property alias editBookStatusText: statusText

    signal saved()

    function loadCopiesBreakdown(bookId) {
        copiesListModel.clear()
        if (typeof librarianAdmin === "undefined" || !librarianAdmin) return
        try {
            var raw = librarianAdmin.getBookCopiesDetail(bookId)
            var res = JSON.parse(raw)
            if (res.ok && res.data) {
                editDialog.availableCopies = res.data.available_copies
                editDialog.onLoanCopies = res.data.on_loan_copies
                var copies = res.data.copies || []
                var rank = 0
                for (var r = copies.length - 1; r >= 0; r--) {
                    copies[r].remove_rank = copies[r].can_remove ? (++rank) : 0
                }
                editDialog.minAllowedCopies = Math.max(1, copies.length - rank)
                for (var i = 0; i < copies.length; i++) {
                    copiesListModel.append(copies[i])
                }
            }
        } catch (e) {}
    }

    function stepCopies(delta) {
        var cur = parseInt(copiesInput.text) || 1
        var next = Math.max(1, cur + delta)
        copiesInput.text = next.toString()
    }

    function calculateDiff() {
        var cur = parseInt(copiesInput.text) || editDialog.currentTotalCopies
        return cur - editDialog.currentTotalCopies
    }

    function isBelowOnLoan() {
        var target = parseInt(copiesInput.text) || editDialog.currentTotalCopies
        return target < editDialog.minAllowedCopies
    }

    background: Rectangle {
        color: "#ffffff"
        radius: 12
        border.color: "#cbd5e1"
        border.width: 1
    }

    contentItem: ColumnLayout {
        spacing: 0

        // Custom Header
        Rectangle {
            Layout.fillWidth: true
            height: 56
            color: "#0f172a"
            radius: 12
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 12
                color: "#0f172a"
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 10

                Rectangle {
                    width: 30; height: 30; radius: 6
                    color: "#1e293b"
                    border.color: "#38bdf8"
                    Text {
                        anchors.centerIn: parent
                        text: "✏️"
                        font.pixelSize: 14
                    }
                }

                ColumnLayout {
                    spacing: 1
                    RowLayout {
                        spacing: 8
                        Text {
                            text: "แก้ไขข้อมูลหนังสือ & ปรับแก้จำนวนเล่ม"
                            color: "#ffffff"
                            font.bold: true
                            font.pixelSize: 14
                        }
                        Rectangle {
                            height: 18
                            width: bookIdText.contentWidth + 10
                            radius: 9
                            color: "#0284c7"
                            Text {
                                id: bookIdText
                                anchors.centerIn: parent
                                text: "#" + editDialog.targetBookId
                                font.bold: true
                                font.pixelSize: 10
                                color: "#ffffff"
                            }
                        }
                    }
                    Text {
                        text: "แก้ไขรายละเอียดบรรณานุกรม และปรับแก้จำนวนเล่มเมื่อกรอกผิดพลาด"
                        color: "#94a3b8"
                        font.pixelSize: 11
                    }
                }

                Item { Layout.fillWidth: true }

                StyledButton {
                    variant: StyledButton.Ghost
                    text: "✕"
                    flat: true
                    font.pixelSize: 13
                    Layout.preferredWidth: 32
                    contentItem: Text {
                        text: "✕"
                        color: "#94a3b8"
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                    }
                    onClicked: editDialog.close()
                }
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.maximumHeight: 520
            clip: true

            ColumnLayout {
                width: editDialog.width - 32
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 12

                Item { height: 4 }

                // Section 1: Metadata Card
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: metaCol.implicitHeight + 20
                    color: "#f8fafc"
                    radius: 8
                    border.color: "#e2e8f0"

                    ColumnLayout {
                        id: metaCol
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

                        Text {
                            text: "📖 ข้อมูลบรรณานุกรม"
                            font.bold: true
                            font.pixelSize: 12
                            color: "#334155"
                        }

                        // Title
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            Text { text: "ชื่อหนังสือ *"; font.bold: true; font.pixelSize: 11; color: "#475569" }
                            StyledTextInput {
                                id: titleInput
                                objectName: "editBookTitleInput"
                                Layout.fillWidth: true
                                selectByMouse: true
                                font.pixelSize: 12
                            }
                        }

                        // Author & ISBN Grid
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3
                                Text { text: "ผู้แต่ง (Author)"; font.bold: true; font.pixelSize: 11; color: "#475569" }
                                StyledTextInput {
                                    id: authorInput
                                    objectName: "editBookAuthorInput"
                                    Layout.fillWidth: true
                                    selectByMouse: true
                                    font.pixelSize: 12
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3
                                Text { text: "ISBN"; font.bold: true; font.pixelSize: 11; color: "#475569" }
                                StyledTextInput {
                                    id: isbnInput
                                    objectName: "editBookIsbnInput"
                                    Layout.fillWidth: true
                                    selectByMouse: true
                                    font.pixelSize: 12
                                }
                            }
                        }

                        // Category & Shelf Grid
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3
                                Text { text: "หมวดหมู่"; font.bold: true; font.pixelSize: 11; color: "#475569" }
                                StyledComboBox {
                                    id: categoryCombo
                                    objectName: "editBookCategoryCombo"
                                    Layout.fillWidth: true
                                    textRole: "name"
                                    model: ListModel { id: categoryModel }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3
                                Text { text: "ตำแหน่งชั้นวาง"; font.bold: true; font.pixelSize: 11; color: "#475569" }
                                StyledTextInput {
                                    id: shelfInput
                                    objectName: "editBookShelfInput"
                                    Layout.fillWidth: true
                                    selectByMouse: true
                                    font.pixelSize: 12
                                }
                            }
                        }
                    }
                }

                // Section 2: Inventory & Copy Correction Card
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: copyCol.implicitHeight + 20
                    color: "#ffffff"
                    radius: 8
                    border.color: "#38bdf8"
                    border.width: 1.5

                    ColumnLayout {
                        id: copyCol
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "📦 ปรับแก้จำนวนเล่มในคลัง (กรณีใส่ผิดพลาด)"
                                font.bold: true
                                font.pixelSize: 12
                                color: "#0369a1"
                            }
                            Item { Layout.fillWidth: true }
                            // Status pills
                            RowLayout {
                                spacing: 6
                                Rectangle {
                                    height: 18; width: availText.contentWidth + 10; radius: 4
                                    color: "#dcfce7"; border.color: "#86efac"
                                    Text { id: availText; anchors.centerIn: parent; text: "พร้อมยืม: " + editDialog.availableCopies; font.pixelSize: 9; font.bold: true; color: "#166534" }
                                }
                                Rectangle {
                                    height: 18; width: loanText.contentWidth + 10; radius: 4
                                    color: "#e0f2fe"; border.color: "#7dd3fc"
                                    Text { id: loanText; anchors.centerIn: parent; text: "กำลังยืม: " + editDialog.onLoanCopies; font.pixelSize: 9; font.bold: true; color: "#0369a1" }
                                }
                            }
                        }

                        // Copy Adjustment Stepper & Quick-buttons
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            Text {
                                text: "จำนวนเล่มที่ถูกต้อง:"
                                font.bold: true
                                font.pixelSize: 11
                                color: "#334155"
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6

                                StyledButton {
                                    variant: StyledButton.Neutral
                                    text: "−"
                                    Layout.preferredWidth: Math.max(32, Math.round(font.pixelSize * 2.2))
                                    Layout.preferredHeight: Math.max(32, Math.round(font.pixelSize * 2.0))
                                    font.bold: true
                                    font.pixelSize: 14
                                    onClicked: editDialog.stepCopies(-1)
                                }

                                StyledTextInput {
                                    id: copiesInput
                                    objectName: "editBookCopiesInput"
                                    Layout.preferredWidth: Math.max(64, Math.round(font.pixelSize * 4.0))
                                    Layout.preferredHeight: Math.max(38, Math.round(((font.pixelSize > 0 ? font.pixelSize : 13)) * 2.2))
                                    text: "1"
                                    horizontalAlignment: Text.AlignHCenter
                                    font.bold: true
                                    font.pixelSize: 13
                                    validator: IntValidator { bottom: 1; top: 99 }
                                    selectByMouse: true
                                    background: Rectangle {
                                        implicitHeight: parent.implicitHeight
                                        border.color: editDialog.isBelowOnLoan() ? "#ef4444" : (parent.activeFocus ? "#2563eb" : "#cbd5e1")
                                        border.width: editDialog.isBelowOnLoan() ? 2 : 1
                                        radius: 6
                                        color: "#ffffff"
                                    }
                                }

                                StyledButton {
                                    variant: StyledButton.Neutral
                                    text: "+"
                                    Layout.preferredWidth: Math.max(32, Math.round(font.pixelSize * 2.2))
                                    Layout.preferredHeight: Math.max(32, Math.round(font.pixelSize * 2.0))
                                    font.bold: true
                                    font.pixelSize: 14
                                    onClicked: editDialog.stepCopies(1)
                                }

                                Item { Layout.preferredWidth: 6 }

                                StyledButton {
                                    variant: StyledButton.Neutral
                                    text: "+1"
                                    Layout.preferredWidth: Math.max(36, Math.round(font.pixelSize * 2.4))
                                    Layout.preferredHeight: Math.max(28, Math.round(font.pixelSize * 1.8))
                                    font.pixelSize: 10
                                    onClicked: editDialog.stepCopies(1)
                                }
                                StyledButton {
                                    variant: StyledButton.Neutral
                                    text: "+5"
                                    Layout.preferredWidth: Math.max(36, Math.round(font.pixelSize * 2.4))
                                    Layout.preferredHeight: Math.max(28, Math.round(font.pixelSize * 1.8))
                                    font.pixelSize: 10
                                    onClicked: editDialog.stepCopies(5)
                                }
                                StyledButton {
                                    variant: StyledButton.Neutral
                                    text: "-1"
                                    Layout.preferredWidth: Math.max(36, Math.round(font.pixelSize * 2.4))
                                    Layout.preferredHeight: Math.max(28, Math.round(font.pixelSize * 1.8))
                                    font.pixelSize: 10
                                    enabled: (parseInt(copiesInput.text) || 1) > 1
                                    onClicked: editDialog.stepCopies(-1)
                                }

                                Item { Layout.fillWidth: true }
                            }
                        }

                        // Live Action Feedback Banner
                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: Math.max(34, bannerRow.implicitHeight + 12)
                            radius: 6
                            color: {
                                if (editDialog.isBelowOnLoan()) return "#fee2e2"
                                var d = editDialog.calculateDiff()
                                if (d > 0) return "#f0fdf4"
                                if (d < 0) return "#fffbeb"
                                return "#f1f5f9"
                            }
                            border.color: {
                                if (editDialog.isBelowOnLoan()) return "#fca5a5"
                                var d = editDialog.calculateDiff()
                                if (d > 0) return "#bbf7d0"
                                if (d < 0) return "#fde68a"
                                return "#cbd5e1"
                            }

                            RowLayout {
                                id: bannerRow
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                spacing: 6
                                Text {
                                    text: {
                                        if (editDialog.isBelowOnLoan()) return "⛔"
                                        var d = editDialog.calculateDiff()
                                        if (d > 0) return "📈"
                                        if (d < 0) return "⚠️"
                                        return "ℹ️"
                                    }
                                    font.pixelSize: 11
                                }
                                Text {
                                    Layout.fillWidth: true
                                    font.pixelSize: 10
                                    font.bold: true
                                    wrapMode: Text.Wrap
                                    color: {
                                        if (editDialog.isBelowOnLoan()) return "#991b1b"
                                        var d = editDialog.calculateDiff()
                                        if (d > 0) return "#166534"
                                        if (d < 0) return "#92400e"
                                        return "#475569"
                                    }
                                    text: {
                                        if (editDialog.isBelowOnLoan()) {
                                            return "ไม่สามารถลดต่ำกว่า " + editDialog.minAllowedCopies + " เล่มได้ เนื่องจากติดการยืมหรือมีประวัติการยืมแล้ว"
                                        }
                                        var d = editDialog.calculateDiff()
                                        if (d > 0) {
                                            return "เพิ่ม " + d + " เล่ม: ระบบจะสร้างรหัสบาร์โค้ดใหม่ต่อท้ายให้อัตโนมัติ"
                                        } else if (d < 0) {
                                            return "ลด " + Math.abs(d) + " เล่ม (แก้ไขกรอกผิด): ระบบจะลบบาร์โค้ดเล่มว่างล่าสุดออกจากระบบอย่างปลอดภัย"
                                        }
                                        return "จำนวนเล่มคงเดิม (" + editDialog.currentTotalCopies + " เล่ม)"
                                    }
                                }
                            }
                        }

                        // Barcode Tray Preview
                        Text {
                            text: "บาร์โค้ดประจำเล่มในระบบตอนนี้:"
                            font.bold: true
                            font.pixelSize: 10
                            color: "#64748b"
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: 6
                            Repeater {
                                model: ListModel { id: copiesListModel }
                                delegate: Rectangle {
                                    height: 24
                                    width: bcRow.width + 10
                                    radius: 4
                                    property bool willBeRemoved: {
                                        var d = editDialog.calculateDiff()
                                        if (d >= 0) return false
                                        return model.remove_rank > 0 && model.remove_rank <= Math.abs(d)
                                    }
                                    color: willBeRemoved ? "#fee2e2" : (model.status === "available" ? "#f1f5f9" : "#e0f2fe")
                                    border.color: willBeRemoved ? "#ef4444" : (model.status === "available" ? "#cbd5e1" : "#7dd3fc")

                                    RowLayout {
                                        id: bcRow
                                        anchors.centerIn: parent
                                        spacing: 4
                                        Text {
                                            text: model.barcode
                                            font.pixelSize: 10
                                            font.family: "monospace"
                                            font.strikeout: willBeRemoved
                                            color: willBeRemoved ? "#b91c1c" : (model.status === "available" ? "#0f766e" : "#0369a1")
                                        }
                                        Text {
                                            text: willBeRemoved ? "ลบ" : (model.status === "available" ? "ว่าง" : "ยืม")
                                            font.pixelSize: 8
                                            font.bold: true
                                            color: willBeRemoved ? "#991b1b" : "#64748b"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Error / Status Text
                Text {
                    id: statusText
                    objectName: "editBookStatusText"
                    Layout.fillWidth: true
                    text: ""
                    font.pixelSize: 11
                    font.bold: true
                    wrapMode: Text.Wrap
                    color: text.indexOf("✗") !== -1 ? "#ef4444" : "#10b981"
                    visible: text !== ""
                }

                Item { height: 4 }
            }
        }

        // Dialog Footer Actions
        Rectangle {
            Layout.fillWidth: true
            height: 52
            color: "#f8fafc"
            border.color: "#e2e8f0"
            radius: 12
            Rectangle {
                anchors.top: parent.top
                width: parent.width
                height: 12
                color: "#f8fafc"
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 10

                Item { Layout.fillWidth: true }

                StyledButton {
                    variant: StyledButton.Neutral
                    text: "ยกเลิก"
                    Layout.preferredWidth: Math.max(90, implicitWidth)
                    implicitHeight: Math.max(36, Math.round(contentItem.implicitHeight + 12))
                    onClicked: editDialog.close()
                }

                StyledButton {
                    variant: StyledButton.Primary
                    
                    text: "💾 บันทึกข้อมูลและปรับปรุงจำนวน"
                    highlighted: true
                    Layout.preferredWidth: Math.max(220, implicitWidth)
                    implicitHeight: Math.max(36, Math.round(contentItem.implicitHeight + 12))
                    font.bold: true
                    enabled: !editDialog.isBelowOnLoan()
                    onClicked: {
                        if (editDialog.rootWindow) {
                            editDialog.rootWindow.submitEditBook()
                        } else {
                            editDialog.saved()
                        }
                    }
                }
            }
        }
    }
}
