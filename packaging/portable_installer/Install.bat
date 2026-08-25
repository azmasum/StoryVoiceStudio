@echo off
rem StoryVoice Studio - one-click installer entry point
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
