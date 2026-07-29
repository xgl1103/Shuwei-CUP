$ErrorActionPreference = "Stop"

# AI-assisted disclosure (non-core): convenience launcher for the local dashboard server.
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (-not (Test-Path $Python)) {
  $Python = "python"
}

Set-Location $ProjectRoot
Write-Host "Serving B question dashboard at http://127.0.0.1:5178/dashboard/index.html"
& $Python .\dashboard_server.py
