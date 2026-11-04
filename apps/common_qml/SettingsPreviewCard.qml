import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: previewCard
    objectName: "previewCard"
    Layout.fillWidth: true
    color: "#ffffff"
    radius: 10
    border.color: "#e2e8f0"
    implicitHeight: prevCol.implicitHeight + 32

    property string currentFontFamily: "System Default"
    property string activeFontFamily: ""
    property int currentFontSize: 14
    property real currentUiScale: 1.0

    ColumnLayout {
        id: prevCol
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "👁️ ตัวอย่างการแสดงผล (Live Visual Preview)"
                font.bold: true
                font.pixelSize: 15
                color: "#0f172a"
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "ฟอนต์: " + previewCard.currentFontFamily + " | ขนาด: " + previewCard.currentFontSize + "px | สเกล: " + Math.round(previewCard.currentUiScale * 100) + "%"
                color: "#64748b"
                font.pixelSize: 12
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: "#f1f5f9"
        }

        Text {
            text: "โรงเรียนวิทยาศาสตร์จุฬาภรณราชวิทยาลัย (Princess Chulabhorn Science High School)"
            font.family: previewCard.activeFontFamily
            font.pixelSize: Math.round(previewCard.currentFontSize * 1.3 * previewCard.currentUiScale)
            font.bold: true
            color: "#1e293b"
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        Text {
            text: "ระบบงานสารสนเทศและทะเบียนนักเรียน (Student Registry & Library Circulation System)\nทดสอบการแสดงผลภาษาไทย: กขคง ๑๒๓๔๕ ทดสอบสระบนล่าง ที่นี่ มีปัญหาสระลอยหรือไม่ 0123456789"
            font.family: previewCard.activeFontFamily
            font.pixelSize: Math.round(previewCard.currentFontSize * previewCard.currentUiScale)
            color: "#334155"
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        RowLayout {
            spacing: 12
            Rectangle {
                radius: 6
                color: "#dcfce7"
                implicitWidth: badgeTxt.implicitWidth + 16
                implicitHeight: Math.max(28, Math.round(badgeTxt.implicitHeight + 8))
                height: implicitHeight
                Text {
                    id: badgeTxt
                    anchors.centerIn: parent
                    text: "✓ ตัวอย่างสถานะ (Active)"
                    color: "#166534"
                    font.pixelSize: Math.round(previewCard.currentFontSize * previewCard.currentUiScale)
                    font.family: previewCard.activeFontFamily
                }
            }
            Button {
                text: "ปุ่มตัวอย่าง (Sample Button)"
                font.family: previewCard.activeFontFamily
                font.pixelSize: Math.round(previewCard.currentFontSize * previewCard.currentUiScale)
            }
        }
    }
}
