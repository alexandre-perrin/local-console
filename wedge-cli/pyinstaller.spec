# -*- mode: python ; coding: utf-8 -*-
import sys
import os

from kivy_deps import sdl2, glew
from kivymd import hooks_path as kivymd_hooks_path

path = os.path.abspath('src\\wedge_cli')
#sys.path.insert(0, os.path.join(path, "libs"))

a = Analysis(
    ['src\\wedge_cli\\__main__.py'],
    pathex=[path],
    hiddenimports=['kivymd.icon_definitions', 'kivymd.icon_definitions.md_icons'],
    hookspath=[kivymd_hooks_path],
    cipher=None,
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
a.datas += (
    Tree('src\\wedge_cli\\gui\\assets', prefix='wedge_cli\\gui\\assets')
    + Tree('src\\wedge_cli\\assets', prefix='wedge_cli\\assets', excludes=['tmp', '*.pyc', '*.py'])
    + Tree('src\\wedge_cli\\gui\\View', prefix='wedge_cli\\gui\\View', excludes=['tmp', '*.pyc', '*.py'])
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    name="wedge_cli",
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)],
    strip=False,
    upx=True,
    upx_exclude=[],
    name='wedge_cli',
)
