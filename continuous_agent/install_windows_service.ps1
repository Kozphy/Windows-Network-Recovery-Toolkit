param(
    [string]$TaskName = "WNRTContinuousAgent",
    [string]$PythonExe = "python",
    [string]$ConfigPath = (Join-Path $PSScriptRoot "config.example.json")
)

$ErrorActionPreference = "Stop"

$repositoryRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$agentPath = Join-Path $PSScriptRoot "agent.py"
if (-not (Test-Path $agentPath)) { throw "Agent not found: $agentPath" }
if (-not (Test-Path $ConfigPath)) { throw "Config not found: $ConfigPath" }

$pythonResolved = (Get-Command $PythonExe -ErrorAction Stop).Source
$arguments = '"{0}" --config "{1}"' -f $agentPath, $ConfigPath

$action = New-ScheduledTaskAction `
    -Execute $pythonResolved `
    -Argument $arguments `
    -WorkingDirectory $repositoryRoot

$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Run the WNRT continuous read-only monitoring agent at startup." `
    -Force | Out-Null

Write-Host "Installed startup task: $TaskName"
Write-Host "Start now: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Inspect: Get-ScheduledTaskInfo -TaskName '$TaskName'"
Write-Host "Remove: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
Write-Host "Review config and grant write access only to the configured artifacts directory before starting."
