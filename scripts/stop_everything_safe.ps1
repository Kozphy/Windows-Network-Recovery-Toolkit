[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LogsDir = Join-Path $RepoRoot "logs"

function Stop-ManagedDevProcess {
    param([string]$Name)
    $pidPath = Join-Path $LogsDir "one_click_$Name.pid"
    if (-not (Test-Path $pidPath)) {
        Write-Host "[WNRT] No PID file for $Name"
        return
    }

    $pidText = (Get-Content -Path $pidPath -ErrorAction SilentlyContinue | Select-Object -First 1)
    $processId = 0
    if (-not [int]::TryParse([string]$pidText, [ref]$processId)) {
        Write-Host "[WNRT][WARN] Invalid PID file for $Name`: $pidText" -ForegroundColor Yellow
        return
    }

    $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($proc) {
        & taskkill.exe /PID $processId /T /F 1>$null 2>$null
        Write-Host "[WNRT] Stopped $Name PID $processId"
    }
    else {
        Write-Host "[WNRT] $Name PID $processId is not running"
    }
}

Stop-ManagedDevProcess -Name "backend"
Stop-ManagedDevProcess -Name "frontend"
Write-Host "[WNRT] Stop routine finished. This only targets launcher-managed dev server PID files."
