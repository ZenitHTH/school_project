import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../common_qml"

ApplicationWindow {
    id: boothWindow
    visible: true
    width: 1024
    height: 768
    minimumWidth: 800
    minimumHeight: 600
    title: "จุดบริการยืม-คืนหนังสืออัตโนมัติ (Self-Service Booth)"
    color: "#0f172a"

    property var identifiedStudent: null
    property var connectionStatus: ({"connected": true, "host": "local", "port": 8765, "mode": "local", "error": ""})
    property bool isDbEmpty: false

    Component.onCompleted: {
        refreshConnectionStatus()
        refreshDbEmpty()
    }

    StackLayout {
        id: kioskStack
        objectName: "kioskStack"
        anchors.fill: parent
        currentIndex: 0

        Item {
            id: kioskHomePage
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.centerIn: parent
                width: Math.min(parent.width - 80, 700)
                spacing: 18

        Text {
            text: "📖 บริการยืม-คืนหนังสือด้วยตนเอง"
            color: "#ffffff"
            font.bold: true
            font.pixelSize: 28
            Layout.alignment: Qt.AlignHCenter
        }

        // LAN Connection Status Bar
        Rectangle {
            id: lanStatusBanner
            objectName: "lanStatusBanner"
            Layout.fillWidth: true
            implicitHeight: Math.max(40, Math.round(lanStatusRow.implicitHeight + 16))
            height: implicitHeight
            radius: 8
            color: connectionStatus.mode === "local"
                   ? "#1e293b"
                   : (connectionStatus.connected ? "#064e3b" : "#450a0a")
            border.color: connectionStatus.mode === "local"
                          ? "#334155"
                          : (connectionStatus.connected ? "#10b981" : "#ef4444")

            RowLayout {
                id: lanStatusRow
                anchors.fill: parent
                anchors.margins: 10
                spacing: 12

                Text {
                    id: lanStatusText
                    objectName: "lanStatusText"
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    font.pixelSize: 13
                    font.bold: true
                    color: connectionStatus.mode === "local"
                           ? "#cbd5e1"
                           : (connectionStatus.connected ? "#6ee7b7" : "#fca5a5")
                    text: connectionStatus.mode === "local"
                          ? "โหมดฐานข้อมูลในเครื่อง (Local)"
                          : (connectionStatus.connected
                             ? ("🟢 เชื่อมต่อเซิร์ฟเวอร์: " + connectionStatus.host + ":" + connectionStatus.port)
                             : ("🔴 ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์" + (connectionStatus.error ? " (" + connectionStatus.error + ")" : "")))
                }

                StyledButton {
                    objectName: "btnLanSettings"
                    variant: StyledButton.Neutral
                    text: "ตั้งค่าเซิร์ฟเวอร์"
                    onClicked: openLanSettings()
                }

                StyledButton {
                    id: btnOpenBoothSettings
                    objectName: "btnOpenBoothSettings"
                    variant: StyledButton.Primary
                    text: "⚙️ ตั้งค่าระบบ"
                    onClicked: openBoothSettings()
                }
            }
        }

        // Empty DB Warning Banner
        Rectangle {
            id: emptyDbWarningBanner
            objectName: "emptyDbWarningBanner"
            Layout.fillWidth: true
            implicitHeight: Math.max(48, Math.round(emptyDbRow.implicitHeight + 20))
            height: implicitHeight
            color: "#451a03"
            radius: 8
            border.color: "#b45309"
            visible: boothWindow.isDbEmpty

            RowLayout {
                id: emptyDbRow
                anchors.fill: parent
                anchors.margins: 12
                spacing: 10
                Text {
                    text: "⚠️"
                    font.pixelSize: 22
                }
                ColumnLayout {
                    spacing: 2
                    Layout.fillWidth: true
                    Text {
                        text: "ยังไม่มีข้อมูลในระบบ หรือฐานข้อมูลว่าง"
                        color: "#fde047"
                        font.bold: true
                        font.pixelSize: 13
                    }
                    Text {
                        text: "กรุณาติดต่อบรรณารักษ์เพื่อทำการ Sync ข้อมูลนักเรียน/หนังสือเข้าระบบก่อนเริ่มใช้งาน"
                        color: "#fef08a"
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }
        }

        // Student Card
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: Math.max(120, Math.round(studentCardCol.implicitHeight + 36))
            height: implicitHeight
            color: "#1e293b"
            radius: 12
            border.color: "#334155"

            ColumnLayout {
                id: studentCardCol
                anchors.fill: parent
                anchors.margins: 18
                spacing: 10

                Text {
                    text: "ขั้นตอนที่ 1: แตะบัตรหรือกรอกรหัสนักเรียน"
                    color: "#94a3b8"
                    font.pixelSize: 14
                }

                RowLayout {
                    StyledSearchField {
                        id: studentIdInput
                        objectName: "studentIdInput"
                        placeholderText: "พิมพ์รหัสนักเรียน..."
                        font.pixelSize: 18
                        horizontalAlignment: TextInput.AlignLeft
                        verticalAlignment: TextInput.AlignVCenter
                        Layout.fillWidth: true
                        onAccepted: identifyStudent()
                    }
                    StyledButton {
                        objectName: "btnIdentify"
                        variant: StyledButton.Primary
                        text: "ยืนยันตัวตน"
                        highlighted: true
                        onClicked: identifyStudent()
                    }
                }

                Text {
                    id: studentStatusMsg
                    objectName: "studentStatusMsg"
                    text: boothWindow.identifiedStudent ? ("ยินดีต้อนรับ: " + boothWindow.identifiedStudent.full_name) : "ยังไม่ได้ระบุตัวตน"
                    color: boothWindow.identifiedStudent ? "#34d399" : "#64748b"
                    font.bold: true
                    font.pixelSize: 15
                }
            }
        }

        // Book Scan Card
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: Math.max(130, Math.round(bookCardCol.implicitHeight + 36))
            height: implicitHeight
            color: "#1e293b"
            radius: 12
            border.color: "#334155"

            ColumnLayout {
                id: bookCardCol
                anchors.fill: parent
                anchors.margins: 18
                spacing: 12

                Text {
                    text: "ขั้นตอนที่ 2: สแกนบาร์โค้ดหนังสือ"
                    color: "#94a3b8"
                    font.pixelSize: 14
                }

                StyledSearchField {
                    id: bookBarcodeInput
                    objectName: "bookBarcodeInput"
                    placeholderText: "สแกนบาร์โค้ดหนังสือ..."
                    font.pixelSize: 18
                    horizontalAlignment: TextInput.AlignLeft
                    verticalAlignment: TextInput.AlignVCenter
                    Layout.fillWidth: true
                }

                RowLayout {
                    spacing: 16
                    Layout.alignment: Qt.AlignHCenter

                    StyledButton {
                        objectName: "btnCheckout"
                        variant: StyledButton.Primary
                        text: "✅ ยืมหนังสือ (Checkout)"
                        highlighted: true
                        enabled: boothWindow.identifiedStudent !== null
                        onClicked: doCheckout()
                    }

                    StyledButton {
                        objectName: "btnReturn"
                        variant: StyledButton.Neutral
                        text: "📥 คืนหนังสือ (Return)"
                        onClicked: doReturn()
                    }
                }
            }
        }

        // Result Message Banner
        ActionFeedbackBanner {
            id: feedbackBanner
            objectName: "feedbackBanner"
            Layout.fillWidth: true
            font.pixelSize: 16
            text: "กรุณาระบุตัวตนเพื่อเริ่มทำรายการ"
        }

        StyledButton {
            objectName: "btnLogout"
            variant: StyledButton.Neutral
            text: "เสร็จสิ้น / ออกจากระบบ"
            Layout.alignment: Qt.AlignHCenter
            onClicked: {
                boothWindow.identifiedStudent = null
                studentIdInput.text = ""
                bookBarcodeInput.text = ""
                feedbackBanner.isError = false
                    feedbackBanner.text = "ขอบคุณที่ใช้บริการ"
                }
            }
        }
    }

    ColumnLayout {
        id: boothSettingsPage
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: Math.max(52, Math.round(settingsTopRow.implicitHeight + 20))
            height: implicitHeight
            color: "#1e293b"

            RowLayout {
                id: settingsTopRow
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12

                Text {
                    text: "⚙️ ตั้งค่าระบบและเชื่อมต่อเซิร์ฟเวอร์ (Booth Settings)"
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 16
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }

                StyledButton {
                    id: btnBackToKiosk
                    objectName: "btnBackToKiosk"
                    variant: StyledButton.Neutral
                    text: "← กลับหน้าบริการ (Back to Kiosk)"
                    onClicked: closeBoothSettings()
                }
            }
        }

        SettingsView {
            id: boothSettingsView
            objectName: "boothSettingsView"
            showLanClientCard: true
            targetWindow: boothWindow
            Layout.fillWidth: true
            Layout.fillHeight: true
            onLanConnectionUpdated: function(st) {
                boothWindow.connectionStatus = st
                boothWindow.refreshDbEmpty()
            }
        }
    }
    }

    LanSettingsDialog {
        id: lanSettingsDialog
        onAccepted: {
            applyLanSettings()
            close()
        }
        onAutoDiscoverRequested: runAutoDiscover()
    }

    Timer {
        id: reconnectTimer
        objectName: "lanReconnectTimer"
        interval: 5000
        repeat: true
        running: connectionStatus.mode === "lan" && !connectionStatus.connected && !lanSettingsDialog.visible
        onTriggered: {
            refreshConnectionStatus()
            if (connectionStatus.connected) {
                refreshDbEmpty()
            }
        }
    }

    function refreshConnectionStatus() {
        if (typeof boothAdapter === "undefined" || boothAdapter === null || !boothAdapter.getConnectionStatus) {
            return
        }
        try {
            connectionStatus = JSON.parse(boothAdapter.getConnectionStatus())
        } catch (e) {}
    }

    function refreshDbEmpty() {
        if (typeof boothAdapter === "undefined" || boothAdapter === null) {
            isDbEmpty = false
            return
        }
        isDbEmpty = boothAdapter.isDatabaseEmpty()
    }

    function openBoothSettings() {
        boothSettingsView.refreshLanClientInfo()
        kioskStack.currentIndex = 1
    }

    function closeBoothSettings() {
        kioskStack.currentIndex = 0
        refreshConnectionStatus()
        refreshDbEmpty()
    }

    function openLanSettings() {
        refreshConnectionStatus()
        lanSettingsDialog.hostText = connectionStatus.mode === "lan" ? (connectionStatus.host || "") : ""
        lanSettingsDialog.portText = String(connectionStatus.port > 0 ? connectionStatus.port : 8765)
        lanSettingsDialog.tokenText = ""
        lanSettingsDialog.discoverStatusText = ""
        lanSettingsDialog.open()
    }

    function runAutoDiscover() {
        if (typeof boothAdapter === "undefined" || boothAdapter === null || !boothAdapter.discoverServer) {
            return
        }
        var res = JSON.parse(boothAdapter.discoverServer())
        if (res.ok) {
            lanSettingsDialog.hostText = res.host
            lanSettingsDialog.portText = String(res.port)
            lanSettingsDialog.discoverStatusText = "พบเซิร์ฟเวอร์: " + res.host + ":" + res.port
        } else {
            lanSettingsDialog.discoverStatusText = "ไม่พบเซิร์ฟเวอร์ในเครือข่าย LAN"
        }
    }

    function applyLanSettings() {
        if (typeof boothAdapter === "undefined" || boothAdapter === null || !boothAdapter.configureConnection) {
            return
        }
        var portNum = parseInt(lanSettingsDialog.portText) || 8765
        var res = JSON.parse(boothAdapter.configureConnection(lanSettingsDialog.hostText, portNum, lanSettingsDialog.tokenText))
        connectionStatus = res
        refreshDbEmpty()
    }

    function identifyStudent() {
        var res = JSON.parse(boothAdapter.searchStudents(studentIdInput.text))
        if (res.length > 0) {
            boothWindow.identifiedStudent = res[0]
            feedbackBanner.isError = false
            feedbackBanner.text = "ระบุตัวตนสำเร็จ: " + res[0].full_name
        } else {
            feedbackBanner.isError = true
            feedbackBanner.text = "ไม่พบรหัสนักเรียนในระบบ"
        }
    }

    function doCheckout() {
        if (!boothWindow.identifiedStudent || !bookBarcodeInput.text) {
            feedbackBanner.isError = true
            feedbackBanner.text = "กรุณากรอกข้อมูลให้ครบถ้วน"
            return
        }
        var res = JSON.parse(boothAdapter.checkout(boothWindow.identifiedStudent.student_id, bookBarcodeInput.text))
        if (res.ok) {
            feedbackBanner.isError = false
            feedbackBanner.text = "ยืมหนังสือสำเร็จ! กำหนดคืน: " + res.data.due_at.substring(0, 10)
            bookBarcodeInput.text = ""
        } else {
            feedbackBanner.isError = true
            feedbackBanner.text = "ยืมไม่สำเร็จ: " + res.error
        }
    }

    function doReturn() {
        if (!bookBarcodeInput.text) {
            feedbackBanner.isError = true
            feedbackBanner.text = "กรุณาสแกนบาร์โค้ดหนังสือที่ต้องการคืน"
            return
        }
        var res = JSON.parse(boothAdapter.returnByBarcode(bookBarcodeInput.text))
        if (res.ok) {
            feedbackBanner.isError = false
            feedbackBanner.text = "คืนหนังสือสำเร็จเรียบร้อยแล้ว ขอบคุณที่ใช้บริการ"
            bookBarcodeInput.text = ""
        } else {
            feedbackBanner.isError = true
            feedbackBanner.text = "คืนไม่สำเร็จ: " + res.error
        }
    }
}
