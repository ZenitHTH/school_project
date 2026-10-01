import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    Layout.fillWidth: true
    height: 48
    color: "#f8fafc"
    border.color: "#e2e8f0"
    border.width: 1
    radius: 6
    visible: totalPages > 1

    property int currentPage: 1
    property int totalPages: 1
    property int totalCount: 0
    property string countUnit: "รายการ"

    signal pageRequested(int page)

    function getPaginationPages(current, total) {
        if (total <= 1) return []
        if (total <= 7) {
            var all = []
            for (var i = 1; i <= total; i++) all.push(i.toString())
            return all
        }
        var pages = ["1"]
        if (current <= 4) {
            for (var a = 2; a <= 5; a++) pages.push(a.toString())
            pages.push("...")
            pages.push(total.toString())
        } else if (current >= total - 3) {
            pages.push("...")
            for (var b = total - 4; b <= total; b++) pages.push(b.toString())
        } else {
            pages.push("...")
            pages.push((current - 1).toString())
            pages.push(current.toString())
            pages.push((current + 1).toString())
            pages.push("...")
            pages.push(total.toString())
        }
        return pages
    }

    RowLayout {
        anchors.centerIn: parent
        spacing: 8

        // First page button
        Button {
            id: btnFirstPage
            enabled: root.currentPage > 1
            implicitWidth: 36
            implicitHeight: 32
            contentItem: Text {
                text: "«"
                font.pixelSize: 14
                font.bold: true
                color: btnFirstPage.enabled ? "#334155" : "#94a3b8"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: btnFirstPage.down ? "#e2e8f0" : (btnFirstPage.hovered ? "#f1f5f9" : "#ffffff")
                border.color: "#cbd5e1"
                radius: 6
            }
            onClicked: root.pageRequested(1)
        }

        // Prev page button
        Button {
            id: btnPrevPage
            enabled: root.currentPage > 1
            implicitWidth: 70
            implicitHeight: 32
            contentItem: Text {
                text: "‹ ก่อนหน้า"
                font.pixelSize: 12
                font.bold: true
                color: btnPrevPage.enabled ? "#334155" : "#94a3b8"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: btnPrevPage.down ? "#e2e8f0" : (btnPrevPage.hovered ? "#f1f5f9" : "#ffffff")
                border.color: "#cbd5e1"
                radius: 6
            }
            onClicked: root.pageRequested(root.currentPage - 1)
        }

        // Numbered pages + Ellipsis
        Repeater {
            model: root.getPaginationPages(root.currentPage, root.totalPages)

            delegate: Rectangle {
                id: pageBtnRect
                implicitWidth: modelData === "..." ? 28 : 34
                implicitHeight: 32
                radius: 6
                color: modelData === root.currentPage.toString() ? "#2563eb" : (pageMouse.containsMouse && modelData !== "..." ? "#eff6ff" : "#ffffff")
                border.color: modelData === root.currentPage.toString() ? "#2563eb" : (modelData === "..." ? "transparent" : "#cbd5e1")
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: modelData
                    font.bold: modelData === root.currentPage.toString()
                    font.pixelSize: 12
                    color: modelData === root.currentPage.toString() ? "#ffffff" : (modelData === "..." ? "#64748b" : "#334155")
                }

                MouseArea {
                    id: pageMouse
                    anchors.fill: parent
                    hoverEnabled: modelData !== "..."
                    cursorShape: modelData !== "..." ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: {
                        if (modelData !== "...") {
                            root.pageRequested(parseInt(modelData))
                        }
                    }
                }
            }
        }

        // Next page button
        Button {
            id: btnNextPage
            enabled: root.currentPage < root.totalPages
            implicitWidth: 70
            implicitHeight: 32
            contentItem: Text {
                text: "ถัดไป ›"
                font.pixelSize: 12
                font.bold: true
                color: btnNextPage.enabled ? "#334155" : "#94a3b8"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: btnNextPage.down ? "#e2e8f0" : (btnNextPage.hovered ? "#f1f5f9" : "#ffffff")
                border.color: "#cbd5e1"
                radius: 6
            }
            onClicked: root.pageRequested(root.currentPage + 1)
        }

        // Last page button
        Button {
            id: btnLastPage
            enabled: root.currentPage < root.totalPages
            implicitWidth: 36
            implicitHeight: 32
            contentItem: Text {
                text: "»"
                font.pixelSize: 14
                font.bold: true
                color: btnLastPage.enabled ? "#334155" : "#94a3b8"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: btnLastPage.down ? "#e2e8f0" : (btnLastPage.hovered ? "#f1f5f9" : "#ffffff")
                border.color: "#cbd5e1"
                radius: 6
            }
            onClicked: root.pageRequested(root.totalPages)
        }

        // Page Summary Info Text
        Text {
            text: "หน้า " + root.currentPage + " จาก " + root.totalPages + " (" + root.totalCount + " " + root.countUnit + ")"
            color: "#64748b"
            font.pixelSize: 12
            Layout.leftMargin: 8
        }
    }
}
