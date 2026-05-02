#Requires -Version 5.1
<#
.SYNOPSIS
  Runs diagnose_proxy.bat, optionally invokes reset_proxy_safe.ps1 interactively, then launches Cursor.exe.
.DESCRIPTION
  Diagnose emits reports\proxy_guard_report.txt (read-only). Optional reset modifies HKCU / WinHTTP / Git /
  npm proxies only inside reset_proxy_safe.ps1 after typed YES—not firewall adapters.
.NOTES
  SAFETY — Diagnose-only path has no HKCU mutations. Guided reset inherits reset_proxy_safe.ps1 risks.
  PRIVILEGES — Executes as invoking user standard token.
  SIDE EFFECTS — May launch Cursor.exe with user approval; inherits reset logging to reports/proxy_guard_actions.jsonl when reset runs.
.AUDIT
  Correlate reports\proxy_guard_report.txt timestamps with Cursor launch troubleshooting steps.
#>
$ErrorActionPreference = 'SilentlyContinue'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host '=== Proxy Guard — start_cursor_safe ===' -ForegroundColor Cyan
Write-Host 'Running diagnose_proxy.bat ...' -ForegroundColor DarkGray
$diagBat = Join-Path $ScriptDir 'diagnose_proxy.bat'
& cmd.exe /c "`"$diagBat`""

try {
    $p = Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction Stop
    $susp = ($p.ProxyEnable -eq 1) -and ($p.ProxyServer -match '(?i)127\.|localhost')
} catch { $susp = $false }

if ($susp) {
    Write-Warning 'HKCU shows an enabled proxy that may point to loopback (common with stale dev proxies).'
    $r = Read-Host 'Start interactive reset_proxy_safe.ps1 in this window? (Y/N — you will type YES inside that script to confirm)'
    if ($r.Trim().Equals('Y', [System.StringComparison]::OrdinalIgnoreCase)) {
        & (Join-Path $ScriptDir 'reset_proxy_safe.ps1')
    } else {
        Write-Host 'Skipping reset. Run reset_proxy_safe.bat manually if needed.' -ForegroundColor DarkYellow
    }
}

$paths = @(
    (Join-Path $env:LOCALAPPDATA 'Programs\Cursor\Cursor.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\cursor\Cursor.exe'),
    (Join-Path $env:ProgramFiles 'Cursor\Cursor.exe')
)
$exe = $null
foreach ($c in $paths) {
    if (Test-Path -LiteralPath $c) { $exe = $c; break }
}
if (-not $exe) {
    Write-Host ''
    Write-Host 'Cursor.exe not found. Install Cursor or add it to PATH, then re-run.' -ForegroundColor Yellow
    Write-Host 'Common locations checked:' -ForegroundColor DarkGray
    $paths | ForEach-Object { Write-Host "  - $_" }
    exit 1
}
Write-Host "Launching: $exe" -ForegroundColor Green
Start-Process -FilePath $exe
exit 0
