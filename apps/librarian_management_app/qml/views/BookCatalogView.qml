import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../../common_qml"
import "../../../common_qml/Typography.js" as Typography

Rectangle {
    id: root
    color: "#ffffff"

    property alias catalogSearchInput: catalogSearchInput
    property alias btnSearchBooks: btnSearchBooks
    property alias catalogList: catalogList
    property alias catalogModel: catalogModel
    property alias catalogCategoryCombo: catalogCategoryCombo
    property alias catalogCategoryModel: catalogCategoryModel
    property alias btnOpenGeneratorPage: btnOpenGeneratorPage
    property alias btnOpenPrintPage: btnOpenPrintPage
    property alias chulabookResultsModel: chulabookResultsModel

    signal searchRequested()
    signal openGeneratorRequested()
    signal openPrintPageRequested()
    signal addCopiesRequested(int bookId, string title)
    signal editBookRequested(int bookId, string title, string author, string isbn, int categoryId, string shelfLocation, int totalCopies)
    signal deleteBookRequested(int bookId, string title)
    signal detectChulabookRequested()

    property string chulabookStatus: ""
    property bool chulabookDialogOpen: false
    property var chulabookBooks: []

    function loadCategories() {
        catalogCategoryModel.clear()
        catalogCategoryModel.append({ "category_id": 0, "name": "-- ทุกหมวดหมู่ --" })
        try {
            var cats = JSON.parse(librarianAdmin.listCategories())
            for (var i = 0; i < cats.length; i++) {
                catalogCategoryModel.append(cats[i])
            }
        } catch (e) {}
        catalogCategoryCombo.currentIndex = 0
    }

    Component.onCompleted: loadCategories()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "แคตตาล็อกหนังสือ (Book Catalog)"
                font.bold: true
                font.pixelSize: 22
                color: "#1e293b"
            }
            Item { Layout.fillWidth: true }
            StyledButton {
                variant: StyledButton.Primary
                id: btnDetectChulabook
                objectName: "btnDetectChulabook"
                text: "📕 ตรวจ Chulabook"
                onClicked: root.detectChulabookRequested()
            }
            StyledButton {
                variant: StyledButton.Primary
                id: btnOpenGeneratorPage
                objectName: "btnOpenGeneratorPage"
                text: "📚 เพิ่มหนังสือ / หมวดหมู่"
                onClicked: root.openGeneratorRequested()
            }
            StyledButton {
                variant: StyledButton.Primary
                id: btnOpenPrintPage
                objectName: "btnOpenPrintPage"
                text: "🏷️ พิมพ์สติกเกอร์บาร์โค้ด"
                onClicked: root.openPrintPageRequested()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            StyledTextInput {
                id: catalogSearchInput
                objectName: "catalogSearchInput"
                placeholderText: "ค้นหาชื่อหนังสือ, ผู้แต่ง, ISBN หรือ บาร์โค้ด"
                Layout.fillWidth: true
                selectByMouse: true
                onAccepted: root.searchRequested()
            }
            StyledComboBox {
                id: catalogCategoryCombo
                objectName: "catalogCategoryCombo"
                textRole: "name"
                model: ListModel { id: catalogCategoryModel; objectName: "catalogCategoryModel" }
                Layout.preferredWidth: 180
                Layout.minimumWidth: 140
            }
            StyledButton {
                variant: StyledButton.Primary
                id: btnSearchBooks
                objectName: "btnSearchBooks"
                text: "ค้นหา"
                onClicked: root.searchRequested()
            }
        }

        Text {
            id: chulabookStatusText
            objectName: "chulabookStatusText"
            text: root.chulabookStatus
            visible: root.chulabookStatus !== ""
            color: text.startsWith("✗") ? "#dc2626" : "#0f766e"
            font.pixelSize: Math.max(11, Math.round(13 * (window.fontScale || 1.0)))
            Component.onCompleted: Typography.applyToItem(this)
        }

        ListView {
            id: catalogList
            objectName: "catalogList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 4
            onCountChanged: Qt.callLater(function() { if (typeof settingsView !== "undefined" && settingsView) settingsView.applySettingsToWindow() })
            model: ListModel { id: catalogModel; objectName: "catalogModel" }
            delegate: Rectangle {
                id: catalogDelegate
                width: catalogList.width
                implicitHeight: Math.max(64, Math.round(catalogRowLayout.implicitHeight + 20))
                height: implicitHeight
                border.color: "#e2e8f0"
                color: index % 2 === 0 ? "#ffffff" : "#f8fafc"

                Component.onCompleted: Typography.applyToItem(this)

                RowLayout {
                    id: catalogRowLayout
                    anchors.fill: parent
                    anchors.margins: 14
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 280
                        Layout.preferredWidth: 380
                        spacing: 2
                        Text {
                            text: model.title
                            font.bold: true
                            font.pixelSize: Math.max(12, Math.round(15 * (window.fontScale || 1.0)))
                            color: "#0f172a"
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                            maximumLineCount: 1
                        }
                        Text {
                            text: "ผู้แต่ง: " + (model.author || "-") + " | ISBN: " + (model.isbn || "-")
                            color: "#64748b"
                            font.pixelSize: Math.max(10, Math.round(12 * (window.fontScale || 1.0)))
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                            maximumLineCount: 1
                        }
                    }
                    Text {
                        text: "หมวดหมู่: " + (model.category_name || "-")
                        font.pixelSize: Math.max(10, Math.round(12 * (window.fontScale || 1.0)))
                        color: "#475569"
                        Layout.preferredWidth: Math.round(130 * (window.fontScale || 1.0))
                    }
                    Text {
                        text: "มีทั้งหมด: " + model.total_copies + " เล่ม (พร้อมยืม: " + model.available_copies + ")"
                        font.pixelSize: Math.max(10, Math.round(12 * (window.fontScale || 1.0)))
                        color: "#059669"
                        font.bold: true
                        Layout.fillWidth: false
                        Layout.preferredWidth: Math.round(220 * (window.fontScale || 1.0))
                    }
                    StyledButton {
                        variant: StyledButton.Primary
                        text: "+ เพิ่มเล่ม"
                        onClicked: root.addCopiesRequested(model.book_id, model.title)
                    }
                    StyledButton {
                        variant: StyledButton.Ghost
                        text: "✏️ แก้ไข"
                        font.pixelSize: Math.max(10, Math.round(12 * (window.fontScale || 1.0)))
                        onClicked: root.editBookRequested(model.book_id, model.title, model.author || "", model.isbn || "", model.category_id || 0, model.shelf_location || "", model.total_copies || 1)
                    }
                    StyledButton {
                        variant: StyledButton.Ghost
                        text: "🗑️ ลบ"
                        font.pixelSize: Math.max(10, Math.round(12 * (window.fontScale || 1.0)))
                        contentItem: Text {
                            text: "🗑️ ลบ"
                            font.pixelSize: Math.max(10, Math.round(12 * (window.fontScale || 1.0)))
                            color: "#ef4444"
                            verticalAlignment: Text.AlignVCenter
                            horizontalAlignment: Text.AlignHCenter
                        }
                        onClicked: root.deleteBookRequested(model.book_id, model.title)
                    }
                }
            }
        }
    }

    Dialog {
        id: chulabookDialog
        objectName: "chulabookDialog"
        visible: root.chulabookDialogOpen
        modal: true
        implicitWidth: 560
        implicitHeight: 440
        title: "พบ " + root.chulabookBooks.length + " เล่มที่พบเฉพาะใน Chulabook"
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10
            Text {
                text: "ISBN ของหนังสือเหล่านี้ไม่พบในฐานข้อมูลมาตรฐาน (NLT / SE-ED / Open Library)"
                color: "#64748b"
                font.pixelSize: Math.max(10, Math.round(12 * (window.fontScale || 1.0)))
                wrapMode: Text.Wrap
                Layout.fillWidth: true
                Component.onCompleted: Typography.applyToItem(this)
            }
            ListView {
                id: chulabookResultsList
                objectName: "chulabookResultsList"
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: ListModel { id: chulabookResultsModel; objectName: "chulabookResultsModel" }
                delegate: Rectangle {
                    width: chulabookResultsList.width
                    implicitHeight: Math.max(34, Math.round(cbTitleText.implicitHeight + 14))
                    height: implicitHeight
                    color: index % 2 === 0 ? "#ffffff" : "#f8fafc"
                    border.color: "#e2e8f0"
                    Component.onCompleted: Typography.applyToItem(this)
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        Layout.minimumWidth: 200
                        Text {
                            id: cbTitleText
                            text: model.title || "-"
                            font.bold: true
                            font.pixelSize: Math.max(12, Math.round(14 * (window.fontScale || 1.0)))
                            color: "#0f172a"
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                            maximumLineCount: 1
                        }
                        Text {
                            text: "ISBN: " + (model.isbn || "-")
                            font.pixelSize: Math.max(10, Math.round(12 * (window.fontScale || 1.0)))
                            color: "#64748b"
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                            maximumLineCount: 1
                        }
                    }
                }
            }
            StyledButton {
                variant: StyledButton.Ghost
                id: btnCloseChulabookDialog
                objectName: "btnCloseChulabookDialog"
                text: "ปิด"
                Layout.alignment: Qt.AlignRight
                onClicked: root.chulabookDialogOpen = false
            }
        }
    }
}
