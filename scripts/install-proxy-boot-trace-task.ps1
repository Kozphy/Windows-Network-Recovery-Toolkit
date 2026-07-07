#Requires -Version 5.1
<#
.SYNOPSIS
  Preview or install an automatic post-logon proxy boot trace task.
.DESCRIPTION
  Runs the repo-native boot-trace installer. On apply it prefers a per-user
  Scheduled Task, but if Task Scheduler is blocked it falls back automatically
  to a Startup hook. The trace is read-only and records observations into
  logs\proxy_boot_trace.jsonl for startup-time proxy drift analysis.
#>
param(
    [int]$DurationSeconds = 180,
    [int]$IntervalSeconds = 2,
    [switch]$Uninstall,
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}

Set-Location -LiteralPath $RepoRoot
$env:PYTHONPATH = $RepoRoot

if ($Uninstall) {
    if ($Apply) {
        & $Python -m src uninstall-boot-trace-task `
            --confirm UNINSTALL_BOOT_TRACE_TASK `
            --dry-run false
    } else {
        & $Python -m src uninstall-boot-trace-task
    }
    exit $LASTEXITCODE
}

if ($Apply) {
    & $Python -m src install-boot-trace-task `
        --duration $DurationSeconds `
        --interval $IntervalSeconds `
        --confirm INSTALL_BOOT_TRACE_TASK `
        --dry-run false
} else {
    & $Python -m src install-boot-trace-task `
        --duration $DurationSeconds `
        --interval $IntervalSeconds
}
exit $LASTEXITCODE
