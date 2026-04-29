param(
    [int]$IntervalSeconds = 5
)

# Windows Network Recovery Toolkit
# Read-only root cause monitoring script for state changes over time.

if ($IntervalSeconds -lt 5) { $IntervalSeconds = 5 }
if ($IntervalSeconds -gt 10) { $IntervalSeconds = 10 }

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$logDir = Join-Path $repoRoot "logs"
$logFile = Join-Path $logDir "network_monitor.log"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$previous = $null

function Get-UserProxyState {
    $path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    $item = Get-ItemProperty -Path $path -ErrorAction SilentlyContinue

    [PSCustomObject]@{
        ProxyEnable   = if ($null -ne $item.ProxyEnable) { [int]$item.ProxyEnable } else { 0 }
        ProxyServer   = if ($null -ne $item.ProxyServer) { [string]$item.ProxyServer } else { "" }
        AutoConfigURL = if ($null -ne $item.AutoConfigURL) { [string]$item.AutoConfigURL } else { "" }
        AutoDetect    = if ($null -ne $item.AutoDetect) { [int]$item.AutoDetect } else { 0 }
    }
}

function Get-MonitorState {
    $winHttpProxyRaw = (netsh winhttp show proxy | Out-String).Trim()
    $userProxy = Get-UserProxyState
    $tcpTest = Test-NetConnection google.com -Port 443 -WarningAction SilentlyContinue
    $tcp443 = [bool]$tcpTest.TcpTestSucceeded

    $curlExit = 1
    $curlOutput = ""
    try {
        $curlOutput = (& curl.exe -I --max-time 5 https://www.google.com 2>&1 | Out-String).Trim()
        $curlExit = $LASTEXITCODE
    } catch {
        $curlOutput = $_.Exception.Message
        $curlExit = 1
    }
    $curlSuccess = ($curlExit -eq 0)

    $recentProcesses = Get-Process |
        Sort-Object StartTime |
        Select-Object -Last 5 Name, Id, StartTime

    [PSCustomObject]@{
        Timestamp       = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        WinHttpProxyRaw = $winHttpProxyRaw
        UserProxy       = $userProxy
        Tcp443          = $tcp443
        CurlSuccess     = $curlSuccess
        CurlExitCode    = $curlExit
        CurlOutput      = $curlOutput
        RecentProcesses = $recentProcesses
    }
}

function Detect-Changes {
    param(
        $Prev,
        $Curr
    )

    if ($null -eq $Prev) { return @() }

    $changes = @()
    if ($Prev.UserProxy.ProxyEnable -ne $Curr.UserProxy.ProxyEnable) {
        $changes += "ProxyEnable changed: $($Prev.UserProxy.ProxyEnable) -> $($Curr.UserProxy.ProxyEnable)"
    }

    if ([string]::IsNullOrWhiteSpace($Prev.UserProxy.ProxyServer) -and -not [string]::IsNullOrWhiteSpace($Curr.UserProxy.ProxyServer)) {
        $changes += "ProxyServer appeared: $($Curr.UserProxy.ProxyServer)"
    }

    if ($Prev.UserProxy.AutoDetect -eq 0 -and $Curr.UserProxy.AutoDetect -eq 1) {
        $changes += "AutoDetect flipped: 0 -> 1"
    }

    if ($Prev.Tcp443 -eq $true -and $Curr.Tcp443 -eq $false) {
        $changes += "TCP 443 changed: True -> False"
    }

    if ($Prev.CurlSuccess -eq $true -and $Curr.CurlSuccess -eq $false) {
        $changes += "curl HTTPS changed: Success -> Timeout/Failure"
    }

    return $changes
}

function Write-LogBlock {
    param(
        $State,
        [string[]]$Changes
    )

    Add-Content -Path $logFile -Value "===== $($State.Timestamp) ====="
    Add-Content -Path $logFile -Value "[WinHTTP Proxy]"
    Add-Content -Path $logFile -Value $State.WinHttpProxyRaw
    Add-Content -Path $logFile -Value ""
    Add-Content -Path $logFile -Value "[User Proxy]"
    Add-Content -Path $logFile -Value ("ProxyEnable: {0}" -f $State.UserProxy.ProxyEnable)
    Add-Content -Path $logFile -Value ("ProxyServer: {0}" -f $State.UserProxy.ProxyServer)
    Add-Content -Path $logFile -Value ("AutoConfigURL: {0}" -f $State.UserProxy.AutoConfigURL)
    Add-Content -Path $logFile -Value ("AutoDetect: {0}" -f $State.UserProxy.AutoDetect)
    Add-Content -Path $logFile -Value ""
    Add-Content -Path $logFile -Value "[TCP 443]"
    Add-Content -Path $logFile -Value ("TcpTestSucceeded: {0}" -f $State.Tcp443)
    Add-Content -Path $logFile -Value ""
    Add-Content -Path $logFile -Value "[HTTPS Test]"
    Add-Content -Path $logFile -Value ("curl success: {0}" -f $State.CurlSuccess)
    Add-Content -Path $logFile -Value ("curl exit code: {0}" -f $State.CurlExitCode)
    Add-Content -Path $logFile -Value ("curl output: {0}" -f $State.CurlOutput)
    Add-Content -Path $logFile -Value ""
    Add-Content -Path $logFile -Value "[Recent Processes]"
    foreach ($p in $State.RecentProcesses) {
        Add-Content -Path $logFile -Value ("{0} (PID {1}) started {2}" -f $p.Name, $p.Id, $p.StartTime)
    }
    if ($Changes.Count -gt 0) {
        Add-Content -Path $logFile -Value "!!! CHANGE DETECTED !!!"
        foreach ($c in $Changes) {
            Add-Content -Path $logFile -Value ("- " + $c)
        }
    }
    Add-Content -Path $logFile -Value ""
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Root Cause Monitoring Mode" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Interval: $IntervalSeconds seconds"
Write-Host "Log file: $logFile"
Write-Host "Press Ctrl+C to stop."
Write-Host ""

while ($true) {
    $state = Get-MonitorState
    $changes = Detect-Changes -Prev $previous -Curr $state
    Write-LogBlock -State $state -Changes $changes

    Write-Host "--------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "Timestamp: $($state.Timestamp)"
    Write-Host "Summary:"
    Write-Host ("- TCP 443: {0}" -f $state.Tcp443)
    Write-Host ("- curl HTTPS: {0}" -f $state.CurlSuccess)
    Write-Host ("- ProxyEnable: {0}" -f $state.UserProxy.ProxyEnable)
    Write-Host ("- ProxyServer: {0}" -f $(if ([string]::IsNullOrWhiteSpace($state.UserProxy.ProxyServer)) { "<empty>" } else { $state.UserProxy.ProxyServer }))
    Write-Host ("- AutoDetect: {0}" -f $state.UserProxy.AutoDetect)

    if ($changes.Count -gt 0) {
        Write-Host "!!! CHANGE DETECTED !!!" -ForegroundColor Yellow
        foreach ($c in $changes) {
            Write-Host ("- " + $c) -ForegroundColor Yellow
        }
    } else {
        Write-Host "No state change detected in this cycle." -ForegroundColor Green
    }

    Write-Host "[Recent Processes]"
    foreach ($p in $state.RecentProcesses) {
        Write-Host ("- {0} (PID {1}) started {2}" -f $p.Name, $p.Id, $p.StartTime)
    }

    $previous = $state
    Start-Sleep -Seconds $IntervalSeconds
}
