# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = [
    ('../data/migrations/*.sql', 'data/migrations'),
    ('../apps/librarian_management_app/qml/*.qml', 'apps/librarian_management_app/qml'),
    ('../apps/common_qml/*.qml', 'apps/common_qml'),
    ('../apps/common_qml/qmldir', 'apps/common_qml'),
]
binaries = []
hiddenimports = ['sqlcipher3', 'pysqlcipher3', 'sqlite3']

for pkg in ['core', 'data', 'apps']:
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ['../apps/librarian_management_app/main.py'],
    pathex=['..'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
