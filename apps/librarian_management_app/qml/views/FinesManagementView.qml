import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../../common_qml"
import "../../../common_qml/Typography.js" as Typography

Rectangle {
    id: root
    color: "#ffffff"

    property alias fineList: fineList
    property alias fineModel: fineModel

    signal loadFinesRequested()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        Text {
            text: "ค่าปรับค้างชำระและการบันทึกการชำระ"
            font.bold: true
            font.pixelSize: 22
            color: "#1e293b"
        }

        ListView {
            id: fineList
            objectName: "fineList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: ListModel { id: fineModel; objectName: "fineModel" }
            delegate: Rectangle {
                id: fineRow
                width: fineList.width
                implicitHeight: Math.max(54, Math.round(rowContent.implicitHeight + 16))
                height: implicitHeight
                border.color: "#e2e8f0"
                color: index % 2 === 0 ? "#ffffff" : "#f8fafc"
                Component.onCompleted: Typography.applyToItem(this)

                RowLayout {
                    id: rowContent
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8
                    Text {
                        text: model.full_name
                        font.bold: true
                        font.pixelSize: Math.max(10, Math.round(13 * (window.fontScale || 1.0)))
                        Layout.preferredWidth: Math.max(180, Math.round(180 * (window.fontScale || 1.0)))
                        color: "#1e293b"
                    }
                    Text {
                        text: model.title
                        font.pixelSize: Math.max(10, Math.round(13 * (window.fontScale || 1.0)))
                        Layout.preferredWidth: 260
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                        color: "#334155"
                    }
                    Text {
                        text: model.amount + " บาท (" + model.reason + ")"
                        color: "#dc2626"
                        font.bold: true
                        font.pixelSize: Math.max(10, Math.round(13 * (window.fontScale || 1.0)))
                        Layout.preferredWidth: Math.max(160, Math.round(160 * (window.fontScale || 1.0)))
                    }
                    Text {
                        text: model.paid ? "ชำระแล้ว" : "ค้างชำระ"
                        color: model.paid ? "#166534" : "#991b1b"
                        Layout.fillWidth: true
                        font.bold: true
                        font.pixelSize: Math.max(10, Math.round(13 * (window.fontScale || 1.0)))
                    }
                    StyledButton {
                        variant: StyledButton.Primary
                        text: "บันทึกการชำระ"
                        visible: !model.paid
                        font.pixelSize: Math.max(10, Math.round(12 * (window.fontScale || 1.0)))
                        implicitHeight: Math.max(32, Math.round(contentItem.implicitHeight + 8))
                        onClicked: {
                            librarianAdmin.payFine(model.fine_id)
                            root.loadFinesRequested()
                        }
                    }
                }
            }
        }
    }
}
