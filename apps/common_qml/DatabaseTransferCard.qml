import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "Theme.js" as Theme
import "Typography.js" as Typography

Rectangle {
    id: root
    objectName: "databaseTransferCard"
    Layout.fillWidth: true
    color: Theme.surfaceWhite
    radius: 10
    border.color: Theme.borderSubtle
    implicitHeight: cardLayout.implicitHeight + 32
    height: implicitHeight

    property string domainTitle: "ส่งออก / นำเข้าฐานข้อมูลหนังสือ (Book Database)"
    property string domainSubtitle: "สำรองข้อมูลหรือซิงค์หมวดหมู่ รายการหนังสือ และบาร์โค้ด (.sqlite / .xlsx) พร้อมตรวจสอบ SHA-256 และ Diff ก่อนนำเข้า"
    property string selectedImportPath: ""
    property bool previewReady: false
    property bool includeCirculation: false
    readonly property string selectedFormat: transferFormatCombo.currentValue || "sqlite"
    readonly property string selectedMode: transferModeCombo.currentValue || "merge"

    property alias btnExportDb: btnExportDb
    property alias btnPreviewImportDb: btnPreviewImportDb
    property alias btnApplyImportDb: btnApplyImportDb
    property alias transferFormatCombo: transferFormatCombo
    property alias transferModeCombo: transferModeCombo
    property alias diffSummaryText: diffSummaryText
    property alias statusBanner: statusBanner

    signal exportRequested(string path, string fmt)
    signal previewRequested(string path, string mode)
    signal importRequested(string path, string mode)

    function acceptExportPath(fileUrlOrPath) {
        exportRequested(String(fileUrlOrPath), selectedFormat)
    }

    function acceptImportPath(fileUrlOrPath) {
        selectedImportPath = String(fileUrlOrPath)
        clearPreview()
        previewRequested(selectedImportPath, selectedMode)
    }

    function clearPreview() {
        previewReady = false
        diffSummaryText.text = ""
    }

    function setPreviewResult(res) {
        if (res && res.ok) {
            var d = res.data || {}
            var skipped = d.skipped_copies !== undefined ? d.skipped_copies : (d.skipped_locked_copies || 0)
            var parts = [
                "สรุปผลการตรวจสอบ (" + (selectedMode === "replace" ? "แทนที่ทั้งหมด: Replace" : "ผสานข้อมูล: Merge") + "):",
                "• หมวดหมู่ใหม่: " + (d.new_categories || 0)
                    + " | หนังสือใหม่: " + (d.new_books || 0)
                    + " | อัปเดตหนังสือ: " + (d.updated_books || 0)
                    + " | บาร์โค้ดใหม่: " + (d.new_copies || 0)
                    + (skipped > 0 ? (" | ข้ามที่มีอยู่แล้ว: " + skipped) : "")
            ]
            diffSummaryText.text = parts.join("\n")
            if (d.can_apply === false) {
                previewReady = false
                statusBanner.isError = true
                statusBanner.text = "✗ " + (d.blocked_reason || "ไม่สามารถแทนที่ฐานข้อมูลได้ในขณะนี้")
            } else {
                previewReady = true
                statusBanner.text = ""
            }
        } else {
            clearPreview()
            statusBanner.isError = true
            statusBanner.text = "✗ " + ((res && res.error) ? res.error : "ตรวจสอบไฟล์นำเข้าไม่สำเร็จ")
        }
    }

    function setExportResult(res) {
        if (res && res.ok) {
            statusBanner.isError = false
            var outPath = (res.data && res.data.output_path) ? res.data.output_path : ""
            statusBanner.text = "✓ ส่งออกฐานข้อมูลสำเร็จ" + (outPath ? (": " + outPath) : "")
        } else {
            statusBanner.isError = true
            statusBanner.text = "✗ " + ((res && res.error) ? res.error : "ส่งออกฐานข้อมูลไม่สำเร็จ")
        }
    }

    function setImportResult(res) {
        previewReady = false
        if (res && res.ok) {
            statusBanner.isError = false
            statusBanner.text = "✓ นำเข้าข้อมูลฐานข้อมูลสำเร็จเรียบร้อยแล้ว"
        } else {
            statusBanner.isError = true
            statusBanner.text = "✗ " + ((res && res.error) ? res.error : "นำเข้าข้อมูลฐานข้อมูลไม่สำเร็จ")
        }
    }

    FileDialog {
        id: exportFileDialog
        title: "บันทึกไฟล์ส่งออกฐานข้อมูล"
        fileMode: FileDialog.SaveFile
        nameFilters: root.selectedFormat === "xlsx"
            ? ["Excel Workbook (*.xlsx)", "All files (*)"]
            : ["SQLite Database Bundle (*.sqlite *.db)", "All files (*)"]
        onAccepted: root.acceptExportPath(selectedFile.toString())
    }

    FileDialog {
        id: importFileDialog
        title: "เลือกไฟล์ฐานข้อมูลเพื่อตรวจสอบและนำเข้า"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Book Database Bundle (*.sqlite *.db *.xlsx)", "All files (*)"]
        onAccepted: root.acceptImportPath(selectedFile.toString())
    }

    ColumnLayout {
        id: cardLayout
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        Text {
            text: root.domainTitle
            font.bold: true
            font.pixelSize: 16
            color: Theme.textStrong
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        Text {
            text: root.domainSubtitle
            font.pixelSize: 12
            color: Theme.textMuted
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        Flow {
            Layout.fillWidth: true
            spacing: 10

            StyledComboBox {
                id: transferFormatCombo
                objectName: "transferFormatCombo"
                width: Math.max(200, Math.min(280, cardLayout.width))
                textRole: "label"
                valueRole: "value"
                model: [
                    { label: "SQLite (.sqlite)", value: "sqlite" },
                    { label: "Excel (.xlsx)", value: "xlsx" }
                ]
            }

            StyledButton {
                id: btnExportDb
                objectName: "btnExportDb"
                variant: StyledButton.Neutral
                text: "📤 ส่งออกฐานข้อมูล..."
                onClicked: exportFileDialog.open()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 1
            height: 1
            color: Theme.borderSubtle
        }

        Flow {
            Layout.fillWidth: true
            spacing: 10

            StyledComboBox {
                id: transferModeCombo
                objectName: "transferModeCombo"
                width: Math.max(220, Math.min(300, cardLayout.width))
                textRole: "label"
                valueRole: "value"
                model: [
                    { label: "ผสานข้อมูล (Merge — แนะนำ)", value: "merge" },
                    { label: "แทนที่ทั้งหมด (Replace — สำรองอัตโนมัติ)", value: "replace" }
                ]
                onCurrentIndexChanged: root.clearPreview()
            }

            StyledButton {
                id: btnPreviewImportDb
                objectName: "btnPreviewImportDb"
                variant: StyledButton.Neutral
                text: "🔍 เลือกไฟล์และตรวจสอบ (Preview)"
                onClicked: importFileDialog.open()
            }

            StyledButton {
                id: btnApplyImportDb
                objectName: "btnApplyImportDb"
                variant: root.selectedMode === "replace" ? StyledButton.Danger : StyledButton.Primary
                text: "📥 ยืนยันนำเข้าข้อมูล (Apply)"
                enabled: root.previewReady && root.selectedImportPath !== ""
                onClicked: root.importRequested(root.selectedImportPath, root.selectedMode)
            }
        }

        Text {
            visible: root.selectedImportPath !== ""
            text: "ไฟล์ที่เลือก: " + root.selectedImportPath
            font.pixelSize: 12
            color: Theme.textSecondary
            wrapMode: Text.WrapAnywhere
            Layout.fillWidth: true
        }

        Rectangle {
            id: diffSummaryBox
            Layout.fillWidth: true
            visible: diffSummaryText.text !== ""
            color: Theme.accentSurface
            border.color: Theme.borderLightBlue
            border.width: 1
            radius: 6
            implicitHeight: Math.max(44, Math.round(diffSummaryText.implicitHeight + 20))
            height: implicitHeight

            Text {
                id: diffSummaryText
                objectName: "diffSummaryText"
                anchors.fill: parent
                anchors.margins: 10
                text: ""
                font.pixelSize: 12
                color: Theme.accentDeep
                wrapMode: Text.Wrap
                verticalAlignment: Text.AlignVCenter
            }
        }

        ActionFeedbackBanner {
            id: statusBanner
            objectName: "statusBanner"
        }
    }
}
