@echo off
setlocal
REM StoryVoice Studio - development launcher (no venv required)
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH. Install Python 3.10+ from python.org
    pause
    exit /b 1
)

if not exist ".pylibs" mkdir ".pylibs"

echo Checking dependencies...
python -c "import numpy, scipy, soundfile, pyloudnorm, piper" >nul 2>nul
if errorlevel 1 (
    echo Installing requirements into .pylibs ...
    python -m pip install --target .pylibs --upgrade -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed. See messages above.
        pause
        exit /b 1
    )
)

set "PYTHONPATH=%~dp0;%~dp0.pylibs"
echo Launching StoryVoice Studio...
python -m app.main %*
if errorlevel 1 pause
endlocal
