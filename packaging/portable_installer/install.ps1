# StoryVoice Studio - portable installer logic (Windows PowerShell 5.1+)
# Narration runs on the Google Gemini API: nothing to download except the
# app files themselves. Paste an API key in the app's Voice panel.
param(
    [string]$TargetDir = "",
    [switch]$Silent
)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$PayloadRoot = $PSScriptRoot
$ExeName     = "StoryVoiceStudio.exe"

function Read-Choice($message, $default) {
    $answer = Read-Host "$message [$default]"
    if ([string]::IsNullOrWhiteSpace($answer)) { return $default }
    return $answer.Trim()
}

if (-not $TargetDir) {
    if ($Silent) {
        $TargetDir = Join-Path $env:LOCALAPPDATA "StoryVoiceStudio"
    } else {
        Write-Host "=== StoryVoice Studio installer ===" -ForegroundColor Cyan
        $def = Join-Path $env:LOCALAPPDATA "StoryVoiceStudio"
        $inp = Read-Host "Install folder (Enter = $def)"
        if ([string]::IsNullOrWhiteSpace($inp)) { $TargetDir = $def } else { $TargetDir = $inp.Trim() }
    }
}

Write-Host "`nInstalling to: $TargetDir"
robocopy $PayloadRoot $TargetDir /E /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "Copy failed (robocopy exit $LASTEXITCODE)" }
Write-Host "Application files copied."

# --- Shortcuts -----------------------------------------------------------
$shell = New-Object -ComObject WScript.Shell
foreach ($base in @(
    [Environment]::GetFolderPath("Desktop"),
    (Join-Path ([Environment]::GetFolderPath("Programs")) "StoryVoiceStudio"))) {
    New-Item -ItemType Directory -Force -Path $base | Out-Null
    $lnk = $shell.CreateShortcut((Join-Path $base "StoryVoice Studio.lnk"))
    $lnk.TargetPath = Join-Path $TargetDir $ExeName
    $lnk.WorkingDirectory = $TargetDir
    $lnk.IconLocation = Join-Path $TargetDir $ExeName
    $lnk.Save()
}
Write-Host "Shortcuts created (Desktop + Start Menu)."

if (-not (Test-Path (Join-Path $TargetDir $ExeName))) {
    throw "Installation looks incomplete - $ExeName not found."
}

Write-Host ""
Write-Host "Done! Launch 'StoryVoice Studio' from the Desktop or Start Menu." -ForegroundColor Green
Write-Host "Then paste a Gemini API key (aistudio.google.com/apikey) into the Voice panel." -ForegroundColor Yellow
if (-not $Silent) { Read-Host "Press Enter to close" | Out-Null }