#Requires -Version 5.1
<#
.SYNOPSIS
  Install auto-clear for dead localhost WinINET proxy drift (no admin required).
.DESCRIPTION
  Registers a per-user Startup hook running scripts/run-proxy-guardian-loop.ps1.
  Guardian invokes proxy-guardian --once on an interval; only remediates DEAD_PROXY_CONFIG.

  Inputs:
    -IntervalMinutes   Loop sleep in minutes (default 5; auto-fix-proxy uses 1)
    -UseScheduledTask  Also try Task Scheduler (may fail on locked-down PCs)
    -StartNow          Launch background loop immediately (default true)
    -Uninstall         Remove hook, tasks, and background loop

  Outputs:
    Install/uninstall status on stdout

  Privileges:
    Startup folder write (user). Task Scheduler may require elevation when -UseScheduledTask.

  Side effects:
    - Creates Startup\WNRT-DeadProxyGuardian.cmd
    - Hidden powershell loop calling proxy-guardian
    - HKCU WinINET mutation only when guardian detects dead proxy (no listener)

  Safety boundaries:
    Never disables proxy while localhost listener is bound. Does not touch WinHTTP by default.

  Idempotency:
    Re-install overwrites the same Startup hook. -Uninstall is reversible.

  Recovery:
    .\scripts\install-dead-proxy-guardian.ps1 -Uninstall
    Manual: delete Startup hook and stop powershell processes running run-proxy-guardian-loop.ps1

  Example:
    .\scripts\install-dead-proxy-guardian.ps1
    .\scripts\install-dead-proxy-guardian.ps1 -IntervalMinutes 1
    .\scripts\install-dead-proxy-guardian.ps1 -UseScheduledTask
.NOTES
  Audit: guardian apply rows in .audit/proxy-disable.jsonl when remediation runs.
#>
param(
    [int]$IntervalMinutes = 5,
    [switch]$UseScheduledTask,
    [bool]$StartNow = $true,
    [switch]$Uninstall
)

$TaskName = 'WNRT-DeadProxyGuardian'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}

$StartupHook = Join-Path ([Environment]::GetFolderPath('Startup')) 'WNRT-DeadProxyGuardian.cmd'
$LoopScript = Join-Path $RepoRoot 'scripts\run-proxy-guardian-loop.ps1'

function Stop-GuardianLoop {
    Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like '*run-proxy-guardian-loop.ps1*' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

function Remove-GuardianScheduledTasks {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    $null = & schtasks.exe /Delete /TN $TaskName /F 2>&1
    $null = & schtasks.exe /Delete /TN "$TaskName-Repeat" /F 2>&1
}

function Install-StartupHook {
    if (-not (Test-Path -LiteralPath $LoopScript)) {
        throw "Missing loop script: $LoopScript"
    }
    @(
        '@echo off',
        "cd /d `"$RepoRoot`"",
        "start /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$LoopScript`""
    ) | Set-Content -LiteralPath $StartupHook -Encoding ASCII
}

function Install-ScheduledTasks {
    param([string]$TaskCommand)

    $null = & schtasks.exe /Create /TN $TaskName /TR $TaskCommand /SC ONLOGON /RL LIMITED /F 2>&1
    if ($LASTEXITCODE -ne 0) {
        return $false
    }
    $null = & schtasks.exe /Create /TN "$TaskName-Repeat" /TR $TaskCommand /SC MINUTE /MO $IntervalMinutes /RL LIMITED /F 2>&1
    return ($LASTEXITCODE -eq 0)
}

function Install-ScheduledTasksCmdlet {
    $action = New-ScheduledTaskAction `
        -Execute $Python `
        -Argument "-m windows_network_toolkit proxy-guardian --once" `
        -WorkingDirectory $RepoRoot
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    $triggers = @(
        (New-ScheduledTaskTrigger -AtLogOn),
        (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
            -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
            -RepetitionDuration (New-TimeSpan -Days 3650))
    )
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers `
        -Principal $principal -Settings $settings -Force -ErrorAction Stop | Out-Null
    return $true
}

if ($Uninstall) {
    Remove-GuardianScheduledTasks
    if (Test-Path -LiteralPath $StartupHook) {
        Remove-Item -LiteralPath $StartupHook -Force
    }
    Stop-GuardianLoop
    Write-Host "Removed guardian: $TaskName (scheduled tasks, startup hook, background loop)" -ForegroundColor Green
    exit 0
}

$taskCmd = "`"$Python`" -m windows_network_toolkit proxy-guardian --once"
$scheduledOk = $false

Install-StartupHook

if ($UseScheduledTask) {
    try {
        $scheduledOk = Install-ScheduledTasks -TaskCommand $taskCmd
    } catch {
        $scheduledOk = $false
    }
    if (-not $scheduledOk) {
        try {
            $scheduledOk = Install-ScheduledTasksCmdlet
        } catch {
            $scheduledOk = $false
        }
    }
}

if ($StartNow) {
    Stop-GuardianLoop
    Start-Process powershell.exe -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden',
        '-File', $LoopScript
    ) -WindowStyle Hidden
}

Write-Host "Installed guardian: $TaskName" -ForegroundColor Green
Write-Host "  Python:       $Python"
Write-Host "  Repo:         $RepoRoot"
Write-Host "  Startup hook: $StartupHook"
Write-Host "  Interval:     every $IntervalMinutes minute(s) via background loop"
if ($UseScheduledTask) {
    if ($scheduledOk) {
        Write-Host "  Task Scheduler: registered" -ForegroundColor Green
    } else {
        Write-Host "  Task Scheduler: skipped (access denied or policy block; startup hook is active)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Task Scheduler: not requested (use -UseScheduledTask to try)" -ForegroundColor DarkGray
}
Write-Host ""
Write-Host "Test now:" -ForegroundColor Cyan
Write-Host "  & `"$Python`" -m windows_network_toolkit proxy-guardian --once"
Write-Host ""
Write-Host "Uninstall:" -ForegroundColor DarkGray
Write-Host "  .\scripts\install-dead-proxy-guardian.ps1 -Uninstall"
