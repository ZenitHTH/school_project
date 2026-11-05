import QtQuick 2.15
import "Theme.js" as Theme
import QtQuick.Controls 2.15

TextField {
    id: control
    implicitWidth: Math.max(180, Math.round(contentWidth + leftPadding + rightPadding + 20))
    implicitHeight: Math.max(38, Math.round(((font.pixelSize > 0 ? font.pixelSize : 14)) * 2.2))
    leftPadding: 12
    rightPadding: 12
    horizontalAlignment: TextInput.AlignLeft
    verticalAlignment: TextInput.AlignVCenter
    color: Theme.textPrimary
    placeholderTextColor: Theme.textMuted
    selectByMouse: true
    selectionColor: Theme.borderLightBlue
    selectedTextColor: Theme.textPrimary

    background: Rectangle {
        implicitHeight: control.implicitHeight
        color: Theme.surfaceWhite
        border.color: control.activeFocus ? Theme.accentMid : Theme.borderDefault
        border.width: control.activeFocus ? 2 : 1
        radius: 6
    }
}
