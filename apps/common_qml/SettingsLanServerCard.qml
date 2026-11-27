import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "Theme.js" as Theme

Rectangle {
    id: lanCardRoot
    Layout.fillWidth: true
    color: Theme.surfaceWhite
    radius: 10
    border.color: Theme.borderSubtle
    implicitHeight: lanLayout.implicitHeight + 32

    property bool serverRunning: false
    property bool serverEnabled: true
    property string serverIp: ""
    property int serverPort: 8765
    property int discoveryPort: 8766
    property string serverToken: "123456"
    property string serverError: ""
    property string saveFeedback: ""
    property alias lanStatusBadge: lanStatusBadge
    property alias btnRefreshLanStatus: btnRefreshLanStatus
    property alias lanEnabledCheck: lanEnabledCheck
    property alias lanPortInput: lanPortInput
    property alias lanDiscoveryPortInput: lanDiscoveryPortInput
    property alias lanTokenInput: lanTokenInput
    property alias btnResetLanDefaults: btnResetLanDefaults
    property alias btnSaveLanConfig: btnSaveLanConfig
    property alias lanSaveStatusText: lanSaveStatusText

    function getLanAdapter() { return (typeof librarianAdmin !== "undefined" && librarianAdmin && librarianAdmin.getLanConfig) ? librarianAdmin : null }

    function _applyLanState(res, syncInputs) {
        if (!res) return
        if (res.running !== undefined) serverRunning = !!res.running
        if (res.enabled !== undefined) serverEnabled = !!res.enabled
        if (res.ip !== undefined) serverIp = res.ip || ""
        if (res.port !== undefined) serverPort = res.port
        if (res.discovery_port !== undefined) discoveryPort = res.discovery_port
        if (res.token !== undefined) serverToken = res.token || ""
        serverError = res.error || ""
        if (syncInputs) {
            lanEnabledCheck.checked = serverEnabled
            lanPortInput.text = String(serverPort)
            lanDiscoveryPortInput.text = String(discoveryPort)
            lanTokenInput.text = serverToken
        }
    }

    function refreshFromAdapter() {
        var adapter = getLanAdapter()
        if (!adapter) return
        try { _applyLanState(JSON.parse(adapter.getLanConfig()), true) }
        catch (e) { serverError = String(e) }
    }

    function saveToAdapter() {
        var adapter = getLanAdapter()
        if (!adapter || !adapter.saveAndApplyLanConfig) return
        var portVal = parseInt(lanPortInput.text, 10) || 0
        var discVal = parseInt(lanDiscoveryPortInput.text, 10) || 0
        try {
            var res = JSON.parse(adapter.saveAndApplyLanConfig(lanEnabledCheck.checked, portVal, discVal, lanTokenInput.text))
            _applyLanState(res, !!res.ok)
            saveFeedback = res.ok ? "✓ บันทึกและอัปเดตเซิร์ฟเวอร์ LAN แล้ว" : ("✗ " + (res.error || "บันทึกไม่สำเร็จ"))
        } catch (e) { saveFeedback = "✗ บันทึกไม่สำเร็จ" }
    }

    Component.onCompleted: { if (getLanAdapter()) refreshFromAdapter() }

    component FormLabel: Text {
        font.bold: true; color: Theme.textStrong
        Layout.minimumWidth: 110; Layout.preferredWidth: Math.max(130, Math.min(200, implicitWidth))
        wrapMode: Text.Wrap
    }

    ColumnLayout {
        id: lanLayout
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Text {
                text: "🌐 เครือข่ายและเซิร์ฟเวอร์ (LAN Server & Self-Service Booth)"
                font.bold: true; font.pixelSize: 16; color: Theme.textStrong
                wrapMode: Text.Wrap; Layout.fillWidth: true
            }
            Rectangle {
                id: lanStatusBadge; objectName: "lanStatusBadge"; radius: 12
                Layout.maximumWidth: Math.max(140, lanLayout.width * 0.45)
                implicitWidth: Math.min(lanStatusBadgeText.implicitWidth + 24, Layout.maximumWidth)
                implicitHeight: Math.max(28, Math.round(lanStatusBadgeText.implicitHeight + 12)); height: implicitHeight
                color: lanCardRoot.serverRunning ? Theme.successBackground : (!lanCardRoot.serverEnabled ? Theme.surfaceHover : Theme.errorBackground)
                border.color: lanCardRoot.serverRunning ? Theme.successBorder : (!lanCardRoot.serverEnabled ? Theme.borderDefault : Theme.errorBorder)
                border.width: 1
                Text {
                    id: lanStatusBadgeText; objectName: "lanStatusBadgeText"
                    anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
                    font.bold: true; font.pixelSize: 12
                    color: lanCardRoot.serverRunning ? Theme.successText : (!lanCardRoot.serverEnabled ? Theme.textSecondary : Theme.errorText)
                    text: lanCardRoot.serverRunning ? "● กำลังทำงาน (Online)" : (!lanCardRoot.serverEnabled ? "○ ปิดใช้งาน (Disabled)" : "✕ ไม่สามารถเริ่มเซิร์ฟเวอร์ (Error)")
                }
            }
            StyledButton { id: btnRefreshLanStatus; objectName: "btnRefreshLanStatus"; variant: StyledButton.Neutral; text: "🔄 รีเฟรช"; onClicked: lanCardRoot.refreshFromAdapter() }
        }

        Rectangle {
            id: lanInfoBox
            objectName: "lanInfoBox"
            Layout.fillWidth: true
            color: Theme.accentSurface
            border.color: Theme.borderLightBlue; border.width: 1; radius: 8
            implicitHeight: infoCol.implicitHeight + 24
            ColumnLayout {
                id: infoCol
                anchors.fill: parent; anchors.margins: 12; spacing: 6
                GridLayout {
                    Layout.fillWidth: true
                    columns: lanInfoBox.width < 460 ? 2 : 4
                    columnSpacing: 10; rowSpacing: 6
                    Text { text: "Server LAN IP:"; font.bold: true; color: Theme.accentDeep; wrapMode: Text.Wrap }
                    Text { id: lanIpValueText; objectName: "lanIpValueText"; text: lanCardRoot.serverIp || "-"; font.bold: true; color: Theme.textPrimary; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Text { text: "Discovery UDP Port:"; font.bold: true; color: Theme.accentDeep; wrapMode: Text.Wrap }
                    Text { text: String(lanCardRoot.discoveryPort); font.bold: true; color: Theme.textPrimary; wrapMode: Text.Wrap }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    Text { text: "Endpoint URL:"; font.bold: true; color: Theme.accentDeep; wrapMode: Text.Wrap }
                    Text {
                        id: lanEndpointValueText; objectName: "lanEndpointValueText"
                        text: lanCardRoot.serverRunning ? ("http://" + lanCardRoot.serverIp + ":" + lanCardRoot.serverPort) : "ไม่ได้เปิดให้บริการ"
                        font.bold: true; color: Theme.textPrimary; wrapMode: Text.Wrap; Layout.fillWidth: true
                    }
                }
                Text {
                    text: "เครื่อง Self-Service Booth ในวง LAN เดียวกันสามารถค้นหาอัตโนมัติ (UDP) หรือเชื่อมต่อด้วย Endpoint URL และ Token ด้านล่างนี้"
                    font.pixelSize: 12; color: Theme.textSecondary; wrapMode: Text.Wrap; Layout.fillWidth: true
                }
            }
        }

        Rectangle {
            id: lanErrorBanner
            objectName: "lanErrorBanner"
            visible: lanCardRoot.serverError !== ""
            Layout.fillWidth: true
            color: Theme.errorBackground; border.color: Theme.errorBorder; border.width: 1; radius: 6
            implicitHeight: Math.max(32, Math.round(lanErrorText.implicitHeight + 16))
            Text { id: lanErrorText; anchors.fill: parent; anchors.margins: 8; text: lanCardRoot.serverError; color: Theme.errorText; font.pixelSize: 12; wrapMode: Text.Wrap; verticalAlignment: Text.AlignVCenter }
        }

        CheckBox {
            id: lanEnabledCheck; objectName: "lanEnabledCheck"; checked: true
            text: "เปิดให้บริการ LAN Server สำหรับเครื่อง Self-Service Booth"
            Layout.fillWidth: true
            implicitHeight: Math.max(28, Math.round(lanCheckText.implicitHeight + 10)); height: implicitHeight
            contentItem: Text {
                id: lanCheckText
                width: lanEnabledCheck.availableWidth
                text: lanEnabledCheck.text; font: lanEnabledCheck.font; color: Theme.textPrimary
                verticalAlignment: Text.AlignVCenter; wrapMode: Text.Wrap
                leftPadding: (lanEnabledCheck.indicator ? lanEnabledCheck.indicator.width : 20) + lanEnabledCheck.spacing
            }
        }

        RowLayout {
            Layout.fillWidth: true
            FormLabel { text: "HTTP Port:" }
            StyledTextInput { id: lanPortInput; objectName: "lanPortInput"; Layout.fillWidth: true; text: "8765"; placeholderText: "8765"; horizontalAlignment: TextInput.AlignLeft; verticalAlignment: TextInput.AlignVCenter; leftPadding: 12; validator: IntValidator { bottom: 1; top: 65535 } }
        }
        RowLayout {
            Layout.fillWidth: true
            FormLabel { text: "Discovery UDP Port:" }
            StyledTextInput { id: lanDiscoveryPortInput; objectName: "lanDiscoveryPortInput"; Layout.fillWidth: true; text: "8766"; placeholderText: "8766"; horizontalAlignment: TextInput.AlignLeft; verticalAlignment: TextInput.AlignVCenter; leftPadding: 12; validator: IntValidator { bottom: 1; top: 65535 } }
        }
        RowLayout {
            Layout.fillWidth: true
            FormLabel { text: "Token สำหรับเชื่อมต่อ (Booth):" }
            StyledTextInput {
                id: lanTokenInput; objectName: "lanTokenInput"; Layout.fillWidth: true
                property bool showToken: false
                text: "123456"; placeholderText: "123456"
                echoMode: showToken ? TextInput.Normal : TextInput.Password
                horizontalAlignment: TextInput.AlignLeft; verticalAlignment: TextInput.AlignVCenter; leftPadding: 12
            }
            StyledButton {
                id: btnToggleServerToken; objectName: "btnToggleServerToken"
                variant: StyledButton.Neutral
                text: lanTokenInput.showToken ? "ซ่อน" : "แสดง"
                onClicked: lanTokenInput.showToken = !lanTokenInput.showToken
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: lanLayout.width < 520 ? 1 : 3
            columnSpacing: 10
            rowSpacing: 8
            Text { id: lanSaveStatusText; objectName: "lanSaveStatusText"; text: lanCardRoot.saveFeedback; color: text.indexOf("✓") === 0 ? Theme.successDot : Theme.errorDot; font.bold: true; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true }
            StyledButton {
                id: btnResetLanDefaults; objectName: "btnResetLanDefaults"; variant: StyledButton.Neutral; text: "คืนค่าเริ่มต้น LAN"
                Layout.alignment: Qt.AlignRight
                onClicked: { lanEnabledCheck.checked = true; lanPortInput.text = "8765"; lanDiscoveryPortInput.text = "8766"; lanTokenInput.text = "123456"; lanCardRoot.saveFeedback = "" }
            }
            StyledButton { id: btnSaveLanConfig; objectName: "btnSaveLanConfig"; variant: StyledButton.Primary; text: "💾 บันทึกและใช้การตั้งค่า LAN"; Layout.alignment: Qt.AlignRight; onClicked: lanCardRoot.saveToAdapter() }
        }
    }
}
