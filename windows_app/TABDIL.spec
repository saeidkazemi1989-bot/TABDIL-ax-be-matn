# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for TABDIL.
Build on Windows:  Build-EXE.bat
"""
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None
ROOT = os.path.abspath('.')

datas = [
    (os.path.join('TABDIL', 'tessdata'), os.path.join('tessdata')),
    (os.path.join('TABDIL', 'assets'), os.path.join('assets')),
]
binaries = []
hiddenimports = ['pytesseract', 'customtkinter', 'tkinterdnd2',
                 'openpyxl', 'docx', 'cv2', 'PIL']

for pkg in ('customtkinter', 'tkinterdnd2'):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ['run_app.py'],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['matplotlib', 'paddle', 'paddleocr', 'paddlepaddle',
              'torch', 'torchvision', 'scipy', 'pandas'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TABDIL',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join('TABDIL', 'assets', 'logo.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='TABDIL',
)
