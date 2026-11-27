import QtQuick 2.15
import "Theme.js" as Theme
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    Layout.fillWidth: true
    implicitHeight: visible ? Math.max(48, Math.round(pagRow.implicitHeight + 16)) : 0
    height: implicitHeight
    clip: true
    color: Theme.surfaceSubtle
    border.color: Theme.borderSubtle
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
        id: pagRow
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        spacing: 6

        Item { Layout.fillWidth: true }

        // First page button
        Button {
            id: btnFirstPage
            enabled: root.currentPage > 1
            implicitWidth: Math.max(34, Math.round(firstTxt.implicitWidth + 16))
            implicitHeight: Math.max(32, Math.round(firstTxt.implicitHeight + 10))
            contentItem: Text {
                id: firstTxt
                text: "«"
                font.pixelSize: 14
                font.bold: true
                color: btnFirstPage.enabled ? Theme.textSecondary : Theme.textFaint
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: btnFirstPage.down ? Theme.borderSubtle : (btnFirstPage.hovered ? Theme.surfaceHover : Theme.surfaceWhite)
                border.color: Theme.borderDefault
                radius: 6
            }
            onClicked: root.pageRequested(1)
        }

        // Prev page button
        Button {
            id: btnPrevPage
            enabled: root.currentPage > 1
            implicitWidth: Math.max(64, Math.round(prevTxt.implicitWidth + 18))
            implicitHeight: Math.max(32, Math.round(prevTxt.implicitHeight + 10))
            contentItem: Text {
                id: prevTxt
                text: "‹ ก่อนหน้า"
                font.pixelSize: 12
                font.bold: true
                color: btnPrevPage.enabled ? Theme.textSecondary : Theme.textFaint
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: btnPrevPage.down ? Theme.borderSubtle : (btnPrevPage.hovered ? Theme.surfaceHover : Theme.surfaceWhite)
                border.color: Theme.borderDefault
                radius: 6
            }
            onClicked: root.pageRequested(root.currentPage - 1)
        }

        // Numbered pages + Ellipsis
        Repeater {
            model: root.getPaginationPages(root.currentPage, root.totalPages)

            delegate: Rectangle {
                id: pageBtnRect
                implicitWidth: Math.max(modelData === "..." ? 24 : 32, Math.round(pageBtnTxt.implicitWidth + 14))
                implicitHeight: Math.max(32, Math.round(pageBtnTxt.implicitHeight + 10))
                height: implicitHeight
                radius: 6
                color: modelData === root.currentPage.toString() ? Theme.accentPrimary : (pageMouse.containsMouse && modelData !== "..." ? Theme.accentSurface : Theme.surfaceWhite)
                border.color: modelData === root.currentPage.toString() ? Theme.accentPrimary : (modelData === "..." ? "transparent" : Theme.borderDefault)
                border.width: 1

                Text {
                    id: pageBtnTxt
                    anchors.centerIn: parent
                    text: modelData
                    font.bold: modelData === root.currentPage.toString()
                    font.pixelSize: 12
                    color: modelData === root.currentPage.toString() ? Theme.surfaceWhite : (modelData === "..." ? Theme.textMuted : Theme.textSecondary)
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
            implicitWidth: Math.max(64, Math.round(nextTxt.implicitWidth + 18))
            implicitHeight: Math.max(32, Math.round(nextTxt.implicitHeight + 10))
            contentItem: Text {
                id: nextTxt
                text: "ถัดไป ›"
                font.pixelSize: 12
                font.bold: true
                color: btnNextPage.enabled ? Theme.textSecondary : Theme.textFaint
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: btnNextPage.down ? Theme.borderSubtle : (btnNextPage.hovered ? Theme.surfaceHover : Theme.surfaceWhite)
                border.color: Theme.borderDefault
                radius: 6
            }
            onClicked: root.pageRequested(root.currentPage + 1)
        }

        // Last page button
        Button {
            id: btnLastPage
            enabled: root.currentPage < root.totalPages
            implicitWidth: Math.max(34, Math.round(lastTxt.implicitWidth + 16))
            implicitHeight: Math.max(32, Math.round(lastTxt.implicitHeight + 10))
            contentItem: Text {
                id: lastTxt
                text: "»"
                font.pixelSize: 14
                font.bold: true
                color: btnLastPage.enabled ? Theme.textSecondary : Theme.textFaint
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: btnLastPage.down ? Theme.borderSubtle : (btnLastPage.hovered ? Theme.surfaceHover : Theme.surfaceWhite)
                border.color: Theme.borderDefault
                radius: 6
            }
            onClicked: root.pageRequested(root.totalPages)
        }

        // Page Summary Info Text
        Text {
            text: "หน้า " + root.currentPage + " จาก " + root.totalPages + " (" + root.totalCount + " " + root.countUnit + ")"
            color: Theme.textMuted
            font.pixelSize: 12
            elide: Text.ElideRight
            Layout.leftMargin: 6
            Layout.maximumWidth: implicitWidth
            Layout.fillWidth: true
        }

        Item { Layout.fillWidth: true }
    }
}
