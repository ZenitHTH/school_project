import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#ffffff"

    property real baseFontSize: 13
    property alias btnExportSnapshot: btnExportSnapshot
    property alias exportStatusText: exportStatusText

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        Text {
            text: "ส่งออกข้อมูลนักเรียนเพื่อ Sync กับห้องสมุด (LINE)"
            font.bold: true
            font.pixelSize: 22
            color: "#0f172a"
        }

        Text {
            text: "สร้างไฟล์ snapshot.sqlite เพื่อส่งต่อให้ผู้ดูแลห้องสมุดนำเข้าสู่ระบบ"
            color: "#64748b"
        }

        Button {
            id: btnExportSnapshot
            objectName: "btnExportSnapshot"
            text: "สร้างไฟล์ Snapshot ทันที"
            highlighted: true
            onClicked: {
                var res = JSON.parse(studentAdmin.exportSnapshot("snapshot.sqlite", "Admin"))
                exportStatusText.text = res.ok
                    ? ("สร้างไฟล์สำเร็จ: มีนักเรียน " + res.data.student_count + " คน ใน " + res.data.output_path)
                    : ("เกิดข้อผิดพลาด: " + res.error)
            }
        }

        Text {
            id: exportStatusText
            objectName: "exportStatusText"
            font.pixelSize: Math.max(13, root.baseFontSize)
            color: "#2563eb"
        }

        Item { Layout.fillHeight: true }
    }
}
