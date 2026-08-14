# -*- mode: python ; coding: utf-8 -*-
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
MAIN = os.path.join(ROOT, "main.py")

datas = []
for src, dest in [
    (os.path.join(ROOT, "logo.png"), "."),
    (os.path.join(ROOT, "water_demand_app", "assets", "logo.png"), "assets"),
    (os.path.join(ROOT, "templates", "WaterDemand_Template.xlsx"), "templates"),
    (os.path.join(ROOT, "water_demand_app", "templates", "WaterDemand_Template.xlsx"), "templates"),
]:
    if os.path.isfile(src):
        datas.append((src, dest))

a = Analysis(
    [MAIN],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "PIL",
        "PIL.Image",
        "tkcalendar",
        "openpyxl",
        "reportlab",
        "reportlab.lib.utils",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AmericanEdge_WaterDemand',
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
)
