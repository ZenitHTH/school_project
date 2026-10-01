import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#ffffff"

    property var currentCheckoutStudent: null

    property alias studentLookupInput: studentLookupInput
    property alias btnLookupStudent: btnLookupStudent
    property alias checkoutStudentName: checkoutStudentName
    property alias barcodeInput: barcodeInput
    property alias btnCheckout: btnCheckout
    property alias btnReturn: btnReturn
    property alias deskStatusText: deskStatusText

    signal lookupStudentRequested()
    signal checkoutRequested()
    signal returnRequested()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        Text {
            text: "เคาน์เตอร์ ยืม-คืน หนังสือ (Desk Checkout/Return)"
            font.bold: true
            font.pixelSize: 22
            color: "#1e293b"
        }

        // Student lookup section
        Rectangle {
            Layout.fillWidth: true
            height: 120
            color: "#f1f5f9"
            radius: 8
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8
                Text { text: "1. ระบุนักเรียนผู้ยืม:"; font.bold: true; color: "#1e293b" }
                RowLayout {
                    TextField {
                        id: studentLookupInput
                        objectName: "studentLookupInput"
                        placeholderText: "พิมพ์รหัสนักเรียน หรือชื่อ..."
                        Layout.preferredWidth: 260
                        selectByMouse: true
                        onAccepted: root.lookupStudentRequested()
                    }
                    Button {
                        id: btnLookupStudent
                        objectName: "btnLookupStudent"
                        text: "ค้นหา"
                        onClicked: root.lookupStudentRequested()
                    }
                    Text {
                        id: checkoutStudentName
                        objectName: "checkoutStudentName"
                        text: root.currentCheckoutStudent ? ("ผู้ยืม: " + root.currentCheckoutStudent.full_name + " (รหัส " + root.currentCheckoutStudent.student_id + " - สถานะ " + root.currentCheckoutStudent.status + ")") : "ยังไม่ได้เลือกนักเรียน"
                        font.bold: true
                        color: root.currentCheckoutStudent ? "#0f766e" : "#64748b"
                    }
                }
            }
        }

        // Barcode scan section
        Rectangle {
            Layout.fillWidth: true
            height: 140
            color: "#f8fafc"
            border.color: "#cbd5e1"
            radius: 8
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8
                Text { text: "2. สแกนบาร์โค้ดประจำเล่มหนังสือ (Tracking Barcode):"; font.bold: true; color: "#1e293b" }
                RowLayout {
                    TextField {
                        id: barcodeInput
                        objectName: "barcodeInput"
                        placeholderText: "สแกนบาร์โค้ด..."
                        Layout.preferredWidth: 260
                        font.pixelSize: 16
                        selectByMouse: true
                        onAccepted: root.checkoutRequested()
                    }
                    Button {
                        id: btnCheckout
                        objectName: "btnCheckout"
                        text: "ยืมหนังสือ (Checkout)"
                        highlighted: true
                        onClicked: root.checkoutRequested()
                    }
                    Button {
                        id: btnReturn
                        objectName: "btnReturn"
                        text: "คืนหนังสือ (Return)"
                        onClicked: root.returnRequested()
                    }
                }
                Text {
                    id: deskStatusText
                    objectName: "deskStatusText"
                    font.pixelSize: 14
                    color: "#2563eb"
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
