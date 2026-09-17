# StoryVoice Studio - portable installer logic (Windows PowerShell 5.1+)
param(
    [string]$TargetDir = "",
    [switch]$WithClone,
    [switch]$WithParler,
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
        if (-not $WithClone) {
            $ans = Read-Choice "Install optional Voice Clone pack (~350 MB download)? (Y/N)" "N"
            if ($ans -match '^[Yy]') { $WithClone = $true }
        }
        if (-not $WithParler) {
            $ans = Read-Choice "Install optional Parler transformer voices (~1.5 GB download)? (Y/N)" "N"
            if ($ans -match '^[Yy]') { $WithParler = $true }
        }
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

# --- Optional voice clone pack ------------------------------------------
if ($WithClone) {
    Write-Host "`n--- Voice Clone pack ---" -ForegroundColor Cyan
    $rt   = Join-Path $TargetDir "_runtime"
    $py   = Join-Path $rt "python\python.exe"
    $libs = Join-Path $TargetDir "clone_libs"

    if (-not (Test-Path $py)) {
        New-Item -ItemType Directory -Force -Path $rt | Out-Null
        $zipPath = Join-Path $rt "python-embed.zip"
        Write-Host "Downloading embedded Python 3.11..."
        Invoke-WebRequest "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" `
            -OutFile $zipPath -UseBasicParsing
        Expand-Archive $zipPath (Join-Path $rt "python") -Force
        Remove-Item $zipPath -Force
    }
    # Enable pip support inside the embeddable distribution.
    $pth = Join-Path $rt "python\python311._pth"
    (Get-Content $pth -Raw) -replace "#import site", "import site" |
        Set-Content $pth -NoNewline -Encoding ASCII
    Add-Content $pth "Lib\site-packages" -Encoding ASCII

    if (-not (Test-Path (Join-Path $rt "python\Lib\site-packages\pip"))) {
        Write-Host "Bootstrapping pip..."
        $gp = Join-Path $rt "get-pip.py"
        Invoke-WebRequest "https://bootstrap.pypa.io/get-pip.py" -OutFile $gp -UseBasicParsing
        & $py $gp --no-warn-script-location --quiet
        Remove-Item $gp -Force
    }

    Write-Host "Installing torch (CPU)... this is the big one, please wait."
    & $py -m pip install --no-warn-script-location --quiet `
        --target $libs --upgrade torch --index-url https://download.pytorch.org/whl/cpu
    if ($LASTEXITCODE) { throw "torch install failed" }

    Write-Host "Installing librosa..."
    & $py -m pip install --no-warn-script-location --quiet --target $libs --upgrade librosa
    if ($LASTEXITCODE) { throw "librosa install failed" }

    # Make the bundled runtime able to import the pack too (debugging aid;
    # the app itself wires clone_libs into sys.path on its own).
    Add-Content $pth "$libs" -Encoding ASCII

    $models = Join-Path $env:LOCALAPPDATA "StoryVoiceStudio\models\openvoice"
    New-Item -ItemType Directory -Force -Path $models | Out-Null
    foreach ($f in @("checkpoint.pth", "config.json")) {
        $dest = Join-Path $models $f
        if (Test-Path $dest) { Write-Host "exists: $f"; continue }
        Write-Host "Downloading $f..."
        Invoke-WebRequest "https://huggingface.co/myshell-ai/OpenVoiceV2/resolve/main/converter/$f" `
            -OutFile $dest -UseBasicParsing
    }
    Write-Host "Voice Clone pack installed." -ForegroundColor Green
}

# --- Optional Parler transformer voices ----------------------------------
if ($WithParler) {
    Write-Host "`n--- Parler transformer voices ---" -ForegroundColor Cyan
    $rt   = Join-Path $TargetDir "_runtime"
    $py   = Join-Path $rt "python\python.exe"
    $libs = Join-Path $TargetDir "clone_libs"

    if (-not (Test-Path $py)) {
        throw "Parler voices need the embedded Python from the Voice Clone pack - re-run with -WithClone first."
    }

    Write-Host "Installing torchaudio (CPU)..."
    & $py -m pip install --no-warn-script-location --quiet `
        --target $libs --upgrade torchaudio --index-url https://download.pytorch.org/whl/cpu
    if ($LASTEXITCODE) { throw "torchaudio install failed" }

    Write-Host "Installing transformer stack (transformers, parler-tts)... this is big, please wait."
    & $py -m pip install --no-warn-script-location --quiet --target $libs --upgrade `
        transformers tokenizers safetensors huggingface_hub sentencepiece parler-tts accelerate
    if ($LASTEXITCODE) { throw "transformer stack install failed" }

    Write-Host "Parler engine libraries installed." -ForegroundColor Green
    Write-Host "The voice model itself (~4 GB) downloads on demand from the Model Manager."
    Write-Host "It is access-gated: accept the license at huggingface.co/ai4bharat/indic-parler-tts"
    Write-Host "and paste a read-only token into the Model Manager."
}

Write-Host ""
Write-Host "Done! Launch 'StoryVoice Studio' from the Desktop or Start Menu." -ForegroundColor Green
if (-not $Silent) { Read-Host "Press Enter to close" | Out-Null }