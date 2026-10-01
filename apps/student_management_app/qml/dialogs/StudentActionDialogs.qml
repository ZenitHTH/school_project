import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent

    property var rootWindow: null

    property alias roomDialog: roomDialog
    property alias newRoomInput: newRoomInput
    property alias roomReasonInput: roomReasonInput

    property alias statusDialog: statusDialog
    property alias statusCombo: statusCombo
    property alias statusReasonInput: statusReasonInput

    property alias nameDialog: nameDialog
    property alias editPrefixInput: editPrefixInput
    property alias editFirstNameInput: editFirstNameInput
    property alias editLastNameInput: editLastNameInput
    property alias nameReasonInput: nameReasonInput

    property alias idDialog: idDialog
    property alias newIdInput: newIdInput
    property alias idReasonInput: idReasonInput

    property alias confirmImportDialog: confirmImportDialog
    property alias confirmImportMsg: confirmImportMsg
    property alias diffNewText: diffNewText
    property alias diffPromoteText: diffPromoteText
    property alias diffMissingText: diffMissingText
    property alias diffConflictText: diffConflictText
    property alias diffYearInput: diffYearInput
    property alias diffSemInput: diffSemInput

    function openRoomDialog() {
        newRoomInput.text = ""
        roomReasonInput.text = ""
        roomDialog.open()
    }

    function openStatusDialog() {
        statusReasonInput.text = ""
        statusDialog.open()
    }

    function openNameDialog() {
        if (rootWindow && rootWindow.selectedStudent) {
            editPrefixInput.text = rootWindow.selectedStudent.prefix || ""
            editFirstNameInput.text = rootWindow.selectedStudent.first_name || ""
            editLastNameInput.text = rootWindow.selectedStudent.last_name || ""
        } else {
            editPrefixInput.text = ""
            editFirstNameInput.text = ""
            editLastNameInput.text = ""
        }
        nameReasonInput.text = ""
        nameDialog.open()
    }

    function openIdDialog() {
        newIdInput.text = ""
        idReasonInput.text = ""
        idDialog.open()
    }

    function showConfirmImport(warning, newCount, promoCount, missingCount, conflictCount, detectedYear, detectedSem) {
        if (warning) confirmImportMsg.text = warning
        diffNewText.text = "• นักเรียนใหม่: " + (newCount !== undefined ? newCount : 0) + " คน"
        diffPromoteText.text = "• นักเรียนที่เลื่อนชั้น/เปลี่ยนห้อง: " + (promoCount !== undefined ? promoCount : 0) + " คน"
        diffMissingText.text = "• นักเรียนที่ไม่มีในไฟล์ใหม่: " + (missingCount !== undefined ? missingCount : 0) + " คน (คงสถานะเดิม ไม่ลบ)"
        diffConflictText.text = "• รายชื่อที่สะกดต่างจากเดิม: " + (conflictCount !== undefined ? conflictCount : 0) + " คน"
        if (detectedYear) {
            var detYr = detectedYear
            if (detYr < 2400) detYr += 543
            diffYearInput.text = detYr.toString()
        }
        if (detectedSem) {
            diffSemInput.text = detectedSem.toString()
        }
        confirmImportDialog.open()
    }

    // 1. Room Dialog
    Dialog {
        id: roomDialog
        objectName: "roomDialog"
        title: "เปลี่ยนห้องเรียน"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: parent
        closePolicy: Popup.CloseOnEscape

        ColumnLayout {
            spacing: 10
            Label { text: "เลขห้องใหม่:" }
            TextField {
                id: newRoomInput
                objectName: "newRoomInput"
                placeholderText: "เช่น 2 หรือ 3"
                inputMethodHints: Qt.ImhDigitsOnly
            }
            Label { text: "เหตุผล:" }
            TextField {
                id: roomReasonInput
                objectName: "roomReasonInput"
                placeholderText: "ปรับสมดุลชั้นเรียน..."
            }
        }

        onAccepted: {
            if (rootWindow && rootWindow.selectedStudent && newRoomInput.text) {
                var res = JSON.parse(studentAdmin.changeClassroom(
                    rootWindow.selectedStudent.student_id, parseInt(newRoomInput.text), roomReasonInput.text, "Admin"))
                if (rootWindow.actionFeedback) {
                    rootWindow.actionFeedback.isError = !res.ok
                    rootWindow.actionFeedback.text = res.ok
                        ? ("✓ ย้ายห้องสำเร็จ: " + rootWindow.selectedStudent.full_name + " → ห้อง " + newRoomInput.text)
                        : ("✗ " + res.error)
                }
                if (res.ok) {
                    rootWindow.loadStudentDetail(rootWindow.selectedStudent.student_id)
                    rootWindow.doSearch()
                }
            }
        }
    }

    // 2. Status Dialog
    Dialog {
        id: statusDialog
        objectName: "statusDialog"
        title: "เปลี่ยนสถานะนักเรียน"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: parent
        closePolicy: Popup.CloseOnEscape

        ColumnLayout {
            spacing: 10
            Label { text: "สถานะใหม่:" }
            ComboBox {
                id: statusCombo
                objectName: "statusCombo"
                model: ["active", "on_leave", "transferred_out"]
            }
            Label { text: "เหตุผล:" }
            TextField {
                id: statusReasonInput
                objectName: "statusReasonInput"
                placeholderText: "เหตุผล"
            }
        }

        onAccepted: {
            if (rootWindow && rootWindow.selectedStudent) {
                var res = JSON.parse(studentAdmin.updateStatus(
                    rootWindow.selectedStudent.student_id, statusCombo.currentText, statusReasonInput.text, "Admin"))
                if (rootWindow.actionFeedback) {
                    rootWindow.actionFeedback.isError = !res.ok
                    rootWindow.actionFeedback.text = res.ok
                        ? ("✓ เปลี่ยนสถานะเป็น '" + statusCombo.currentText + "' สำเร็จ")
                        : ("✗ " + res.error)
                }
                if (res.ok) {
                    rootWindow.loadStudentDetail(rootWindow.selectedStudent.student_id)
                    rootWindow.doSearch()
                }
            }
        }
    }

    // 3. Name Dialog
    Dialog {
        id: nameDialog
        objectName: "nameDialog"
        title: "แก้ไขชื่อ-นามสกุล"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: parent
        closePolicy: Popup.CloseOnEscape

        ColumnLayout {
            spacing: 10
            Label { text: "คำนำหน้า:" }
            TextField {
                id: editPrefixInput
                objectName: "editPrefixInput"
                placeholderText: "เช่น เด็กชาย, นาย, นางสาว"
            }
            Label { text: "ชื่อ:*" }
            TextField {
                id: editFirstNameInput
                objectName: "editFirstNameInput"
                placeholderText: "ชื่อ"
            }
            Label { text: "นามสกุล:*" }
            TextField {
                id: editLastNameInput
                objectName: "editLastNameInput"
                placeholderText: "นามสกุล"
            }
            Label { text: "เหตุผล:" }
            TextField {
                id: nameReasonInput
                objectName: "nameReasonInput"
                placeholderText: "แก้ไขการสะกด..."
            }
        }

        onAccepted: {
            if (rootWindow && rootWindow.selectedStudent && editFirstNameInput.text && editLastNameInput.text) {
                var res = JSON.parse(studentAdmin.updateName(
                    rootWindow.selectedStudent.student_id,
                    editPrefixInput.text,
                    editFirstNameInput.text,
                    editLastNameInput.text,
                    nameReasonInput.text,
                    "Admin"))
                if (rootWindow.actionFeedback) {
                    rootWindow.actionFeedback.isError = !res.ok
                    rootWindow.actionFeedback.text = res.ok
                        ? ("✓ แก้ไขชื่อสำเร็จ: " + editPrefixInput.text + editFirstNameInput.text + " " + editLastNameInput.text)
                        : ("✗ " + res.error)
                }
                if (res.ok) {
                    rootWindow.loadStudentDetail(rootWindow.selectedStudent.student_id)
                    rootWindow.doSearch()
                }
            }
        }
    }

    // 4. ID Dialog
    Dialog {
        id: idDialog
        objectName: "idDialog"
        title: "เปลี่ยนรหัสนักเรียน (Renumber ID)"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: parent
        closePolicy: Popup.CloseOnEscape

        ColumnLayout {
            spacing: 10
            Label { text: "รหัสนักเรียนใหม่:*" }
            TextField {
                id: newIdInput
                objectName: "newIdInput"
                placeholderText: "รหัสใหม่"
                inputMethodHints: Qt.ImhDigitsOnly
            }
            Label { text: "เหตุผล:" }
            TextField {
                id: idReasonInput
                objectName: "idReasonInput"
                placeholderText: "แก้ไขข้อผิดพลาด..."
            }
        }

        onAccepted: {
            if (rootWindow && rootWindow.selectedStudent && newIdInput.text) {
                var newId = parseInt(newIdInput.text)
                var res = JSON.parse(studentAdmin.changeStudentID(
                    rootWindow.selectedStudent.student_id, newId, idReasonInput.text, "Admin"))
                if (rootWindow.actionFeedback) {
                    rootWindow.actionFeedback.isError = !res.ok
                    rootWindow.actionFeedback.text = res.ok
                        ? ("✓ เปลี่ยนรหัสสำเร็จ: " + rootWindow.selectedStudent.student_id + " → " + newIdInput.text)
                        : ("✗ " + res.error)
                }
                if (res.ok) {
                    rootWindow.loadStudentDetail(newId)
                    rootWindow.doSearch()
                }
            }
        }
    }

    // 5. Confirm Import Dialog
    Dialog {
        id: confirmImportDialog
        objectName: "confirmImportDialog"
        title: "ตรวจสอบการเปรียบเทียบข้อมูลและการเลื่อนชั้น (Diff Preview)"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        width: Math.min(520, rootWindow ? rootWindow.width - 40 : 500)
        anchors.centerIn: parent
        closePolicy: Popup.CloseOnEscape

        ColumnLayout {
            spacing: 12
            Text {
                id: confirmImportMsg
                text: "พบข้อมูลในระบบ ระบบจะทำการเลื่อนชั้นและเพิ่มนักเรียนใหม่โดยไม่ลบประวัติเดิม:"
                wrapMode: Text.Wrap
                Layout.fillWidth: true
                font.bold: true
            }
            Rectangle {
                Layout.fillWidth: true
                height: 120
                color: "#f8fafc"
                border.color: "#cbd5e1"
                radius: 6
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 6
                    Text { id: diffNewText; text: "• นักเรียนใหม่: 0 คน"; color: "#059669"; font.bold: true }
                    Text { id: diffPromoteText; text: "• นักเรียนที่เลื่อนชั้น/เปลี่ยนห้อง: 0 คน"; color: "#0284c7"; font.bold: true }
                    Text { id: diffMissingText; text: "• นักเรียนที่ไม่มีในไฟล์ใหม่: 0 คน (คงสถานะเดิม)"; color: "#64748b" }
                    Text { id: diffConflictText; text: "• รายชื่อที่สะกดต่างจากเดิม: 0 คน"; color: "#d97706" }
                }
            }
            RowLayout {
                spacing: 8
                Text { text: "ปีการศึกษา:" }
                TextField { id: diffYearInput; text: "2568"; Layout.preferredWidth: 80 }
                Text { text: "ภาคเรียน:" }
                TextField { id: diffSemInput; text: "1"; Layout.preferredWidth: 60 }
            }
        }

        onAccepted: {
            var yr = parseInt(diffYearInput.text) || 2568
            var sem = parseInt(diffSemInput.text) || 1
            var res = JSON.parse(studentAdmin.applyXlsxDiff(rootWindow.selectedXlsxPath, yr, sem, "Admin"))
            if (res.ok) {
                if (rootWindow.importStatusText) {
                    rootWindow.importStatusText.text = "นำเข้าและเลื่อนชั้นสำเร็จ!\n" +
                        "นักเรียนใหม่: " + res.data.new_added + " คน\n" +
                        "เลื่อนชั้นเรียน: " + res.data.promoted + " คน"
                }
                rootWindow.doSearch()
            } else {
                if (rootWindow.importStatusText) {
                    rootWindow.importStatusText.text = "เกิดข้อผิดพลาด: " + res.error
                }
            }
        }
    }
}
