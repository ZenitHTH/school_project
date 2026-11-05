import QtQuick 2.15
import "Theme.js" as Theme
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15
import "Typography.js" as Typography

Rectangle {
    id: settingsRoot
    objectName: "settingsRoot"
    color: Theme.surfaceSubtle

    property string currentFontFamily: "System Default"
    property string activeFontFamily: ""
    property int currentFontSize: 14
    property real currentUiScale: 1.0
    property var targetWindow: null

    signal settingsChanged()
    signal resetRequested()

    property alias fontFamilyCombo: controlsCard.fontFamilyCombo
    property alias fontSizeSlider: controlsCard.fontSizeSlider
    property alias btnFontSizeMinus: controlsCard.btnFontSizeMinus
    property alias btnFontSizePlus: controlsCard.btnFontSizePlus
    property alias scaleSlider: controlsCard.scaleSlider
    property alias btnResetSettings: footerBar.btnResetSettings
    property alias btnSaveSettings: footerBar.btnSaveSettings
    property alias previewCard: previewCard

    BundledFonts { id: bundledFonts }
    Timer {
        id: statusTimer
        interval: 4000
        repeat: false
        onTriggered: footerBar.saveStatusText.text = ""
    }

    function getActiveAdapter() {
        if (typeof librarianAdmin !== "undefined" && librarianAdmin) return librarianAdmin
        if (typeof studentAdmin !== "undefined" && studentAdmin) return studentAdmin
        return null
    }

    function _applySettingsPayload(data) {
        if (!data) return
        if (data.font_size) {
            currentFontSize = data.font_size
            fontSizeSlider.value = data.font_size
        }
        if (data.ui_scale) {
            currentUiScale = data.ui_scale
            scaleSlider.value = Math.round(data.ui_scale * 100)
        }
        if (data.font_family) {
            currentFontFamily = data.font_family
            activeFontFamily = (data.font_family === "System Default") ? "" : data.font_family
            var idx = fontFamilyCombo.model.indexOf(data.font_family)
            if (idx >= 0) {
                fontFamilyCombo.currentIndex = idx
            }
        }
    }

    function loadPersistedSettings() {
        var adapter = getActiveAdapter()
        if (!adapter || !adapter.loadSettings) return
        try {
            var raw = adapter.loadSettings()
            var res = JSON.parse(raw)
            _applySettingsPayload(res.data || res)
            applySettingsToWindow()
        } catch (e) {
            console.warn("Failed to load persisted settings:", e)
        }
    }

    function saveSettings() {
        var adapter = getActiveAdapter()
        if (!adapter || !adapter.saveSettings) {
            footerBar.saveStatusText.text = "✓ บันทึกการตั้งค่าเรียบร้อยแล้ว"
            statusTimer.restart()
            return
        }
        try {
            var res = JSON.parse(adapter.saveSettings(currentFontFamily, currentFontSize, currentUiScale))
            footerBar.saveStatusText.text = res.ok ? "✓ บันทึกการตั้งค่าเรียบร้อยแล้ว" : ("✗ " + (res.error || "บันทึกไม่สำเร็จ"))
        } catch (e) {
            console.warn("Failed to save settings:", e)
            footerBar.saveStatusText.text = "✗ บันทึกไม่สำเร็จ"
        }
        statusTimer.restart()
    }

    function resetToDefaults() {
        var adapter = getActiveAdapter()
        if (adapter && adapter.resetSettings) {
            try {
                adapter.resetSettings()
            } catch (e) {
                console.warn("Failed to reset settings via adapter:", e)
            }
        }
        fontFamilyCombo.currentIndex = 0
        fontSizeSlider.value = 14
        scaleSlider.value = 100
        currentFontFamily = "System Default"
        activeFontFamily = ""
        currentFontSize = 14
        currentUiScale = 1.0
        footerBar.saveStatusText.text = ""
        resetRequested()
        settingsChanged()
    }

    function applySettingsToWindow() {
        var win = targetWindow || Window.window || settingsRoot
        var factor = (currentFontSize / 14.0) * currentUiScale
        Typography.applyToTree(win, { family: activeFontFamily, factor: factor }, previewCard)
        var px = Math.round(currentFontSize * currentUiScale)
        var adapter = getActiveAdapter()
        if (adapter && adapter.setAppFont) adapter.setAppFont(activeFontFamily, px)
    }

    Component.onCompleted: loadPersistedSettings()
    onSettingsChanged: {
        applySettingsToWindow()
        if (footerBar.saveStatusText.text !== "") {
            footerBar.saveStatusText.text = ""
        }
    }
    onTargetWindowChanged: applySettingsToWindow()

    ScrollView {
        id: scrollPane
        anchors.fill: parent
        anchors.margins: 24
        clip: true

        ColumnLayout {
            width: Math.max(500, scrollPane.availableWidth)
            spacing: 16

            SettingsHeader {}

            SettingsControlsCard {
                id: controlsCard
                onFontChanged: {
                    settingsRoot.currentFontFamily = family
                    settingsRoot.activeFontFamily = (family === "System Default") ? "" : family
                    settingsRoot.settingsChanged()
                }
                onFontSizeChanged: {
                    settingsRoot.currentFontSize = size
                    settingsRoot.settingsChanged()
                }
                onUiScaleChanged: {
                    settingsRoot.currentUiScale = scale
                    settingsRoot.settingsChanged()
                }
            }

            SettingsPreviewCard {
                id: previewCard
                objectName: "previewCard"
                currentFontFamily: settingsRoot.currentFontFamily
                activeFontFamily: settingsRoot.activeFontFamily
                currentFontSize: settingsRoot.currentFontSize
                currentUiScale: settingsRoot.currentUiScale
            }

            SettingsFooter {
                id: footerBar
                onResetClicked: settingsRoot.resetToDefaults()
                onSaveClicked: settingsRoot.saveSettings()
            }
        }
    }
}
