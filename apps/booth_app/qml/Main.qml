import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: boothWindow
    visible: true
    width: 1024
    height: 768
    minimumWidth: 800
    minimumHeight: 600
    title: "จุดบริการยืม-คืนหนังสืออัตโนมัติ (Self-Service Booth)"
    color: "#0f172a"

    property var identifiedStudent: null

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 80, 700)
        spacing: 24

        Text {
            text: "📖 บริการยืม-คืนหนังสือด้วยตนเอง"
            color: "#ffffff"
            font.bold: true
            font.pixelSize: 28
            Layout.alignment: Qt.AlignHCenter
        }

        // Empty DB Warning Banner
        Rectangle {
            id: emptyDbWarningBanner
            objectName: "emptyDbWarningBanner"
            Layout.fillWidth: true
            height: 60
            color: "#451a03"
            radius: 8
            border.color: "#b45309"
            visible: (typeof boothAdapter !== "undefined" && boothAdapter !== null) ? boothAdapter.isDatabaseEmpty() : false

            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 10
                Text {
                    text: "⚠️"
                    font.pixelSize: 22
                }
                ColumnLayout {
                    spacing: 2
                    Text {
                        text: "ยังไม่มีข้อมูลในระบบ หรือฐานข้อมูลว่าง"
                        color: "#fde047"
                        font.bold: true
                        font.pixelSize: 13
                    }
                    Text {
                        text: "กรุณาติดต่อบรรณารักษ์เพื่อทำการ Sync ข้อมูลนักเรียน/หนังสือเข้าระบบก่อนเริ่มใช้งาน"
                        color: "#fef08a"
                        font.pixelSize: 11
                    }
                }
            }
        }

        // Student Card
        Rectangle {
            Layout.fillWidth: true
            height: 140
            color: "#1e293b"
            radius: 12
            border.color: "#334155"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 10

                Text {
                    text: "ขั้นตอนที่ 1: แตะบัตรหรือกรอกรหัสนักเรียน"
                    color: "#94a3b8"
                    font.pixelSize: 14
                }

                RowLayout {
                    TextField {
                        id: studentIdInput
                        objectName: "studentIdInput"
                        placeholderText: "พิมพ์รหัสนักเรียน..."
                        font.pixelSize: 18
                        Layout.fillWidth: true
                        color: "#ffffff"
                        onAccepted: identifyStudent()
                    }
                    Button {
                        objectName: "btnIdentify"
                        text: "ยืนยันตัวตน"
                        highlighted: true
                        onClicked: identifyStudent()
                    }
                }

                Text {
                    id: studentStatusMsg
                    objectName: "studentStatusMsg"
                    text: boothWindow.identifiedStudent ? ("ยินดีต้อนรับ: " + boothWindow.identifiedStudent.full_name) : "ยังไม่ได้ระบุตัวตน"
                    color: boothWindow.identifiedStudent ? "#34d399" : "#64748b"
                    font.bold: true
                    font.pixelSize: 15
                }
            }
        }

        // Book Scan Card
        Rectangle {
            Layout.fillWidth: true
            height: 160
            color: "#1e293b"
            radius: 12
            border.color: "#334155"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 12

                Text {
                    text: "ขั้นตอนที่ 2: สแกนบาร์โค้ดหนังสือ"
                    color: "#94a3b8"
                    font.pixelSize: 14
                }

                TextField {
                    id: bookBarcodeInput
                    objectName: "bookBarcodeInput"
                    placeholderText: "สแกนบาร์โค้ดหนังสือ..."
                    font.pixelSize: 18
                    Layout.fillWidth: true
                    color: "#ffffff"
                }

                RowLayout {
                    spacing: 16
                    Layout.alignment: Qt.AlignHCenter

                    Button {
                        objectName: "btnCheckout"
                        text: "✅ ยืมหนังสือ (Checkout)"
                        highlighted: true
                        enabled: boothWindow.identifiedStudent !== null
                        onClicked: doCheckout()
                    }

                    Button {
                        objectName: "btnReturn"
                        text: "📥 คืนหนังสือ (Return)"
                        onClicked: doReturn()
                    }
                }
            }
        }

        // Result Message Banner
        Rectangle {
            Layout.fillWidth: true
            height: 60
            color: "#1e293b"
            radius: 8
            border.color: "#38bdf8"

            Text {
                id: feedbackBanner
                objectName: "feedbackBanner"
                anchors.centerIn: parent
                text: "กรุณาระบุตัวตนเพื่อเริ่มทำรายการ"
                color: "#38bdf8"
                font.bold: true
                font.pixelSize: 16
            }
        }

        Button {
            objectName: "btnLogout"
            text: "เสร็จสิ้น / ออกจากระบบ"
            Layout.alignment: Qt.AlignHCenter
            onClicked: {
                boothWindow.identifiedStudent = null
                studentIdInput.text = ""
                bookBarcodeInput.text = ""
                feedbackBanner.text = "ขอบคุณที่ใช้บริการ"
            }
        }
    }

    function identifyStudent() {
        var res = JSON.parse(boothAdapter.searchStudents(studentIdInput.text))
        if (res.length > 0) {
            boothWindow.identifiedStudent = res[0]
            feedbackBanner.text = "ระบุตัวตนสำเร็จ: " + res[0].full_name
        } else {
            feedbackBanner.text = "ไม่พบรหัสนักเรียนในระบบ"
        }
    }

    function doCheckout() {
        if (!boothWindow.identifiedStudent || !bookBarcodeInput.text) {
            feedbackBanner.text = "กรุณากรอกข้อมูลให้ครบถ้วน"
            return
        }
        var res = JSON.parse(boothAdapter.checkout(boothWindow.identifiedStudent.student_id, bookBarcodeInput.text))
        if (res.ok) {
            feedbackBanner.text = "ยืมหนังสือสำเร็จ! กำหนดคืน: " + res.data.due_at.substring(0, 10)
            bookBarcodeInput.text = ""
        } else {
            feedbackBanner.text = "ยืมไม่สำเร็จ: " + res.error
        }
    }

    function doReturn() {
        if (!bookBarcodeInput.text) {
            feedbackBanner.text = "กรุณาสแกนบาร์โค้ดหนังสือที่ต้องการคืน"
            return
        }
        var res = JSON.parse(boothAdapter.returnByBarcode(bookBarcodeInput.text))
        if (res.ok) {
            feedbackBanner.text = "คืนหนังสือสำเร็จเรียบร้อยแล้ว ขอบคุณที่ใช้บริการ"
            bookBarcodeInput.text = ""
        } else {
            feedbackBanner.text = "คืนไม่สำเร็จ: " + res.error
        }
    }
}
