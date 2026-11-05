import QtQuick 2.15
import QtQuick.Controls 2.15
import "Theme.js" as Theme

Button {
    id: control
    enum Variant { Primary, Neutral, Danger, Ghost }
    property int variant: Primary
    implicitHeight: Math.max(38, Math.round(((font.pixelSize > 0 ? font.pixelSize : 14)) * 2.2))

    font.bold: true
    font.pixelSize: 13

    property color buttonBackgroundColor:
        control.variant === StyledButton.Primary ? Theme.accentPrimary
        : control.variant === StyledButton.Danger ? Theme.errorDot
        : control.variant === StyledButton.Ghost ? "transparent"
        : Theme.surfaceWhite
    property color hoverBackgroundColor:
        control.variant === StyledButton.Primary ? Theme.accentHover
        : control.variant === StyledButton.Danger ? Theme.errorDeep
        : control.variant === StyledButton.Ghost ? Theme.surfaceHover
        : Theme.surfaceHover

    property color buttonTextColor:
        (control.variant === StyledButton.Primary || control.variant === StyledButton.Danger)
            ? Theme.surfaceWhite
            : Theme.textSecondary
    property color buttonBorderColor:
        control.variant === StyledButton.Neutral ? Theme.borderDefault : "transparent"

    contentItem: Text {
        text: control.text
        color: control.enabled ? control.buttonTextColor : Theme.textFaint
        font: control.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        implicitHeight: control.implicitHeight
        color: control.down ? control.buttonBackgroundColor
             : (control.hovered && control.enabled ? control.hoverBackgroundColor : control.buttonBackgroundColor)
        border.color: control.buttonBorderColor
        border.width: control.variant === StyledButton.Neutral ? 1 : 0
        radius: 6
    }
}
