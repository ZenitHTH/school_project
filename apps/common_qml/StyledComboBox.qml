import QtQuick 2.15
import QtQuick.Controls 2.15
import "Theme.js" as Theme

ComboBox {
    id: control
    implicitHeight: Math.max(38, Math.round(((font.pixelSize > 0 ? font.pixelSize : 14)) * 2.2))

    background: Rectangle {
        implicitHeight: control.implicitHeight
        color: Theme.surfaceWhite
        border.color: control.activeFocus ? Theme.accentPrimary : Theme.borderDefault
        border.width: control.activeFocus ? 2 : 1
        radius: 6
    }

    contentItem: Text {
        leftPadding: 12
        rightPadding: 24
        text: control.displayText
        color: control.enabled ? Theme.textPrimary : Theme.textFaint
        font.pixelSize: 13
        horizontalAlignment: Text.AlignLeft
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    delegate: ItemDelegate {
        width: control.width
        height: Math.max(36, Math.round(13 * 2.6))
        padding: 12
        contentItem: Text {
            text: text
            color: highlighted ? Theme.accentDeep : Theme.textPrimary
            font.pixelSize: 13
            horizontalAlignment: Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            color: highlighted ? Theme.accentSurface : (hovered ? Theme.surfaceHover : "transparent")
        }
        highlighted: control.currentIndex === index
    }

    popup: Popup {
        y: control.height + 4
        width: control.width
        implicitHeight: Math.min(implicitContentHeight, 240)
        padding: 4
        background: Rectangle {
            color: Theme.surfaceWhite
            border.color: Theme.borderDefault
            radius: 6
        }
    }
}
