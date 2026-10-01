import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#ffffff"

    property alias snapshotPathInput: snapshotPathInput
    property alias btnPreviewDiff: btnPreviewDiff
    property alias applySyncBtn: applySyncBtn
    property alias diffSummaryText: diffSummaryText
    property alias diffDetailsList: diffDetailsList
    property alias diffModel: diffModel

    signal previewDiffRequested()
    signal applySyncRequested()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        Text {
            text: "Sync ข้อมูลนักเรียนจากฝ่ายทะเบียน (LINE Snapshot)"
            font.bold: true
            font.pixelSize: 22
            color: "#1e293b"
        }

        RowLayout {
            TextField {
                id: snapshotPathInput
                objectName: "snapshotPathInput"
                text: "snapshot.sqlite"
                placeholderText: "path ของไฟล์ snapshot.sqlite"
                Layout.preferredWidth: 320
                selectByMouse: true
                onAccepted: root.previewDiffRequested()
            }
            Button {
                id: btnPreviewDiff
                objectName: "btnPreviewDiff"
                text: "ตรวจสอบความเปลี่ยนแปลง (Preview Diff)"
                highlighted: true
                onClicked: root.previewDiffRequested()
            }
            Button {
                id: applySyncBtn
                objectName: "applySyncBtn"
                text: "ยืนยันนำเข้าข้อมูล (Apply Sync)"
                enabled: false
                onClicked: root.applySyncRequested()
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
                    color: "#1e293b"
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
                        font.pixelSize: 13
                    }
                }
            }
        }
    }
}
