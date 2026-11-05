import QtQuick 2.15
import "Theme.js" as Theme
import QtQuick.Layouts 1.15

ColumnLayout {
    spacing: 4
    Text {
        text: "⚙️ การตั้งค่าระบบและการแสดงผล (Visual Settings)"
        font.bold: true
        font.pixelSize: 22
        color: Theme.textPrimary
    }
    Text {
        text: "ปรับแต่งรูปแบบตัวอักษร, ขนาดฟอนต์ และมาตราส่วนหน้าจอ (UI Scaling 50% - 150%)"
        font.pixelSize: 13
        color: Theme.textMuted
    }
}
