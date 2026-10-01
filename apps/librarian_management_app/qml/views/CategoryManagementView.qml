import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: categoryScreen
    objectName: "categoryScreen"
    color: "#ffffff"

    property alias categoryNameInput: categoryNameInput
    property alias btnAddCategory: btnAddCategory
    property alias categoryStatusText: categoryStatusText
    property alias categoryListView: categoryListView
    property alias categoryListModel: categoryListModel

    signal editCategoryRequested(int catId, string catName)
    signal deleteCategoryRequested(int catId, string catName)
    signal categoryAdded()

    ListModel {
        id: categoryListModel
        objectName: "categoryListModel"
    }

    function loadCategoriesList() {
        categoryListModel.clear()
        try {
            var raw = librarianAdmin.listCategories()
            var cats = JSON.parse(raw)
            for (var i = 0; i < cats.length; i++) {
                categoryListModel.append({
                    "category_id": cats[i].category_id,
                    "name": cats[i].name
                })
            }
        } catch (e) {
            console.error("Failed to load categories: " + e)
        }
    }

    function addNewCategory() {
        var name = categoryNameInput.text.trim()
        if (!name) {
            categoryStatusText.text = "⚠️ กรุณากรอกชื่อหมวดหมู่"
            categoryStatusText.color = "#ef4444"
            return
        }

        try {
            var res = JSON.parse(librarianAdmin.addCategory(name))
            if (res.ok) {
                categoryStatusText.text = "✓ เพิ่มหมวดหมู่ '" + name + "' เรียบร้อยแล้ว"
                categoryStatusText.color = "#10b981"
                categoryNameInput.text = ""
                loadCategoriesList()
                categoryScreen.categoryAdded()
            } else {
                categoryStatusText.text = "✗ " + (res.error || "เกิดข้อผิดพลาดในการเพิ่มหมวดหมู่")
                categoryStatusText.color = "#ef4444"
            }
        } catch (e) {
            categoryStatusText.text = "✗ เกิดข้อผิดพลาดในการเชื่อมต่อ: " + e
            categoryStatusText.color = "#ef4444"
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        // Header
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                spacing: 4
                Text {
                    text: "📁 จัดการหมวดหมู่หนังสือ (Category Management)"
                    font.bold: true
                    font.pixelSize: 22
                    color: "#1e293b"
                }
                Text {
                    text: "เพิ่มและตรวจสอบรายการหมวดหมู่สำหรับจัดหมวดหมู่หนังสือในระบบห้องสมุด"
                    font.pixelSize: 13
                    color: "#64748b"
                }
            }
            Item { Layout.fillWidth: true }
            Button {
                text: "🔄 รีเฟรช"
                flat: true
                onClicked: categoryScreen.loadCategoriesList()
            }
        }

        // Input Card
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 96
            color: "#f8fafc"
            radius: 8
            border.color: "#e2e8f0"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    TextField {
                        id: categoryNameInput
                        objectName: "categoryNameInput"
                        placeholderText: "ระบุชื่อหมวดหมู่ใหม่..."
                        Layout.fillWidth: true
                        font.pixelSize: 13
                        selectByMouse: true
                        onAccepted: categoryScreen.addNewCategory()
                    }
                    Button {
                        id: btnAddCategory
                        objectName: "btnAddCategory"
                        text: "+ เพิ่มหมวดหมู่"
                        highlighted: true
                        Layout.preferredWidth: 140
                        onClicked: categoryScreen.addNewCategory()
                    }
                }

                Text {
                    id: categoryStatusText
                    objectName: "categoryStatusText"
                    Layout.fillWidth: true
                    text: ""
                    font.pixelSize: 12
                }
            }
        }

        // Categories List
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "📋 รายการหมวดหมู่ทั้งหมด"
                    font.bold: true
                    font.pixelSize: 16
                    color: "#1e293b"
                }
                Text {
                    text: "(" + categoryListModel.count + " หมวดหมู่)"
                    font.pixelSize: 13
                    color: "#64748b"
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                color: "#f8fafc"
                border.color: "#e2e8f0"
                radius: 8
                visible: categoryListModel.count === 0

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 8
                    Text {
                        text: "📂 ยังไม่มีหมวดหมู่ในระบบ"
                        font.pixelSize: 15
                        font.bold: true
                        color: "#64748b"
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Text {
                        text: "พิมพ์ชื่อหมวดหมู่ในช่องด้านบน แล้วกด '+ เพิ่มหมวดหมู่' เพื่อเริ่มต้น"
                        font.pixelSize: 13
                        color: "#94a3b8"
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }

            ListView {
                id: categoryListView
                objectName: "categoryListView"
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 8
                visible: categoryListModel.count > 0
                model: categoryListModel

                delegate: Rectangle {
                    width: categoryListView.width
                    height: 50
                    color: "#ffffff"
                    border.color: "#e2e8f0"
                    radius: 6

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 12

                        Rectangle {
                            width: 36
                            height: 26
                            radius: 4
                            color: "#e0f2fe"
                            border.color: "#38bdf8"
                            Text {
                                anchors.centerIn: parent
                                text: "#" + model.category_id
                                font.bold: true
                                color: "#0284c7"
                                font.pixelSize: 11
                            }
                        }

                        Text {
                            text: model.name
                            font.pixelSize: 14
                            font.bold: true
                            color: "#1e293b"
                            Layout.fillWidth: true
                        }

                        Button {
                            id: btnEditCategory
                            text: "✏️ แก้ไข"
                            font.pixelSize: 11
                            flat: true
                            onClicked: categoryScreen.editCategoryRequested(model.category_id, model.name)
                        }

                        Button {
                            id: btnDeleteCategory
                            text: "🗑️ ลบ"
                            font.pixelSize: 11
                            flat: true
                            contentItem: Text {
                                text: "🗑️ ลบ"
                                font.pixelSize: 11
                                color: "#ef4444"
                                verticalAlignment: Text.AlignVCenter
                                horizontalAlignment: Text.AlignHCenter
                            }
                            onClicked: categoryScreen.deleteCategoryRequested(model.category_id, model.name)
                        }
                    }
                }
            }
        }
    }
}
