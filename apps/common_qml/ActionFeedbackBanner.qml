import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    Layout.fillWidth: true
    height: messageText.text !== "" ? 44 : 0
    color: isError ? "#fee2e2" : "#dcfce7"
    border.color: isError ? "#fca5a5" : "#86efac"
    border.width: messageText.text !== "" ? 1 : 0
    radius: 6
    visible: messageText.text !== ""

    property alias text: messageText.text
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
        color: root.isError ? "#991b1b" : "#166534"
        font.pixelSize: 13
        font.bold: true
    }
}
