# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build specification for Bazaar Overlay
Optimized for faster builds
"""

from pathlib import Path

block_cipher = None
root = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(root)],
    binaries=[],
    datas=[
        ('data/items.json', 'data'),
    ],
    hiddenimports=[
        'cv2',
        'numpy',
        'mss',
        'pynput',
        'PySide6',
        'easyocr',
        'torch',
        'torchvision',
        'PIL',
        'win32api',
        'win32con',
        'win32gui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'IPython',
        'notebook',
        'sphinx',
        'pytest',
        'tensorflow',
        'keras',
        'pandas',
        'sklearn',
        'scipy',
        'PIL.ImageFilter',
        'PIL.MpegImagePlugin',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BazaarOverlay',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(root / 'assets' / 'icon.ico'),
    version=str(root / 'version_info.txt'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BazaarOverlay',
)
