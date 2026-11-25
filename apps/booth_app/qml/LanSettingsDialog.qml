import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../common_qml"

StyledDialog {
    id: root
    objectName: "lanSettingsDialog"
    title: "ตั้งค่าเซิร์ฟเวอร์ห้องสมุด (LAN)"
    standardButtons: Dialog.Ok | Dialog.Cancel

    property alias hostText: lanHostInput.text
    property alias portText: lanPortInput.text
    property alias tokenText: lanTokenInput.text
    property alias discoverStatusText: discoverStatusLabel.text

    signal autoDiscoverRequested()

    onRejected: close()

    ColumnLayout {
        width: parent.width
        spacing: 10

        Text {
            text: "IP / Host ของเครื่องบรรณารักษ์"
            font.pixelSize: 13
            color: "#334155"
        }
        StyledTextInput {
            id: lanHostInput
            objectName: "lanHostInput"
            Layout.fillWidth: true
            placeholderText: "เช่น 192.168.1.10"
            horizontalAlignment: TextInput.AlignLeft
            verticalAlignment: TextInput.AlignVCenter
        }

        Text {
            text: "พอร์ต (Port)"
            font.pixelSize: 13
            color: "#334155"
        }
        StyledTextInput {
            id: lanPortInput
            objectName: "lanPortInput"
            Layout.fillWidth: true
            placeholderText: "8765"
            horizontalAlignment: TextInput.AlignLeft
            verticalAlignment: TextInput.AlignVCenter
        }

        Text {
            text: "รหัสเชื่อมต่อ (Token)"
            font.pixelSize: 13
            color: "#334155"
        }
        StyledTextInput {
            id: lanTokenInput
            objectName: "lanTokenInput"
            Layout.fillWidth: true
            placeholderText: "เว้นว่างเพื่อใช้ค่าเดิม (ค่าเริ่มต้น 123456)"
            horizontalAlignment: TextInput.AlignLeft
            verticalAlignment: TextInput.AlignVCenter
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            StyledButton {
                objectName: "btnAutoDiscover"
                variant: StyledButton.Neutral
                text: "🔍 ค้นหาอัตโนมัติ (Auto-Discover)"
                onClicked: root.autoDiscoverRequested()
            }
            Text {
                id: discoverStatusLabel
                objectName: "discoverStatusLabel"
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                font.pixelSize: 12
                color: "#475569"
                text: ""
            }
        }
    }
}
