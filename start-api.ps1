# Start API — always uses repo .venv (avoids Hermes/global uvicorn on PATH).
# From repo root:
#   .\start-api.ps1
param(
    [string]$ListenHost = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Reload
)

& (Join-Path $PSScriptRoot "scripts\run-backend.ps1") -ListenHost $ListenHost -Port $Port -Reload:$Reload
