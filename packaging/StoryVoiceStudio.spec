# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for StoryVoice Studio (Windows, one-folder portable build)

import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

datas = [
    ("..\\assets", "assets"),
    ("..\\models", "models"),
    # Vendored MIT-licensed OpenVoice (voice-clone tone transfer). Copied
    # as a top-level package so `import openvoice` resolves at runtime.
    ("..\\audio\\clone\\openvoice", "openvoice"),
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
        "appdirs",
        "scipy.signal",
        "scipy.io.wavfile",
        "PySide6.QtMultimedia",
        "ctypes.wintypes",
        "pickletools",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pytest",
              "setuptools", "pkg_resources"],
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
