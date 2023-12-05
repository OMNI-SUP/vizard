# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\1\\Desktop\\scripts\\vizard\\win\\vizard.pyw'],
    pathex=[],
    binaries=[],
    datas=[('C:/Users/1/Desktop/scripts/vizard/win', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='vizard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\1\\Desktop\\scripts\\vizard\\win\\omni.ico'],
)
