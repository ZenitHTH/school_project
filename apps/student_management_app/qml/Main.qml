import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../../common_qml"
import "views"
import "dialogs"

ApplicationWindow {
    id: window
    visible: true
    width: 1200
    height: 800
    minimumWidth: 900
    minimumHeight: 600
    title: "ระบบจัดการข้อมูลนักเรียน (Student Management)"
    color: "#f5f6f8"

    property var selectedStudent: null
    property string selectedXlsxPath: ""

    // Responsive font scaling based on window width
    property real baseFontSize: Math.max(11, Math.min(14, (window.width - 240) / 130))

    // Pagination properties
    property bool __initialSearch__: true
    property int currentOffset: 0
    property int currentPage: 1
    property int pageSize: 50
    property int totalStudentsCount: 0
    property int totalPages: Math.max(1, Math.ceil(totalStudentsCount / pageSize))

    // Aliases to inner elements for test and script access
    property alias searchInput: searchView.searchInput
    property alias searchButton: searchView.searchButton
    property alias studentList: searchView.studentList
    property alias searchResultsModel: searchView.searchResultsModel

    property alias actionFeedback: detailView.actionFeedback

    property alias selectFileButton: importView.selectFileButton
    property alias selectedFilePath: importView.selectedFilePath
    property alias btnPreviewDiff: importView.btnPreviewDiff
    property alias importButton: importView.importButton
    property alias importStatusText: importView.importStatusText
    property alias newBadgeText: importView.newBadgeText
    property alias promoBadgeText: importView.promoBadgeText
    property alias missingBadgeText: importView.missingBadgeText
    property alias conflictBadgeText: importView.conflictBadgeText
    property alias diffListView: importView.diffListView
    property alias diffModel: importView.diffModel

    property alias logList: auditLogView.logList
    property alias logModel: auditLogView.logModel

    property alias roomDialog: actionDialogs.roomDialog
    property alias statusDialog: actionDialogs.statusDialog
    property alias nameDialog: actionDialogs.nameDialog
    property alias idDialog: actionDialogs.idDialog
    property alias confirmImportDialog: actionDialogs.confirmImportDialog

    property alias firstLaunchDialog: firstLaunchDialog

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Sidebar Navigation
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 240
            color: "#1e293b"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Text {
                    text: "🎓 งานทะเบียนนักเรียน"
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 18
                    Layout.alignment: Qt.AlignHCenter
                    Layout.topMargin: 10
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: "#334155"
                    Layout.bottomMargin: 10
                }

                Repeater {
                    model: [
                        { text: "🔍 ค้นหานักเรียน", index: 0 },
                        { text: "👤 ข้อมูลนักเรียน / แก้ไข", index: 1 },
                        { text: "📈 เลื่อนชั้นประจำปี", index: 2 },
                        { text: "📤 ส่งออกข้อมูล (LINE Sync)", index: 3 },
                        { text: "📜 ประวัติกิจกรรม (Audit Log)", index: 4 },
                        { text: "📥 นำเข้าไฟล์ Excel (.xlsx)", index: 5 }
                    ]
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        height: 42
                        radius: 8
                        color: stackLayout.currentIndex === modelData.index ? "#2563eb" : (sideMouse.containsMouse ? "#1e293b" : "transparent")

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            Text {
                                text: modelData.text
                                color: stackLayout.currentIndex === modelData.index ? "#ffffff" : "#cbd5e1"
                                font.pixelSize: Math.max(13, baseFontSize)
                                font.bold: stackLayout.currentIndex === modelData.index
                                Layout.fillWidth: true
                            }
                        }

                        MouseArea {
                            id: sideMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (modelData.index === 4) loadLogs()
                                stackLayout.currentIndex = modelData.index
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                Button {
                    id: openWizardBtn
                    objectName: "openWizardBtn"
                    Layout.fillWidth: true
                    text: "⚙️ ตัวช่วยสร้างฐานข้อมูล"
                    font.pixelSize: 11
                    flat: true
                    contentItem: Text {
                        text: openWizardBtn.text
                        font: openWizardBtn.font
                        color: "#94a3b8"
                        horizontalAlignment: Text.AlignHCenter
                    }
                    onClicked: firstLaunchDialog.open()
                }

                Text {
                    text: "สถานะ: เชื่อมต่อฐานข้อมูลแล้ว"
                    color: "#94a3b8"
                    font.pixelSize: 12
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }

        // Content Area
        StackLayout {
            id: stackLayout
            objectName: "mainStack"
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: 0

            // 0. Search Screen
            StudentSearchView {
                id: searchView
                baseFontSize: window.baseFontSize
                currentPage: window.currentPage
                totalPages: window.totalPages
                totalStudentsCount: window.totalStudentsCount
                onSearchRequested: window.doSearch()
                onViewStudentRequested: function(studentId) {
                    window.loadStudentDetail(studentId)
                    stackLayout.currentIndex = 1
                }
                onPageRequested: function(page) {
                    window.goToPage(page)
                }
            }

            // 1. Student Detail & Actions Screen
            StudentDetailView {
                id: detailView
                baseFontSize: window.baseFontSize
                selectedStudent: window.selectedStudent
                onBackToSearchRequested: stackLayout.currentIndex = 0
                onRequestChangeRoom: actionDialogs.openRoomDialog()
                onRequestChangeStatus: actionDialogs.openStatusDialog()
                onRequestEditName: actionDialogs.openNameDialog()
                onRequestChangeId: actionDialogs.openIdDialog()
                onDirectLookupRequested: function(query) {
                    var res = JSON.parse(studentAdmin.searchStudents(query))
                    if (res.length > 0) {
                        window.loadStudentDetail(res[0].student_id)
                    }
                }
            }

            // 2. Bulk Promotion Screen
            BulkPromotionView {
                id: promotionView
                baseFontSize: window.baseFontSize
            }

            // 3. Snapshot Export Screen
            LineSyncExportView {
                id: exportView
                baseFontSize: window.baseFontSize
            }

            // 4. Audit Log Screen (Shared component from common_qml)
            AuditLogView {
                id: auditLogView
            }

            // 5. Import Excel Screen
            ExcelImportView {
                id: importView
                baseFontSize: window.baseFontSize
                selectedXlsxPath: window.selectedXlsxPath
                onSelectFileClicked: excelFileDialog.open()
                onPreviewDiffClicked: window.previewXlsxDiff()
                onImportClicked: window.doImportXlsx(false)
            }
        }
    }

    // Action Dialogs
    StudentActionDialogs {
        id: actionDialogs
        rootWindow: window
    }

    // First Launch Wizard Dialog (from common_qml)
    FirstLaunchDialog {
        id: firstLaunchDialog
        bannerTitle: "ยินดีต้อนรับสู่ระบบงานทะเบียนนักเรียน"
        bannerSubtitle: "ยังไม่พบข้อมูลนักเรียนในระบบ หรือเป็นการเริ่มต้นใช้งานครั้งแรก"
        promptText: "คุณมีไฟล์บัญชีรายชื่อนักเรียน (.xlsx) หรือไม่?"
        explanationText: "• หากมีไฟล์ Excel: เลือกระบบนำเข้าเพื่อสร้างบัญชีรายชื่อ ม.1 - ม.6 อัตโนมัติ\n• หากไม่มีไฟล์: ระบบจะสร้างฐานข้อมูลเปล่าตามโครงสร้างตารางมาตรฐานพร้อมใช้งาน"
        importButtonText: "📁 มีไฟล์ Excel (.xlsx) — เลือกไฟล์นำเข้า"
        blankButtonText: "🆕 ไม่มีไฟล์ — สร้างฐานข้อมูลเปล่า"
        onImportClicked: firstLaunchFileDialog.open()
        onBlankClicked: {
            var res = JSON.parse(studentAdmin.initializeBlankDatabase("Admin"))
            firstLaunchDialog.close()
            actionFeedback.isError = !res.ok
            actionFeedback.text = res.ok
                ? "✓ สร้างฐานข้อมูลเปล่าตามโครงสร้างระบบเรียบร้อยแล้ว พร้อมใช้งาน"
                : ("✗ " + res.error)
            doSearch()
        }
    }

    FileDialog {
        id: firstLaunchFileDialog
        objectName: "firstLaunchFileDialog"
        title: "เลือกไฟล์บัญชีรายชื่อนักเรียน (.xlsx)"
        nameFilters: ["Excel files (*.xlsx *.xls)", "All files (*)"]
        onAccepted: {
            var path = selectedFile.toString()
            if (path.indexOf("file://") === 0) {
                path = decodeURIComponent(path.substring(7))
            }
            firstLaunchDialog.statusText = "กำลังนำเข้าข้อมูลจาก: " + path + "..."
            var res = JSON.parse(studentAdmin.importXlsx(path, false, "Admin"))
            if (res.need_confirm) {
                firstLaunchDialog.close()
                window.selectedXlsxPath = path
                actionDialogs.showConfirmImport(res.warning, 0, 0, 0, 0)
                return
            }
            if (res.ok) {
                firstLaunchDialog.statusText = "✓ นำเข้าสำเร็จ " + res.data.students + " คน เรียบร้อยแล้ว"
                actionFeedback.isError = false
                actionFeedback.text = "✓ นำเข้าข้อมูลนักเรียน " + res.data.students + " คน สำเร็จ"
                doSearch()
                firstLaunchTimer.start()
            } else {
                firstLaunchDialog.statusText = "✗ เกิดข้อผิดพลาด: " + res.error
            }
        }
    }

    Timer {
        id: firstLaunchTimer
        interval: 1200
        repeat: false
        onTriggered: {
            firstLaunchDialog.close()
        }
    }

    FileDialog {
        id: excelFileDialog
        title: "เลือกไฟล์บัญชีรายชื่อนักเรียน (.xlsx)"
        nameFilters: ["Excel files (*.xlsx *.xls)", "All files (*)"]
        onAccepted: {
            var path = selectedFile.toString()
            if (path.indexOf("file://") === 0) {
                path = decodeURIComponent(path.substring(7))
            }
            window.selectedXlsxPath = path
        }
    }

    function loadStudentDetail(studentId) {
        if (typeof studentAdmin === "undefined" || !studentAdmin) return
        var res = JSON.parse(studentAdmin.getStudent(studentId))
        if (res && res.student_id) {
            window.selectedStudent = res
        }
    }

    function goToPage(page) {
        if (page < 1 || page > window.totalPages) return
        window.currentPage = page
        window.currentOffset = (page - 1) * window.pageSize
        loadSearchResults()
    }

    function doSearch() {
        window.currentPage = 1
        window.currentOffset = 0
        window.totalStudentsCount = (typeof studentAdmin !== "undefined" && studentAdmin && studentAdmin.countStudents)
            ? studentAdmin.countStudents(searchView.searchInput.text)
            : 0
        loadSearchResults()
    }

    function loadSearchResults() {
        searchResultsModel.clear()
        if (typeof studentAdmin === "undefined" || !studentAdmin) return
        var query = searchView.searchInput ? searchView.searchInput.text : ""
        var results = JSON.parse(studentAdmin.searchStudents(query, window.currentOffset))
        if (results.length === 0 && window.__initialSearch__) {
            searchResultsModel.append({"_empty": true})
        } else if (results.length > 0) {
            for (var i = 0; i < results.length; i++) {
                searchResultsModel.append(results[i])
            }
        }
        window.__initialSearch__ = false
    }

    function loadMoreStudents() {
        goToPage(window.currentPage + 1)
    }

    function previewXlsxDiff() {
        if (!window.selectedXlsxPath) {
            importStatusText.text = "กรุณาเลือกไฟล์ Excel ก่อนตรวจสอบ"
            return
        }
        diffModel.clear()
        importStatusText.text = "กำลังตรวจสอบโครงสร้างและเปรียบเทียบข้อมูล..."
        var diffRes = JSON.parse(studentAdmin.previewXlsxDiff(window.selectedXlsxPath))
        if (!diffRes.ok) {
            importStatusText.text = "เกิดข้อผิดพลาดในการตรวจสอบ: " + diffRes.error
            return
        }
        var data = diffRes.data
        var newCount = data.new_students ? data.new_students.length : 0
        var promoCount = data.grade_room_changes ? data.grade_room_changes.length : 0
        var missingCount = data.missing_students ? data.missing_students.length : 0
        var conflictCount = data.identity_conflicts ? data.identity_conflicts.length : 0

        newBadgeText.text = "• นักเรียนใหม่: " + newCount + " คน"
        promoBadgeText.text = "• เลื่อนชั้น/เปลี่ยนห้อง: " + promoCount + " คน"
        missingBadgeText.text = "• ไม่มีในไฟล์: " + missingCount + " คน (คงเดิม)"
        conflictBadgeText.text = "• สะกดต่างจากเดิม: " + conflictCount + " คน"

        importStatusText.text = "ผลการตรวจสอบความเปลี่ยนแปลง (พบทั้งหมด " + data.total_in_file + " คนในไฟล์): ตรวจสอบรายการด้านล่างแล้วกด 'ยืนยันนำเข้าข้อมูล'"

        // Populate conflicts first
        if (data.identity_conflicts) {
            for (var c = 0; c < data.identity_conflicts.length; c++) {
                var conf = data.identity_conflicts[c]
                diffModel.append({
                    desc: "⚠️ ชื่อสะกดต่าง: รหัส " + conf.student_id + " (ในระบบ: " + conf.db_name + " ➔ ในไฟล์: " + conf.file_name + ")",
                    category: "conflict"
                })
            }
        }
        // Populate grade/room changes
        if (data.grade_room_changes) {
            for (var p = 0; p < data.grade_room_changes.length; p++) {
                var chg = data.grade_room_changes[p]
                diffModel.append({
                    desc: "📈 เลื่อนชั้น/ย้ายห้อง: รหัส " + chg.student_id + " (ม." + (chg.old_grade || "-") + "/" + (chg.old_room || "-") + " ➔ ม." + (chg.new_grade || "-") + "/" + (chg.new_room || "-") + ")",
                    category: "promo"
                })
            }
        }
        // Populate new students
        if (data.new_students) {
            for (var n = 0; n < data.new_students.length; n++) {
                var ns = data.new_students[n]
                diffModel.append({
                    desc: "✨ นักเรียนใหม่: รหัส " + ns.student_id + " " + (ns.full_name || "") + " (ม." + (ns.grade_level || "-") + "/" + (ns.room || "-") + ")",
                    category: "new"
                })
            }
        }
        // Populate missing students
        if (data.missing_students) {
            for (var m = 0; m < data.missing_students.length; m++) {
                var ms = data.missing_students[m]
                diffModel.append({
                    desc: "ℹ️ ไม่มีในไฟล์ใหม่: รหัส " + ms.student_id + " " + (ms.full_name || "") + " (คงสถานะปกติ)",
                    category: "missing"
                })
            }
        }
    }

    function doImportXlsx(force) {
        if (!window.selectedXlsxPath) {
            importStatusText.text = "กรุณาเลือกไฟล์ Excel ก่อนนำเข้า"
            return
        }
        importStatusText.text = "กำลังตรวจสอบโครงสร้างและเปรียบเทียบข้อมูล..."
        var diffRes = JSON.parse(studentAdmin.previewXlsxDiff(window.selectedXlsxPath))
        if (diffRes.ok) {
            actionDialogs.showConfirmImport(
                "พบข้อมูลในระบบ ระบบจะทำการเลื่อนชั้นและเพิ่มนักเรียนใหม่โดยไม่ลบประวัติเดิม:",
                diffRes.data.new_students.length,
                diffRes.data.grade_room_changes.length,
                diffRes.data.missing_students.length,
                diffRes.data.identity_conflicts.length,
                diffRes.data.detected_year,
                diffRes.data.detected_semester
            )
            importStatusText.text = "รอการยืนยันการนำเข้าและเลื่อนชั้น..."
            return
        }

        var res = JSON.parse(studentAdmin.importXlsx(window.selectedXlsxPath, force, "Admin"))
        if (res.ok) {
            importStatusText.text = "นำเข้าสำเร็จ!\n" +
                "นักเรียน: " + res.data.students + " คน\n" +
                "การลงทะเบียน: " + res.data.enrollments + " รายการ\n" +
                "ย้ายออก: " + res.data.transfers_out + " | ย้ายเข้า: " + res.data.transfers_in
            doSearch()
        } else {
            importStatusText.text = "เกิดข้อผิดพลาด: " + res.error
        }
    }

    function loadLogs() {
        logModel.clear()
        if (typeof studentAdmin === "undefined" || !studentAdmin) return
        var logs = JSON.parse(studentAdmin.getActivityLogs())
        for (var i = 0; i < logs.length; i++) logModel.append(logs[i])
    }

    Component.onCompleted: {
        if (typeof studentAdmin !== "undefined" && studentAdmin !== null) {
            doSearch()
            if (studentAdmin.isFirstLaunch()) {
                firstLaunchDialog.open()
            }
        }
    }
}
