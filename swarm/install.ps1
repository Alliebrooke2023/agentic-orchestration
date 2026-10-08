# C:\swarm\install.ps1  -- run in PowerShell:  powershell -ExecutionPolicy Bypass -File .\install.ps1
$ErrorActionPreference = "Stop"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  winget install -e --id Ollama.Ollama --accept-source-agreements --accept-package-agreements
  $env:Path += ";$env:LOCALAPPDATA\Programs\Ollama"
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
}
Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue
Start-Sleep 4
ollama pull qwen2.5:1.5b-instruct-q4_K_M
ollama pull llama3.2:1b
Get-Service | Where-Object { $_.Name -match "sunshine" } | Format-Table Name, Status
python -m unittest tests.test_swarm
Write-Host "Done. Run:  python -m swarm"
