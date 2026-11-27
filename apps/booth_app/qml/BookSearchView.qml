import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../common_qml"
import "../../common_qml/Theme.js" as Theme
import "../../common_qml/Typography.js" as Typography

Rectangle {
    id: root
    objectName: "boothBookSearchView"
    color: "#0f172a"

    property var targetWindow: null
    readonly property real fontScale: (targetWindow && targetWindow.fontScale) ? targetWindow.fontScale : 1.0
    property bool _loadingCategories: false

    signal backRequested()

    component InfoBadge: Rectangle {
        property string badgeText: ""
        property color textColor: "#cbd5e1"
        property bool boldText: false
        property int padX: 16; property int padY: 8; property int minH: 24; property int maxW: 320
        implicitWidth: Math.min(maxW, Math.round(label.implicitWidth + padX))
        implicitHeight: Math.max(minH, Math.round(label.implicitHeight + padY))
        height: implicitHeight; radius: 6; clip: true
        Text {
            id: label; anchors.centerIn: parent; text: parent.badgeText; color: parent.textColor
            width: Math.min(implicitWidth, parent.width - parent.padX)
            elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter
            font.bold: parent.boldText; font.pixelSize: Math.max(10, Math.round(12 * root.fontScale))
        }
    }

    function refresh() { loadCategories(); performSearch() }

    function loadCategories() {
        _loadingCategories = true
        categoryFilterModel.clear()
        categoryFilterModel.append({"category_id": 0, "name": "ทุกหมวดหมู่"})
        if (typeof boothAdapter !== "undefined" && boothAdapter && boothAdapter.listCategories) {
            try {
                var cats = JSON.parse(boothAdapter.listCategories())
                for (var i = 0; i < cats.length; i++) {
                    categoryFilterModel.append({"category_id": Number(cats[i].category_id || 0), "name": String(cats[i].name || "")})
                }
            } catch (e) {}
        }
        categoryFilterCombo.currentIndex = 0
        _loadingCategories = false
    }

    function performSearch() {
        bookResultsModel.clear()
        if (typeof boothAdapter === "undefined" || boothAdapter === null || !boothAdapter.searchBooks) {
            statusText.text = "ไม่พบหนังสือที่ตรงกับการค้นหา"
            return
        }
        var idx = categoryFilterCombo.currentIndex
        var catId = (idx >= 0 && idx < categoryFilterModel.count) ? (categoryFilterModel.get(idx).category_id || 0) : 0
        try {
            var rows = JSON.parse(boothAdapter.searchBooks(searchInput.text, catId, 50, 0))
            for (var i = 0; i < rows.length; i++) {
                var r = rows[i]
                bookResultsModel.append({
                    "book_id": Number(r.book_id || 0), "title": String(r.title || ""),
                    "author": String(r.author || ""), "isbn": String(r.isbn || ""),
                    "category_name": String(r.category_name || ""), "shelf_location": String(r.shelf_location || ""),
                    "total_copies": Number(r.total_copies || 0), "available_copies": Number(r.available_copies || 0)
                })
            }
        } catch (e) {}
        statusText.text = bookResultsModel.count > 0 ? ("พบ " + bookResultsModel.count + " รายการ") : "ไม่พบหนังสือที่ตรงกับการค้นหา"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: Math.max(52, Math.round(topBarRow.implicitHeight + 24))
            height: implicitHeight; color: "#1e293b"
            RowLayout {
                id: topBarRow; anchors.fill: parent; anchors.margins: 12; spacing: 12
                Text { text: "🔍 ค้นหาหนังสือและตำแหน่งชั้นวาง"; color: "#ffffff"; font.bold: true; font.pixelSize: Math.max(14, Math.round(18 * root.fontScale)); wrapMode: Text.Wrap; Layout.fillWidth: true }
                StyledButton { id: btnBackFromBookSearch; objectName: "btnBackFromBookSearch"; variant: StyledButton.Neutral; text: "← กลับหน้าบริการ"; onClicked: root.backRequested() }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.margins: 20; spacing: 12

            RowLayout {
                Layout.fillWidth: true; spacing: 10
                StyledSearchField {
                    id: searchInput; objectName: "boothBookSearchInput"; Layout.fillWidth: true; Layout.minimumWidth: 160
                    placeholderText: "ค้นหาชื่อหนังสือ ผู้แต่ง หรือ ISBN..."
                    horizontalAlignment: TextInput.AlignLeft; verticalAlignment: TextInput.AlignVCenter
                    onAccepted: root.performSearch()
                }
                StyledComboBox {
                    id: categoryFilterCombo; objectName: "boothCategoryFilter"; textRole: "name"
                    Layout.preferredWidth: Math.min(280, Math.max(180, Math.round(180 * root.fontScale)))
                    model: ListModel { id: categoryFilterModel; objectName: "boothCategoryFilterModel" }
                    onCurrentIndexChanged: if (!root._loadingCategories) root.performSearch()
                }
                StyledButton {
                    id: btnBoothSearchBooks; objectName: "btnBoothSearchBooks"
                    variant: StyledButton.Primary; text: "ค้นหา"; onClicked: root.performSearch()
                }
            }

            Text { id: statusText; objectName: "boothBookSearchStatus"; Layout.fillWidth: true; wrapMode: Text.Wrap; color: "#cbd5e1"; font.pixelSize: Math.max(12, Math.round(14 * root.fontScale)); text: "พบ 0 รายการ" }

            ListView {
                id: resultsList; objectName: "boothBookResultsList"
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 8
                model: ListModel { id: bookResultsModel; objectName: "bookResultsModel" }

                delegate: Rectangle {
                    id: bookCard
                    width: resultsList.width
                    implicitHeight: Math.max(76, Math.round(cardCol.implicitHeight + 24))
                    height: implicitHeight; radius: 10; color: "#1e293b"; clip: true
                    border.color: model.available_copies > 0 ? "#334155" : "#7f1d1d"
                    Component.onCompleted: Typography.applyToItem(this)

                    ColumnLayout {
                        id: cardCol; anchors.fill: parent; anchors.margins: 12; spacing: 6
                        RowLayout {
                            Layout.fillWidth: true; spacing: 8
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 2
                                Text {
                                    text: model.title || ""; color: "#ffffff"; font.bold: true
                                    font.pixelSize: Math.max(13, Math.round(16 * root.fontScale)); wrapMode: Text.WordWrap; Layout.fillWidth: true
                                }
                                Text {
                                    text: (model.author || "ไม่ระบุผู้แต่ง") + (model.isbn ? (" • ISBN: " + model.isbn) : "")
                                    color: "#94a3b8"; font.pixelSize: Math.max(11, Math.round(13 * root.fontScale)); wrapMode: Text.WordWrap; Layout.fillWidth: true
                                }
                            }
                            InfoBadge {
                                padX: 20; padY: 10; minH: 26; boldText: true
                                color: model.available_copies > 0 ? Theme.successBackground : Theme.errorBackground
                                border.color: model.available_copies > 0 ? Theme.successBorder : Theme.errorBorder
                                textColor: model.available_copies > 0 ? Theme.successText : Theme.errorText
                                badgeText: model.available_copies > 0
                                    ? ("ว่าง " + model.available_copies + " / " + model.total_copies + " เล่ม")
                                    : ("ถูกยืมหมด (0 / " + model.total_copies + " เล่ม)")
                            }
                        }
                        Flow {
                            Layout.fillWidth: true; spacing: 8
                            InfoBadge {
                                maxW: Math.max(160, cardCol.width - 16)
                                color: "#0f172a"; border.color: "#334155"; textColor: "#cbd5e1"
                                badgeText: "🏷️ " + (model.category_name || "ไม่ระบุหมวดหมู่")
                            }
                            InfoBadge {
                                maxW: Math.max(160, cardCol.width - 16)
                                color: "#172554"; border.color: "#1d4ed8"; textColor: "#93c5fd"; boldText: true
                                badgeText: "📍 ชั้นวาง: " + (model.shelf_location || "ไม่ระบุชั้นวาง")
                            }
                        }
                    }
                }
            }
        }
    }
}
