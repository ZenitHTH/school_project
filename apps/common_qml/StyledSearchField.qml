import QtQuick 2.15
import QtQuick.Controls 2.15

TextField {
    id: control
    implicitHeight: 38
    color: "#0f172a"
    placeholderTextColor: "#94a3b8"
    selectByMouse: true
    selectionColor: "#bfdbfe"
    selectedTextColor: "#0f172a"

    background: Rectangle {
        implicitHeight: 38
        color: "#ffffff"
        border.color: control.activeFocus ? "#3b82f6" : "#cbd5e1"
        border.width: control.activeFocus ? 2 : 1
        radius: 6
    }
}
