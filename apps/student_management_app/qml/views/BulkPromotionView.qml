import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#ffffff"

    property real baseFontSize: 13
    property alias btnPromote: btnPromote
    property alias promoteResultText: promoteResultText

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        Text {
            text: "การเลื่อนชั้นเรียนประจำปีการศึกษา (Bulk Promotion)"
            font.bold: true
            font.pixelSize: 22
            color: "#0f172a"
        }

        Text {
            text: "ระบบจะทำการเลื่อนชั้นนักเรียนที่สถานะ 'ปกติ' ทั้งหมดจาก ม.1 -> ม.2, ม.2 -> ม.3 ... ม.5 -> ม.6 และจบการศึกษา ม.6"
            color: "#475569"
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        Button {
            id: btnPromote
            objectName: "btnPromote"
            text: "ยืนยันและดำเนินการเลื่อนชั้น"
            highlighted: true
            onClicked: {
                var res = JSON.parse(studentAdmin.bulkPromote(2567, 1, 2568, 1, "Admin"))
                promoteResultText.text = res.ok
                    ? ("สำเร็จ: เลื่อนชั้น " + res.data.promoted_count + " คน, สำเร็จการศึกษา " + res.data.graduated_count + " คน")
                    : ("เกิดข้อผิดพลาด: " + res.error)
            }
        }

        Text {
            id: promoteResultText
            objectName: "promoteResultText"
            font.pixelSize: Math.max(13, root.baseFontSize)
            color: "#059669"
        }

        Item { Layout.fillHeight: true }
    }
}
