import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "Theme.js" as Theme

Dialog {
    id: root
    modal: true
    closePolicy: Popup.CloseOnEscape
    anchors.centerIn: parent
    padding: 16
    implicitWidth: 440

    background: Rectangle {
        color: Theme.surfaceWhite
        border.color: Theme.borderSubtle
        border.width: 1
        radius: 12
    }

    header: Text {
        text: root.title
        visible: root.title !== ""
        Layout.fillWidth: true
        Layout.preferredHeight: root.title === "" ? 0 : implicitHeight
        color: Theme.textPrimary
        font.bold: true
        font.pixelSize: 16
        wrapMode: Text.Wrap
        elide: Text.ElideRight
    }

    footer: RowLayout {
        spacing: 8
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
        visible: (root.standardButtons & (Dialog.Ok | Dialog.Cancel)) !== 0
        Layout.preferredHeight: (root.standardButtons & (Dialog.Ok | Dialog.Cancel)) === 0 ? 0 : implicitHeight

        StyledButton {
            objectName: "dialogCancelButton"
            variant: StyledButton.Neutral
            visible: root.standardButtons & Dialog.Cancel
            text: qsTr("Cancel")
            font.pixelSize: 13
            onClicked: root.rejected()
        }

        StyledButton {
            objectName: "dialogOkButton"
            variant: StyledButton.Primary
            visible: root.standardButtons & Dialog.Ok
            text: qsTr("OK")
            font.pixelSize: 13
            onClicked: root.accepted()
        }
    }
}
