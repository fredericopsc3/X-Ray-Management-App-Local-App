# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=['.'],
    datas=[
      ('model/best.pt', 'model'),
      ('data/patients.db', 'data'),
      ('data/xrays', 'data/xrays'),
    ],
    hiddenimports=['ultralytics', 'PySide6'],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, name='XrayApp', console=False)
