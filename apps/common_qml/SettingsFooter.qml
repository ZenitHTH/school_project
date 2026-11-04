import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

RowLayout {
    id: footerRoot
    Layout.fillWidth: true
    spacing: 12

    property alias saveStatusText: statusLabel
    property alias btnResetSettings: btnReset
    property alias btnSaveSettings: btnSave

    signal resetClicked()
    signal saveClicked()

    Text {
        id: statusLabel
        objectName: "saveStatusText"
        text: ""
        color: text.startsWith("✓") ? "#16a34a" : "#dc2626"
        font.bold: true
        font.pixelSize: 13
    }

    Item { Layout.fillWidth: true }

    Button {
        id: btnReset
        objectName: "btnResetSettings"
        text: "🔄 คืนค่าเริ่มต้น (Reset to Defaults)"
        onClicked: footerRoot.resetClicked()
    }

    Button {
        id: btnSave
        objectName: "btnSaveSettings"
        text: "💾 บันทึกการตั้งค่า (Save Settings)"
        highlighted: true
        onClicked: footerRoot.saveClicked()
    }
}
