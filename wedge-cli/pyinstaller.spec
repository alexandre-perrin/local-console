# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import platform

from kivymd import hooks_path as kivymd_hooks_path

path = os.path.abspath('src/wedge_cli')

a = Analysis(
    ['src/wedge_cli/__main__.py'],
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
    Tree('wedge-cli/src/wedge_cli/gui/assets', prefix='wedge_cli/gui/assets')
    + Tree('wedge-cli/src/wedge_cli/assets', prefix='wedge_cli/assets', excludes=['tmp', '*.pyc', '*.py'])
    + Tree('wedge-cli/src/wedge_cli/gui/View', prefix='wedge_cli/gui/View', excludes=['tmp', '*.pyc', '*.py'])
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
    name="offline-tool",
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

bins = []
if platform.system() == "Windows":
    from kivy_deps import sdl2, glew
    bins = [Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)]

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    *bins,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='offline_tool',
)
