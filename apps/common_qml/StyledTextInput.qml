import QtQuick 2.15
import QtQuick.Controls 2.15

TextField {
    id: control
    implicitWidth: Math.max(120, Math.round(contentWidth + leftPadding + rightPadding + 20))
    implicitHeight: Math.max(38, Math.round(((font.pixelSize > 0 ? font.pixelSize : 14)) * 2.2))
    leftPadding: 12
    rightPadding: 12
    horizontalAlignment: TextInput.AlignLeft
    verticalAlignment: TextInput.AlignVCenter
    color: "#0f172a"
    placeholderTextColor: "#64748b"
    selectByMouse: true
    selectionColor: "#bfdbfe"
    selectedTextColor: "#0f172a"

    background: Rectangle {
        implicitHeight: control.implicitHeight
        color: "#ffffff"
        border.color: control.activeFocus ? "#2563eb" : "#cbd5e1"
        border.width: control.activeFocus ? 2 : 1
        radius: 6
    }
}
