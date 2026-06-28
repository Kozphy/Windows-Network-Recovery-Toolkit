# Start API — always uses repo .venv and fails fast if port is occupied.
# From repo root:
#   .\start-api.ps1
param(
    [string]$ListenHost = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Reload
)

$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

if ($existing) {
    Write-Host "ERROR: Port $Port is already in use." -ForegroundColor Red
    Write-Host ""
    Write-Host "Current listener(s):"

    foreach ($conn in $existing) {
        $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue

        [PSCustomObject]@{
            LocalAddress  = $conn.LocalAddress
            LocalPort     = $conn.LocalPort
            OwningProcess = $conn.OwningProcess
            ProcessName   = if ($proc) { $proc.ProcessName } else { "<unknown>" }
            Path          = if ($proc) { $proc.Path } else { "<unknown>" }
        }
    }

    Write-Host ""
    Write-Host "Use a different port, for example:" -ForegroundColor Yellow
    Write-Host "  .\start-api.ps1 -Port 8001"
    exit 1
}

& (Join-Path $PSScriptRoot "scripts\run-backend.ps1") -ListenHost $ListenHost -Port $Port -Reload:$Reload