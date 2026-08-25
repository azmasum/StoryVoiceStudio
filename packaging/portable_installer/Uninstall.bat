@echo off
rem StoryVoice Studio - uninstaller
set /p CONFIRM=Remove StoryVoice Studio and its shortcuts? (Y/N): 
if /I not "%CONFIRM%"=="Y" goto :eof
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$t = Join-Path $env:LOCALAPPDATA 'StoryVoiceStudio';" ^
  "if (Test-Path $t) { Remove-Item $t -Recurse -Force };" ^
  "$d = [Environment]::GetFolderPath('Desktop');" ^
  "Remove-Item (Join-Path $d 'StoryVoice Studio.lnk') -Force -ErrorAction SilentlyContinue;" ^
  "$s = Join-Path ([Environment]::GetFolderPath('Programs')) 'StoryVoiceStudio';" ^
  "if (Test-Path $s) { Remove-Item $s -Recurse -Force };"
echo Uninstalled.
pause
