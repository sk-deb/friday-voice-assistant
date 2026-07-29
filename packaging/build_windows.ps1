<#
.SYNOPSIS
    Builds friday.exe and, when Inno Setup is available, the Windows installer.

.DESCRIPTION
    Run this on a Windows machine with Python 3.10 or newer. It creates an
    isolated build virtual environment, installs FRIDAY plus PyInstaller,
    freezes the app with packaging/friday.spec, and optionally compiles
    FridaySetup.exe.

    Everything lands in:
        dist/Friday/friday.exe          the app
        dist/installer/FridaySetup.exe  the installer (if Inno Setup is present)

.PARAMETER SkipInstaller
    Build only the exe and skip Inno Setup.

.PARAMETER Clean
    Delete build/ and dist/ before starting.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
#>

[CmdletBinding()]
param(
    [switch]$SkipInstaller,
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'

function Write-Step($message) {
    Write-Host ""
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Write-Note($message) {
    Write-Host "    $message" -ForegroundColor DarkGray
}

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
Write-Note "Repository: $Root"

# --------------------------------------------------------------- prerequisites
Write-Step 'Checking Python'
$python = $null
foreach ($candidate in @('py -3', 'python', 'python3')) {
    $parts = $candidate.Split(' ')
    $exe = $parts[0]
    if (Get-Command $exe -ErrorAction SilentlyContinue) {
        $python = $candidate
        break
    }
}
if (-not $python) {
    throw 'Python was not found. Install Python 3.10+ from python.org and tick "Add python.exe to PATH".'
}

$versionText = & ([scriptblock]::Create("$python --version")) 2>&1
Write-Note "Using $python ($versionText)"

$version = [regex]::Match($versionText, '(\d+)\.(\d+)')
if ($version.Success) {
    $major = [int]$version.Groups[1].Value
    $minor = [int]$version.Groups[2].Value
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
        throw "FRIDAY needs Python 3.10 or newer, found $versionText."
    }
}

if ($Clean) {
    Write-Step 'Cleaning previous build output'
    foreach ($dir in @('build', 'dist')) {
        if (Test-Path $dir) {
            Remove-Item $dir -Recurse -Force
            Write-Note "Removed $dir"
        }
    }
}

# ------------------------------------------------------------------ build venv
$venv = Join-Path $Root '.build-venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'

if (-not (Test-Path $venvPython)) {
    Write-Step 'Creating build environment (.build-venv)'
    & ([scriptblock]::Create("$python -m venv `"$venv`""))
} else {
    Write-Step 'Reusing build environment (.build-venv)'
}

Write-Step 'Installing dependencies (this takes a few minutes the first time)'
& $venvPython -m pip install --upgrade pip setuptools wheel --quiet
& $venvPython -m pip install -r requirements.txt --quiet
& $venvPython -m pip install pyinstaller --quiet

# webrtcvad has no prebuilt Windows wheel and needs a C++ compiler; the
# -wheels fork ships binaries, so prefer it and keep the build toolchain-free.
Write-Note 'Ensuring a Windows-compatible webrtcvad build'
& $venvPython -m pip install webrtcvad-wheels --quiet 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Note 'webrtcvad-wheels unavailable; keeping the source build.'
    $global:LASTEXITCODE = 0
}

Write-Step 'Running the test suite before packaging'
& $venvPython -m unittest discover -s tests -t .
if ($LASTEXITCODE -ne 0) {
    throw 'Tests failed. Fix them before shipping an installer.'
}

# ---------------------------------------------------------------------- freeze
Write-Step 'Freezing FRIDAY with PyInstaller'
& $venvPython -m PyInstaller 'packaging\friday.spec' --noconfirm --clean
if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller failed.'
}

$exePath = Join-Path $Root 'dist\Friday\friday.exe'
if (-not (Test-Path $exePath)) {
    throw "Expected $exePath but it was not produced."
}

$sizeMb = [math]::Round((Get-ChildItem 'dist\Friday' -Recurse | Measure-Object Length -Sum).Sum / 1MB, 1)
Write-Note "Built dist\Friday ($sizeMb MB)"

Write-Step 'Smoke testing the exe'
& $exePath --version
if ($LASTEXITCODE -ne 0) {
    Write-Warning 'The exe did not report its version cleanly. Check dist\Friday manually.'
}

# ------------------------------------------------------------------- installer
if ($SkipInstaller) {
    Write-Step 'Skipping the installer as requested'
} else {
    $iscc = $null
    foreach ($candidate in @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )) {
        if (Test-Path $candidate) { $iscc = $candidate; break }
    }
    if (-not $iscc -and (Get-Command iscc -ErrorAction SilentlyContinue)) {
        $iscc = 'iscc'
    }

    if ($iscc) {
        Write-Step 'Building the installer with Inno Setup'
        & $iscc 'packaging\friday_installer.iss'
        if ($LASTEXITCODE -ne 0) { throw 'Inno Setup failed.' }
        Write-Note 'Built dist\installer\FridaySetup.exe'
    } else {
        Write-Step 'Inno Setup not found - skipping the installer'
        Write-Note 'Install it with:  winget install JRSoftware.InnoSetup'
        Write-Note 'The app in dist\Friday works without it; run friday.exe directly.'
    }
}

Write-Host ""
Write-Host 'Done.' -ForegroundColor Green
Write-Host "  App:       dist\Friday\friday.exe"
if (Test-Path 'dist\installer\FridaySetup.exe') {
    Write-Host "  Installer: dist\installer\FridaySetup.exe"
}
Write-Host ""
Write-Host 'Before first run, put your Gemini key in:' -ForegroundColor Yellow
Write-Host "  $env:APPDATA\Friday\.env    ->  GEMINI_API_KEY=your_key_here"
