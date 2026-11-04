import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: controlsRoot
    Layout.fillWidth: true
    color: "#ffffff"
    radius: 10
    border.color: "#e2e8f0"
    implicitHeight: ctrlLayout.implicitHeight + 32

    property alias fontFamilyCombo: fontFamilyCombo
    property alias fontSizeSlider: fontSizeSlider
    property alias btnFontSizeMinus: btnFontSizeMinus
    property alias btnFontSizePlus: btnFontSizePlus
    property alias scaleSlider: scaleSlider

    signal fontChanged(string family)
    signal fontSizeChanged(int size)
    signal uiScaleChanged(real scale)

    ColumnLayout {
        id: ctrlLayout
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "รูปแบบฟอนต์ (Font Family):"
                font.bold: true
                color: "#1e293b"
                Layout.minimumWidth: 160
                Layout.preferredWidth: Math.max(180, implicitWidth)
                wrapMode: Text.Wrap
            }
            ComboBox {
                id: fontFamilyCombo
                objectName: "fontFamilyCombo"
                Layout.fillWidth: true
                model: ["System Default", "Noto Sans", "Sarabun", "TH Sarabun New", "Segoe UI", "Sukhumvit Set", "Tahoma"]
                onCurrentTextChanged: controlsRoot.fontChanged(currentText)
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "ขนาดตัวอักษร (Font Size):"
                font.bold: true
                color: "#1e293b"
                Layout.minimumWidth: 160
                Layout.preferredWidth: Math.max(180, implicitWidth)
                wrapMode: Text.Wrap
            }
            Button {
                id: btnFontSizeMinus
                objectName: "btnFontSizeMinus"
                text: "−"
                Layout.preferredWidth: 36
                onClicked: fontSizeSlider.value = Math.max(10, fontSizeSlider.value - 1)
            }
            Slider {
                id: fontSizeSlider
                objectName: "fontSizeSlider"
                from: 10
                to: 24
                stepSize: 1
                value: 14
                Layout.fillWidth: true
                onValueChanged: controlsRoot.fontSizeChanged(Math.round(value))
            }
            Button {
                id: btnFontSizePlus
                objectName: "btnFontSizePlus"
                text: "+"
                Layout.preferredWidth: 36
                onClicked: fontSizeSlider.value = Math.min(24, fontSizeSlider.value + 1)
            }
            Rectangle {
                Layout.preferredWidth: 60
                height: 32
                radius: 6
                color: "#f1f5f9"
                Text {
                    anchors.centerIn: parent
                    text: Math.round(fontSizeSlider.value) + " px"
                    font.bold: true
                    color: "#0f172a"
                    font.pixelSize: 12
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "มาตราส่วน (UI Scaling):"
                font.bold: true
                color: "#1e293b"
                Layout.minimumWidth: 160
                Layout.preferredWidth: Math.max(180, implicitWidth)
                wrapMode: Text.Wrap
            }
            Slider {
                id: scaleSlider
                objectName: "scaleSlider"
                from: 50
                to: 150
                stepSize: 5
                value: 100
                Layout.fillWidth: true
                onValueChanged: controlsRoot.uiScaleChanged(Math.round(value) / 100.0)
            }
            Rectangle {
                Layout.preferredWidth: 60
                height: 32
                radius: 6
                color: "#eff6ff"
                Text {
                    anchors.centerIn: parent
                    text: Math.round(scaleSlider.value) + "%"
                    font.bold: true
                    color: "#1d4ed8"
                    font.pixelSize: 12
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Item { Layout.preferredWidth: 180 }
            Repeater {
                model: [50, 75, 100, 125, 150]
                Button {
                    text: modelData === 100 ? "100% (ปกติ)" : (modelData + "%")
                    highlighted: Math.round(scaleSlider.value) === modelData
                    onClicked: scaleSlider.value = modelData
                }
            }
        }
    }
}
