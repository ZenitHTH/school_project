# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None
_ver_file = os.path.join(SPECPATH, '..', 'VERSION')
APP_VERSION = open(_ver_file, encoding='utf-8').read().strip() if os.path.exists(_ver_file) else '0.0.0'
_strip_binaries = not sys.platform.startswith('win')

datas = [
    ('../VERSION', '.'),
    ('../data/migrations/*.sql', 'data/migrations'),
    ('../apps/booth_app/qml/*.qml', 'apps/booth_app/qml'),
    ('../apps/common_qml/*.qml', 'apps/common_qml'),
    ('../apps/common_qml/*.js', 'apps/common_qml'),
    ('../apps/common_qml/fonts/*', 'apps/common_qml/fonts'),
    ('../apps/common_qml/qmldir', 'apps/common_qml'),
    ('../assets/icons/*.png', 'assets/icons'),
]
binaries = []
hiddenimports = ['sqlite3']

a = Analysis(
    ['../apps/booth_app/main.py'],
    pathex=['..'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'tkinter', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

if sys.platform.startswith("linux"):
    EXCLUDE_BINARIES = ("libglib", "libgio", "libgobject", "libgmodule")
    a.binaries = [
        x for x in a.binaries
        if not any(os.path.basename(x[0]).lower().startswith(p) for p in EXCLUDE_BINARIES)
    ]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BoothApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=_strip_binaries,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../assets/icons/boothapp.ico' if sys.platform == 'win32' else '../assets/icons/boothapp.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=_strip_binaries,
    upx=False,
    upx_exclude=[],
    name='BoothApp',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='BoothApp.app',
        icon='../assets/icons/boothapp.icns',
        bundle_identifier='com.school.boothapp',
        version=APP_VERSION,
    )
