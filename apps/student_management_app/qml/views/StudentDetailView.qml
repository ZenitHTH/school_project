import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../../common_qml/Typography.js" as Typography
import "../../../common_qml"

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
                font.pixelSize: Math.max(20, Math.round(22 * (window.fontScale || 1.0)))
                color: "#0f172a"
            }
            Item { Layout.fillWidth: true }
            StyledButton {
                variant: StyledButton.Neutral
                id: btnBackToSearch
                text: "← กลับไปค้นหานักเรียน"
                font.pixelSize: Math.max(12, Math.round(13 * (window.fontScale || 1.0)))
                implicitWidth: 160
                onClicked: root.backToSearchRequested()
            }
        }

        // Empty state — shown when no student is selected
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: Math.max(160, Math.round(emptyStateContent.implicitHeight + 48))
            height: implicitHeight
            color: "#f8fafc"
            border.color: "#cbd5e1"
            radius: 10
            visible: root.selectedStudent === null

            ColumnLayout {
                id: emptyStateContent
                anchors.centerIn: parent
                spacing: 14

                Text {
                    text: "🔍 ยังไม่ได้เลือกข้อมูลนักเรียน"
                    font.bold: true
                    font.pixelSize: Math.max(16, Math.round(18 * (window.fontScale || 1.0)))
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
                    StyledTextInput {
                        id: directIdInput
                        objectName: "directIdInput"
                        placeholderText: "พิมพ์รหัสนักเรียน หรือชื่อ..."
                        font.pixelSize: Math.max(13, root.baseFontSize)
                        Layout.preferredWidth: 260
                        selectByMouse: true
                        onAccepted: {
                            if (directIdInput.text) {
                                root.directLookupRequested(directIdInput.text)
                            }
                        }
                    }
                    StyledButton {
                        variant: StyledButton.Primary
                        id: btnDirectOpen
                        text: "เปิดดูข้อมูล"
                        font.bold: true
                        font.pixelSize: 13
                        implicitWidth: 110
                        onClicked: {
                            if (directIdInput.text) {
                                root.directLookupRequested(directIdInput.text)
                            }
                        }
                    }
                    StyledButton {
                        variant: StyledButton.Neutral
                        id: btnGoSearch
                        text: "🔍 ไปที่หน้ารายการค้นหา"
                        font.pixelSize: 13
                        implicitWidth: 170
                        onClicked: root.backToSearchRequested()
                    }
                }
            }
        }

        // Student info card — shown when a student is selected
        Rectangle {
            id: infoCard
            objectName: "infoCard"
            Layout.fillWidth: true
            implicitHeight: Math.max(140, Math.round(infoCardContent.implicitHeight + 32))
            height: implicitHeight
            color: "#ffffff"
            border.color: "#e2e8f0"
            radius: 10
            visible: root.selectedStudent !== null
            Component.onCompleted: Typography.applyToItem(this)

            Rectangle {
                width: 6
                height: parent.height
                color: "#2563eb"
                radius: 3
                anchors.left: parent.left
            }

            ColumnLayout {
                id: infoCardContent
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
                        font.pixelSize: Math.max(20, Math.round(22 * (window.fontScale || 1.0)))
                        color: "#0f172a"
                    }
                    Rectangle {
                        id: detailStatusBadge
                        objectName: "detailStatusBadge"
                        implicitHeight: Math.max(26, Math.round(detailStatusTxt.implicitHeight + 6))
                        height: implicitHeight
                        radius: 13
                        Layout.preferredWidth: Math.max(80, Math.round(80 * (window.fontScale || 1.0)))
                        color: (root.selectedStudent && (!root.selectedStudent.status || root.selectedStudent.status === "active")) ? "#dcfce7" : (root.selectedStudent && root.selectedStudent.status === "on_leave" ? "#fef9c3" : (root.selectedStudent && root.selectedStudent.status === "transferred_out" ? "#fee2e2" : "#f1f5f9"))
                        Text {
                            id: detailStatusTxt
                            anchors.centerIn: parent
                            text: root.selectedStudent ? ((!root.selectedStudent.status || root.selectedStudent.status === "active") ? "ปกติ" : (root.selectedStudent.status === "on_leave" ? "พักการเรียน" : (root.selectedStudent.status === "transferred_out" ? "จำหน่าย" : root.selectedStudent.status))) : ""
                            color: (root.selectedStudent && (!root.selectedStudent.status || root.selectedStudent.status === "active")) ? "#166534" : (root.selectedStudent && root.selectedStudent.status === "on_leave" ? "#854d0e" : (root.selectedStudent && root.selectedStudent.status === "transferred_out" ? "#991b1b" : "#475569"))
                            font.pixelSize: Math.max(9, Math.round(11 * (window.fontScale || 1.0)))
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
                        font.pixelSize: Math.max(12, Math.round(13 * (window.fontScale || 1.0)))
                    }
                }

                Text {
                    text: root.selectedStudent
                        ? ("เลขประจำตัวประชาชน: " + (root.selectedStudent.national_id || "ไม่มีข้อมูล"))
                        : ""
                    color: "#94a3b8"
                    font.pixelSize: Math.max(12, Math.round(13 * (window.fontScale || 1.0)))
                }
            }
        }

        Text {
            text: "การดำเนินการทางทะเบียน (คลิกปุ่มเพื่อดำเนินการ):"
            font.bold: true
            font.pixelSize: Math.max(14, Math.round(16 * (window.fontScale || 1.0)))
            color: "#334155"
            visible: root.selectedStudent !== null
        }

        // Action buttons row
        Flow {
            Layout.fillWidth: true
            spacing: 12
            visible: root.selectedStudent !== null

            StyledButton {
                variant: StyledButton.Primary
                id: btnRoom
                objectName: "btnChangeRoom"
                text: "🏫 เปลี่ยนห้องเรียน"
                font.bold: true
                font.pixelSize: Math.max(13, root.baseFontSize)
                enabled: root.selectedStudent !== null
                implicitWidth: 160
                onClicked: root.requestChangeRoom()
            }

            StyledButton {
                variant: StyledButton.Primary
                id: btnStatus
                objectName: "btnChangeStatus"
                text: "📋 เปลี่ยนสถานะ"
                font.bold: true
                font.pixelSize: Math.max(13, root.baseFontSize)
                enabled: root.selectedStudent !== null
                background: Rectangle {
                    implicitWidth: 150
                    implicitHeight: Math.max(40, Math.round(btnStatus.contentItem.implicitHeight + 14))
                    color: btnStatus.down ? "#b45309" : (btnStatus.hovered ? "#d97706" : "#f59e0b")
                    radius: 8
                }
                onClicked: root.requestChangeStatus()
            }

            StyledButton {
                variant: StyledButton.Primary
                id: btnName
                objectName: "btnEditName"
                text: "✏️ แก้ไขชื่อ-นามสกุล"
                font.bold: true
                font.pixelSize: Math.max(13, root.baseFontSize)
                enabled: root.selectedStudent !== null
                background: Rectangle {
                    implicitWidth: 170
                    implicitHeight: Math.max(40, Math.round(btnName.contentItem.implicitHeight + 14))
                    color: btnName.down ? "#047857" : (btnName.hovered ? "#059669" : "#10b981")
                    radius: 8
                }
                onClicked: root.requestEditName()
            }

            StyledButton {
                variant: StyledButton.Primary
                id: btnId
                objectName: "btnChangeId"
                text: "🔢 เปลี่ยนรหัสนักเรียน"
                font.bold: true
                font.pixelSize: Math.max(13, root.baseFontSize)
                enabled: root.selectedStudent !== null
                background: Rectangle {
                    implicitWidth: 175
                    implicitHeight: Math.max(40, Math.round(btnId.contentItem.implicitHeight + 14))
                    color: btnId.down ? "#6d28d9" : (btnId.hovered ? "#7c3aed" : "#8b5cf6")
                    radius: 8
                }
                onClicked: root.requestChangeId()
            }
        }

        // Action result feedback
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: actionFeedback.text ? Math.max(36, Math.round(actionFeedback.implicitHeight + 14)) : 0
            height: implicitHeight
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
