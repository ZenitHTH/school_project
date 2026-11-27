import QtQuick 2.15
import "Theme.js" as Theme
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "Typography.js" as Typography

Rectangle {
    id: root
    color: Theme.surfaceWhite

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
            color: Theme.textPrimary
            Layout.fillWidth: true
            elide: Text.ElideRight
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
                anchors.fill: parent
                visible: logModel.count === 0
                color: "transparent"
                Text {
                    anchors.centerIn: parent
                    width: Math.max(0, parent.width - 32)
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                    text: "ยังไม่มีบันทึกประวัติกิจกรรม"
                    color: Theme.textFaint
                    font.pixelSize: 14
                }
            }

            delegate: Rectangle {
                id: logRow
                width: logList.width
                readonly property real uiScale: (typeof window !== "undefined" && window && window.fontScale) ? window.fontScale : (Typography.scale(12) / 12.0)
                implicitHeight: Math.max(48, Math.round(rowContent.implicitHeight + 14))
                height: implicitHeight
                border.color: Theme.borderSubtle
                color: index % 2 === 0 ? Theme.surfaceWhite : Theme.surfaceSubtle
                Component.onCompleted: Typography.applyToItem(this)

                RowLayout {
                    id: rowContent
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 12

                    Text {
                        text: model.logged_at ? (model.logged_at.length > 19 ? model.logged_at.substring(0, 19) : model.logged_at) : ""
                        color: Theme.textMuted
                        font.pixelSize: Math.max(10, Math.round(12 * logRow.uiScale))
                        Layout.minimumWidth: 90
                        Layout.preferredWidth: Math.min(Math.round(150 * logRow.uiScale), Math.max(90, Math.round(logRow.width * 0.28)))
                        elide: Text.ElideRight
                    }

                    Text {
                        text: model.action || ""
                        font.bold: true
                        color: Theme.textStrong
                        font.pixelSize: Math.max(10, Math.round(13 * logRow.uiScale))
                        Layout.minimumWidth: 90
                        Layout.preferredWidth: Math.min(Math.round(160 * logRow.uiScale), Math.max(90, Math.round(logRow.width * 0.30)))
                        elide: Text.ElideRight
                    }

                    Text {
                        text: model.detail || ""
                        color: Theme.textSecondary
                        font.pixelSize: Math.max(10, Math.round(13 * logRow.uiScale))
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
}
