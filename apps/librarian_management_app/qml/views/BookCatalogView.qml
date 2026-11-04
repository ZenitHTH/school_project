import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../../common_qml/Typography.js" as Typography

Rectangle {
    id: root
    color: "#ffffff"

    property alias catalogSearchInput: catalogSearchInput
    property alias btnSearchBooks: btnSearchBooks
    property alias catalogList: catalogList
    property alias catalogModel: catalogModel
    property alias btnOpenGeneratorPage: btnOpenGeneratorPage
    property alias btnOpenPrintPage: btnOpenPrintPage

    signal searchRequested()
    signal openGeneratorRequested()
    signal openPrintPageRequested()
    signal addCopiesRequested(int bookId, string title)
    signal editBookRequested(int bookId, string title, string author, string isbn, int categoryId, string shelfLocation, int totalCopies)
    signal deleteBookRequested(int bookId, string title)

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
            Button {
                id: btnOpenGeneratorPage
                objectName: "btnOpenGeneratorPage"
                text: "📚 เพิ่มหนังสือ / หมวดหมู่"
                onClicked: root.openGeneratorRequested()
            }
            Button {
                id: btnOpenPrintPage
                objectName: "btnOpenPrintPage"
                text: "🏷️ พิมพ์สติกเกอร์บาร์โค้ด"
                highlighted: true
                onClicked: root.openPrintPageRequested()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            TextField {
                id: catalogSearchInput
                objectName: "catalogSearchInput"
                placeholderText: "ค้นหาชื่อหนังสือ, ผู้แต่ง, ISBN..."
                Layout.fillWidth: true
                implicitHeight: Math.max(38, Math.round(((font.pixelSize > 0 ? font.pixelSize : 14)) * 2.2))
                leftPadding: 12
                rightPadding: 12
                verticalAlignment: TextInput.AlignVCenter
                placeholderTextColor: "#64748b"
                selectByMouse: true
                background: Rectangle {
                    implicitHeight: parent.implicitHeight
                    color: "#ffffff"
                    border.color: parent.activeFocus ? "#2563eb" : "#cbd5e1"
                    radius: 6
                }
                onAccepted: root.searchRequested()
            }
            Button {
                id: btnSearchBooks
                objectName: "btnSearchBooks"
                text: "ค้นหา"
                onClicked: root.searchRequested()
            }
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
                    Button {
                        text: "+ เพิ่มเล่ม"
                        onClicked: root.addCopiesRequested(model.book_id, model.title)
                    }
                    Button {
                        text: "✏️ แก้ไข"
                        flat: true
                        font.pixelSize: Math.max(10, Math.round(12 * (window.fontScale || 1.0)))
                        onClicked: root.editBookRequested(model.book_id, model.title, model.author || "", model.isbn || "", model.category_id || 0, model.shelf_location || "", model.total_copies || 1)
                    }
                    Button {
                        text: "🗑️ ลบ"
                        flat: true
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
}
