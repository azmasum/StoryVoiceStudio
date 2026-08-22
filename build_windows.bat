@echo off
setlocal
REM StoryVoice Studio - Windows release build (tests + PyInstaller + portable zip)
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    pause
    exit /b 1
)

echo === Installing/updating build dependencies ===
python -m pip install --upgrade -r requirements.txt pyinstaller || goto :fail

echo === Running test suite (release gate) ===
set "PYTHONPATH=%~dp0;%~dp0.pylibs"
python -m pytest tests -q || goto :fail

echo === Building EXE with PyInstaller ===
python -m PyInstaller packaging\StoryVoiceStudio.spec --noconfirm || goto :fail

echo === Creating portable ZIP ===
python packaging\make_portable_zip.py || goto :fail

echo.
echo === BUILD OK ===
echo Artifacts in dist\
pause
exit /b 0

:fail
echo [ERROR] Build failed. See messages above.
pause
exit /b 1
