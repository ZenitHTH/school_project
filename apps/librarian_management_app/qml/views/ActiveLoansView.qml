import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#ffffff"

    property alias activeLoanList: activeLoanList
    property alias activeLoanModel: activeLoanModel

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        Text {
            text: "รายการหนังสือที่กำลังยืมอยู่ทั้งหมด"
            font.bold: true
            font.pixelSize: 22
            color: "#1e293b"
        }

        ListView {
            id: activeLoanList
            objectName: "activeLoanList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: ListModel { id: activeLoanModel; objectName: "activeLoanModel" }
            delegate: Rectangle {
                width: activeLoanList.width
                height: 54
                border.color: "#e2e8f0"
                color: index % 2 === 0 ? "#ffffff" : "#f8fafc"
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    Text { text: model.barcode; font.bold: true; Layout.preferredWidth: 120; color: "#0f766e" }
                    Text { text: model.title; font.pixelSize: 14; Layout.preferredWidth: 280; color: "#1e293b" }
                    Text { text: model.full_name + " (" + model.student_id + ")"; Layout.preferredWidth: 200; color: "#334155" }
                    Text { text: "กำหนดคืน: " + (model.due_at ? model.due_at.substring(0, 10) : "-"); color: "#dc2626"; Layout.fillWidth: true }
                }
            }
        }
    }
}
