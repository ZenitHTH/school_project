import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Dialog {
    id: firstLaunchDialog
    objectName: "firstLaunchDialog"
    title: "🎉 เริ่มต้นใช้งานระบบ (First Launch Setup)"
    modal: true
    anchors.centerIn: parent
    width: 520
    standardButtons: Dialog.NoButton
    closePolicy: Popup.CloseOnEscape

    property string bannerIcon: "🏫"
    property string bannerTitle: "ยินดีต้อนรับสู่ระบบ"
    property string bannerSubtitle: "ยังไม่พบข้อมูลในระบบ หรือเป็นการเริ่มต้นใช้งานครั้งแรก"
    property string promptText: "คุณมีไฟล์ข้อมูลเพื่อนำเข้าหรือไม่?"
    property string explanationText: "• หากมีไฟล์ข้อมูล: เลือกระบบนำเข้าเพื่อสร้างฐานข้อมูลอัตโนมัติ\n• หากไม่มีไฟล์: ระบบจะสร้างฐานข้อมูลเปล่าตามโครงสร้างมาตรฐานพร้อมใช้งาน"
    property string importButtonText: "📁 มีไฟล์ข้อมูล — เลือกไฟล์นำเข้า"
    property string blankButtonText: "🆕 ไม่มีไฟล์ — สร้างฐานข้อมูลเปล่า"

    signal importClicked()
    signal blankClicked()

    property alias statusText: firstLaunchStatusText.text

    ColumnLayout {
        spacing: 16
        width: parent.width

        Rectangle {
            Layout.fillWidth: true
            height: 70
            color: "#eff6ff"
            radius: 8
            border.color: "#bfdbfe"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12

                Text {
                    text: firstLaunchDialog.bannerIcon
                    font.pixelSize: 32
                }

                ColumnLayout {
                    spacing: 4

                    Text {
                        text: firstLaunchDialog.bannerTitle
                        font.bold: true
                        font.pixelSize: 15
                        color: "#1e3a8a"
                    }

                    Text {
                        text: firstLaunchDialog.bannerSubtitle
                        font.pixelSize: 12
                        color: "#3b82f6"
                    }
                }
            }
        }

        Text {
            text: firstLaunchDialog.promptText
            font.bold: true
            font.pixelSize: 14
            color: "#1e293b"
        }

        Text {
            text: firstLaunchDialog.explanationText
            font.pixelSize: 12
            color: "#64748b"
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        Text {
            id: firstLaunchStatusText
            objectName: "firstLaunchStatusText"
            text: ""
            font.pixelSize: 12
            color: text.indexOf("✗") !== -1 ? "#ef4444" : "#10b981"
            wrapMode: Text.Wrap
            Layout.fillWidth: true
            visible: text !== ""
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Button {
                id: firstLaunchImportBtn
                objectName: "firstLaunchImportBtn"
                Layout.fillWidth: true
                text: firstLaunchDialog.importButtonText
                highlighted: true
                onClicked: firstLaunchDialog.importClicked()
            }

            Button {
                id: firstLaunchBlankBtn
                objectName: "firstLaunchBlankBtn"
                Layout.fillWidth: true
                text: firstLaunchDialog.blankButtonText
                onClicked: firstLaunchDialog.blankClicked()
            }
        }
    }
}
