#!/usr/bin/env python3
"""Unified Desktop Launcher for School Management & Library System."""

import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

APPS = {
    "student": (
        "🏫 Student Management (งานทะเบียนนักเรียน)",
        PROJECT_ROOT / "apps" / "student_management_app" / "main.py",
    ),
    "librarian": (
        "📚 Librarian Management (ระบบจัดการห้องสมุด)",
        PROJECT_ROOT / "apps" / "librarian_management_app" / "main.py",
    ),
    "booth": (
        "💻 Self-Service Booth (ตู้บริการยืม-คืนอัตโนมัติ)",
        PROJECT_ROOT / "apps" / "booth_app" / "main.py",
    ),
}


def launch_app(key: str):
    script_path = APPS[key][1]
    env = os.environ.copy()
    proc = subprocess.Popen([sys.executable, str(script_path)], env=env)
    return proc


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower().strip("-")
        if arg in APPS:
            launch_app(arg)
            return

    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QApplication,
            QLabel,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("PySide6 not installed. Choose an app to run:")
        for idx, (k, (name, _)) in enumerate(APPS.items(), 1):
            print(f"  {idx}) {k:10} - {name}")
        choice = input("Enter choice (student/librarian/booth): ").strip().lower()
        if choice in APPS:
            launch_app(choice)
        return

    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("School System App Launcher")
    window.setFixedSize(420, 280)

    layout = QVBoxLayout()
    layout.setContentsMargins(24, 24, 24, 24)
    layout.setSpacing(12)

    title = QLabel("🏫 School & Library Management")
    title.setAlignment(Qt.AlignCenter)
    title.setStyleSheet("font-size: 16px; font-weight: bold;")
    layout.addWidget(title)

    desc = QLabel("Select an application to launch:")
    desc.setAlignment(Qt.AlignCenter)
    desc.setStyleSheet("color: #666; font-size: 12px; margin-bottom: 8px;")
    layout.addWidget(desc)

    for key, (label, _) in APPS.items():
        btn = QPushButton(label)
        btn.setFixedHeight(44)
        btn.setStyleSheet("font-size: 13px; font-weight: 500; border-radius: 6px;")
        btn.clicked.connect(lambda checked, k=key: launch_app(k))
        layout.addWidget(btn)

    window.setLayout(layout)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
