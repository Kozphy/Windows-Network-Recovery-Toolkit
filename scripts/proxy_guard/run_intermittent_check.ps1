#Requires -Version 5.1
# SAFETY — Read-only watch and investigation; no registry or proxy mutations.
# PRIVILEGES — Executes as invoking user token.
# OUTPUT — Populates logs/proxy_guard.jsonl during watch; prints triage to console.
<#
.SYNOPSIS
  End-to-end intermittent proxy drift check: baseline, timed watch, report, investigate, attribution.
.PARAMETER WatchMinutes
  Duration for background watch (default 15). Ignored when -ForegroundWatch is set.
.PARAMETER IntervalSeconds
  Poll interval passed to ``python -m src proxy-watch`` (default 5).
.PARAMETER ReportTail
  Number of rows for ``proxy-watch-report`` (default 20).
.PARAMETER InvestigateSince
  Look-back window for ``proxy-investigate`` (default 30m).
.PARAMETER ForegroundWatch
  Run proxy-watch in the foreground until you press Ctrl+C, then continue triage.
.PARAMETER TriageOnly
  Skip the watch phase; run report, investigate, owner, and final status only.
.NOTES
  Requires Windows. Sets PYTHONPATH to the repository root.
  Example: .\scripts\proxy_guard\run_intermittent_check.ps1 -WatchMinutes 10
  Example: make proxy-intermittent WATCH_MINUTES=10
#>
param(
    [int]$WatchMinutes = 15,
    [double]$IntervalSeconds = 5,
    [int]$ReportTail = 20,
    [string]$InvestigateSince = '30m',
    [switch]$ForegroundWatch,
    [switch]$TriageOnly
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir '..\..')).Path
$env:PYTHONPATH = $RepoRoot

$script:LastStepExitCode = 0

function Write-StepHeader {
    param([string]$Message)
    Write-Host ""
    Write-Host "=== $Message ===" -ForegroundColor Cyan
}

function Invoke-ToolkitStep {
    param(
        [string]$Label,
        [string[]]$PythonArgs
    )
    Write-StepHeader $Label
    & python @PythonArgs
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        Write-Host "Step exited with code $code" -ForegroundColor Yellow
        if ($script:LastStepExitCode -eq 0) {
            $script:LastStepExitCode = $code
        }
    }
    return $code
}

if ($env:OS -notmatch 'Windows') {
    Write-Error 'run_intermittent_check.ps1 requires Windows.'
    exit 2
}

Set-Location -LiteralPath $RepoRoot
Write-Host "Repository: $RepoRoot" -ForegroundColor DarkGray
Write-Host "Read-only intermittent proxy check (no mutations)." -ForegroundColor DarkGray

Invoke-ToolkitStep '1/7 Baseline proxy-status' @(
    '-m', 'windows_network_toolkit', 'proxy-status'
) | Out-Null

if (-not $TriageOnly) {
    if ($ForegroundWatch) {
        Write-StepHeader "2/7 Foreground watch (Ctrl+C when finished reproducing the issue)"
        Write-Host "Logging to logs\proxy_guard.jsonl" -ForegroundColor DarkGray
        try {
            & python -m src proxy-watch --interval $IntervalSeconds
        } catch {
            if ($_.Exception -isnot [System.Management.Automation.PipelineStoppedException]) {
                throw
            }
        }
    } else {
        Write-StepHeader "2/7 Watch ${WatchMinutes}m (interval ${IntervalSeconds}s)"
        Write-Host "Reproduce the issue now (browse Edge/LinkedIn). Logging to logs\proxy_guard.jsonl" -ForegroundColor DarkGray
        $watchProc = Start-Process -FilePath python `
            -ArgumentList @('-m', 'src', 'proxy-watch', '--interval', "$IntervalSeconds") `
            -WorkingDirectory $RepoRoot `
            -PassThru `
            -WindowStyle Hidden
        try {
            Start-Sleep -Seconds ($WatchMinutes * 60)
        } finally {
            if ($null -ne $watchProc -and -not $watchProc.HasExited) {
                Stop-Process -Id $watchProc.Id -Force -ErrorAction SilentlyContinue
            }
        }
        if ($null -ne $watchProc) {
            $watchProc.WaitForExit(5000) | Out-Null
        }
    }
} else {
    Write-StepHeader '2/7 Watch skipped (-TriageOnly)'
}

Invoke-ToolkitStep "3/7 proxy-watch-report (tail $ReportTail)" @(
    '-m', 'src', 'proxy-watch-report', '--tail', "$ReportTail"
) | Out-Null

Invoke-ToolkitStep "4/7 proxy-investigate (since $InvestigateSince)" @(
    '-m', 'src', 'proxy-investigate', '--since', $InvestigateSince
) | Out-Null

Invoke-ToolkitStep '5/7 proxy-owner' @(
    '-m', 'windows_network_toolkit', 'proxy-owner'
) | Out-Null

Invoke-ToolkitStep '6/7 proxy-writer-attribution' @(
    '-m', 'windows_network_toolkit', 'proxy-writer-attribution'
) | Out-Null

Invoke-ToolkitStep '7/7 Final proxy-status' @(
    '-m', 'windows_network_toolkit', 'proxy-status'
) | Out-Null

Write-Host ""
if ($script:LastStepExitCode -eq 0) {
    Write-Host 'Intermittent proxy check complete.' -ForegroundColor Green
} else {
    Write-Host "Intermittent proxy check finished with exit code $($script:LastStepExitCode)." -ForegroundColor Yellow
}

exit $script:LastStepExitCode
