import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#ffffff"

    property var selectedStudent: null
    property real baseFontSize: 13

    property alias actionFeedback: actionFeedback
    property alias btnChangeRoom: btnRoom
    property alias btnChangeStatus: btnStatus
    property alias btnEditName: btnName
    property alias btnChangeId: btnId

    signal backToSearchRequested()
    signal requestChangeRoom()
    signal requestChangeStatus()
    signal requestEditName()
    signal requestChangeId()
    signal directLookupRequested(string query)

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
                onClicked: root.backToSearchRequested()
            }
        }

        // Empty state — shown when no student is selected
        Rectangle {
            Layout.fillWidth: true
            height: 180
            color: "#f8fafc"
            border.color: "#cbd5e1"
            radius: 10
            visible: root.selectedStudent === null

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
                    font.pixelSize: Math.max(13, root.baseFontSize)
                    Layout.alignment: Qt.AlignHCenter
                }
                RowLayout {
                    spacing: 10
                    Layout.alignment: Qt.AlignHCenter
                    TextField {
                        id: directIdInput
                        placeholderText: "พิมพ์รหัสนักเรียน หรือชื่อ..."
                        font.pixelSize: Math.max(13, root.baseFontSize)
                        Layout.preferredWidth: 260
                        onAccepted: {
                            if (directIdInput.text) {
                                root.directLookupRequested(directIdInput.text)
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
                                root.directLookupRequested(directIdInput.text)
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
                        onClicked: root.backToSearchRequested()
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
            visible: root.selectedStudent !== null

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
                        text: root.selectedStudent ? root.selectedStudent.full_name : ""
                        font.bold: true
                        font.pixelSize: 22
                        color: "#0f172a"
                    }
                    Rectangle {
                        height: 26
                        radius: 13
                        Layout.preferredWidth: 80
                        color: (root.selectedStudent && (!root.selectedStudent.status || root.selectedStudent.status === "active")) ? "#dcfce7" : (root.selectedStudent && root.selectedStudent.status === "on_leave" ? "#fef9c3" : (root.selectedStudent && root.selectedStudent.status === "transferred_out" ? "#fee2e2" : "#f1f5f9"))
                        Text {
                            anchors.centerIn: parent
                            text: root.selectedStudent ? ((!root.selectedStudent.status || root.selectedStudent.status === "active") ? "ปกติ" : (root.selectedStudent.status === "on_leave" ? "พักการเรียน" : (root.selectedStudent.status === "transferred_out" ? "จำหน่าย" : root.selectedStudent.status))) : ""
                            color: (root.selectedStudent && (!root.selectedStudent.status || root.selectedStudent.status === "active")) ? "#166534" : (root.selectedStudent && root.selectedStudent.status === "on_leave" ? "#854d0e" : (root.selectedStudent && root.selectedStudent.status === "transferred_out" ? "#991b1b" : "#475569"))
                            font.pixelSize: Math.max(10, root.baseFontSize)
                            font.bold: true
                        }
                    }
                }

                RowLayout {
                    spacing: 20
                    Text {
                        id: detailSub
                        text: root.selectedStudent
                            ? ("รหัสประจำตัว: " + root.selectedStudent.student_id
                               + "   |   ระดับชั้น: " + ((root.selectedStudent.grade_level && root.selectedStudent.room) ? (root.selectedStudent.grade_level + "/" + root.selectedStudent.room) : (root.selectedStudent.grade_level || root.selectedStudent.room || "-"))
                               + "   |   แผนการเรียน: " + (root.selectedStudent.track || "-"))
                            : ""
                        color: "#475569"
                        font.pixelSize: Math.max(13, root.baseFontSize)
                    }
                }

                Text {
                    text: root.selectedStudent
                        ? ("เลขประจำตัวประชาชน: " + (root.selectedStudent.national_id || "ไม่มีข้อมูล"))
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
            visible: root.selectedStudent !== null
        }

        // Action buttons row
        Flow {
            Layout.fillWidth: true
            spacing: 12
            visible: root.selectedStudent !== null

            Button {
                id: btnRoom
                objectName: "btnChangeRoom"
                text: "🏫 เปลี่ยนห้องเรียน"
                font.bold: true
                font.pixelSize: Math.max(13, root.baseFontSize)
                enabled: root.selectedStudent !== null
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
                onClicked: root.requestChangeRoom()
            }

            Button {
                id: btnStatus
                objectName: "btnChangeStatus"
                text: "📋 เปลี่ยนสถานะ"
                font.bold: true
                font.pixelSize: Math.max(13, root.baseFontSize)
                enabled: root.selectedStudent !== null
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
                onClicked: root.requestChangeStatus()
            }

            Button {
                id: btnName
                objectName: "btnEditName"
                text: "✏️ แก้ไขชื่อ-นามสกุล"
                font.bold: true
                font.pixelSize: Math.max(13, root.baseFontSize)
                enabled: root.selectedStudent !== null
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
                onClicked: root.requestEditName()
            }

            Button {
                id: btnId
                objectName: "btnChangeId"
                text: "🔢 เปลี่ยนรหัสนักเรียน"
                font.bold: true
                font.pixelSize: Math.max(13, root.baseFontSize)
                enabled: root.selectedStudent !== null
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
                onClicked: root.requestChangeId()
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
                font.pixelSize: Math.max(13, root.baseFontSize)
                font.bold: true
            }
        }

        Item { Layout.fillHeight: true }
    }
}
