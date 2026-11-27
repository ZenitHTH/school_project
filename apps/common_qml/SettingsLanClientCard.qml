import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "Theme.js" as Theme

Rectangle {
    id: clientCardRoot
    Layout.fillWidth: true
    color: Theme.surfaceWhite
    radius: 10
    border.color: Theme.borderSubtle
    implicitHeight: clientLayout.implicitHeight + 32

    signal connectionUpdated(var status)

    property bool clientConnected: false
    property string connectionMode: "local"
    property string currentHost: ""
    property int currentPort: 8765
    property string connectionError: ""
    property string statusFeedback: ""

    property alias lanClientStatusBadge: lanClientStatusBadge
    property alias lanClientStatusBadgeText: lanClientStatusBadgeText
    property alias btnRefreshClientStatus: btnRefreshClientStatus
    property alias lanClientInfoBox: lanClientInfoBox
    property alias lanClientEndpointText: lanClientEndpointText
    property alias lanClientErrorBanner: lanClientErrorBanner
    property alias btnDiscoverClientServer: btnDiscoverClientServer
    property alias lanDiscoverFeedbackText: lanDiscoverFeedbackText
    property alias lanClientHostInput: lanClientHostInput
    property alias lanClientPortInput: lanClientPortInput
    property alias lanClientTokenInput: lanClientTokenInput
    property alias lanClientSaveStatusText: lanClientSaveStatusText
    property alias btnResetClientLan: btnResetClientLan
    property alias btnConnectSwitchServer: btnConnectSwitchServer

    function getClientAdapter() {
        return (typeof boothAdapter !== "undefined" && boothAdapter && boothAdapter.getConnectionStatus) ? boothAdapter : null
    }

    function _applyClientStatus(res, syncInputs) {
        if (!res) return
        if (res.connected !== undefined) clientConnected = !!res.connected
        if (res.mode !== undefined) connectionMode = res.mode || "local"
        if (res.host !== undefined) currentHost = (connectionMode === "local" && res.host === "local") ? "" : (res.host || "")
        if (res.port !== undefined) currentPort = res.port > 0 ? res.port : 8765
        connectionError = res.error || ""
        if (syncInputs) {
            lanClientHostInput.text = connectionMode === "lan" ? currentHost : ""
            lanClientPortInput.text = String(currentPort)
        }
    }

    function refreshFromAdapter() {
        var adapter = getClientAdapter()
        if (!adapter) return
        try {
            var res = JSON.parse(adapter.getConnectionStatus())
            _applyClientStatus(res, true)
            connectionUpdated(res)
        } catch (e) { connectionError = String(e) }
    }

    function discoverOnLan() {
        var adapter = getClientAdapter()
        if (!adapter || !adapter.discoverServer) return
        try {
            var res = JSON.parse(adapter.discoverServer())
            if (res.ok) {
                lanClientHostInput.text = res.host || ""
                lanClientPortInput.text = String(res.port > 0 ? res.port : 8765)
                lanDiscoverFeedbackText.text = "✓ พบเซิร์ฟเวอร์: " + res.host + ":" + res.port
            } else {
                lanDiscoverFeedbackText.text = "✗ ไม่พบเซิร์ฟเวอร์ใน LAN"
            }
        } catch (e) { lanDiscoverFeedbackText.text = "✗ ไม่พบเซิร์ฟเวอร์ใน LAN" }
    }

    function connectAndSwitch() {
        var host = lanClientHostInput.text.trim()
        var portVal = parseInt(lanClientPortInput.text, 10)
        if (!host) { statusFeedback = "✗ กรุณากรอก IP หรือ Host ของเซิร์ฟเวอร์"; return }
        if (isNaN(portVal) || portVal < 1 || portVal > 65535) { statusFeedback = "✗ กรุณากรอกพอร์ตที่ถูกต้อง (1-65535)"; return }
        var adapter = getClientAdapter()
        if (!adapter || !adapter.configureConnection) return
        try {
            var res = JSON.parse(adapter.configureConnection(host, portVal, lanClientTokenInput.text))
            _applyClientStatus(res, false)
            connectionUpdated(res)
            statusFeedback = res.connected
                ? ("✓ เชื่อมต่อเซิร์ฟเวอร์ " + res.host + ":" + res.port + " แล้ว")
                : ("✗ ไม่สามารถเชื่อมต่อ: " + (res.error || "ไม่ทราบสาเหตุ"))
        } catch (e) { statusFeedback = "✗ ไม่สามารถเชื่อมต่อ: " + String(e) }
    }

    Component.onCompleted: { if (getClientAdapter()) refreshFromAdapter() }

    component ClientFormLabel: Text {
        font.bold: true; color: Theme.textStrong
        Layout.minimumWidth: 110; Layout.preferredWidth: Math.max(130, Math.min(200, implicitWidth))
        wrapMode: Text.Wrap
    }

    ColumnLayout {
        id: clientLayout
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Text {
                text: "🔌 เชื่อมต่อ / สลับเซิร์ฟเวอร์ (Connect & Switch Server)"
                font.bold: true; font.pixelSize: 16; color: Theme.textStrong
                wrapMode: Text.Wrap; Layout.fillWidth: true
            }
            Rectangle {
                id: lanClientStatusBadge; objectName: "lanClientStatusBadge"; radius: 12
                Layout.maximumWidth: Math.max(140, clientLayout.width * 0.45)
                implicitWidth: Math.min(lanClientStatusBadgeText.implicitWidth + 24, Layout.maximumWidth)
                implicitHeight: Math.max(28, Math.round(lanClientStatusBadgeText.implicitHeight + 12)); height: implicitHeight
                color: clientCardRoot.connectionMode === "local" ? Theme.accentSurface : (clientCardRoot.clientConnected ? Theme.successBackground : Theme.errorBackground)
                border.color: clientCardRoot.connectionMode === "local" ? Theme.borderLightBlue : (clientCardRoot.clientConnected ? Theme.successBorder : Theme.errorBorder)
                border.width: 1
                Text {
                    id: lanClientStatusBadgeText; objectName: "lanClientStatusBadgeText"
                    anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
                    font.bold: true; font.pixelSize: 12
                    color: clientCardRoot.connectionMode === "local" ? Theme.accentDeep : (clientCardRoot.clientConnected ? Theme.successText : Theme.errorText)
                    text: clientCardRoot.connectionMode === "local" ? "● โหมดในเครื่อง (Local)" : (clientCardRoot.clientConnected ? "● เชื่อมต่อแล้ว (Connected)" : "✕ ไม่สามารถเชื่อมต่อ (Disconnected)")
                }
            }
            StyledButton { id: btnRefreshClientStatus; objectName: "btnRefreshClientStatus"; variant: StyledButton.Neutral; text: "🔄 ตรวจสอบ"; onClicked: clientCardRoot.refreshFromAdapter() }
        }

        Rectangle {
            id: lanClientInfoBox; objectName: "lanClientInfoBox"
            Layout.fillWidth: true; color: Theme.accentSurface; border.color: Theme.borderLightBlue; border.width: 1; radius: 8
            implicitHeight: clientInfoCol.implicitHeight + 24
            ColumnLayout {
                id: clientInfoCol; anchors.fill: parent; anchors.margins: 12; spacing: 6
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    Text { text: "โหมดการทำงาน:"; font.bold: true; color: Theme.accentDeep; wrapMode: Text.Wrap }
                    Text { text: clientCardRoot.connectionMode === "local" ? "Local DB" : "LAN Client"; font.bold: true; color: Theme.textPrimary; wrapMode: Text.Wrap; Layout.fillWidth: true }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    Text { text: "เซิร์ฟเวอร์ที่ใช้งาน:"; font.bold: true; color: Theme.accentDeep; wrapMode: Text.Wrap }
                    Text {
                        id: lanClientEndpointText; objectName: "lanClientEndpointText"
                        text: clientCardRoot.connectionMode === "local" ? "ฐานข้อมูลภายในเครื่อง (Local)" : (clientCardRoot.currentHost ? ("http://" + clientCardRoot.currentHost + ":" + clientCardRoot.currentPort) : "ยังไม่ได้เชื่อมต่อ")
                        font.bold: true; color: Theme.textPrimary; wrapMode: Text.Wrap; Layout.fillWidth: true
                    }
                }
            }
        }

        Rectangle {
            id: lanClientErrorBanner; objectName: "lanClientErrorBanner"
            visible: clientCardRoot.connectionError !== ""
            Layout.fillWidth: true; color: Theme.errorBackground; border.color: Theme.errorBorder; border.width: 1; radius: 6
            implicitHeight: Math.max(32, Math.round(lanClientErrorText.implicitHeight + 16))
            Text { id: lanClientErrorText; anchors.fill: parent; anchors.margins: 8; text: clientCardRoot.connectionError; color: Theme.errorText; font.pixelSize: 12; wrapMode: Text.Wrap; verticalAlignment: Text.AlignVCenter }
        }

        RowLayout {
            Layout.fillWidth: true; spacing: 10
            StyledButton { id: btnDiscoverClientServer; objectName: "btnDiscoverClientServer"; variant: StyledButton.Neutral; text: "🔍 ค้นหาเซิร์ฟเวอร์ใน LAN อัตโนมัติ (Auto-Discover)"; onClicked: clientCardRoot.discoverOnLan() }
            Text { id: lanDiscoverFeedbackText; objectName: "lanDiscoverFeedbackText"; text: ""; color: text.indexOf("✓") === 0 ? Theme.successDot : Theme.errorDot; font.bold: true; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
        }

        RowLayout {
            Layout.fillWidth: true
            ClientFormLabel { text: "Server IP / Host:" }
            StyledTextInput { id: lanClientHostInput; objectName: "lanClientHostInput"; Layout.fillWidth: true; placeholderText: "เช่น 192.168.1.10"; horizontalAlignment: TextInput.AlignLeft; verticalAlignment: TextInput.AlignVCenter; leftPadding: 12 }
        }
        RowLayout {
            Layout.fillWidth: true
            ClientFormLabel { text: "Port:" }
            StyledTextInput { id: lanClientPortInput; objectName: "lanClientPortInput"; Layout.fillWidth: true; text: "8765"; placeholderText: "8765"; horizontalAlignment: TextInput.AlignLeft; verticalAlignment: TextInput.AlignVCenter; leftPadding: 12; validator: IntValidator { bottom: 1; top: 65535 } }
        }
        RowLayout {
            Layout.fillWidth: true
            ClientFormLabel { text: "Token:" }
            StyledTextInput {
                id: lanClientTokenInput; objectName: "lanClientTokenInput"; Layout.fillWidth: true
                property bool showToken: false
                placeholderText: "เว้นว่างเพื่อใช้ค่าเดิม (ค่าเริ่มต้น 123456)"
                echoMode: showToken ? TextInput.Normal : TextInput.Password
                horizontalAlignment: TextInput.AlignLeft; verticalAlignment: TextInput.AlignVCenter; leftPadding: 12
            }
            StyledButton {
                id: btnToggleClientToken; objectName: "btnToggleClientToken"
                variant: StyledButton.Neutral
                text: lanClientTokenInput.showToken ? "ซ่อน" : "แสดง"
                onClicked: lanClientTokenInput.showToken = !lanClientTokenInput.showToken
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: clientLayout.width < 520 ? 1 : 3
            columnSpacing: 10
            rowSpacing: 8
            Text { id: lanClientSaveStatusText; objectName: "lanClientSaveStatusText"; text: clientCardRoot.statusFeedback; color: text.indexOf("✓") === 0 ? Theme.successDot : Theme.errorDot; font.bold: true; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true }
            StyledButton {
                id: btnResetClientLan; objectName: "btnResetClientLan"; variant: StyledButton.Neutral; text: "ค่าเริ่มต้น"
                Layout.alignment: Qt.AlignRight
                onClicked: { lanClientHostInput.text = ""; lanClientPortInput.text = "8765"; lanClientTokenInput.text = ""; lanDiscoverFeedbackText.text = ""; clientCardRoot.statusFeedback = "" }
            }
            StyledButton { id: btnConnectSwitchServer; objectName: "btnConnectSwitchServer"; variant: StyledButton.Primary; text: "🔌 เชื่อมต่อ / สลับเซิร์ฟเวอร์"; Layout.alignment: Qt.AlignRight; onClicked: clientCardRoot.connectAndSwitch() }
        }
    }
}
