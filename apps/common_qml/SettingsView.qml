import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15
import "Typography.js" as Typography

Rectangle {
    id: settingsRoot
    objectName: "settingsRoot"
    color: "#f8fafc"

    property string currentFontFamily: "System Default"
    property string activeFontFamily: ""
    property int currentFontSize: 14
    property real currentUiScale: 1.0
    property var targetWindow: null

    signal settingsChanged()
    signal resetRequested()

    property alias fontFamilyCombo: fontFamilyCombo
    property alias fontSizeSlider: fontSizeSlider
    property alias btnFontSizeMinus: btnFontSizeMinus
    property alias btnFontSizePlus: btnFontSizePlus
    property alias scaleSlider: scaleSlider
    property alias btnResetSettings: btnResetSettings
    property alias previewCard: previewCard

    BundledFonts { id: bundledFonts }

    function resetToDefaults() {
        fontFamilyCombo.currentIndex = 0; fontSizeSlider.value = 14; scaleSlider.value = 100
        currentFontFamily = "System Default"; activeFontFamily = ""
        currentFontSize = 14; currentUiScale = 1.0
        resetRequested(); settingsChanged()
    }

    function applySettingsToWindow() {
        var win = targetWindow || Window.window || settingsRoot
        var factor = (currentFontSize / 14.0) * currentUiScale
        Typography.applyToTree(win, { family: activeFontFamily, factor: factor }, previewCard)
        var px = Math.round(currentFontSize * currentUiScale)
        if (typeof librarianAdmin !== "undefined" && librarianAdmin && librarianAdmin.setAppFont) librarianAdmin.setAppFont(activeFontFamily, px)
        if (typeof studentAdmin !== "undefined" && studentAdmin && studentAdmin.setAppFont) studentAdmin.setAppFont(activeFontFamily, px)
    }

    onSettingsChanged: applySettingsToWindow()
    onTargetWindowChanged: applySettingsToWindow()

    ScrollView {
        id: scrollPane
        anchors.fill: parent; anchors.margins: 24; clip: true

        ColumnLayout {
            width: Math.max(500, scrollPane.availableWidth)
            spacing: 16

            ColumnLayout {
                spacing: 4
                Text { text: "⚙️ การตั้งค่าระบบและการแสดงผล (Visual Settings)"; font.bold: true; font.pixelSize: 22; color: "#0f172a" }
                Text { text: "ปรับแต่งรูปแบบตัวอักษร, ขนาดฟอนต์ และมาตราส่วนหน้าจอ (UI Scaling 50% - 150%)"; font.pixelSize: 13; color: "#64748b" }
            }

            Rectangle {
                Layout.fillWidth: true; color: "#ffffff"; radius: 10; border.color: "#e2e8f0"
                implicitHeight: ctrlLayout.implicitHeight + 32

                ColumnLayout {
                    id: ctrlLayout; anchors.fill: parent; anchors.margins: 16; spacing: 14

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "รูปแบบฟอนต์ (Font Family):"; font.bold: true; color: "#1e293b"; Layout.minimumWidth: 160; Layout.preferredWidth: Math.max(180, implicitWidth); wrapMode: Text.Wrap }
                        ComboBox {
                            id: fontFamilyCombo; objectName: "fontFamilyCombo"; Layout.fillWidth: true
                            model: ["System Default", "Noto Sans", "Sarabun", "TH Sarabun New", "Segoe UI", "Sukhumvit Set", "Tahoma"]
                            onCurrentTextChanged: {
                                settingsRoot.currentFontFamily = currentText
                                settingsRoot.activeFontFamily = (currentText === "System Default") ? "" : currentText
                                settingsRoot.settingsChanged()
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "ขนาดตัวอักษร (Font Size):"; font.bold: true; color: "#1e293b"; Layout.minimumWidth: 160; Layout.preferredWidth: Math.max(180, implicitWidth); wrapMode: Text.Wrap }
                        Button { id: btnFontSizeMinus; objectName: "btnFontSizeMinus"; text: "−"; Layout.preferredWidth: 36; onClicked: fontSizeSlider.value = Math.max(10, fontSizeSlider.value - 1) }
                        Slider {
                            id: fontSizeSlider; objectName: "fontSizeSlider"; from: 10; to: 24; stepSize: 1; value: 14; Layout.fillWidth: true
                            onValueChanged: { settingsRoot.currentFontSize = Math.round(value); settingsRoot.settingsChanged() }
                        }
                        Button { id: btnFontSizePlus; objectName: "btnFontSizePlus"; text: "+"; Layout.preferredWidth: 36; onClicked: fontSizeSlider.value = Math.min(24, fontSizeSlider.value + 1) }
                        Rectangle {
                            Layout.preferredWidth: 60; height: 32; radius: 6; color: "#f1f5f9"
                            Text { anchors.centerIn: parent; text: settingsRoot.currentFontSize + " px"; font.bold: true; color: "#0f172a"; font.pixelSize: 12 }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "มาตราส่วน (UI Scaling):"; font.bold: true; color: "#1e293b"; Layout.minimumWidth: 160; Layout.preferredWidth: Math.max(180, implicitWidth); wrapMode: Text.Wrap }
                        Slider {
                            id: scaleSlider; objectName: "scaleSlider"; from: 50; to: 150; stepSize: 5; value: 100; Layout.fillWidth: true
                            onValueChanged: { settingsRoot.currentUiScale = Math.round(value) / 100.0; settingsRoot.settingsChanged() }
                        }
                        Rectangle {
                            Layout.preferredWidth: 60; height: 32; radius: 6; color: "#eff6ff"
                            Text { anchors.centerIn: parent; text: Math.round(scaleSlider.value) + "%"; font.bold: true; color: "#1d4ed8"; font.pixelSize: 12 }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true; spacing: 8
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

            Rectangle {
                id: previewCard; objectName: "previewCard"
                Layout.fillWidth: true; color: "#ffffff"; radius: 10; border.color: "#e2e8f0"
                implicitHeight: prevCol.implicitHeight + 32

                ColumnLayout {
                    id: prevCol; anchors.fill: parent; anchors.margins: 16; spacing: 12
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "👁️ ตัวอย่างการแสดงผล (Live Visual Preview)"; font.bold: true; font.pixelSize: 15; color: "#0f172a" }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: "ฟอนต์: " + settingsRoot.currentFontFamily + " | ขนาด: " + settingsRoot.currentFontSize + "px | สเกล: " + Math.round(settingsRoot.currentUiScale * 100) + "%"
                            color: "#64748b"; font.pixelSize: 12
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: "#f1f5f9" }

                    Text {
                        text: "โรงเรียนวิทยาศาสตร์จุฬาภรณราชวิทยาลัย (Princess Chulabhorn Science High School)"
                        font.family: settingsRoot.activeFontFamily
                        font.pixelSize: Math.round(settingsRoot.currentFontSize * 1.3 * settingsRoot.currentUiScale)
                        font.bold: true; color: "#1e293b"
                    }

                    Text {
                        text: "ระบบงานสารสนเทศและทะเบียนนักเรียน (Student Registry & Library Circulation System)\nทดสอบการแสดงผลภาษาไทย: กขคง ๑๒๓๔๕ ทดสอบสระบนล่าง ที่นี่ มีปัญหาสระลอยหรือไม่ 0123456789"
                        font.family: settingsRoot.activeFontFamily
                        font.pixelSize: Math.round(settingsRoot.currentFontSize * settingsRoot.currentUiScale)
                        color: "#334155"; wrapMode: Text.Wrap; Layout.fillWidth: true
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
                                font.pixelSize: Math.round(settingsRoot.currentFontSize * settingsRoot.currentUiScale)
                                font.family: settingsRoot.activeFontFamily
                            }
                        }
                        Button {
                            text: "ปุ่มตัวอย่าง (Sample Button)"
                            font.family: settingsRoot.activeFontFamily
                            font.pixelSize: Math.round(settingsRoot.currentFontSize * settingsRoot.currentUiScale)
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button {
                    id: btnResetSettings; objectName: "btnResetSettings"
                    text: "🔄 คืนค่าเริ่มต้น (Reset to Defaults)"
                    onClicked: settingsRoot.resetToDefaults()
                }
            }
        }
    }
}
