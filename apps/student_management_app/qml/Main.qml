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
    title: "ระบบจัดการข้อมูลนักเรียน (Student Management)"
    color: "#f5f6f8"

    property var selectedStudent: null
    property string selectedXlsxPath: ""

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Sidebar Navigation
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 240
            color: "#1e293b"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Text {
                    text: "🎓 งานทะเบียนนักเรียน"
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

                Repeater {
                    model: [
                        { text: "🔍 ค้นหานักเรียน", index: 0 },
                        { text: "👤 ข้อมูลนักเรียน / แก้ไข", index: 1 },
                        { text: "📈 เลื่อนชั้นประจำปี", index: 2 },
                        { text: "📤 ส่งออกข้อมูล (LINE Sync)", index: 3 },
                        { text: "📜 ประวัติกิจกรรม (Audit Log)", index: 4 },
                        { text: "📥 นำเข้าไฟล์ Excel (.xlsx)", index: 5 }
                    ]
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        height: 42
                        radius: 8
                        color: stackLayout.currentIndex === modelData.index ? "#2563eb" : (sideMouse.containsMouse ? "#1e293b" : "transparent")

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            Text {
                                text: modelData.text
                                color: stackLayout.currentIndex === modelData.index ? "#ffffff" : "#cbd5e1"
                                font.pixelSize: 14
                                font.bold: stackLayout.currentIndex === modelData.index
                                Layout.fillWidth: true
                            }
                        }

                        MouseArea {
                            id: sideMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (modelData.index === 4) loadLogs()
                                stackLayout.currentIndex = modelData.index
                            }
                        }
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
                    text: "สถานะ: เชื่อมต่อฐานข้อมูลแล้ว"
                    color: "#94a3b8"
                    font.pixelSize: 12
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }

        // Content Area
        StackLayout {
            id: stackLayout
            objectName: "mainStack"
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: 0

            // 1. Search Screen
            Rectangle {
                color: "#ffffff"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 16

                    Text {
                        text: "ค้นหาและจัดการข้อมูลนักเรียน"
                        font.bold: true
                        font.pixelSize: 22
                        color: "#0f172a"
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        TextField {
                            id: searchInput
                            objectName: "searchInput"
                            placeholderText: "พิมพ์ชื่อ, นามสกุล, เลขประจำตัว หรือเลขประจำตัวประชาชน..."
                            Layout.fillWidth: true
                            font.pixelSize: 14
                            onAccepted: doSearch()
                        }

                        Button {
                            id: searchBtn
                            objectName: "searchButton"
                            text: "🔍 ค้นหา"
                            font.bold: true
                            font.pixelSize: 14
                            contentItem: Text {
                                text: searchBtn.text
                                font: searchBtn.font
                                color: "#ffffff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                implicitWidth: 84
                                implicitHeight: 38
                                color: searchBtn.down ? "#1d4ed8" : (searchBtn.hovered ? "#2563eb" : "#3b82f6")
                                radius: 6
                            }
                            onClicked: doSearch()
                        }
                    }

                    ListView {
                        id: studentList
                        objectName: "studentList"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 6
                        model: ListModel { id: searchResultsModel; objectName: "searchResultsModel" }
                        delegate: Rectangle {
                            id: studentRow
                            width: studentList.width
                            height: 64
                            color: rowMouse.containsMouse ? "#eff6ff" : "#ffffff"
                            border.color: rowMouse.containsMouse ? "#3b82f6" : "#e2e8f0"
                            border.width: rowMouse.containsMouse ? 1.5 : 1
                            radius: 8

                            MouseArea {
                                id: rowMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    loadStudentDetail(model.student_id)
                                    stackLayout.currentIndex = 1
                                }
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 16
                                anchors.rightMargin: 16
                                spacing: 16

                                Text {
                                    text: model.student_id
                                    font.bold: true
                                    font.pixelSize: 15
                                    color: "#2563eb"
                                    Layout.preferredWidth: 70
                                }

                                Text {
                                    text: model.full_name
                                    font.pixelSize: 15
                                    font.bold: true
                                    color: "#0f172a"
                                    Layout.preferredWidth: 220
                                    elide: Text.ElideRight
                                }

                                Text {
                                    text: (model.grade_level || "-") + "/" + (model.room || "-")
                                    font.pixelSize: 14
                                    color: "#475569"
                                    Layout.preferredWidth: 70
                                }

                                Rectangle {
                                    Layout.preferredWidth: 90
                                    height: 28
                                    radius: 14
                                    color: model.status === "active" ? "#dcfce7" : (model.status === "on_leave" ? "#fef9c3" : "#fee2e2")
                                    Text {
                                        anchors.centerIn: parent
                                        text: model.status === "active" ? "ปกติ" : (model.status === "on_leave" ? "พักการเรียน" : "จำหน่าย")
                                        color: model.status === "active" ? "#166534" : (model.status === "on_leave" ? "#854d0e" : "#991b1b")
                                        font.pixelSize: 12
                                        font.bold: true
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                Button {
                                    id: rowDetailBtn
                                    objectName: "btnViewDetail"
                                    text: "👁️ ดูรายละเอียด"
                                    font.bold: true
                                    font.pixelSize: 13
                                    contentItem: Text {
                                        text: rowDetailBtn.text
                                        font: rowDetailBtn.font
                                        color: "#ffffff"
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                    background: Rectangle {
                                        implicitWidth: 124
                                        implicitHeight: 34
                                        color: rowDetailBtn.down ? "#1d4ed8" : (rowDetailBtn.hovered ? "#2563eb" : "#3b82f6")
                                        radius: 6
                                    }
                                    onClicked: {
                                        loadStudentDetail(model.student_id)
                                        stackLayout.currentIndex = 1
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // 2. Student Detail & Actions Screen
            Rectangle {
                color: "#ffffff"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 16

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "ข้อมูลนักเรียนรายบุคคลและการจัดการ"
                            font.bold: true
                            font.pixelSize: 22
                            color: "#0f172a"
                        }
                        Item { Layout.fillWidth: true }
                        Button {
                            id: btnBackToSearch
                            text: "← กลับไปค้นหานักเรียน"
                            font.pixelSize: 13
                            contentItem: Text {
                                text: btnBackToSearch.text
                                color: "#334155"
                                font.bold: true
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                implicitWidth: 160
                                implicitHeight: 36
                                color: btnBackToSearch.down ? "#e2e8f0" : (btnBackToSearch.hovered ? "#f1f5f9" : "#ffffff")
                                border.color: "#cbd5e1"
                                radius: 6
                            }
                            onClicked: stackLayout.currentIndex = 0
                        }
                    }

                    // Empty state — shown when no student is selected
                    Rectangle {
                        Layout.fillWidth: true
                        height: 180
                        color: "#f8fafc"
                        border.color: "#cbd5e1"
                        radius: 10
                        visible: window.selectedStudent === null

                        ColumnLayout {
                            anchors.centerIn: parent
                            spacing: 14

                            Text {
                                text: "🔍 ยังไม่ได้เลือกข้อมูลนักเรียน"
                                font.bold: true
                                font.pixelSize: 18
                                color: "#1e293b"
                                Layout.alignment: Qt.AlignHCenter
                            }
                            Text {
                                text: "ท่านสามารถไปที่หน้าค้นหาแล้วกดปุ่ม 'ดูรายละเอียด' หรือพิมพ์รหัส/ชื่อนักเรียนด้านล่างนี้ได้เลย:"
                                color: "#64748b"
                                font.pixelSize: 14
                                Layout.alignment: Qt.AlignHCenter
                            }
                            RowLayout {
                                spacing: 10
                                Layout.alignment: Qt.AlignHCenter
                                TextField {
                                    id: directIdInput
                                    placeholderText: "พิมพ์รหัสนักเรียน หรือชื่อ..."
                                    font.pixelSize: 14
                                    Layout.preferredWidth: 260
                                    onAccepted: {
                                        if (directIdInput.text) {
                                            var res = JSON.parse(studentAdmin.searchStudents(directIdInput.text))
                                            if (res.length > 0) {
                                                loadStudentDetail(res[0].student_id)
                                            }
                                        }
                                    }
                                }
                                Button {
                                    id: btnDirectOpen
                                    text: "เปิดดูข้อมูล"
                                    font.bold: true
                                    font.pixelSize: 13
                                    contentItem: Text {
                                        text: btnDirectOpen.text
                                        font: btnDirectOpen.font
                                        color: "#ffffff"
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                    background: Rectangle {
                                        implicitWidth: 110
                                        implicitHeight: 38
                                        color: btnDirectOpen.down ? "#1d4ed8" : (btnDirectOpen.hovered ? "#2563eb" : "#3b82f6")
                                        radius: 6
                                    }
                                    onClicked: {
                                        if (directIdInput.text) {
                                            var res = JSON.parse(studentAdmin.searchStudents(directIdInput.text))
                                            if (res.length > 0) {
                                                loadStudentDetail(res[0].student_id)
                                            }
                                        }
                                    }
                                }
                                Button {
                                    id: btnGoSearch
                                    text: "🔍 ไปที่หน้ารายการค้นหา"
                                    font.pixelSize: 13
                                    contentItem: Text {
                                        text: btnGoSearch.text
                                        color: "#2563eb"
                                        font.bold: true
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                    background: Rectangle {
                                        implicitWidth: 170
                                        implicitHeight: 38
                                        color: btnGoSearch.down ? "#dbeafe" : (btnGoSearch.hovered ? "#eff6ff" : "#ffffff")
                                        border.color: "#93c5fd"
                                        radius: 6
                                    }
                                    onClicked: stackLayout.currentIndex = 0
                                }
                            }
                        }
                    }

                    // Student info card — shown when a student is selected
                    Rectangle {
                        Layout.fillWidth: true
                        height: 140
                        color: "#ffffff"
                        border.color: "#e2e8f0"
                        radius: 10
                        visible: window.selectedStudent !== null

                        Rectangle {
                            width: 6
                            height: parent.height
                            color: "#2563eb"
                            radius: 3
                            anchors.left: parent.left
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 24
                            anchors.rightMargin: 20
                            anchors.topMargin: 16
                            anchors.bottomMargin: 16
                            spacing: 8

                            RowLayout {
                                spacing: 12
                                Text {
                                    id: detailName
                                    text: window.selectedStudent ? window.selectedStudent.full_name : ""
                                    font.bold: true
                                    font.pixelSize: 22
                                    color: "#0f172a"
                                }
                                Rectangle {
                                    height: 26
                                    radius: 13
                                    Layout.preferredWidth: 80
                                    color: window.selectedStudent && window.selectedStudent.status === "active" ? "#dcfce7" : (window.selectedStudent && window.selectedStudent.status === "on_leave" ? "#fef9c3" : "#fee2e2")
                                    Text {
                                        anchors.centerIn: parent
                                        text: window.selectedStudent ? (window.selectedStudent.status === "active" ? "ปกติ" : (window.selectedStudent.status === "on_leave" ? "พักการเรียน" : "จำหน่าย")) : ""
                                        color: window.selectedStudent && window.selectedStudent.status === "active" ? "#166534" : (window.selectedStudent && window.selectedStudent.status === "on_leave" ? "#854d0e" : "#991b1b")
                                        font.pixelSize: 12
                                        font.bold: true
                                    }
                                }
                            }

                            RowLayout {
                                spacing: 20
                                Text {
                                    id: detailSub
                                    text: window.selectedStudent
                                        ? ("รหัสประจำตัว: " + window.selectedStudent.student_id
                                           + "   |   ระดับชั้น: " + (window.selectedStudent.grade_level || "-")
                                           + "/" + (window.selectedStudent.room || "-")
                                           + "   |   แผนการเรียน: " + (window.selectedStudent.track || "-"))
                                        : ""
                                    color: "#475569"
                                    font.pixelSize: 14
                                }
                            }

                            Text {
                                text: window.selectedStudent
                                    ? ("เลขประจำตัวประชาชน: " + (window.selectedStudent.national_id || "ไม่มีข้อมูล"))
                                    : ""
                                color: "#94a3b8"
                                font.pixelSize: 13
                            }
                        }
                    }

                    Text {
                        text: "การดำเนินการทางทะเบียน (คลิกปุ่มเพื่อดำเนินการ):"
                        font.bold: true
                        font.pixelSize: 16
                        color: "#334155"
                        visible: window.selectedStudent !== null
                    }

                    // Action buttons row
                    Flow {
                        Layout.fillWidth: true
                        spacing: 12
                        visible: window.selectedStudent !== null

                        Button {
                            id: btnRoom
                            objectName: "btnChangeRoom"
                            text: "🏫 เปลี่ยนห้องเรียน"
                            font.bold: true
                            font.pixelSize: 14
                            enabled: window.selectedStudent !== null
                            contentItem: Text {
                                text: btnRoom.text
                                font: btnRoom.font
                                color: "#ffffff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                implicitWidth: 160
                                implicitHeight: 42
                                color: btnRoom.down ? "#1d4ed8" : (btnRoom.hovered ? "#2563eb" : "#3b82f6")
                                radius: 8
                            }
                            onClicked: {
                                newRoomInput.text = ""
                                roomReasonInput.text = ""
                                roomDialog.open()
                            }
                        }

                        Button {
                            id: btnStatus
                            objectName: "btnChangeStatus"
                            text: "📋 เปลี่ยนสถานะ"
                            font.bold: true
                            font.pixelSize: 14
                            enabled: window.selectedStudent !== null
                            contentItem: Text {
                                text: btnStatus.text
                                font: btnStatus.font
                                color: "#ffffff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                implicitWidth: 150
                                implicitHeight: 42
                                color: btnStatus.down ? "#b45309" : (btnStatus.hovered ? "#d97706" : "#f59e0b")
                                radius: 8
                            }
                            onClicked: {
                                statusReasonInput.text = ""
                                statusDialog.open()
                            }
                        }

                        Button {
                            id: btnName
                            objectName: "btnEditName"
                            text: "✏️ แก้ไขชื่อ-นามสกุล"
                            font.bold: true
                            font.pixelSize: 14
                            enabled: window.selectedStudent !== null
                            contentItem: Text {
                                text: btnName.text
                                font: btnName.font
                                color: "#ffffff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                implicitWidth: 170
                                implicitHeight: 42
                                color: btnName.down ? "#047857" : (btnName.hovered ? "#059669" : "#10b981")
                                radius: 8
                            }
                            onClicked: {
                                editPrefixInput.text = window.selectedStudent ? (window.selectedStudent.prefix || "") : ""
                                editFirstNameInput.text = window.selectedStudent ? (window.selectedStudent.first_name || "") : ""
                                editLastNameInput.text = window.selectedStudent ? (window.selectedStudent.last_name || "") : ""
                                nameReasonInput.text = ""
                                nameDialog.open()
                            }
                        }

                        Button {
                            id: btnId
                            objectName: "btnChangeId"
                            text: "🔢 เปลี่ยนรหัสนักเรียน"
                            font.bold: true
                            font.pixelSize: 14
                            enabled: window.selectedStudent !== null
                            contentItem: Text {
                                text: btnId.text
                                font: btnId.font
                                color: "#ffffff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                implicitWidth: 175
                                implicitHeight: 42
                                color: btnId.down ? "#6d28d9" : (btnId.hovered ? "#7c3aed" : "#8b5cf6")
                                radius: 8
                            }
                            onClicked: {
                                newIdInput.text = ""
                                idReasonInput.text = ""
                                idDialog.open()
                            }
                        }
                    }

                    // Action result feedback
                    Rectangle {
                        Layout.fillWidth: true
                        height: actionFeedback.text ? 44 : 0
                        color: actionFeedback.isError ? "#fee2e2" : "#dcfce7"
                        radius: 6
                        visible: actionFeedback.text !== ""
                        Text {
                            id: actionFeedback
                            objectName: "actionFeedback"
                            property bool isError: false
                            anchors.centerIn: parent
                            text: ""
                            color: isError ? "#991b1b" : "#166534"
                            font.pixelSize: 14
                            font.bold: true
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }


            // 3. Bulk Promotion Screen
            Rectangle {
                color: "#ffffff"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 16

                    Text {
                        text: "การเลื่อนชั้นเรียนประจำปีการศึกษา (Bulk Promotion)"
                        font.bold: true
                        font.pixelSize: 22
                        color: "#0f172a"
                    }

                    Text {
                        text: "ระบบจะทำการเลื่อนชั้นนักเรียนที่สถานะ 'ปกติ' ทั้งหมดจาก ม.1 -> ม.2, ม.2 -> ม.3 ... ม.5 -> ม.6 และจบการศึกษา ม.6"
                        color: "#475569"
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }

                    Button {
                        objectName: "btnPromote"
                        text: "ยืนยันและดำเนินการเลื่อนชั้น"
                        highlighted: true
                        onClicked: {
                            var res = JSON.parse(studentAdmin.bulkPromote(2567, 1, 2568, 1, "Admin"))
                            promoteResultText.text = res.ok ? ("สำเร็จ: เลื่อนชั้น " + res.data.promoted_count + " คน, สำเร็จการศึกษา " + res.data.graduated_count + " คน") : ("เกิดข้อผิดพลาด: " + res.error)
                        }
                    }

                    Text {
                        id: promoteResultText
                        objectName: "promoteResultText"
                        font.pixelSize: 15
                        color: "#059669"
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // 4. Snapshot Export Screen
            Rectangle {
                color: "#ffffff"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 16

                    Text {
                        text: "ส่งออกข้อมูลนักเรียนเพื่อ Sync กับห้องสมุด (LINE)"
                        font.bold: true
                        font.pixelSize: 22
                    }

                    Text {
                        text: "สร้างไฟล์ snapshot.sqlite เพื่อส่งต่อให้ผู้ดูแลห้องสมุดนำเข้าสู่ระบบ"
                        color: "#64748b"
                    }

                    Button {
                        objectName: "btnExportSnapshot"
                        text: "สร้างไฟล์ Snapshot ทันที"
                        highlighted: true
                        onClicked: {
                            var res = JSON.parse(studentAdmin.exportSnapshot("snapshot.sqlite", "Admin"))
                            exportStatusText.text = res.ok ? ("สร้างไฟล์สำเร็จ: มีนักเรียน " + res.data.student_count + " คน ใน " + res.data.output_path) : ("เกิดข้อผิดพลาด: " + res.error)
                        }
                    }

                    Text {
                        id: exportStatusText
                        objectName: "exportStatusText"
                        font.pixelSize: 15
                        color: "#2563eb"
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // 5. Audit Log Screen
            Rectangle {
                color: "#ffffff"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 16

                    Text {
                        text: "บันทึกประวัติกิจกรรม (Audit Log)"
                        font.bold: true
                        font.pixelSize: 22
                    }

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
                                Text { text: model.logged_at; color: "#64748b"; font.pixelSize: 12; Layout.preferredWidth: 150 }
                                Text { text: model.action; font.bold: true; color: "#1e293b"; Layout.preferredWidth: 160 }
                                Text { text: model.detail; color: "#334155"; Layout.fillWidth: true }
                            }
                        }
                    }
                }
            }

            // 6. Import Excel Screen
            Rectangle {
                color: "#ffffff"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 16

                    Text {
                        text: "นำเข้าข้อมูลทะเบียนนักเรียนจากไฟล์ Excel (.xlsx)"
                        font.bold: true
                        font.pixelSize: 22
                    }

                    Text {
                        text: "คลิกปุ่มเพื่อเลือกไฟล์ Excel บัญชีรายชื่อนักเรียนจากเครื่องคอมพิวเตอร์ (ต้องมีชีต ม.1 - ม.6 ตามโครงสร้างมาตรฐาน)"
                        color: "#64748b"
                    }

                    // File selection component
                    Rectangle {
                        Layout.fillWidth: true
                        height: 100
                        color: "#f8fafc"
                        border.color: window.selectedXlsxPath ? "#3b82f6" : "#cbd5e1"
                        border.width: window.selectedXlsxPath ? 2 : 1
                        radius: 8

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 16

                            Button {
                                objectName: "selectFileButton"
                                text: "📁 เลือกไฟล์ Excel (.xlsx)..."
                                font.pixelSize: 14
                                font.bold: true
                                highlighted: !window.selectedXlsxPath
                                onClicked: excelFileDialog.open()
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4
                                Text {
                                    text: window.selectedXlsxPath ? "ไฟล์ที่เลือกพร้อมนำเข้า:" : "ยังไม่ได้เลือกไฟล์"
                                    color: window.selectedXlsxPath ? "#059669" : "#64748b"
                                    font.bold: true
                                }
                                Text {
                                    objectName: "selectedFilePath"
                                    text: window.selectedXlsxPath ? window.selectedXlsxPath : "กรุณากดปุ่ม 'เลือกไฟล์ Excel' เพื่อเปิดหน้าต่างเลือกไฟล์"
                                    color: "#1e293b"
                                    font.pixelSize: 13
                                    elide: Text.ElideMiddle
                                    Layout.fillWidth: true
                                }
                            }

                            Button {
                                objectName: "importButton"
                                text: "⚡ เริ่มนำเข้าข้อมูลทันที"
                                highlighted: true
                                enabled: window.selectedXlsxPath !== ""
                                onClicked: doImportXlsx(false)
                            }
                        }
                    }

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
                                text: "สถานะการนำเข้า:"
                                font.bold: true
                            }
                            Text {
                                id: importStatusText
                                objectName: "importStatusText"
                                text: "ยังไม่มีการนำเข้า"
                                color: "#334155"
                            }
                        }
                    }
                }
            }
        }
    }

    // Dialogs
    Dialog {
        id: roomDialog
        objectName: "roomDialog"
        title: "เปลี่ยนห้องเรียน"
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: parent
        ColumnLayout {
            spacing: 10
            Label { text: "เลขห้องใหม่:" }
            TextField { id: newRoomInput; objectName: "newRoomInput"; placeholderText: "เช่น 2 หรือ 3"; inputMethodHints: Qt.ImhDigitsOnly }
            Label { text: "เหตุผล:" }
            TextField { id: roomReasonInput; objectName: "roomReasonInput"; placeholderText: "ปรับสมดุลชั้นเรียน..." }
        }
        onAccepted: {
            if (window.selectedStudent && newRoomInput.text) {
                var res = JSON.parse(studentAdmin.changeClassroom(
                    window.selectedStudent.student_id, parseInt(newRoomInput.text), roomReasonInput.text, "Admin"))
                actionFeedback.isError = !res.ok
                actionFeedback.text = res.ok
                    ? ("✓ ย้ายห้องสำเร็จ: " + window.selectedStudent.full_name + " → ห้อง " + newRoomInput.text)
                    : ("✗ " + res.error)
                if (res.ok) {
                    loadStudentDetail(window.selectedStudent.student_id)
                    doSearch()
                }
            }
        }
    }

    Dialog {
        id: statusDialog
        objectName: "statusDialog"
        title: "เปลี่ยนสถานะนักเรียน"
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: parent
        ColumnLayout {
            spacing: 10
            Label { text: "สถานะใหม่:" }
            ComboBox {
                id: statusCombo
                objectName: "statusCombo"
                model: ["active", "on_leave", "transferred_out"]
            }
            Label { text: "เหตุผล:" }
            TextField { id: statusReasonInput; objectName: "statusReasonInput"; placeholderText: "เหตุผล" }
        }
        onAccepted: {
            if (window.selectedStudent) {
                var res = JSON.parse(studentAdmin.updateStatus(
                    window.selectedStudent.student_id, statusCombo.currentText, statusReasonInput.text, "Admin"))
                actionFeedback.isError = !res.ok
                actionFeedback.text = res.ok
                    ? ("✓ เปลี่ยนสถานะเป็น '" + statusCombo.currentText + "' สำเร็จ")
                    : ("✗ " + res.error)
                if (res.ok) {
                    loadStudentDetail(window.selectedStudent.student_id)
                    doSearch()
                }
            }
        }
    }

    Dialog {
        id: nameDialog
        objectName: "nameDialog"
        title: "แก้ไขชื่อ-นามสกุล"
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: parent
        ColumnLayout {
            spacing: 10
            Label { text: "คำนำหน้า:" }
            TextField { id: editPrefixInput; objectName: "editPrefixInput"; placeholderText: "เช่น เด็กชาย, นาย, นางสาว" }
            Label { text: "ชื่อ:*" }
            TextField { id: editFirstNameInput; objectName: "editFirstNameInput"; placeholderText: "ชื่อ" }
            Label { text: "นามสกุล:*" }
            TextField { id: editLastNameInput; objectName: "editLastNameInput"; placeholderText: "นามสกุล" }
            Label { text: "เหตุผล:" }
            TextField { id: nameReasonInput; objectName: "nameReasonInput"; placeholderText: "แก้ไขการสะกด..." }
        }
        onAccepted: {
            if (window.selectedStudent && editFirstNameInput.text && editLastNameInput.text) {
                var res = JSON.parse(studentAdmin.updateName(
                    window.selectedStudent.student_id,
                    editPrefixInput.text,
                    editFirstNameInput.text,
                    editLastNameInput.text,
                    nameReasonInput.text,
                    "Admin"))
                actionFeedback.isError = !res.ok
                actionFeedback.text = res.ok
                    ? ("✓ แก้ไขชื่อสำเร็จ: " + editPrefixInput.text + editFirstNameInput.text + " " + editLastNameInput.text)
                    : ("✗ " + res.error)
                if (res.ok) {
                    loadStudentDetail(window.selectedStudent.student_id)
                    doSearch()
                }
            }
        }
    }

    Dialog {
        id: idDialog
        objectName: "idDialog"
        title: "เปลี่ยนรหัสนักเรียน (Renumber ID)"
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: parent
        ColumnLayout {
            spacing: 10
            Label { text: "รหัสนักเรียนใหม่:*" }
            TextField { id: newIdInput; objectName: "newIdInput"; placeholderText: "รหัสใหม่"; inputMethodHints: Qt.ImhDigitsOnly }
            Label { text: "เหตุผล:" }
            TextField { id: idReasonInput; objectName: "idReasonInput"; placeholderText: "แก้ไขข้อผิดพลาด..." }
        }
        onAccepted: {
            if (window.selectedStudent && newIdInput.text) {
                var newId = parseInt(newIdInput.text)
                var res = JSON.parse(studentAdmin.changeStudentID(
                    window.selectedStudent.student_id, newId, idReasonInput.text, "Admin"))
                actionFeedback.isError = !res.ok
                actionFeedback.text = res.ok
                    ? ("✓ เปลี่ยนรหัสสำเร็จ: " + window.selectedStudent.student_id + " → " + newIdInput.text)
                    : ("✗ " + res.error)
                if (res.ok) {
                    loadStudentDetail(newId)
                    doSearch()
                }
            }
        }
    }

    function loadStudentDetail(studentId) {
        var res = JSON.parse(studentAdmin.getStudent(studentId))
        if (res && res.student_id) {
            window.selectedStudent = res
        }
    }

    function doSearch() {
        searchResultsModel.clear()
        var results = JSON.parse(studentAdmin.searchStudents(searchInput.text))
        for (var i = 0; i < results.length; i++) {
            searchResultsModel.append(results[i])
        }
    }

    FileDialog {
        id: excelFileDialog
        title: "เลือกไฟล์บัญชีรายชื่อนักเรียน (.xlsx)"
        nameFilters: ["Excel files (*.xlsx *.xls)", "All files (*)"]
        onAccepted: {
            var path = selectedFile.toString()
            if (path.indexOf("file://") === 0) {
                path = decodeURIComponent(path.substring(7))
            }
            window.selectedXlsxPath = path
        }
    }

    Dialog {
        id: confirmImportDialog
        title: "⚠️ คำเตือนการนำเข้าข้อมูลซ้ำ (Re-import Warning)"
        standardButtons: Dialog.Yes | Dialog.No
        Text {
            id: confirmImportMsg
            text: ""
            wrapMode: Text.Wrap
            width: 400
        }
        onAccepted: {
            doImportXlsx(true)
        }
    }

    FileDialog {
        id: firstLaunchFileDialog
        objectName: "firstLaunchFileDialog"
        title: "เลือกไฟล์บัญชีรายชื่อนักเรียน (.xlsx)"
        nameFilters: ["Excel files (*.xlsx *.xls)", "All files (*)"]
        onAccepted: {
            var path = selectedFile.toString()
            if (path.indexOf("file://") === 0) {
                path = decodeURIComponent(path.substring(7))
            }
            firstLaunchStatusText.text = "กำลังนำเข้าข้อมูลจาก: " + path + "..."
            var res = JSON.parse(studentAdmin.importXlsx(path, false, "Admin"))
            if (res.need_confirm) {
                firstLaunchDialog.close()
                window.selectedXlsxPath = path
                confirmImportMsg.text = res.warning
                confirmImportDialog.open()
                return
            }
            if (res.ok) {
                firstLaunchStatusText.text = "✓ นำเข้าสำเร็จ " + res.data.students + " คน เรียบร้อยแล้ว"
                actionFeedback.isError = false
                actionFeedback.text = "✓ นำเข้าข้อมูลนักเรียน " + res.data.students + " คน สำเร็จ"
                doSearch()
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
        title: "🎉 เริ่มต้นใช้งานระบบ (First Launch Setup)"
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
                        text: "🏫"
                        font.pixelSize: 32
                    }
                    ColumnLayout {
                        spacing: 4
                        Text {
                            text: "ยินดีต้อนรับสู่ระบบงานทะเบียนนักเรียน"
                            font.bold: true
                            font.pixelSize: 15
                            color: "#1e3a8a"
                        }
                        Text {
                            text: "ยังไม่พบข้อมูลนักเรียนในระบบ หรือเป็นการเริ่มต้นใช้งานครั้งแรก"
                            font.pixelSize: 12
                            color: "#3b82f6"
                        }
                    }
                }
            }

            Text {
                text: "คุณมีไฟล์บัญชีรายชื่อนักเรียน (.xlsx) หรือไม่?"
                font.bold: true
                font.pixelSize: 14
                color: "#1e293b"
            }

            Text {
                text: "• หากมีไฟล์ Excel: เลือกระบบนำเข้าเพื่อสร้างบัญชีรายชื่อ ม.1 - ม.6 อัตโนมัติ\n• หากไม่มีไฟล์: ระบบจะสร้างฐานข้อมูลเปล่าตามโครงสร้างตารางมาตรฐานพร้อมใช้งาน"
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
                    text: "📁 มีไฟล์ Excel (.xlsx) — เลือกไฟล์นำเข้า"
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
                        var res = JSON.parse(studentAdmin.initializeBlankDatabase("Admin"))
                        firstLaunchDialog.close()
                        actionFeedback.isError = !res.ok
                        actionFeedback.text = res.ok
                            ? "✓ สร้างฐานข้อมูลเปล่าตามโครงสร้างระบบเรียบร้อยแล้ว พร้อมใช้งาน"
                            : ("✗ " + res.error)
                        doSearch()
                    }
                }
            }
        }
    }

    function doImportXlsx(force) {
        if (!window.selectedXlsxPath) {
            importStatusText.text = "กรุณาเลือกไฟล์ Excel ก่อนนำเข้า"
            return
        }
        importStatusText.text = "กำลังประมวลผลไฟล์..."
        var res = JSON.parse(studentAdmin.importXlsx(window.selectedXlsxPath, force, "Admin"))
        if (res.need_confirm) {
            confirmImportMsg.text = res.warning
            confirmImportDialog.open()
            importStatusText.text = "รอการยืนยันจากผู้ใช้..."
            return
        }
        if (res.ok) {
            importStatusText.text = "นำเข้าสำเร็จ!\n" +
                "นักเรียน: " + res.data.students + " คน\n" +
                "การลงทะเบียน: " + res.data.enrollments + " รายการ\n" +
                "ย้ายออก: " + res.data.transfers_out + " | ย้ายเข้า: " + res.data.transfers_in
            doSearch()
        } else {
            importStatusText.text = "เกิดข้อผิดพลาด: " + res.error
        }
    }

    function loadLogs() {
        logModel.clear()
        var logs = JSON.parse(studentAdmin.getActivityLogs())
        for (var i = 0; i < logs.length; i++) logModel.append(logs[i])
    }

    Component.onCompleted: {
        doSearch()
        if (studentAdmin.isFirstLaunch()) {
            firstLaunchDialog.open()
        }
    }
}
