import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../../common_qml"

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
            font.pixelSize: 22
            color: "#0f172a"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            StyledSearchField {
                id: searchInput
                objectName: "searchInput"
                placeholderText: "พิมพ์ชื่อ, นามสกุล, เลขประจำตัว หรือเลขประจำตัวประชาชน..."
                Layout.fillWidth: true
                font.pixelSize: Math.max(13, root.baseFontSize)
                onAccepted: root.searchRequested()
            }

            Button {
                id: searchBtn
                objectName: "searchButton"
                text: "🔍 ค้นหา"
                font.bold: true
                font.pixelSize: Math.max(13, root.baseFontSize)
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
                Layout.fillWidth: true
                height: 38
                color: "#f8fafc"
                border.color: "#e2e8f0"
                border.width: 1
                radius: 6

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16
                    spacing: 12

                    Text {
                        text: "รหัสประจำตัว"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#475569"
                        Layout.preferredWidth: 110
                    }

                    Text {
                        text: "ชื่อ - นามสกุล"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#475569"
                        Layout.fillWidth: true
                    }

                    Text {
                        text: "ระดับชั้น/ห้อง"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#475569"
                        Layout.preferredWidth: 100
                    }

                    Text {
                        text: "สถานะ"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#475569"
                        Layout.preferredWidth: 90
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Text {
                        text: "จัดการ"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#475569"
                        Layout.preferredWidth: 110
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
                    width: 320
                    height: 80
                    color: "transparent"
                    visible: searchResultsModel.count === 0 || (searchResultsModel.count === 1 && searchResultsModel.get(0)._empty)
                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 6
                        Text {
                            text: "🔍 ไม่พบข้อมูลนักเรียน"
                            font.bold: true
                            font.pixelSize: 15
                            color: "#64748b"
                            Layout.alignment: Qt.AlignHCenter
                        }
                        Text {
                            text: "ลองค้นหาด้วยคำอื่น หรือนำเข้าไฟล์ข้อมูล Excel"
                            font.pixelSize: 12
                            color: "#94a3b8"
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                }

                delegate: Rectangle {
                    id: studentRow
                    width: studentTable.width
                    height: model._empty ? 0 : 48
                    visible: !model._empty
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
                            if (model._empty) return
                            root.viewStudentRequested(model.student_id)
                        }
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 16
                        anchors.rightMargin: 16
                        spacing: 12

                        Text {
                            text: model.student_id || ""
                            font.bold: true
                            font.pixelSize: 13
                            color: "#2563eb"
                            Layout.preferredWidth: 110
                        }

                        Text {
                            text: model.full_name || ""
                            font.pixelSize: 13
                            font.bold: true
                            color: "#0f172a"
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }

                        Text {
                            text: (model.grade_level && model.room) ? (model.grade_level + "/" + model.room) : (model.grade_level || model.room || "-")
                            font.pixelSize: 13
                            color: "#475569"
                            Layout.preferredWidth: 100
                        }

                        Rectangle {
                            Layout.preferredWidth: 90
                            height: 28
                            radius: 14
                            color: (!model.status || model.status === "active") ? "#dcfce7" : (model.status === "on_leave" ? "#fef9c3" : (model.status === "transferred_out" ? "#fee2e2" : "#f1f5f9"))
                            Text {
                                anchors.centerIn: parent
                                text: (!model.status || model.status === "active") ? "ปกติ" : (model.status === "on_leave" ? "พักการเรียน" : (model.status === "transferred_out" ? "จำหน่าย" : model.status))
                                color: (!model.status || model.status === "active") ? "#166534" : (model.status === "on_leave" ? "#854d0e" : (model.status === "transferred_out" ? "#991b1b" : "#475569"))
                                font.pixelSize: 11
                                font.bold: true
                            }
                        }

                        Button {
                            id: rowDetailBtn
                            objectName: "btnViewDetail"
                            text: "👁️ ดูข้อมูล"
                            font.bold: true
                            font.pixelSize: 12
                            Layout.preferredWidth: 110
                            implicitHeight: 32
                            contentItem: Text {
                                text: rowDetailBtn.text
                                font: rowDetailBtn.font
                                color: "#ffffff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                color: rowDetailBtn.down ? "#1d4ed8" : (rowDetailBtn.hovered ? "#2563eb" : "#3b82f6")
                                radius: 6
                            }
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
