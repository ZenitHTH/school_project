import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: rightPaneRoot
    color: "transparent"

    property alias incomingBookPreviewCard: incomingBookPreviewCard
    property alias incomingTitleText: incomingTitleText
    property alias incomingMetaText: incomingMetaText
    property alias incomingLocationText: incomingLocationText
    property alias incomingCopyCountText: incomingCopyCountText
    property alias incomingBarcodePreviewText: incomingBarcodePreviewText
    property alias incomingBarcodesModel: incomingBarcodesModel

    property alias inventorySearchInput: inventorySearchInput
    property alias inventoryBooksList: inventoryBooksList
    property alias inventoryBooksModel: inventoryBooksModel
    property alias inventorySummaryBadge: inventorySummaryBadge

    property alias categoryNameInput: categoryNameInput
    property alias btnAddCategory: btnAddCategory
    property alias categoryStatusText: categoryStatusText
    property alias categoryListView: categoryListView
    property alias categoryListModel: categoryListModel
    property alias btnGoToPrintPage: btnGoToPrintPage

    signal addCopiesRequested(int bookId, string title)
    signal editBookRequested(int bookId, string title, string author, string isbn, int categoryId, string shelf, int totalCopies)
    signal deleteBookRequested(int bookId, string title)
    signal editCategoryRequested(int catId, string catName)
    signal deleteCategoryRequested(int catId, string catName)
    signal addNewCategoryRequested()
    signal refreshInventoryRequested()
    signal goToPrintPageRequested()

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        // Top Card: Live Incoming Book Preview (Bordered Grid Table)
        Rectangle {
            id: incomingBookPreviewCard
            objectName: "incomingBookPreviewCard"
            Layout.fillWidth: true
            Layout.preferredHeight: 185
            color: "#ffffff"
            radius: 8
            border.color: "#38bdf8"
            border.width: 1.5

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    Rectangle {
                        width: 8; height: 8; radius: 4; color: "#10b981"
                    }
                    Text {
                        text: "📥 หนังสือที่กำลังใส่เข้ามา (Live Incoming Preview)"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#0369a1"
                    }
                    Item { Layout.fillWidth: true }
                    Button {
                        id: btnGoToPrintPage
                        objectName: "btnGoToPrintPage"
                        text: "🏷️ ไปหน้าพิมพ์บาร์โค้ด →"
                        font.pixelSize: 11
                        flat: true
                        onClicked: rightPaneRoot.goToPrintPageRequested()
                    }
                }

                // Bordered Grid Table for Staged Book
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#f8fafc"
                    border.color: "#e2e8f0"
                    radius: 6

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 4

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Text { text: "ชื่อหนังสือ:"; font.bold: true; font.pixelSize: 11; color: "#64748b" }
                            Text {
                                id: incomingTitleText
                                objectName: "incomingTitleText"
                                text: "(ยังไม่ได้ระบุชื่อหนังสือ)"
                                font.bold: true
                                font.pixelSize: 13
                                color: "#0f172a"
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Text { text: "ผู้แต่ง & ISBN:"; font.bold: true; font.pixelSize: 11; color: "#64748b" }
                            Text {
                                id: incomingMetaText
                                objectName: "incomingMetaText"
                                text: "ผู้แต่ง: - | ISBN: -"
                                font.pixelSize: 11
                                color: "#334155"
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Text { text: "หมวด & ชั้นวาง:"; font.bold: true; font.pixelSize: 11; color: "#64748b" }
                            Text {
                                id: incomingLocationText
                                objectName: "incomingLocationText"
                                text: "หมวด: - | ชั้นวาง: -"
                                font.pixelSize: 11
                                color: "#334155"
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            Rectangle {
                                id: incomingCopyCountBadge
                                height: 20
                                width: incomingCopyCountText.contentWidth + 12
                                radius: 4
                                color: "#dbeafe"
                                border.color: "#93c5fd"
                                Text {
                                    id: incomingCopyCountText
                                    objectName: "incomingCopyCountText"
                                    anchors.centerIn: parent
                                    text: "จำนวน: 1 เล่ม"
                                    font.bold: true
                                    font.pixelSize: 10
                                    color: "#1d4ed8"
                                }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: "#e2e8f0" }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Text { text: "รหัสบาร์โค้ดที่จะได้รับ:"; font.bold: true; font.pixelSize: 11; color: "#0f766e" }
                            Text {
                                id: incomingBarcodePreviewText
                                objectName: "incomingBarcodePreviewText"
                                text: "SMTE-00001-01"
                                font.bold: true
                                font.pixelSize: 11
                                font.family: "monospace"
                                color: "#0f766e"
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }

        // Middle Card: Current Inventory Grid Table
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#ffffff"
            radius: 8
            border.color: "#e2e8f0"
            clip: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                // Header & Search
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text {
                        text: "🏛️ ข้อมูลหนังสือที่อยู่ในคลังตอนนี้"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#0f172a"
                    }
                    Rectangle {
                        id: inventorySummaryBadge
                        objectName: "inventorySummaryBadge"
                        height: 20
                        width: invCountText.contentWidth + 10
                        radius: 4
                        color: "#f1f5f9"
                        border.color: "#cbd5e1"
                        Text {
                            id: invCountText
                            anchors.centerIn: parent
                            text: inventoryBooksModel.count + " เรื่อง"
                            font.pixelSize: 10
                            font.bold: true
                            color: "#475569"
                        }
                    }
                    Item { Layout.fillWidth: true }
                    TextField {
                        id: inventorySearchInput
                        objectName: "inventorySearchInput"
                        placeholderText: "🔍 ค้นคลัง..."
                        Layout.preferredWidth: 140
                        font.pixelSize: 11
                        padding: 6
                        background: Rectangle { border.color: "#cbd5e1"; radius: 4 }
                        onTextChanged: rightPaneRoot.refreshInventoryRequested()
                    }
                    Button {
                        text: "🔄"
                        font.pixelSize: 11
                        Layout.preferredWidth: 32
                        flat: true
                        onClicked: rightPaneRoot.refreshInventoryRequested()
                    }
                }

                // Bordered Grid Table Header
                Rectangle {
                    Layout.fillWidth: true
                    height: 26
                    color: "#f1f5f9"
                    border.color: "#cbd5e1"
                    radius: 4

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 6
                        Text { text: "ID"; font.bold: true; font.pixelSize: 10; color: "#475569"; Layout.preferredWidth: 32 }
                        Text { text: "ชื่อหนังสือ / ผู้แต่ง"; font.bold: true; font.pixelSize: 10; color: "#475569"; Layout.fillWidth: true }
                        Text { text: "หมวดหมู่"; font.bold: true; font.pixelSize: 10; color: "#475569"; Layout.preferredWidth: 70 }
                        Text { text: "ชั้นวาง"; font.bold: true; font.pixelSize: 10; color: "#475569"; Layout.preferredWidth: 50 }
                        Text { text: "จำนวน"; font.bold: true; font.pixelSize: 10; color: "#475569"; Layout.preferredWidth: 55 }
                        Text { text: "จัดการ"; font.bold: true; font.pixelSize: 10; color: "#475569"; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
                    }
                }

                // Inventory Books ListView (Bordered Rows)
                ListView {
                    id: inventoryBooksList
                    objectName: "inventoryBooksList"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 4
                    model: ListModel { id: inventoryBooksModel; objectName: "inventoryBooksModel" }

                    delegate: Rectangle {
                        width: inventoryBooksList.width
                        height: 44
                        color: index % 2 === 0 ? "#ffffff" : "#f8fafc"
                        border.color: "#e2e8f0"
                        radius: 4

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8
                            spacing: 6

                            Text {
                                text: "#" + model.book_id
                                font.bold: true
                                font.pixelSize: 10
                                color: "#0284c7"
                                Layout.preferredWidth: 32
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1
                                Text {
                                    text: model.title
                                    font.bold: true
                                    font.pixelSize: 11
                                    color: "#0f172a"
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                Text {
                                    text: (model.author || "-") + " | " + (model.isbn || "-")
                                    font.pixelSize: 9
                                    color: "#64748b"
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                            }

                            Text {
                                text: model.category_name || "-"
                                font.pixelSize: 10
                                color: "#475569"
                                Layout.preferredWidth: 70
                                elide: Text.ElideRight
                            }

                            Text {
                                text: model.shelf_location || "-"
                                font.pixelSize: 10
                                color: "#475569"
                                Layout.preferredWidth: 50
                                elide: Text.ElideRight
                            }

                            Rectangle {
                                Layout.preferredWidth: 55
                                height: 20
                                radius: 4
                                color: "#dcfce7"
                                Text {
                                    anchors.centerIn: parent
                                    text: model.total_copies + " เล่ม"
                                    font.bold: true
                                    font.pixelSize: 10
                                    color: "#166534"
                                }
                            }

                            RowLayout {
                                Layout.preferredWidth: 70
                                spacing: 2
                                Button {
                                    text: "+"
                                    font.pixelSize: 10
                                    Layout.preferredWidth: 22
                                    height: 22
                                    flat: true
                                    onClicked: rightPaneRoot.addCopiesRequested(model.book_id, model.title)
                                }
                                Button {
                                    text: "✏️"
                                    font.pixelSize: 10
                                    Layout.preferredWidth: 22
                                    height: 22
                                    flat: true
                                    onClicked: rightPaneRoot.editBookRequested(
                                        model.book_id,
                                        model.title,
                                        model.author || "",
                                        model.isbn || "",
                                        model.category_id || 0,
                                        model.shelf_location || "",
                                        model.total_copies || 1
                                    )
                                }
                                Button {
                                    text: "🗑️"
                                    font.pixelSize: 10
                                    Layout.preferredWidth: 22
                                    height: 22
                                    flat: true
                                    onClicked: rightPaneRoot.deleteBookRequested(model.book_id, model.title)
                                }
                            }
                        }
                    }
                }
            }
        }

        // Bottom Strip: Quick Category Management Strip (Preserves existing API)
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 110
            color: "#ffffff"
            radius: 8
            border.color: "#e2e8f0"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    Text { text: "📁 หมวดหมู่หนังสือ:"; font.bold: true; font.pixelSize: 11; color: "#334155" }
                    TextField {
                        id: categoryNameInput
                        objectName: "categoryNameInput"
                        placeholderText: "ชื่อหมวดหมู่ใหม่..."
                        Layout.fillWidth: true
                        font.pixelSize: 11
                        padding: 6
                        background: Rectangle { border.color: "#cbd5e1"; radius: 4 }
                        onAccepted: rightPaneRoot.addNewCategoryRequested()
                    }
                    Button {
                        id: btnAddCategory
                        objectName: "btnAddCategory"
                        text: "+ เพิ่มหมวด"
                        font.pixelSize: 11
                        highlighted: true
                        onClicked: rightPaneRoot.addNewCategoryRequested()
                    }
                }

                Text {
                    id: categoryStatusText
                    objectName: "categoryStatusText"
                    text: ""
                    font.pixelSize: 10
                    visible: text !== ""
                }

                ListView {
                    id: categoryListView
                    objectName: "categoryListView"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    orientation: ListView.Horizontal
                    clip: true
                    spacing: 6
                    model: ListModel { id: categoryListModel; objectName: "categoryListModel" }

                    delegate: Rectangle {
                        height: 28
                        width: catRow.width + 12
                        radius: 4
                        color: "#f1f5f9"
                        border.color: "#cbd5e1"

                        RowLayout {
                            id: catRow
                            anchors.centerIn: parent
                            spacing: 4
                            Text {
                                text: model.name
                                font.pixelSize: 10
                                font.bold: true
                                color: "#1e293b"
                            }
                            Text {
                                text: "✏️"
                                font.pixelSize: 9
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: rightPaneRoot.editCategoryRequested(model.category_id, model.name)
                                }
                            }
                            Text {
                                text: "❌"
                                font.pixelSize: 8
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: rightPaneRoot.deleteCategoryRequested(model.category_id, model.name)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    ListModel {
        id: incomingBarcodesModel
        objectName: "incomingBarcodesModel"
    }
}
