import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

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
                width: fineList.width
                height: 54
                border.color: "#e2e8f0"
                color: index % 2 === 0 ? "#ffffff" : "#f8fafc"
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    Text { text: model.full_name; font.bold: true; Layout.preferredWidth: 180; color: "#1e293b" }
                    Text { text: model.title; Layout.preferredWidth: 260; color: "#334155" }
                    Text { text: model.amount + " บาท (" + model.reason + ")"; color: "#dc2626"; font.bold: true; Layout.preferredWidth: 160 }
                    Text { text: model.paid ? "ชำระแล้ว" : "ค้างชำระ"; color: model.paid ? "#166534" : "#991b1b"; Layout.fillWidth: true; font.bold: true }
                    Button {
                        text: "บันทึกการชำระ"
                        visible: !model.paid
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
