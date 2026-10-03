# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for StoryVoice Studio (Windows, one-folder portable build).
#
# Narration runs on the Google Gemini API (stdlib urllib only), so no TTS
# engine packages are bundled - the build is small and fully offline except
# for the API calls the user triggers.

block_cipher = None

datas = [
    ("..\\assets", "assets"),
]

a = Analysis(
    ["..\\app\\main.py"],
    pathex=[".."],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "soundfile",
        "pyloudnorm",
        "appdirs",
        "scipy.signal",
        "scipy.io.wavfile",
        "PySide6.QtMultimedia",
        "wave",
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
