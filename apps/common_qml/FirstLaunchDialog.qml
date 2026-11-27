import QtQuick 2.15
import "Theme.js" as Theme
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

StyledDialog {
    id: firstLaunchDialog
    objectName: "firstLaunchDialog"
    title: "🎉 เริ่มต้นใช้งานระบบ (First Launch Setup)"
    width: parent ? Math.min(520, Math.max(300, parent.width - 32)) : 520
    standardButtons: Dialog.NoButton

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
            implicitHeight: Math.max(70, Math.round(bannerRow.implicitHeight + 24))
            height: implicitHeight
            clip: true
            color: Theme.accentSurface
            radius: 8
            border.color: Theme.borderLightBlue

            RowLayout {
                id: bannerRow
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12

                Text {
                    text: firstLaunchDialog.bannerIcon
                    font.pixelSize: 32
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: firstLaunchDialog.bannerTitle
                        font.bold: true
                        font.pixelSize: 15
                        color: Theme.accentDeep
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }

                    Text {
                        text: firstLaunchDialog.bannerSubtitle
                        font.pixelSize: 12
                        color: Theme.accentMid
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }
            }
        }

        Text {
            text: firstLaunchDialog.promptText
            font.bold: true
            font.pixelSize: 14
            color: Theme.textStrong
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        Text {
            text: firstLaunchDialog.explanationText
            font.pixelSize: 12
            color: Theme.textMuted
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        Text {
            id: firstLaunchStatusText
            objectName: "firstLaunchStatusText"
            text: ""
            font.pixelSize: 12
            color: text.indexOf("✗") !== -1 ? Theme.errorBright : Theme.successBright
            wrapMode: Text.Wrap
            Layout.fillWidth: true
            visible: text !== ""
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            StyledButton {
                id: firstLaunchImportBtn
                objectName: "firstLaunchImportBtn"
                Layout.fillWidth: true
                text: firstLaunchDialog.importButtonText
                variant: StyledButton.Primary
                onClicked: firstLaunchDialog.importClicked()
            }

            StyledButton {
                id: firstLaunchBlankBtn
                objectName: "firstLaunchBlankBtn"
                variant: StyledButton.Neutral
                Layout.fillWidth: true
                text: firstLaunchDialog.blankButtonText
                onClicked: firstLaunchDialog.blankClicked()
            }
        }
    }
}
