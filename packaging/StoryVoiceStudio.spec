# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for StoryVoice Studio (Windows, one-folder portable build)

import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

datas = [
    ("..\\assets", "assets"),
    ("..\\models", "models"),
]
datas += collect_data_files("piper", include_py_files=False)

a = Analysis(
    ["..\\app\\main.py"],
    pathex=[".."],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "piper",
        "soundfile",
        "pyloudnorm",
        "scipy.signal",
        "scipy.io.wavfile",
        "PySide6.QtMultimedia",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pytest", "scipy.stats"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="StoryVoiceStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="StoryVoiceStudio",
)
