# -*- mode: python ; coding: utf-8 -*-
import sys

block_cipher = None

a = Analysis(
    ['../apps/librarian_management_app/main.py'],
    pathex=['..'],
    binaries=[],
    datas=[
        ('../data/migrations/*.sql', 'data/migrations'),
        ('../apps/librarian_management_app/qml/*.qml', 'apps/librarian_management_app/qml'),
    ],
    hiddenimports=['sqlite3'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LibrarianManagement',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='LibrarianManagement.app',
        icon=None,
        bundle_identifier='com.school.librarianmanagement',
    )
