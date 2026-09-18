# School Management & Library System

ระบบบริหารจัดการงานทะเบียนนักเรียนและระบบห้องสมุดโรงเรียน (School Management & Library Automation System) พัฒนาด้วย **Python 3**, **PySide6 (Qt Quick / QML)**, และ **SQLite3** ภายใต้สถาปัตยกรรมแบบ Offline-First พร้อมระบบรักษาความปลอดภัยด้วยรหัส PIN และระบบ Synchronization แบบ Snapshot

---

## 📌 ภาพรวมสถาปัตยกรรม (System Overview)

ระบบแบ่งออกเป็น 3 แอปพลิเคชันหลักที่ทำงานร่วมกัน:

```
                  ┌─────────────────────────────────────────────────┐
                  │    งานทะเบียนนักเรียน (Student Management App)    │
                  │  - ทะเบียนประวัติ, ย้ายห้อง, เปลี่ยนสถานะ, แก้ไขชื่อ   │
                  │  - นำเข้า Excel บัญชีรายชื่อ (.xlsx)               │
                  │  - เลื่อนชั้นเรียนประจำปี (Bulk Promotion)         │
                  └────────────────────────┬────────────────────────┘
                                           │
                                           │ ส่งออก snapshot.sqlite
                                           ▼
┌──────────────────────────────────────────────────┬──────────────────────────────────────────────────┐
│        ระบบห้องสมุด (Librarian Management App)    │      จุดบริการยืม-คืนด้วยตนเอง (Self-Service Booth) │
│  - จัดการแคตตาล็อกหนังสือ และบาร์โค้ดประจำเล่ม           │  - แตะบัตร/พิมพ์รหัสนักเรียนเพื่อยืนยันตัวตน              │
│  - เคาน์เตอร์ยืม-คืนหนังสือประจำวัน                   │  - สแกนบาร์โค้ดเพื่อยืมหนังสือด้วยตนเอง               │
│  - ตรวจสอบรายการยืมค้าง และบันทึกค่าปรับ             │  - สแกนบาร์โค้ดเพื่อคืนหนังสืออัตโนมัติ                  │
│  - Sync ข้อมูลนักเรียนจาก Snapshot (Diff & Apply)  │                                                  │
└──────────────────────────────────────────────────┴──────────────────────────────────────────────────┘
```

---

## 🚀 ฟีเจอร์หลัก (Key Features)

### 1. งานทะเบียนนักเรียน (`apps/student_management_app`)
- **ค้นหาข้อมูลนักเรียน**: ค้นหาผ่านชื่อ-นามสกุล, เลขประจำตัวนักเรียน หรือเลขประจำตัวประชาชน (FTS5 Search)
- **จัดการข้อมูลรายบุคคล**:
  - 🏫 ย้ายห้องเรียน / ปรับสมดุลห้อง
  - 📋 เปลี่ยนสถานะนักเรียน (`active`, `on_leave`, `transferred_out`) พร้อมบันทึกประวัติ
  - ✏️ แก้ไขคำนำหน้า, ชื่อจริง และนามสกุล
  - 🔢 เปลี่ยนรหัสนักเรียน (Renumber ID) พร้อม Cascade อัตโนมัติไปยังประวัติการลงทะเบียน
- **การเลื่อนชั้นเรียน (Bulk Promotion)**: เลื่อนระดับชั้น ม.1 → ม.2, ..., ม.5 → ม.6 และจบการศึกษา ม.6
- **นำเข้าข้อมูลจาก Excel (.xlsx)**: นำเข้าบัญชีรายชื่อมาตรฐาน ม.1 - ม.6 พร้อมระบบตรวจสอบความถูกต้องและระบบป้องกันการนำเข้าทับข้อมูลที่มีการยืมหนังสือแล้ว (Re-import Safeguard)
- **ตัวช่วยตั้งค่าเมื่อเริ่มใช้งานครั้งแรก (First Launch Setup Wizard)**: ตรวจจับฐานข้อมูลว่างอัตโนมัติ ให้ผู้ใช้เลือกว่าจะนำเข้าไฟล์ Excel (.xlsx) หรือสร้างฐานข้อมูลเปล่าตามกฎตาราง
- **ส่งออกข้อมูล Snapshot**: สร้างไฟล์ `snapshot.sqlite` เพื่อส่งต่อให้ห้องสมุดอัปเดตข้อมูล

### 2. ระบบจัดการห้องสมุดสำหรับบรรณารักษ์ (`apps/librarian_management_app`)
- **ตัวช่วยตั้งค่าเมื่อเริ่มใช้งานครั้งแรก (First Launch Setup Wizard)**: ให้เลือกว่าจะซิงค์ข้อมูลนักเรียนจาก `snapshot.sqlite` / Excel (.xlsx) หรือสร้างฐานข้อมูลห้องสมุดเปล่าตามกฎตาราง
- **แคตตาล็อกหนังสือ**: ค้นหาหนังสือ, เพิ่มหนังสือใหม่, ระบุ ISBN, ผู้แต่ง, หมวดหมู่ และบาร์โค้ดประจำเล่ม
- **เคาน์เตอร์ยืม-คืน (Desk Checkout/Return)**: ตรวจสอบสิทธิ์นักเรียน, บันทึกการยืมด้วยบาร์โค้ด, และรับคืนหนังสือ
- **รายการยืมที่ค้างอยู่ (Active Loans)**: แสดงรายการหนังสือที่กำลังถูกยืม พร้อมวันกำหนดคืน
- **การจัดการค่าปรับ (Fines)**: คำนวณค่าปรับเกินกำหนดอัตโนมัติ และบันทึกการชำระเงิน
- **การ Sync ข้อมูลนักเรียน**: ตรวจสอบความเปลี่ยนแปลง (Preview Diff) ก่อนกดยืนยันนำเข้าข้อมูล (Apply Sync) เพื่อความปลอดภัยสูงสุดของประวัติการยืม

### 3. ตู้บริการยืม-คืนหนังสืออัตโนมัติ (`apps/booth_app`)
- **การแจ้งเตือนความพร้อมของฐานข้อมูล**: ตรวจสอบสถานะข้อมูลนักเรียน/หนังสือ พร้อมแสดงป้ายเตือนหากฐานข้อมูลยังว่างอยู่
- **ยืนยันตัวตนนักเรียน**: รองรับการพิมพ์รหัสหรือแตะบัตรนักเรียน
- **ยืมหนังสือด้วยตนเอง**: สแกนบาร์โค้ดหนังสือเพื่อทำรายการยืมทันที
- **คืนหนังสือด้วยตนเอง**: สแกนบาร์โค้ดหนังสือเพื่อคืนเข้าสู่ระบบอัตโนมัติ

---

## 🛠️ โครงสร้างโฟลเดอร์ (Directory Structure)

```
school_project/
├── apps/
│   ├── student_management_app/      # แอปงานทะเบียนนักเรียน
│   │   ├── adapters/                # PySide6 Slot Adapters
│   │   ├── qml/                     # ส่วนติดต่อผู้ใช้ (Main.qml)
│   │   └── main.py
│   ├── librarian_management_app/    # แอปผู้ดูแลห้องสมุด
│   │   ├── adapters/
│   │   ├── qml/
│   │   └── main.py
│   └── booth_app/                   # แอปตู้ยืม-คืนอัตโนมัติ
│       ├── adapters/
│       ├── qml/
│       └── main.py
├── core/
│   ├── student/services/            # Business Logic งานทะเบียน
│   ├── library/services/            # Business Logic ห้องสมุด (Loans, Fines, Catalog)
│   ├── importers/                   # ตัวอ่านและตรวจสอบไฟล์ Excel (.xlsx)
│   └── shared/                      # Activity Log & Utilities
├── data/
│   ├── db.py                        # เชื่อมต่อ SQLite พร้อมระบบ PIN & Salted Hashing
│   ├── migrate.py                   # ระบบ Migration อัตโนมัติ
│   ├── migrations/                  # ไฟล์ SQL Schema Migrations (0001 - 0006)
│   ├── repositories/                # Data Access Objects (DAO)
│   └── sync/                        # ระบบ Export, Diff, และ Apply Snapshot
├── tests/                           # ชุดทดสอบครอบคลุมทั้งระบบ (126 tests)
│   ├── test_ui_student.py           # UI Tests สำหรับแอปทะเบียน (35 tests)
│   ├── test_ui_librarian.py         # UI Tests สำหรับแอปห้องสมุด (16 tests)
│   ├── test_ui_booth.py             # UI Tests สำหรับตู้ยืม-คืน (11 tests)
│   ├── test_adapters.py             # Unit Tests สำหรับ Adapter Layer (32 tests)
│   ├── test_importers.py            # Integration Tests ระบบนำเข้า Excel (12 tests)
│   ├── test_sync_edge_cases.py      # Edge Cases สำหรับการ Sync (6 tests)
│   └── ...
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## 💻 การติดตั้งและเริ่มต้นใช้งาน (Installation & Setup)

### ข้อกำหนดขั้นต่ำ
- **Python**: เวอร์ชัน 3.10 ขึ้นไป (แนะนำ Python 3.11 - 3.14)
- **uv**: เครื่องมือจัดการแพ็กเกจ Python ความเร็วสูง

### 1. ติดตั้ง Dependencies
```bash
# ติดตั้ง uv (หากยังไม่มี)
curl -LsSf https://astral.sh/uv/install.sh | sh

# ติดตั้งแพ็กเกจที่จำเป็น
uv sync
# หรือใช้
uv pip install -r requirements.txt
```

### 2. การเปิดใช้งานแต่ละแอปพลิเคชัน

#### งานทะเบียนนักเรียน (Student Management App)
```bash
uv run python apps/student_management_app/main.py
```

#### ระบบจัดการห้องสมุด (Librarian Management App)
```bash
uv run python apps/librarian_management_app/main.py
```

#### ตู้บริการยืม-คืนอัตโนมัติ (Self-Service Booth)
```bash
uv run python apps/booth_app/main.py
```

> **หมายเหตุการเข้าถึง**: ค่าเริ่มต้นของระบบใช้ PIN: `123456`

---

## 🧪 การทดสอบระบบ (Running Tests)

ระบบมีชุดการทดสอบครอบคลุมทั้งหน่วยการทำงาน (Unit), การบูรณาการ (Integration), และส่วนต่อประสานผู้ใช้ (UI Tests via Qt Offscreen):

```bash
# รันชุดการทดสอบทั้งหมด (137 tests)
uv run pytest -v

# รันเฉพาะชุดการทดสอบ UI (70 tests)
uv run pytest tests/test_ui_student.py tests/test_ui_librarian.py tests/test_ui_booth.py -v

# รันแบบสรุปสั้น
uv run pytest -q
```

---

## 🔒 ความปลอดภัยและการจัดการข้อมูล (Security & Data Integrity)

- **Offline-First & Local Storage**: ฐานข้อมูลทำงานบนเครื่องโลคอลผ่าน SQLite3 โดยไม่ต้องพึ่งพาอินเทอร์เน็ต
- **PIN Verification & Lockout**: ตรวจสอบรหัสผ่านผ่าน Salted SHA-256 พร้อมระบบระงับการเข้าถึงชั่วคราวหากกรอกรหัสผิดติดต่อกันเกินจำนวนครั้งที่กำหนด
- **Foreign Key Integrity**: บังคับใช้ `PRAGMA foreign_keys = ON` เพื่อป้องกันข้อมูลสูญหายหรือข้อมูลอ้างอิงไม่ตรงกัน
- **Audit Logging**: บันทึกประวัติกิจกรรมสำคัญ (การแก้ไขประวัตินักเรียน, การยืม-คืนหนังสือ, การคิดค่าปรับ) ลงในตาราง `activity_log` เสมอ
