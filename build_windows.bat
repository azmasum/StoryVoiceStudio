@echo off
setlocal
REM StoryVoice Studio - Windows release build (tests + PyInstaller + portable zip)
cd /d "%~dp0"

REM Prefer the local Python 3.11 build environment (.build\venv) because
REM Python 3.10.0's compiler emits bytecode that crashes PyInstaller's
REM modulegraph scanner. Create it once with:
REM   .build\python311\tools\python.exe -m venv .build\venv
REM   .build\venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller pytest
set "PY=python"
if exist ".build\venv\Scripts\python.exe" set "PY=.build\venv\Scripts\python.exe"

%PY% --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    pause
    exit /b 1
)

echo === Installing/updating build dependencies ===
%PY% -m pip install --quiet --upgrade -r requirements.txt pyinstaller pytest || goto :fail

echo === Running test suite (release gate) ===
set "PYTHONPATH=%~dp0"
%PY% -m pytest tests -q || goto :fail

echo === Building EXE with PyInstaller ===
%PY% -m PyInstaller packaging\StoryVoiceStudio.spec --noconfirm || goto :fail

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

