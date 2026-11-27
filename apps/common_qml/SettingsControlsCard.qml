import QtQuick 2.15
import "Theme.js" as Theme
import QtQuick.Controls 2.15
import QtQuick.Templates as T
import QtQuick.Layouts 1.15

Rectangle {
    id: controlsRoot
    Layout.fillWidth: true
    color: Theme.surfaceWhite
    radius: 10
    border.color: Theme.borderSubtle
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
                color: Theme.textStrong
                Layout.minimumWidth: 120
                Layout.preferredWidth: Math.max(140, Math.min(200, implicitWidth))
                wrapMode: Text.Wrap
            }
            ComboBox {
                id: fontFamilyCombo
                objectName: "fontFamilyCombo"
                Layout.fillWidth: true
                implicitHeight: Math.max(38, Math.round(((font.pixelSize > 0 ? font.pixelSize : 14)) * 2.2))
                model: ["System Default", "Noto Sans", "Sarabun", "TH Sarabun New", "Segoe UI", "Sukhumvit Set", "Tahoma"]
                onCurrentTextChanged: controlsRoot.fontChanged(currentText)

                contentItem: Text {
                    leftPadding: 12
                    rightPadding: fontFamilyCombo.indicator ? fontFamilyCombo.indicator.width + 12 : 24
                    text: fontFamilyCombo.displayText
                    font: fontFamilyCombo.font
                    color: Theme.textPrimary
                    verticalAlignment: Text.AlignVCenter
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideRight
                }

                background: Rectangle {
                    implicitHeight: fontFamilyCombo.implicitHeight
                    color: Theme.surfaceWhite
                    border.color: fontFamilyCombo.activeFocus ? Theme.accentPrimary : Theme.borderDefault
                    border.width: fontFamilyCombo.activeFocus ? 2 : 1
                    radius: 6
                }

                delegate: ItemDelegate {
                    id: fontRow
                    width: fontFamilyCombo.width
                    implicitHeight: Math.max(36, Math.round(fontRowText.implicitHeight + 16))
                    height: implicitHeight
                    contentItem: Text {
                        id: fontRowText
                        leftPadding: 12
                        text: modelData
                        font: fontFamilyCombo.font
                        color: highlighted ? Theme.accentDeep : Theme.textPrimary
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignLeft
                        elide: Text.ElideRight
                    }
                    background: Rectangle {
                        color: highlighted ? Theme.accentSurface : (hovered ? Theme.surfaceHover : "transparent")
                    }
                    highlighted: fontFamilyCombo.highlightedIndex === index
                }

                popup: Popup {
                    y: fontFamilyCombo.height + 4
                    width: fontFamilyCombo.width
                    implicitHeight: Math.min(implicitContentHeight + padding * 2, 240)
                    padding: 4
                    background: Rectangle {
                        color: Theme.surfaceWhite
                        border.color: Theme.borderDefault
                        radius: 6
                    }
                    contentItem: ListView {
                        clip: true
                        implicitHeight: contentHeight
                        model: fontFamilyCombo.delegateModel
                        currentIndex: fontFamilyCombo.highlightedIndex
                        highlightMoveDuration: 0
                        T.ScrollBar.vertical: ScrollBar { }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "ขนาดตัวอักษร (Font Size):"
                font.bold: true
                color: Theme.textStrong
                Layout.minimumWidth: 120
                Layout.preferredWidth: Math.max(140, Math.min(200, implicitWidth))
                wrapMode: Text.Wrap
            }
            StyledButton {
                id: btnFontSizeMinus
                objectName: "btnFontSizeMinus"
                text: "−"
                variant: StyledButton.Neutral
                implicitWidth: Math.max(36, Math.round(contentItem.implicitWidth + 16))
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
                Layout.minimumHeight: 24
                onValueChanged: controlsRoot.fontSizeChanged(Math.round(value))
            }
            StyledButton {
                id: btnFontSizePlus
                objectName: "btnFontSizePlus"
                text: "+"
                variant: StyledButton.Neutral
                implicitWidth: Math.max(36, Math.round(contentItem.implicitWidth + 16))
                onClicked: fontSizeSlider.value = Math.min(24, fontSizeSlider.value + 1)
            }
            Rectangle {
                Layout.preferredWidth: Math.max(60, Math.round(fontPxBadge.implicitWidth + 16))
                implicitHeight: Math.max(32, Math.round(fontPxBadge.implicitHeight + 12))
                height: implicitHeight
                radius: 6
                color: Theme.surfaceHover
                Text {
                    id: fontPxBadge
                    anchors.centerIn: parent
                    text: Math.round(fontSizeSlider.value) + " px"
                    font.bold: true
                    color: Theme.textPrimary
                    font.pixelSize: 12
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "มาตราส่วน (UI Scaling):"
                font.bold: true
                color: Theme.textStrong
                Layout.minimumWidth: 120
                Layout.preferredWidth: Math.max(140, Math.min(200, implicitWidth))
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
                Layout.minimumHeight: 24
                onValueChanged: controlsRoot.uiScaleChanged(Math.round(value) / 100.0)
            }
            Rectangle {
                Layout.preferredWidth: Math.max(60, Math.round(scalePctBadge.implicitWidth + 16))
                implicitHeight: Math.max(32, Math.round(scalePctBadge.implicitHeight + 12))
                height: implicitHeight
                radius: 6
                color: Theme.accentSurface
                Text {
                    id: scalePctBadge
                    anchors.centerIn: parent
                    text: Math.round(scaleSlider.value) + "%"
                    font.bold: true
                    color: Theme.accentHover
                    font.pixelSize: 12
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Item {
                Layout.preferredWidth: 140
                visible: controlsRoot.width >= 540
            }
            Flow {
                Layout.fillWidth: true
                spacing: 8
                Repeater {
                    model: [50, 75, 100, 125, 150]
                    StyledButton {
                        text: modelData === 100 ? "100% (ปกติ)" : (modelData + "%")
                        variant: Math.round(scaleSlider.value) === modelData ? StyledButton.Primary : StyledButton.Neutral
                        highlighted: Math.round(scaleSlider.value) === modelData
                        onClicked: scaleSlider.value = modelData
                    }
                }
            }
        }
    }
}
