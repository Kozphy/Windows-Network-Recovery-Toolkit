# Stop stale FastAPI / uvicorn servers for this repo (ports 8000-8010).
# Usage (from repo root):
#   .\scripts\stop-backend.ps1
param(
    [int[]]$Ports = @(8000, 8001, 8002, 8003)
)

$ErrorActionPreference = "SilentlyContinue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

$stopped = @()
foreach ($port in $Ports) {
    $lines = netstat -ano | Select-String ":$port\s" | Select-String "LISTENING"
    foreach ($line in $lines) {
        $parts = ($line -split "\s+") | Where-Object { $_ -ne "" }
        $procId = [int]$parts[-1]
        if ($procId -le 0) { continue }
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$procId"
        if (-not $proc) { continue }
        $cmd = if ($proc.CommandLine) { $proc.CommandLine } else { "" }
        $isBackend =
            $cmd -match "backend\.main" -or
            $cmd -match "-m backend" -or
            ($cmd -match "uvicorn" -and $cmd -match [regex]::Escape($Root))
        if (-not $isBackend) {
            Write-Host "Skip PID $procId on port $port (not this repo's backend)"
            continue
        }
        Write-Host "Stopping PID $procId on port $port"
        Stop-Process -Id $procId -Force
        $stopped += $procId
    }
}

if ($stopped.Count -eq 0) {
    Write-Host "No backend listeners found on ports $($Ports -join ', ')."
} else {
    Write-Host "Stopped $($stopped.Count) process(es). Start fresh with: .\start-api.ps1"
}
