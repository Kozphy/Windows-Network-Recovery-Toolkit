param(
    [string]$ServiceName = "WNRTContinuousAgent",
    [string]$PythonExe = "python",
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")),
    [string]$ConfigPath = (Join-Path $PSScriptRoot "config.example.json")
)

$ErrorActionPreference = "Stop"

$agentPath = Join-Path $PSScriptRoot "agent.py"
if (-not (Test-Path $agentPath)) { throw "Agent not found: $agentPath" }
if (-not (Test-Path $ConfigPath)) { throw "Config not found: $ConfigPath" }

$pythonResolved = (Get-Command $PythonExe -ErrorAction Stop).Source
$binaryPath = '"{0}" "{1}" --config "{2}"' -f $pythonResolved, $agentPath, $ConfigPath

if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    throw "Service $ServiceName already exists. Remove it before reinstalling."
}

New-Service `
    -Name $ServiceName `
    -BinaryPathName $binaryPath `
    -DisplayName "WNRT Continuous Read-Only Agent" `
    -Description "Continuously collects bounded diagnostics and writes audit evidence without automatic remediation." `
    -StartupType Automatic

Write-Host "Created $ServiceName."
Write-Host "Before starting, grant the service account write access only to the configured artifacts directory."
Write-Host "Start with: Start-Service -Name $ServiceName"
Write-Host "Remove with: sc.exe delete $ServiceName"

# Production note:
# Plain Python is not itself a native Windows Service host. For production, wrap this
# entrypoint with WinSW/NSSM or implement pywin32 ServiceFramework. This installer is
# retained as an explicit deployment reference and should be validated in a test VM.
