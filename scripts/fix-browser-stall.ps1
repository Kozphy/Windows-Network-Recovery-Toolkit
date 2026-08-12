#Requires -Version 5.1
<#
.SYNOPSIS
  Preview / apply Edge/Chrome cold-start with QUIC disabled (IPv6 stall class).
.EXAMPLE
  .\scripts\fix-browser-stall.ps1
  .\scripts\fix-browser-stall.ps1 -Apply
#>
param(
    [switch]$Apply,
    [switch]$Json,
    [switch]$IncludeWebView,
    [string]$Url = 'https://www.youtube.com'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$Runner = Join-Path $PSScriptRoot 'run_src.py'
if (-not (Test-Path -LiteralPath $Python)) {
    $portable = Join-Path $RepoRoot '.tools\python312\python.exe'
    if (Test-Path -LiteralPath $portable) { $Python = $portable }
    else { $Python = (Get-Command python -ErrorAction Stop).Source }
}

Set-Location -LiteralPath $RepoRoot
$env:PYTHONPATH = $RepoRoot

Write-Host "=== WNRT fix-browser-stall ===" -ForegroundColor Cyan
$argsList = @($Runner, 'fix-browser-stall', '--url', $Url)
if ($Json) { $argsList += '--json' }
if ($IncludeWebView) { $argsList += '--include-webview' }
if ($Apply) {
    $argsList += @('--confirm', 'RESTART_BROWSER_DISABLE_QUIC', '--dry-run', 'false')
    Write-Host "APPLY: full Edge/Chrome quit + --disable-quic cold start" -ForegroundColor Yellow
} else {
    $argsList += @('--dry-run', 'true')
    Write-Host "PREVIEW (default). Re-run with -Apply to restart the browser." -ForegroundColor Cyan
}

& $Python @argsList
exit $LASTEXITCODE
