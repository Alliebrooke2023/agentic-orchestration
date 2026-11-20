# driftrack\start.ps1
# DriftRack launcher. Right-click > Run with PowerShell, or:  .\start.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue) }

function Show-Menu {
    Write-Host ""
    Write-Host "  DRIFTRACK - the night market for pre-loved style" -ForegroundColor Magenta
    Write-Host "  [1] Install check (Python 3.9+)"
    Write-Host "  [2] Run with demo data   (recommended first time)"
    Write-Host "  [3] Run empty            (your own listings only)"
    Write-Host "  [4] Run the tests"
    Write-Host "  [5] Quit"
}

while ($true) {
    Show-Menu
    $pick = Read-Host "  Choose 1-5"
    if ($pick -eq "5") { break }
    if (-not $py) {
        Write-Host "  Python was not found. Get it from https://www.python.org/downloads/ (tick 'Add to PATH')." -ForegroundColor Yellow
        continue
    }
    switch ($pick) {
        "1" { & $py.Source --version; Write-Host "  Nothing else to install - DriftRack uses only built-in Python." -ForegroundColor Green }
        "2" { Start-Process "http://127.0.0.1:8750"; & $py.Source app.py --seed }
        "3" { Start-Process "http://127.0.0.1:8750"; & $py.Source app.py }
        "4" { & $py.Source -m unittest discover -s tests }
        default { Write-Host "  Pick a number from 1 to 5." }
    }
}
