import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#ffffff"

    property alias catalogSearchInput: catalogSearchInput
    property alias btnSearchBooks: btnSearchBooks
    property alias catalogList: catalogList
    property alias catalogModel: catalogModel
    property alias btnOpenGeneratorPage: btnOpenGeneratorPage

    signal searchRequested()
    signal openGeneratorRequested()
    signal addCopiesRequested(int bookId, string title)
    signal editBookRequested(int bookId, string title, string author, string isbn, int categoryId, string shelfLocation)
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
                text: "🏷️ สร้างบาร์โค้ดและเพิ่มหนังสือ"
                highlighted: true
                onClicked: root.openGeneratorRequested()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            TextField {
                id: catalogSearchInput
                objectName: "catalogSearchInput"
                placeholderText: "ค้นหาชื่อหนังสือ, ผู้แต่ง, ISBN..."
                Layout.fillWidth: true
                selectByMouse: true
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
            model: ListModel { id: catalogModel; objectName: "catalogModel" }
            delegate: Rectangle {
                width: catalogList.width
                height: 64
                border.color: "#e2e8f0"
                color: index % 2 === 0 ? "#ffffff" : "#f8fafc"
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    ColumnLayout {
                        Layout.preferredWidth: 350
                        Text { text: model.title; font.bold: true; font.pixelSize: 15; color: "#0f172a" }
                        Text { text: "ผู้แต่ง: " + (model.author || "-") + " | ISBN: " + (model.isbn || "-"); color: "#64748b"; font.pixelSize: 12 }
                    }
                    Text { text: "หมวดหมู่: " + (model.category_name || "-"); color: "#475569"; Layout.preferredWidth: 130 }
                    Text { text: "มีทั้งหมด: " + model.total_copies + " เล่ม (พร้อมยืม: " + model.available_copies + ")"; color: "#059669"; font.bold: true; Layout.fillWidth: true }
                    Button {
                        text: "+ เพิ่มเล่ม"
                        onClicked: root.addCopiesRequested(model.book_id, model.title)
                    }
                    Button {
                        text: "✏️ แก้ไข"
                        flat: true
                        font.pixelSize: 12
                        onClicked: root.editBookRequested(model.book_id, model.title, model.author || "", model.isbn || "", model.category_id || 0, model.shelf_location || "")
                    }
                    Button {
                        text: "🗑️ ลบ"
                        flat: true
                        font.pixelSize: 12
                        contentItem: Text {
                            text: "🗑️ ลบ"
                            font.pixelSize: 12
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
