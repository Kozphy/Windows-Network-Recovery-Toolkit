#Requires -Version 5.1
<#
.SYNOPSIS
  Detect / preview / contain suspicious localhost WinINET rewriter persistence.
.DESCRIPTION
  Operator path for Session-0 scheduled-task + remote iex + system32 payload patterns
  (e.g. VersionUpdaterV12-*) that correlate with recurring localhost proxy rewrites.

  Default is preview (dry-run). Live apply requires -Apply (embeds confirm token).

  Does NOT claim malware attribution or registry-writer proof.
  Keeps KILL_PROXY_PROCESS blocked in the Python policy engine — this is a distinct
  operator-gated composite containment.

.EXAMPLE
  .\scripts\contain-localhost-rewriter.ps1
  .\scripts\contain-localhost-rewriter.ps1 -Apply
  .\scripts\contain-localhost-rewriter.ps1 -Apply -Json
#>
param(
    [switch]$Apply,
    [switch]$Json,
    [switch]$SkipGuardianReminder
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$Runner = Join-Path $PSScriptRoot 'run_src.py'
if (-not (Test-Path -LiteralPath $Python)) {
    $portable = Join-Path $RepoRoot '.tools\python312\python.exe'
    if (Test-Path -LiteralPath $portable) {
        $Python = $portable
    } else {
        $Python = (Get-Command python -ErrorAction Stop).Source
    }
}

Set-Location -LiteralPath $RepoRoot
$env:PYTHONPATH = $RepoRoot

Write-Host "=== WNRT contain-localhost-rewriter ===" -ForegroundColor Cyan

$argsList = @($Runner, 'contain-localhost-rewriter')
if ($Json) { $argsList += '--json' }
if ($Apply) {
    $argsList += @('--confirm', 'CONTAIN_LOCALHOST_REWRITER', '--dry-run', 'false')
    Write-Host "APPLY mode: task delete / process stop / exclusion remove / quarantine" -ForegroundColor Yellow
} else {
    $argsList += @('--dry-run', 'true')
    Write-Host "PREVIEW mode (default). Re-run with -Apply to contain." -ForegroundColor Cyan
}

& $Python @argsList
$code = $LASTEXITCODE

if (-not $SkipGuardianReminder) {
    Write-Host ""
    Write-Host "Keep hold-direct until rewrite stops:" -ForegroundColor Cyan
    Write-Host "  .\enable-proxy-autofix.cmd"
    Write-Host "  Get-Content .\reports\proxy_guardian_heartbeat.json"
    Write-Host "  Get-Content .\logs\proxy_guardian.jsonl -Tail 20"
}

exit $code
