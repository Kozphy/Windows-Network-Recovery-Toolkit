#Requires -Version 5.1
<#
.SYNOPSIS
  Detect / preview / apply Prefer-IPv4 when IPv6 path is broken (YouTube stall class).
.EXAMPLE
  .\scripts\fix-network-path.ps1
  .\scripts\fix-network-path.ps1 -Apply
  .\scripts\fix-network-path.ps1 -Apply -OpenYoutube
#>
param(
    [switch]$Apply,
    [switch]$OpenYoutube,
    [switch]$Json,
    [string]$Interface = 'Wi-Fi'
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

Write-Host "=== WNRT network-path-health ===" -ForegroundColor Cyan
$argsList = @($Runner, 'network-path-health', '--interface', $Interface)
if ($Json) { $argsList += '--json' }

if ($Apply) {
    Write-Host "APPLY Prefer-IPv4 (may prompt UAC)..." -ForegroundColor Yellow
    # Elevate apply so HKLM + Disable-NetAdapterBinding succeed
    $elev = @"
`$env:PYTHONPATH = '$RepoRoot'
Set-Location '$RepoRoot'
& '$Python' '$Runner' network-path-health --interface '$Interface' --all-adapters --force --confirm PREFER_IPV4_OVER_IPV6 --dry-run false --json
exit `$LASTEXITCODE
"@
    $tmp = Join-Path $env:TEMP 'wnrt_nph_apply.ps1'
    Set-Content -Path $tmp -Value $elev -Encoding ASCII
    $p = Start-Process powershell.exe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',$tmp) -Verb RunAs -Wait -PassThru
    if ($null -eq $p -or $p.ExitCode -ne 0) {
        $code = if ($null -eq $p) { 'cancelled' } else { $p.ExitCode }
        Write-Host "Elevated apply exit=$code - falling back to non-elevated apply" -ForegroundColor Yellow
        & $Python $Runner network-path-health --interface $Interface --all-adapters --force --confirm PREFER_IPV4_OVER_IPV6 --dry-run false --json
    }
} else {
    & $Python @argsList
}

if ($OpenYoutube) {
    $fixYt = Join-Path $RepoRoot 'fix-youtube.cmd'
    if (Test-Path $fixYt) { & cmd /c $fixYt }
}

exit 0
