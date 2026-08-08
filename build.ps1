# Build autoClicker.exe (run from project root)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = "$env:LocalAppData\Programs\Python\Python312\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

if (-not (Test-Path ".venv")) {
    & $Python -m venv .venv
}

$VenvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $VenvPython -m pip install -r requirements.txt
& $VenvPython -m PyInstaller --onefile --windowed --uac-admin --name autoClicker --clean main.py

Write-Host ""
Write-Host "Output: dist\autoClicker.exe"
