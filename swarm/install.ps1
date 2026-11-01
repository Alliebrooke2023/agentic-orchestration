# C:\swarm\install.ps1  (setup.bat runs this for you)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
              [Environment]::GetEnvironmentVariable("Path", "User")
}
function Test-Python {
  # the Microsoft Store "python" stub exists but cannot run code
  try { & python -c "import sys; assert sys.version_info >= (3, 8)" 2>$null; return $LASTEXITCODE -eq 0 }
  catch { return $false }
}
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  winget install -e --id Ollama.Ollama --accept-source-agreements --accept-package-agreements
  Refresh-Path
  $env:Path += ";$env:LOCALAPPDATA\Programs\Ollama"
}
if (-not (Test-Python)) {
  winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
  Refresh-Path
  if (-not (Test-Python)) { Write-Host "Python installed. Close this window, reopen, rerun option 1."; exit 1 }
}
if (-not (Get-Process ollama -ErrorAction SilentlyContinue)) {
  Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
  Start-Sleep 4
}
ollama pull qwen2.5:1.5b-instruct-q4_K_M
ollama pull llama3.2:1b
Get-Service | Where-Object { $_.Name -match "sunshine" } | Format-Table Name, Status
python -m unittest discover tests
Write-Host "Done. Run:  python -m swarm"
