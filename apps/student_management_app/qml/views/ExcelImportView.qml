import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#ffffff"

    property string selectedXlsxPath: ""
    property real baseFontSize: 13

    property alias selectFileButton: selectFileButton
    property alias selectedFilePath: selectedFilePath
    property alias btnPreviewDiff: btnPreviewDiff
    property alias importButton: importButton
    property alias importStatusText: importStatusText
    property alias newBadgeText: newBadgeText
    property alias promoBadgeText: promoBadgeText
    property alias missingBadgeText: missingBadgeText
    property alias conflictBadgeText: conflictBadgeText
    property alias diffListView: diffListView
    property alias diffModel: diffModel

    signal selectFileClicked()
    signal previewDiffClicked()
    signal importClicked()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        Text {
            text: "นำเข้าข้อมูลทะเบียนนักเรียนจากไฟล์ Excel (.xlsx)"
            font.bold: true
            font.pixelSize: 22
            color: "#0f172a"
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
            border.color: root.selectedXlsxPath ? "#3b82f6" : "#cbd5e1"
            border.width: root.selectedXlsxPath ? 2 : 1
            radius: 8

            RowLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 16

                Button {
                    id: selectFileButton
                    objectName: "selectFileButton"
                    text: "📁 เลือกไฟล์ Excel (.xlsx)..."
                    font.pixelSize: Math.max(13, root.baseFontSize)
                    font.bold: true
                    highlighted: !root.selectedXlsxPath
                    onClicked: root.selectFileClicked()
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text {
                        text: root.selectedXlsxPath ? "ไฟล์ที่เลือกพร้อมนำเข้า:" : "ยังไม่ได้เลือกไฟล์"
                        color: root.selectedXlsxPath ? "#059669" : "#64748b"
                        font.bold: true
                    }
                    Text {
                        id: selectedFilePath
                        objectName: "selectedFilePath"
                        text: root.selectedXlsxPath ? root.selectedXlsxPath : "กรุณากดปุ่ม 'เลือกไฟล์ Excel' เพื่อเปิดหน้าต่างเลือกไฟล์"
                        color: "#1e293b"
                        font.pixelSize: 13
                        elide: Text.ElideMiddle
                        Layout.fillWidth: true
                    }
                }

                Button {
                    id: btnPreviewDiff
                    objectName: "btnPreviewDiff"
                    text: "🔍 ตรวจสอบความเปลี่ยนแปลง (Preview Diff)"
                    highlighted: true
                    enabled: root.selectedXlsxPath !== ""
                    onClicked: root.previewDiffClicked()
                }

                Button {
                    id: importButton
                    objectName: "importButton"
                    text: "⚡ เริ่มนำเข้าข้อมูลทันที"
                    highlighted: true
                    enabled: root.selectedXlsxPath !== ""
                    onClicked: root.importClicked()
                }
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
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        id: importStatusText
                        objectName: "importStatusText"
                        text: "ยังไม่มีการนำเข้า"
                        font.bold: true
                        font.pixelSize: 15
                        color: "#1e293b"
                        Layout.fillWidth: true
                    }
                }

                // Diff Summary Statistics Badges
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    visible: diffModel.count > 0

                    Rectangle {
                        height: 34
                        radius: 6
                        color: "#ecfdf5"
                        border.color: "#a7f3d0"
                        implicitWidth: newBadgeText.implicitWidth + 28
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            Text {
                                id: newBadgeText
                                objectName: "newBadgeText"
                                text: "• นักเรียนใหม่: 0 คน"
                                color: "#059669"
                                font.bold: true
                                font.pixelSize: 13
                            }
                        }
                    }

                    Rectangle {
                        height: 34
                        radius: 6
                        color: "#f0f9ff"
                        border.color: "#bae6fd"
                        implicitWidth: promoBadgeText.implicitWidth + 28
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            Text {
                                id: promoBadgeText
                                objectName: "promoBadgeText"
                                text: "• เลื่อนชั้น/เปลี่ยนห้อง: 0 คน"
                                color: "#0284c7"
                                font.bold: true
                                font.pixelSize: 13
                            }
                        }
                    }

                    Rectangle {
                        height: 34
                        radius: 6
                        color: "#f8fafc"
                        border.color: "#cbd5e1"
                        implicitWidth: missingBadgeText.implicitWidth + 28
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            Text {
                                id: missingBadgeText
                                objectName: "missingBadgeText"
                                text: "• ไม่มีในไฟล์: 0 คน (คงเดิม)"
                                color: "#64748b"
                                font.bold: true
                                font.pixelSize: 13
                            }
                        }
                    }

                    Rectangle {
                        height: 34
                        radius: 6
                        color: "#fffbeb"
                        border.color: "#fde68a"
                        implicitWidth: conflictBadgeText.implicitWidth + 28
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            Text {
                                id: conflictBadgeText
                                objectName: "conflictBadgeText"
                                text: "• สะกดต่างจากเดิม: 0 คน"
                                color: "#d97706"
                                font.bold: true
                                font.pixelSize: 13
                            }
                        }
                    }
                    Item { Layout.fillWidth: true }
                }

                // Diff Items ListView
                ListView {
                    id: diffListView
                    objectName: "diffListView"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 4
                    model: ListModel { id: diffModel; objectName: "diffModel" }
                    delegate: Rectangle {
                        width: diffListView.width
                        height: 36
                        color: model.category === "conflict" ? "#fffbeb" : (model.category === "new" ? "#ecfdf5" : (model.category === "promo" ? "#f0f9ff" : "#ffffff"))
                        border.color: "#e2e8f0"
                        radius: 4
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 8
                            Text {
                                text: model.desc
                                color: model.category === "conflict" ? "#b45309" : (model.category === "new" ? "#047857" : (model.category === "promo" ? "#0369a1" : "#475569"))
                                font.bold: model.category === "conflict" || model.category === "new"
                                font.pixelSize: 13
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }
        }
    }
}
