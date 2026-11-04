import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../../common_qml/Typography.js" as Typography

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
                id: loanRow
                width: activeLoanList.width
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
                        text: model.barcode
                        font.bold: true
                        font.pixelSize: Math.max(10, Math.round(13 * (window.fontScale || 1.0)))
                        Layout.preferredWidth: Math.max(120, Math.round(120 * (window.fontScale || 1.0)))
                        color: "#0f766e"
                    }
                    Text {
                        text: model.title
                        font.pixelSize: Math.max(11, Math.round(14 * (window.fontScale || 1.0)))
                        Layout.preferredWidth: 280
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                        color: "#1e293b"
                    }
                    Text {
                        text: model.full_name + " (" + model.student_id + ")"
                        font.pixelSize: Math.max(10, Math.round(13 * (window.fontScale || 1.0)))
                        Layout.preferredWidth: Math.max(200, Math.round(200 * (window.fontScale || 1.0)))
                        elide: Text.ElideRight
                        color: "#334155"
                    }
                    Text {
                        text: "กำหนดคืน: " + (model.due_at ? model.due_at.substring(0, 10) : "-")
                        font.pixelSize: Math.max(10, Math.round(13 * (window.fontScale || 1.0)))
                        color: "#dc2626"
                        Layout.preferredWidth: Math.max(160, Math.round(160 * (window.fontScale || 1.0)))
                    }
                }
            }
        }
    }
}
