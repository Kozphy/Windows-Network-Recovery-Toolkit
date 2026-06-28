#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot automatic fix for ChatGPT blank messages / connectivity (no prompts).
.DESCRIPTION
  1. Runs scripts/auto-fix-proxy.ps1 (Cursor no-proxy + dead proxy guardian)
  2. bad-gateway-diagnose against https://chatgpt.com
  3. Legacy scenario diagnose: python -m src diagnose --app chatgpt --json
  4. Applies allowlisted LOW-risk remediations with typed confirmation gate
     (same posture as proxy-disable / proxy-guardian)

  LOW-risk actions (evidence-gated): flush DNS, reset WinHTTP proxy, restart ChatGPT app.
  MEDIUM/BLOCK tier actions are never auto-executed.

.NOTES
  No admin required for most steps. Restart browser after completion.
#>
param(
    [switch]$SkipProxyAutoFix,
    [switch]$SkipGuardianInstall,
    [switch]$DryRun,
    [string]$Url = "https://chatgpt.com"
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}

Set-Location -LiteralPath $RepoRoot
$env:PYTHONPATH = $RepoRoot

Write-Host "=== Auto-fix ChatGPT connectivity ===" -ForegroundColor Cyan

if (-not $SkipProxyAutoFix) {
    Write-Host ""
    Write-Host "[1/4] Dead proxy auto-fix (Cursor + guardian)..." -ForegroundColor Cyan
    $proxyArgs = @()
    if ($SkipGuardianInstall) {
        $proxyArgs += '-SkipGuardianInstall'
    }
    & (Join-Path $PSScriptRoot 'auto-fix-proxy.ps1') @proxyArgs
    if ($LASTEXITCODE -gt 1) {
        Write-Host "WARN: proxy auto-fix returned exit $LASTEXITCODE — continuing diagnosis." -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "[1/4] Skipped proxy auto-fix (--SkipProxyAutoFix)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2/4] Bad-gateway diagnose ($Url)..." -ForegroundColor Cyan
$bgJson = & $Python -m windows_network_toolkit bad-gateway-diagnose --url $Url --json-only 2>&1 | Out-String
Write-Host $bgJson

Write-Host ""
Write-Host "[3/4] ChatGPT scenario diagnose (legacy src)..." -ForegroundColor Cyan
$diagJson = & $Python -m src diagnose --app chatgpt --json 2>&1 | Out-String
Write-Host $diagJson

Write-Host ""
Write-Host "[4/4] LOW-risk remediations (policy-gated)..." -ForegroundColor Cyan
$fixArgs = @(
    '-m', 'windows_network_toolkit', 'auto-fix-chatgpt',
    '--url', $Url,
    '--skip-proxy-auto-fix'
)
if ($SkipGuardianInstall) {
    $fixArgs += '--skip-guardian-install'
}
if ($DryRun) {
    $fixArgs += '--dry-run', 'true'
}

$fixJson = & $Python @fixArgs 2>&1 | Out-String
Write-Host $fixJson

if ($fixJson -match '"chatgpt_https_ok":\s*true') {
    Write-Host "OK: ChatGPT HTTPS probe succeeded. Restart browser or ChatGPT app and retest." -ForegroundColor Green
    exit 0
}
if ($fixJson -match '"outcome":\s*"healthy"') {
    Write-Host "OK: Path looks healthy. Restart browser and retest messages." -ForegroundColor Green
    exit 0
}
if ($DryRun) {
    Write-Host "Dry-run complete — no mutations applied." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Review JSON above. If messages are still blank:" -ForegroundColor Yellow
Write-Host "  - Try a private/incognito window or sign out/in at chatgpt.com"
Write-Host "  - Clear site data for chatgpt.com"
Write-Host "  - MEDIUM actions (firewall reset) require manual review — not auto-applied"
exit 1
