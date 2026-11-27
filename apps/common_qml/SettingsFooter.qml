import QtQuick 2.15
import "Theme.js" as Theme
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

GridLayout {
    id: footerRoot
    Layout.fillWidth: true
    columns: width < 520 ? 1 : 3
    columnSpacing: 12
    rowSpacing: 8

    property alias saveStatusText: statusLabel
    property alias btnResetSettings: btnReset
    property alias btnSaveSettings: btnSave

    signal resetClicked()
    signal saveClicked()

    Text {
        id: statusLabel
        objectName: "saveStatusText"
        text: ""
        color: text.startsWith("✓") ? Theme.successDot : Theme.errorDot
        font.bold: true
        font.pixelSize: 13
        wrapMode: Text.Wrap
        Layout.fillWidth: true
    }

    StyledButton {
        id: btnReset
        objectName: "btnResetSettings"
        text: "🔄 คืนค่าเริ่มต้น (Reset to Defaults)"
        variant: StyledButton.Neutral
        Layout.alignment: Qt.AlignRight
        onClicked: footerRoot.resetClicked()
    }

    StyledButton {
        id: btnSave
        objectName: "btnSaveSettings"
        text: "💾 บันทึกการตั้งค่า (Save Settings)"
        variant: StyledButton.Primary
        highlighted: true
        Layout.alignment: Qt.AlignRight
        onClicked: footerRoot.saveClicked()
    }
}
