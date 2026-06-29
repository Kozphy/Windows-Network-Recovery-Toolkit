# Start FastAPI backend using the repo .venv (not a global/hermes uvicorn).
#
# Purpose:
#   Launch backend.main via project Python with PYTHONPATH and fixture-safe defaults.
#
# Privileges:
#   Standard user. Remediation routes still require API role headers + policy gates.
#
# Side effects:
#   Binds HTTP listener on ListenHost:Port. Sets PLATFORM_FIXTURE_MODE=1 when unset.
#   Does NOT mutate Windows registry or endpoint state.
#
# Recovery:
#   If port is in use, use start-api.ps1 (port conflict check) or -Port 8001.
#
# Usage (from repo root):
#   .\scripts\run-backend.ps1
#   .\scripts\run-backend.ps1 -Reload
#   .\.venv\Scripts\python.exe -m backend
param(
    [string]$ListenHost = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host ""
    Write-Host "ERROR: Project .venv not found." -ForegroundColor Red
    Write-Host "Run once from repo root:"
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\pip install -r requirements.txt"
    Write-Host ""
    Write-Host "Then start the API with:"
    Write-Host "  .\start-api.ps1"
    Write-Host "  .\.venv\Scripts\python.exe -m backend"
    Write-Host ""
    exit 1
}

$env:PYTHONPATH = $Root
if (-not $env:PLATFORM_FIXTURE_MODE) {
    $env:PLATFORM_FIXTURE_MODE = "1"
}
$env:WNRT_API_HOST = $ListenHost
$env:WNRT_API_PORT = "$Port"
if ($Reload) {
    $env:WNRT_API_RELOAD = "1"
} else {
    Remove-Item Env:WNRT_API_RELOAD -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Using Python: $Python" -ForegroundColor Cyan
Write-Host "Do NOT use bare 'uvicorn' — it may point to another venv (e.g. Hermes agent)." -ForegroundColor Yellow
Write-Host "PLATFORM_FIXTURE_MODE=$($env:PLATFORM_FIXTURE_MODE)"
Write-Host "OpenAPI: http://${ListenHost}:${Port}/docs"
Write-Host ""

& $Python -m backend
