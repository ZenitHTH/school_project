import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "Theme.js" as Theme

Dialog {
    id: root
    modal: true
    closePolicy: Popup.CloseOnEscape
    anchors.centerIn: parent
    topPadding: 12
    bottomPadding: 16
    leftPadding: 16
    rightPadding: 16
    implicitWidth: 440

    onAboutToShow: {
        var ch = 0
        for (var i = 0; i < contentChildren.length; ++i) {
            ch = Math.max(ch, contentChildren[i].implicitHeight, contentChildren[i].height)
        }
        var hh = (title !== "" && header) ? header.implicitHeight : 0
        var fh = ((standardButtons & (Dialog.Ok | Dialog.Cancel)) !== 0 && footer) ? footer.implicitHeight : 0
        implicitHeight = Math.max(120, hh + ch + fh + topPadding + bottomPadding)
    }

    background: Rectangle {
        color: Theme.surfaceWhite
        border.color: Theme.borderSubtle
        border.width: 1
        radius: 12
    }

    header: Text {
        text: root.title
        visible: root.title !== ""
        leftPadding: 16
        rightPadding: 16
        topPadding: 16
        bottomPadding: 4
        color: Theme.textPrimary
        font.bold: true
        font.pixelSize: 16
        wrapMode: Text.Wrap
        elide: Text.ElideRight
    }

    footer: Item {
        visible: (root.standardButtons & (Dialog.Ok | Dialog.Cancel)) !== 0
        implicitHeight: visible ? footerRow.implicitHeight + 20 : 0

        RowLayout {
            id: footerRow
            anchors.right: parent.right
            anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8

            StyledButton {
                objectName: "dialogCancelButton"
                variant: StyledButton.Neutral
                visible: (root.standardButtons & Dialog.Cancel) !== 0
                text: qsTr("Cancel")
                font.pixelSize: 13
                onClicked: root.rejected()
            }

            StyledButton {
                objectName: "dialogOkButton"
                variant: StyledButton.Primary
                visible: (root.standardButtons & Dialog.Ok) !== 0
                text: qsTr("OK")
                font.pixelSize: 13
                onClicked: root.accepted()
            }
        }
    }
}
