import QtQuick 2.15
import "Theme.js" as Theme
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    Layout.fillWidth: true
    height: messageText.text !== "" ? 44 : 0
    implicitHeight: height
    color: isError ? Theme.errorBackground : Theme.successBackground
    border.color: isError ? Theme.errorBorder : Theme.successBorder
    border.width: messageText.text !== "" ? 1 : 0
    radius: 6
    visible: messageText.text !== ""

    property alias text: messageText.text
    property alias font: messageText.font
    property bool isError: false
    property int duration: 0

    Timer {
        id: dismissTimer
        interval: root.duration
        running: false
        repeat: false
        onTriggered: {
            root.text = ""
        }
    }

    onTextChanged: {
        if (root.duration > 0 && root.text !== "") {
            dismissTimer.restart()
        }
    }

    Text {
        id: messageText
        anchors.centerIn: parent
        text: ""
        color: root.isError ? Theme.errorText : Theme.successText
        font.pixelSize: 13
        font.bold: true
    }
}
