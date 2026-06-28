#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot automatic fix for ChatGPT blank messages / connectivity (no prompts).
.DESCRIPTION
  Chains proxy auto-fix, read-only diagnosis, and policy-gated LOW-risk remediations.
  See docs/chatgpt-auto-fix.md for limits (does not fix session/cache/server-side issues).

  Steps:
    1. auto-fix-proxy.ps1 — Cursor no-proxy + dead proxy guardian
    2. bad-gateway-diagnose --url (default https://chatgpt.com) — read-only HTTP probe
    3. python -m src diagnose --app chatgpt --json — scenario hypotheses + audit snapshot
    4. auto-fix-chatgpt CLI — LOW-risk apply with confirmation APPLY_CHATGPT_LOW_RISK

  Inputs:
    -SkipProxyAutoFix     Skip step 1
    -SkipGuardianInstall  Forwarded to auto-fix-proxy.ps1
    -DryRun               Pass --dry-run true to step 4 (no mutations)
    -Url                  HTTPS URL for bad-gateway step (default https://chatgpt.com)

  Outputs:
    JSON from each step on stdout; exit 0 when probes healthy or dry-run; else exit 1

  Privileges:
    No admin for most steps. flush_dns via CLI uses ipconfig /flushdns (user scope).

  Side effects (live run, step 4):
    - Same as auto-fix-proxy.ps1 for step 1
    - ipconfig /flushdns, netsh winhttp reset proxy, ChatGPT.exe restart when evidence-gated
    - reports/last_network_recovery_diagnosis.json, logs/network_recovery_events.jsonl

  Safety boundaries:
    MEDIUM/BLOCK actions (firewall reset, disable firewall) are never auto-executed.
    Does not claim malware or prove registry writer identity.

  Idempotency:
    Diagnosis steps are read-only. LOW-risk commands are safe to repeat (WinHTTP reset is idempotent).

  Recovery:
    If messages still blank: Incognito, sign out/in, clear chatgpt.com site data.
    MEDIUM tier requires manual review via python -m src preview --scenario chatgpt_app_firewall

  Example:
    .\scripts\auto-fix-chatgpt.ps1
    .\scripts\auto-fix-chatgpt.ps1 -DryRun
    .\scripts\auto-fix-chatgpt.ps1 -SkipProxyAutoFix -Url https://chatgpt.com
.NOTES
  Audit: logs/network_recovery_events.jsonl and proxy-disable.jsonl after live apply.
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
