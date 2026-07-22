[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet('Assess','Repair','Verify')]
    [string]$Mode = 'Assess',

    [string]$OutputDirectory = (Join-Path $env:USERPROFILE 'Desktop\BSOD-Safe-Repair'),

    [switch]$EnableSmallMemoryDumps,

    [switch]$SkipDISM,

    [switch]$SkipSFC,

    [switch]$SkipDiskScan
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-LoggedCommand {
    param(
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [scriptblock]$Command
    )

    $started = Get-Date
    $record = [ordered]@{
        name = $Name
        started_at = $started.ToString('o')
        status = 'running'
        exit_code = $null
        output = @()
        error = $null
    }

    try {
        $result = & $Command 2>&1 | ForEach-Object { $_.ToString() }
        $record.output = @($result)
        $record.exit_code = $LASTEXITCODE
        if ($null -eq $record.exit_code) { $record.exit_code = 0 }
        $record.status = if ($record.exit_code -eq 0) { 'ok' } else { 'warning' }
    }
    catch {
        $record.status = 'error'
        $record.error = $_.Exception.Message
    }

    $record.ended_at = (Get-Date).ToString('o')
    return [pscustomobject]$record
}

if ($env:OS -ne 'Windows_NT') {
    throw 'This script requires Windows.'
}

if (-not (Test-IsAdministrator)) {
    throw 'Run PowerShell as Administrator.'
}

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$runDirectory = Join-Path $OutputDirectory $timestamp
New-Item -ItemType Directory -Path $runDirectory -Force | Out-Null

$results = [System.Collections.Generic.List[object]]::new()
$summary = [ordered]@{
    tool = 'Invoke-BsodSafeRepair'
    version = '1.0.0'
    mode = $Mode
    started_at = (Get-Date).ToString('o')
    computer = $env:COMPUTERNAME
    read_only_assessment = ($Mode -eq 'Assess')
    reboot_required = $false
    warnings = @()
}

$results.Add((Invoke-LoggedCommand -Name 'System information' -Command {
    Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber, BiosManufacturer, BiosSMBIOSBIOSVersion
}))

$results.Add((Invoke-LoggedCommand -Name 'Recent bug checks' -Command {
    Get-WinEvent -FilterHashtable @{ LogName = 'System'; Id = 1001; StartTime = (Get-Date).AddDays(-30) } -ErrorAction SilentlyContinue |
        Select-Object -First 20 TimeCreated, ProviderName, Id, LevelDisplayName, Message
}))

$results.Add((Invoke-LoggedCommand -Name 'Storage and WHEA events' -Command {
    Get-WinEvent -FilterHashtable @{ LogName = 'System'; StartTime = (Get-Date).AddDays(-14) } -ErrorAction SilentlyContinue |
        Where-Object { $_.ProviderName -match 'disk|stornvme|storahci|WHEA|Ntfs' -or $_.Id -in 7,11,15,17,18,19,20,51,55,129,153,157 } |
        Select-Object -First 100 TimeCreated, ProviderName, Id, LevelDisplayName, Message
}))

$results.Add((Invoke-LoggedCommand -Name 'Physical disk health' -Command {
    Get-PhysicalDisk -ErrorAction SilentlyContinue |
        Select-Object FriendlyName, MediaType, HealthStatus, OperationalStatus, Size
}))

$results.Add((Invoke-LoggedCommand -Name 'Signed storage and display drivers' -Command {
    Get-CimInstance Win32_PnPSignedDriver |
        Where-Object { $_.DeviceClass -in 'SCSIAdapter','HDC','Display' } |
        Select-Object DeviceName, DeviceClass, DriverProviderName, DriverVersion, DriverDate, InfName, IsSigned
}))

$dumpPaths = @(
    Join-Path $env:SystemRoot 'Minidump',
    Join-Path $env:SystemRoot 'MEMORY.DMP'
)
$results.Add((Invoke-LoggedCommand -Name 'Crash dump inventory' -Command {
    foreach ($path in $dumpPaths) {
        if (Test-Path $path) {
            Get-Item $path -Force | Select-Object FullName, Length, LastWriteTime
            if ((Get-Item $path).PSIsContainer) {
                Get-ChildItem $path -Filter '*.dmp' -Force | Select-Object FullName, Length, LastWriteTime
            }
        }
    }
}))

if ($EnableSmallMemoryDumps -and $Mode -ne 'Assess') {
    if ($PSCmdlet.ShouldProcess('Windows crash-control registry', 'Enable small memory dumps')) {
        New-Item -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\CrashControl' -Force | Out-Null
        Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\CrashControl' -Name CrashDumpEnabled -Type DWord -Value 3
        Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\CrashControl' -Name MinidumpDir -Type ExpandString -Value '%SystemRoot%\Minidump'
        $summary.warnings += 'Small memory dumps were enabled. This does not repair the root cause.'
    }
}

if ($Mode -eq 'Repair') {
    if (-not $SkipDISM) {
        $results.Add((Invoke-LoggedCommand -Name 'DISM component-store repair' -Command {
            DISM.exe /Online /Cleanup-Image /RestoreHealth
        }))
    }

    if (-not $SkipSFC) {
        $results.Add((Invoke-LoggedCommand -Name 'System File Checker repair' -Command {
            sfc.exe /scannow
        }))
    }

    if (-not $SkipDiskScan) {
        $results.Add((Invoke-LoggedCommand -Name 'Online system-volume scan' -Command {
            chkdsk.exe $env:SystemDrive /scan
        }))
    }

    $summary.warnings += 'The tool deliberately does not flash BIOS, replace firmware, uninstall drivers, or force driver updates.'
    $summary.warnings += 'If storage/WHEA errors or repeated 0x133 crashes remain, back up data and obtain vendor or technician diagnosis.'
}

if ($Mode -eq 'Verify') {
    $results.Add((Invoke-LoggedCommand -Name 'DISM health verification' -Command {
        DISM.exe /Online /Cleanup-Image /ScanHealth
    }))
    $results.Add((Invoke-LoggedCommand -Name 'Protected-file verification' -Command {
        sfc.exe /verifyonly
    }))
    $results.Add((Invoke-LoggedCommand -Name 'System-volume verification' -Command {
        chkdsk.exe $env:SystemDrive /scan
    }))
}

$summary.ended_at = (Get-Date).ToString('o')
$summary.results = $results

$jsonPath = Join-Path $runDirectory 'result.json'
$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $jsonPath -Encoding UTF8

$reportPath = Join-Path $runDirectory 'REPORT.md'
$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add('# BSOD Safe Repair Report')
$lines.Add('')
$lines.Add("- Mode: **$Mode**")
$lines.Add("- Computer: **$($summary.computer)**")
$lines.Add("- Started: **$($summary.started_at)**")
$lines.Add('')
$lines.Add('## Important')
$lines.Add('This workflow can repair Windows component-store and protected-file corruption, but it cannot guarantee a BSOD fix. Driver, SSD, RAM, firmware, overheating, or motherboard faults require separate diagnosis.')
$lines.Add('')
$lines.Add('## Steps')
foreach ($item in $results) {
    $lines.Add("### $($item.name)")
    $lines.Add("Status: **$($item.status)**; exit code: **$($item.exit_code)**")
    if ($item.error) { $lines.Add("Error: `$($item.error)`") }
    $lines.Add('```text')
    foreach ($line in @($item.output)) { $lines.Add($line) }
    $lines.Add('```')
    $lines.Add('')
}
if ($summary.warnings.Count -gt 0) {
    $lines.Add('## Warnings')
    foreach ($warning in $summary.warnings) { $lines.Add("- $warning") }
}
$lines | Set-Content -Path $reportPath -Encoding UTF8

Write-Host "Completed. Report: $reportPath"
Write-Host "JSON: $jsonPath"
