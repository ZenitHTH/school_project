import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../../common_qml"
import "../../../common_qml/Typography.js" as Typography

Rectangle {
    id: root
    color: "#ffffff"

    property real baseFontSize: 13
    property int currentPage: 1
    property int totalPages: 1
    property int totalStudentsCount: 0

    property alias searchInput: searchInput
    property alias searchButton: searchBtn
    property alias studentList: studentTable
    property alias searchResultsModel: searchResultsModel

    signal searchRequested()
    signal viewStudentRequested(var studentId)
    signal pageRequested(int page)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        Text {
            text: "ค้นหาและจัดการข้อมูลนักเรียน"
            font.bold: true
            font.pixelSize: Math.max(18, Math.round(22 * (window.fontScale || 1.0)))
            color: "#0f172a"
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            StyledSearchField {
                id: searchInput
                objectName: "searchInput"
                placeholderText: "พิมพ์ชื่อ, นามสกุล, เลขประจำตัว หรือเลขประจำตัวประชาชน..."
                Layout.fillWidth: true
                Layout.minimumWidth: 160
                font.pixelSize: Math.max(13, root.baseFontSize)
                onAccepted: root.searchRequested()
            }

            StyledButton {
                variant: StyledButton.Primary
                id: searchBtn
                objectName: "searchButton"
                text: "🔍 ค้นหา"
                font.bold: true
                font.pixelSize: Math.max(13, root.baseFontSize)
                onClicked: root.searchRequested()
            }
        }

        // Student Results Table Area
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 8

            // Table Header
            Rectangle {
                id: tableHeaderRect
                Layout.fillWidth: true
                implicitHeight: Math.max(38, Math.round(headerRow.implicitHeight + 10))
                height: implicitHeight
                clip: true
                color: "#f8fafc"
                border.color: "#e2e8f0"
                border.width: 1
                radius: 6

                RowLayout {
                    id: headerRow
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16
                    spacing: 12

                    Text {
                        text: "รหัสประจำตัว"
                        font.bold: true
                        font.pixelSize: Math.max(10, Math.round(13 * (window.fontScale || 1.0)))
                        color: "#475569"
                        elide: Text.ElideRight
                        Layout.preferredWidth: Math.min(120, Math.max(85, Math.round(95 * (window.fontScale || 1.0))))
                    }

                    Text {
                        text: "ชื่อ - นามสกุล"
                        font.bold: true
                        font.pixelSize: Math.max(10, Math.round(13 * (window.fontScale || 1.0)))
                        color: "#475569"
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                        Layout.minimumWidth: 120
                    }

                    Text {
                        text: "ระดับชั้น/ห้อง"
                        font.bold: true
                        font.pixelSize: Math.max(10, Math.round(13 * (window.fontScale || 1.0)))
                        color: "#475569"
                        elide: Text.ElideRight
                        Layout.preferredWidth: Math.min(105, Math.max(75, Math.round(85 * (window.fontScale || 1.0))))
                    }

                    Text {
                        text: "สถานะ"
                        font.bold: true
                        font.pixelSize: Math.max(10, Math.round(13 * (window.fontScale || 1.0)))
                        color: "#475569"
                        elide: Text.ElideRight
                        Layout.preferredWidth: Math.min(95, Math.max(72, Math.round(80 * (window.fontScale || 1.0))))
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Text {
                        text: "จัดการ"
                        font.bold: true
                        font.pixelSize: Math.max(10, Math.round(13 * (window.fontScale || 1.0)))
                        color: "#475569"
                        elide: Text.ElideRight
                        Layout.preferredWidth: Math.min(120, Math.max(92, Math.round(100 * (window.fontScale || 1.0))))
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }

            // Student ListView
            ListView {
                id: studentTable
                objectName: "studentList"
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 6
                model: ListModel { id: searchResultsModel; objectName: "searchResultsModel" }

                // Empty state indicator
                Rectangle {
                    anchors.centerIn: parent
                    implicitWidth: Math.max(240, emptyCol.implicitWidth + 32)
                    implicitHeight: Math.max(72, emptyCol.implicitHeight + 24)
                    width: Math.min(parent.width - 24, implicitWidth)
                    height: implicitHeight
                    color: "transparent"
                    visible: searchResultsModel.count === 0 || (searchResultsModel.count === 1 && searchResultsModel.get(0)._empty === true)
                    ColumnLayout {
                        id: emptyCol
                        anchors.centerIn: parent
                        width: parent.width - 16
                        spacing: 6
                        Text {
                            text: "🔍 ไม่พบข้อมูลนักเรียน"
                            font.bold: true
                            font.pixelSize: Math.max(13, Math.round(15 * (window.fontScale || 1.0)))
                            color: "#64748b"
                            wrapMode: Text.Wrap
                            horizontalAlignment: Text.AlignHCenter
                            Layout.fillWidth: true
                        }
                        Text {
                            text: "ลองค้นหาด้วยคำอื่น หรือนำเข้าไฟล์ข้อมูล Excel"
                            font.pixelSize: Math.max(11, Math.round(12 * (window.fontScale || 1.0)))
                            color: "#94a3b8"
                            wrapMode: Text.Wrap
                            horizontalAlignment: Text.AlignHCenter
                            Layout.fillWidth: true
                        }
                    }
                }

                delegate: Rectangle {
                    id: studentRow
                    width: studentTable.width
                    implicitHeight: model._empty ? 0 : Math.max(48, Math.round(studentRowContent.implicitHeight + 14))
                    height: implicitHeight
                    clip: true
                    visible: !model._empty
                    color: rowMouse.containsMouse ? "#eff6ff" : "#ffffff"
                    border.color: rowMouse.containsMouse ? "#3b82f6" : "#e2e8f0"
                    border.width: rowMouse.containsMouse ? 1.5 : 1
                    radius: 8
                    Component.onCompleted: Typography.applyToItem(this)

                    MouseArea {
                        id: rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (model._empty) return
                            root.viewStudentRequested(model.student_id)
                        }
                    }

                    RowLayout {
                        id: studentRowContent
                        anchors.fill: parent
                        anchors.leftMargin: 16
                        anchors.rightMargin: 16
                        spacing: 12

                        Text {
                            text: model.student_id || ""
                            font.bold: true
                            font.pixelSize: Math.max(10, Math.round(13 * (window.fontScale || 1.0)))
                            color: "#2563eb"
                            elide: Text.ElideRight
                            Layout.preferredWidth: Math.min(120, Math.max(85, Math.round(95 * (window.fontScale || 1.0))))
                        }

                        Text {
                            text: model.full_name || ""
                            font.pixelSize: Math.max(10, Math.round(13 * (window.fontScale || 1.0)))
                            font.bold: true
                            color: "#0f172a"
                            Layout.fillWidth: true
                            Layout.minimumWidth: 120
                            elide: Text.ElideRight
                        }

                        Text {
                            text: (model.grade_level && model.room) ? (model.grade_level + "/" + model.room) : (model.grade_level || model.room || "-")
                            font.pixelSize: Math.max(10, Math.round(13 * (window.fontScale || 1.0)))
                            color: "#475569"
                            elide: Text.ElideRight
                            Layout.preferredWidth: Math.min(105, Math.max(75, Math.round(85 * (window.fontScale || 1.0))))
                        }

                        Rectangle {
                            id: statusBadge
                            Layout.preferredWidth: Math.min(95, Math.max(72, Math.round(80 * (window.fontScale || 1.0))))
                            implicitHeight: Math.max(26, Math.round(statusTxt.implicitHeight + 6))
                            height: implicitHeight
                            clip: true
                            radius: 14
                            color: (!model.status || model.status === "active") ? "#dcfce7" : (model.status === "on_leave" ? "#fef9c3" : (model.status === "transferred_out" ? "#fee2e2" : "#f1f5f9"))
                            Text {
                                id: statusTxt
                                anchors.centerIn: parent
                                width: parent.width - 10
                                elide: Text.ElideRight
                                horizontalAlignment: Text.AlignHCenter
                                text: (!model.status || model.status === "active") ? "ปกติ" : (model.status === "on_leave" ? "พักการเรียน" : (model.status === "transferred_out" ? "จำหน่าย" : model.status))
                                color: (!model.status || model.status === "active") ? "#166534" : (model.status === "on_leave" ? "#854d0e" : (model.status === "transferred_out" ? "#991b1b" : "#475569"))
                                font.pixelSize: Math.max(9, Math.round(11 * (window.fontScale || 1.0)))
                                font.bold: true
                            }
                        }

                        StyledButton {
                            variant: StyledButton.Primary
                            id: rowDetailBtn
                            objectName: "btnViewDetail"
                            text: "👁️ ดูข้อมูล"
                            font.bold: true
                            font.pixelSize: Math.max(10, Math.round(12 * (window.fontScale || 1.0)))
                            Layout.preferredWidth: Math.min(120, Math.max(92, Math.round(100 * (window.fontScale || 1.0))))
                            implicitHeight: Math.max(32, Math.round(contentItem.implicitHeight + 8))
                            onClicked: root.viewStudentRequested(model.student_id)
                        }
                    }
                }
            }

            // Bottom Pagination Bar
            PaginationBar {
                id: paginationBar
                currentPage: root.currentPage
                totalPages: root.totalPages
                totalCount: root.totalStudentsCount
                countUnit: "รายการ"
                onPageRequested: function(page) {
                    root.pageRequested(page)
                }
            }
        }
    }
}
