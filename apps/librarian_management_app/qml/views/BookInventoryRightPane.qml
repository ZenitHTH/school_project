import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../../common_qml"
import "../../../common_qml/Typography.js" as Typography

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
            Layout.preferredHeight: Math.max(185, previewCol.implicitHeight + 24)
            color: "#ffffff"
            radius: 8
            border.color: "#38bdf8"
            border.width: 1.5

            ColumnLayout {
                id: previewCol
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
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    StyledButton {
                        variant: StyledButton.Ghost
                        id: btnGoToPrintPage
                        objectName: "btnGoToPrintPage"
                        text: "🏷️ ไปหน้าพิมพ์บาร์โค้ด →"
                        font.pixelSize: 11
                        Layout.alignment: Qt.AlignRight
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
                                implicitHeight: Math.max(22, Math.round(incomingCopyCountText.implicitHeight + 4))
                                height: implicitHeight
                                Layout.preferredHeight: implicitHeight
                                implicitWidth: Math.round(incomingCopyCountText.implicitWidth + 12)
                                width: implicitWidth
                                Layout.preferredWidth: implicitWidth
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
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Text {
                            text: "🏛️ ข้อมูลหนังสือที่อยู่ในคลังตอนนี้"
                            font.bold: true
                            font.pixelSize: 13
                            color: "#0f172a"
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Rectangle {
                            id: inventorySummaryBadge
                            objectName: "inventorySummaryBadge"
                            implicitHeight: Math.max(22, Math.round(invCountText.implicitHeight + 4))
                            height: implicitHeight
                            implicitWidth: Math.max(40, Math.round(invCountText.implicitWidth + 12))
                            width: implicitWidth
                            radius: 4
                            color: "#f1f5f9"
                            border.color: "#cbd5e1"
                            Text {
                                id: invCountText
                                anchors.centerIn: parent
                                text: inventoryBooksModel.count + " เรื่อง"
                                font.pixelSize: Math.max(9, Math.round(10 * (window.fontScale || 1.0)))
                                font.bold: true
                                color: "#475569"
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        StyledTextInput {
                            id: inventorySearchInput
                            objectName: "inventorySearchInput"
                            placeholderText: "🔍 ค้นคลัง..."
                            Layout.fillWidth: true
                            font.pixelSize: 11
                            selectByMouse: true
                            onTextChanged: rightPaneRoot.refreshInventoryRequested()
                        }
                        StyledButton {
                            variant: StyledButton.Ghost
                            text: "🔄"
                            font.pixelSize: 11
                            Layout.preferredWidth: 38
                            implicitHeight: inventorySearchInput.implicitHeight
                            onClicked: rightPaneRoot.refreshInventoryRequested()
                        }
                    }
                }

                // Bordered Grid Table Header
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: Math.max(28, Math.round(invHeaderRow.implicitHeight + 8))
                    height: implicitHeight
                    Layout.preferredHeight: implicitHeight
                    color: "#f1f5f9"
                    border.color: "#cbd5e1"
                    radius: 4

                    RowLayout {
                        id: invHeaderRow
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 6
                        Text { text: "ID"; font.bold: true; font.pixelSize: Math.max(10, Math.round(11 * (window.fontScale || 1.0))); color: "#475569"; Layout.preferredWidth: Math.round(32 * (window.fontScale || 1.0)) }
                        Text { text: "ชื่อหนังสือ / ผู้แต่ง"; font.bold: true; font.pixelSize: Math.max(10, Math.round(11 * (window.fontScale || 1.0))); color: "#475569"; Layout.fillWidth: true }
                        Text { text: "หมวดหมู่"; font.bold: true; font.pixelSize: Math.max(10, Math.round(11 * (window.fontScale || 1.0))); color: "#475569"; Layout.preferredWidth: Math.round(70 * (window.fontScale || 1.0)) }
                        Text { text: "ชั้นวาง"; font.bold: true; font.pixelSize: Math.max(10, Math.round(11 * (window.fontScale || 1.0))); color: "#475569"; Layout.preferredWidth: Math.round(50 * (window.fontScale || 1.0)) }
                        Text { text: "จำนวน"; font.bold: true; font.pixelSize: Math.max(10, Math.round(11 * (window.fontScale || 1.0))); color: "#475569"; Layout.preferredWidth: Math.round(55 * (window.fontScale || 1.0)) }
                        Text { text: "จัดการ"; font.bold: true; font.pixelSize: Math.max(10, Math.round(11 * (window.fontScale || 1.0))); color: "#475569"; Layout.preferredWidth: Math.round(76 * (window.fontScale || 1.0)); horizontalAlignment: Text.AlignRight }
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
                    onCountChanged: Qt.callLater(function() { if (typeof settingsView !== "undefined" && settingsView) settingsView.applySettingsToWindow() })
                    model: ListModel { id: inventoryBooksModel; objectName: "inventoryBooksModel" }

                    delegate: Rectangle {
                        id: invDelegateRoot
                        objectName: "invDelegateRoot"
                        width: inventoryBooksList.width
                        implicitHeight: Math.max(48, Math.round(invRowContent.implicitHeight + 14))
                        height: implicitHeight
                        color: index % 2 === 0 ? "#ffffff" : "#f8fafc"
                        border.color: "#e2e8f0"
                        radius: 4

                        Component.onCompleted: Typography.applyToItem(this)

                        RowLayout {
                            id: invRowContent
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8
                            spacing: 6

                            Text {
                                text: "#" + model.book_id
                                font.bold: true
                                font.pixelSize: Math.max(10, Math.round(11 * (window.fontScale || 1.0)))
                                color: "#0284c7"
                                Layout.preferredWidth: Math.round(32 * (window.fontScale || 1.0))
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1
                                Text {
                                    id: invBookTitleText
                                    objectName: "invBookTitleText"
                                    text: model.title
                                    font.bold: true
                                    font.pixelSize: Math.max(11, Math.round(13 * (window.fontScale || 1.0)))
                                    color: "#0f172a"
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                Text {
                                    text: (model.author || "-") + " | " + (model.isbn || "-")
                                    font.pixelSize: Math.max(9, Math.round(11 * (window.fontScale || 1.0)))
                                    color: "#64748b"
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                            }

                            Text {
                                text: model.category_name || "-"
                                font.pixelSize: Math.max(10, Math.round(11 * (window.fontScale || 1.0)))
                                color: "#475569"
                                Layout.preferredWidth: Math.round(70 * (window.fontScale || 1.0))
                                elide: Text.ElideRight
                            }

                            Text {
                                text: model.shelf_location || "-"
                                font.pixelSize: Math.max(10, Math.round(11 * (window.fontScale || 1.0)))
                                color: "#475569"
                                Layout.preferredWidth: Math.round(50 * (window.fontScale || 1.0))
                                elide: Text.ElideRight
                            }

                            Rectangle {
                                Layout.preferredWidth: Math.round(55 * (window.fontScale || 1.0))
                                implicitHeight: Math.max(22, Math.round(invTotalCopiesText.implicitHeight + 4))
                                height: implicitHeight
                                Layout.preferredHeight: implicitHeight
                                radius: 4
                                color: "#dcfce7"
                                Text {
                                    id: invTotalCopiesText
                                    anchors.centerIn: parent
                                    text: model.total_copies + " เล่ม"
                                    font.bold: true
                                    font.pixelSize: Math.max(10, Math.round(11 * (window.fontScale || 1.0)))
                                    color: "#166534"
                                }
                            }

                            RowLayout {
                                Layout.preferredWidth: Math.round(76 * (window.fontScale || 1.0))
                                spacing: 2
                                StyledButton {
                                    variant: StyledButton.Ghost
                                    text: "+"
                                    font.pixelSize: Math.max(10, Math.round(10 * (window.fontScale || 1.0)))
                                    Layout.preferredWidth: Math.max(24, Math.round(24 * (window.fontScale || 1.0)))
                                    implicitHeight: Math.max(24, Math.round(24 * (window.fontScale || 1.0)))
                                    Layout.preferredHeight: implicitHeight
                                    onClicked: rightPaneRoot.addCopiesRequested(model.book_id, model.title)
                                }
                                StyledButton {
                                    variant: StyledButton.Ghost
                                    text: "✏️"
                                    font.pixelSize: Math.max(10, Math.round(10 * (window.fontScale || 1.0)))
                                    Layout.preferredWidth: Math.max(24, Math.round(24 * (window.fontScale || 1.0)))
                                    implicitHeight: Math.max(24, Math.round(24 * (window.fontScale || 1.0)))
                                    Layout.preferredHeight: implicitHeight
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
                                StyledButton {
                                    variant: StyledButton.Ghost
                                    text: "🗑️"
                                    font.pixelSize: Math.max(10, Math.round(10 * (window.fontScale || 1.0)))
                                    Layout.preferredWidth: Math.max(24, Math.round(24 * (window.fontScale || 1.0)))
                                    implicitHeight: Math.max(24, Math.round(24 * (window.fontScale || 1.0)))
                                    Layout.preferredHeight: implicitHeight
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
            Layout.preferredHeight: Math.max(110, catCol.implicitHeight + 20)
            color: "#ffffff"
            radius: 8
            border.color: "#e2e8f0"

            ColumnLayout {
                id: catCol
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    Text { text: "📁 หมวดหมู่หนังสือ:"; font.bold: true; font.pixelSize: 11; color: "#334155" }
                    StyledTextInput {
                        id: categoryNameInput
                        objectName: "categoryNameInput"
                        placeholderText: "ชื่อหมวดหมู่ใหม่..."
                        Layout.fillWidth: true
                        font.pixelSize: 11
                        selectByMouse: true
                        onAccepted: rightPaneRoot.addNewCategoryRequested()
                    }
                    StyledButton {
                        variant: StyledButton.Primary
                        id: btnAddCategory
                        objectName: "btnAddCategory"
                        text: "+ เพิ่มหมวด"
                        font.pixelSize: 11
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
                        id: catDelegateRect
                        implicitHeight: Math.max(28, Math.round(catRow.implicitHeight + 6))
                        height: implicitHeight
                        implicitWidth: Math.round(catRow.implicitWidth + 12)
                        width: implicitWidth
                        radius: 4
                        color: "#f1f5f9"
                        border.color: "#cbd5e1"
                        Component.onCompleted: Typography.applyToItem(this)

                        RowLayout {
                            id: catRow
                            anchors.centerIn: parent
                            spacing: 4
                            Text {
                                text: model.name
                                font.pixelSize: Math.max(9, Math.round(10 * (window.fontScale || 1.0)))
                                font.bold: true
                                color: "#1e293b"
                            }
                            Item {
                                implicitWidth: 24
                                implicitHeight: 24
                                Layout.preferredWidth: 24
                                Layout.preferredHeight: 24
                                Text {
                                    anchors.centerIn: parent
                                    text: "✏️"
                                    font.pixelSize: Math.max(9, Math.round(11 * (window.fontScale || 1.0)))
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: rightPaneRoot.editCategoryRequested(model.category_id, model.name)
                                }
                            }
                            Item {
                                implicitWidth: 24
                                implicitHeight: 24
                                Layout.preferredWidth: 24
                                Layout.preferredHeight: 24
                                Text {
                                    anchors.centerIn: parent
                                    text: "❌"
                                    font.pixelSize: Math.max(8, Math.round(10 * (window.fontScale || 1.0)))
                                }
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
