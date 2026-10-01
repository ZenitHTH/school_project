import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#ffffff"

    property alias title: headerText.text
    property alias logList: logList
    property alias logModel: logModel

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        Text {
            id: headerText
            text: "บันทึกประวัติกิจกรรม (Audit Log)"
            font.bold: true
            font.pixelSize: 22
            color: "#0f172a"
        }

        ListView {
            id: logList
            objectName: "logList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: ListModel {
                id: logModel
                objectName: "logModel"
            }

            Rectangle {
                anchors.centerIn: parent
                visible: logModel.count === 0
                color: "transparent"
                Text {
                    anchors.centerIn: parent
                    text: "ยังไม่มีบันทึกประวัติกิจกรรม"
                    color: "#94a3b8"
                    font.pixelSize: 14
                }
            }

            delegate: Rectangle {
                width: logList.width
                height: 48
                border.color: "#e2e8f0"
                color: index % 2 === 0 ? "#ffffff" : "#f8fafc"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 12

                    Text {
                        text: model.logged_at ? (model.logged_at.length > 19 ? model.logged_at.substring(0, 19) : model.logged_at) : ""
                        color: "#64748b"
                        font.pixelSize: 12
                        Layout.preferredWidth: 150
                    }

                    Text {
                        text: model.action || ""
                        font.bold: true
                        color: "#1e293b"
                        font.pixelSize: 13
                        Layout.preferredWidth: 160
                        elide: Text.ElideRight
                    }

                    Text {
                        text: model.detail || ""
                        color: "#334155"
                        font.pixelSize: 13
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
}
