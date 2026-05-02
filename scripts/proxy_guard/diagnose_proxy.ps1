#Requires -Version 5.1
<#
.SYNOPSIS
  Read-only snapshot of WinINET (HKCU), WinHTTP, Git, npm, and user proxy environment.
.NOTES
  Writes reports/proxy_guard_report.txt under repo root. Does not modify settings.
  Masks IPv4-like sequences and loopback names in the narrative summary (not raw netsh blocks).
#>

$ErrorActionPreference = 'SilentlyContinue'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir '..\..')).Path
$ReportDir = Join-Path $RepoRoot 'reports'
if (-not (Test-Path $ReportDir)) { New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null }
$OutFile = Join-Path $ReportDir 'proxy_guard_report.txt'

function Mask-Plain([string]$s) {
    if ([string]::IsNullOrWhiteSpace($s)) { return '[empty]' }
    $t = $s -replace '(?:(?:25[0-5]|2[0-4][0-9]|1?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|1?[0-9][0-9]?)', '[IP]'
    $t = $t -replace '(?i)\blocalhost\b', '[LOOPBACK]'
    return $t
}

$hkcu = $null
$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine('============================================================')
[void]$sb.AppendLine('Proxy Guard — Diagnose Report (read-only)')
[void]$sb.AppendLine("Generated (UTC): $(([datetime]::UtcNow.ToString('o')))")
[void]$sb.AppendLine("Repository root: $RepoRoot")
[void]$sb.AppendLine('============================================================')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('No settings were modified by this report.')
[void]$sb.AppendLine('Masked summary avoids storing verbatim RFC1918 endpoints in narrative lines.')
[void]$sb.AppendLine('')

# HKCU WinINET
[void]$sb.AppendLine('---------- HKCU WinINET (Internet Settings) ----------')
try {
    $hkcu = Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction Stop
    $pe = $hkcu.ProxyEnable
    [void]$sb.AppendLine("ProxyEnable (DWORD): $pe")
    if ($hkcu.ProxyServer) {
        [void]$sb.AppendLine(('ProxyServer (masked): ' + (Mask-Plain $hkcu.ProxyServer)))
    } else {
        [void]$sb.AppendLine('ProxyServer: [not set]')
    }
} catch {
    [void]$sb.AppendLine('Could not read HKCU Internet Settings.')
}

[void]$sb.AppendLine('')
[void]$sb.AppendLine('---------- WinHTTP (netsh) ----------')
$nw = netsh winhttp show proxy 2>&1 | Out-String
[void]$sb.AppendLine($nw.TrimEnd())

[void]$sb.AppendLine('')
[void]$sb.AppendLine('---------- Git global ----------')
$gitExe = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitExe) {
    [void]$sb.AppendLine('Git not found on PATH.')
} else {
    foreach ($k in @('http.proxy', 'https.proxy')) {
        $v = git config --global --get $k 2>$null
        if ($v) { [void]$sb.AppendLine("$k (masked): $(Mask-Plain $v)") } else { [void]$sb.AppendLine("${k}: [not set]") }
    }
}

[void]$sb.AppendLine('')
[void]$sb.AppendLine('---------- npm (optional) ----------')
$npmExe = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmExe) {
    [void]$sb.AppendLine('npm not found on PATH.')
} else {
    foreach ($k in @('proxy', 'https-proxy')) {
        $raw = npm config get $k 2>$null
        if ($raw -and $raw -notmatch '^(null|undefined)$') {
            [void]$sb.AppendLine("npm $k (masked): $(Mask-Plain $raw)")
        } else {
            [void]$sb.AppendLine("npm ${k}: [not set]")
        }
    }
}

[void]$sb.AppendLine('')
[void]$sb.AppendLine('---------- User environment (proxy-related keys only) ----------')
foreach ($name in @('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY', 'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')) {
    $v = [Environment]::GetEnvironmentVariable($name, 'User')
    if ($v) {
        [void]$sb.AppendLine("${name} (User, masked): $(Mask-Plain $v)")
    }
}

[void]$sb.AppendLine('')
[void]$sb.AppendLine('---------- Masked narrative summary ----------')
$npmProxyVal = $null
if ($npmExe) { $npmProxyVal = npm config get proxy 2>$null }
$issues = @()
if ($hkcu -and ($hkcu.ProxyEnable -eq 1) -and $hkcu.ProxyServer) { $issues += 'HKCU proxy enabled with ProxyServer set' }
if ($gitExe -and (git config --global --get http.proxy 2>$null)) { $issues += 'Git global http.proxy set' }
if ($npmExe -and $npmProxyVal -and ($npmProxyVal -notmatch '^(null|undefined)$')) { $issues += 'npm proxy may be set' }

if ($issues.Count -eq 0) {
    [void]$sb.AppendLine('No obvious proxy misconfiguration flags in scanned layers (manual review still recommended).')
} else {
    foreach ($i in $issues) { [void]$sb.AppendLine("- $i") }
}

[void]$sb.AppendLine('')
[void]$sb.AppendLine('End of report.')

Set-Content -LiteralPath $OutFile -Value $sb.ToString() -Encoding utf8
Write-Host "Report written: $OutFile"
