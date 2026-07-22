[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path $env:USERPROFILE 'Desktop\BSOD-Triage'),
    [int]$Days = 14,
    [switch]$IncludeDumpCopies
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Add-Finding {
    param(
        [System.Collections.Generic.List[object]]$List,
        [string]$Severity,
        [string]$Category,
        [string]$Title,
        [string]$Evidence,
        [string]$Recommendation
    )
    $List.Add([pscustomobject]@{
        severity = $Severity
        category = $Category
        title = $Title
        evidence = $Evidence
        recommendation = $Recommendation
    })
}

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$caseDir = Join-Path $OutputDirectory "case-$timestamp"
New-Item -ItemType Directory -Path $caseDir -Force | Out-Null
$startTime = (Get-Date).AddDays(-1 * [math]::Abs($Days))
$findings = [System.Collections.Generic.List[object]]::new()
$limitations = [System.Collections.Generic.List[string]]::new()

Write-Host 'Collecting read-only Windows crash evidence...' -ForegroundColor Cyan

$computer = Get-CimInstance Win32_ComputerSystem
$os = Get-CimInstance Win32_OperatingSystem
$bios = Get-CimInstance Win32_BIOS
$system = [pscustomobject]@{
    collected_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    computer_name = $env:COMPUTERNAME
    manufacturer = $computer.Manufacturer
    model = $computer.Model
    os_caption = $os.Caption
    os_version = $os.Version
    os_build = $os.BuildNumber
    last_boot = $os.LastBootUpTime
    bios_version = ($bios.SMBIOSBIOSVersion -join ', ')
    bios_date = $bios.ReleaseDate
}
$system | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $caseDir 'system.json') -Encoding UTF8

$bugchecks = @()
try {
    $bugchecks = @(Get-WinEvent -FilterHashtable @{ LogName='System'; Id=1001; StartTime=$startTime } | ForEach-Object {
        $code = $null
        if ($_.Message -match '(?i)bugcheck(?: was)?:\s*(0x[0-9a-f]+)') { $code = $matches[1].ToUpperInvariant() }
        [pscustomobject]@{ time_created=$_.TimeCreated; provider=$_.ProviderName; bugcheck=$code; message=$_.Message }
    })
} catch { $limitations.Add("Could not read BugCheck events: $($_.Exception.Message)") }
$bugchecks | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $caseDir 'bugchecks.json') -Encoding UTF8

try {
    Get-WinEvent -FilterHashtable @{ LogName='System'; Id=41,6008; StartTime=$startTime } |
        Select-Object TimeCreated,Id,ProviderName,LevelDisplayName,Message |
        Export-Csv (Join-Path $caseDir 'unexpected-shutdowns.csv') -NoTypeInformation -Encoding UTF8
} catch { $limitations.Add("Could not read shutdown events: $($_.Exception.Message)") }

$dumpCandidates = @()
$miniDir = Join-Path $env:SystemRoot 'Minidump'
$memoryDump = Join-Path $env:SystemRoot 'MEMORY.DMP'
if (Test-Path $miniDir) { $dumpCandidates += Get-ChildItem $miniDir -Filter '*.dmp' -File -ErrorAction SilentlyContinue }
if (Test-Path $memoryDump) { $dumpCandidates += Get-Item $memoryDump }
$dumps = @($dumpCandidates | Sort-Object LastWriteTime -Descending)
$dumps | Select-Object FullName,Length,CreationTime,LastWriteTime |
    Export-Csv (Join-Path $caseDir 'dump-inventory.csv') -NoTypeInformation -Encoding UTF8

if ($IncludeDumpCopies -and $dumps.Count -gt 0) {
    $dumpDir = Join-Path $caseDir 'dumps'
    New-Item -ItemType Directory -Path $dumpDir -Force | Out-Null
    foreach ($dump in $dumps) {
        try { Copy-Item $dump.FullName $dumpDir -Force }
        catch { $limitations.Add("Could not copy $($dump.FullName): $($_.Exception.Message)") }
    }
}

$drivers = @(Get-CimInstance Win32_PnPSignedDriver -ErrorAction SilentlyContinue | Where-Object { $_.DeviceName -and $_.DriverVersion } | ForEach-Object {
    $driverDate = $null
    try { $driverDate = [Management.ManagementDateTimeConverter]::ToDateTime($_.DriverDate) } catch {}
    [pscustomobject]@{
        device_name=$_.DeviceName; device_class=$_.DeviceClass; manufacturer=$_.Manufacturer
        provider=$_.DriverProviderName; driver_date=$driverDate; version=$_.DriverVersion
        inf_name=$_.InfName; signer=$_.Signer
    }
})
$drivers | Sort-Object device_class,device_name |
    Export-Csv (Join-Path $caseDir 'drivers.csv') -NoTypeInformation -Encoding UTF8

$priorityClasses = @('DISPLAY','HDC','SCSIADAPTER','NET','MEDIA','SYSTEM')
$staleCutoff = (Get-Date).AddYears(-3)
$oldPriorityDrivers = @($drivers | Where-Object {
    ($priorityClasses -contains ([string]$_.device_class).ToUpperInvariant()) -and $_.driver_date -and $_.driver_date -lt $staleCutoff
})
if ($oldPriorityDrivers.Count -gt 0) {
    $evidence = $oldPriorityDrivers | Select-Object -First 12 device_name,device_class,provider,driver_date,version | ConvertTo-Json -Compress
    Add-Finding -List $findings -Severity 'medium' -Category 'driver' -Title 'Old latency-sensitive drivers detected' -Evidence $evidence -Recommendation 'Update only from MSI/OEM or the device vendor. Create a restore point first; avoid generic driver-updater utilities.'
}

try {
    $disks = @(Get-PhysicalDisk | Select-Object FriendlyName,Manufacturer,Model,MediaType,BusType,HealthStatus,OperationalStatus,FirmwareVersion,Size)
    $disks | Export-Csv (Join-Path $caseDir 'physical-disks.csv') -NoTypeInformation -Encoding UTF8
    $unhealthy = @($disks | Where-Object { $_.HealthStatus -and $_.HealthStatus -ne 'Healthy' })
    if ($unhealthy.Count -gt 0) {
        Add-Finding -List $findings -Severity 'high' -Category 'storage' -Title 'Storage health is not Healthy' -Evidence ($unhealthy | ConvertTo-Json -Compress) -Recommendation 'Back up important data immediately and run the MSI/OEM storage diagnostic.'
    }
} catch { $limitations.Add("Get-PhysicalDisk unavailable: $($_.Exception.Message)") }

$events = @()
try {
    $events = @(Get-WinEvent -FilterHashtable @{ LogName='System'; StartTime=$startTime; Level=1,2,3 } | Where-Object {
        $_.ProviderName -match 'disk|stor|nvme|iaStor|stornvme|Display|WHEA|Kernel-PnP|Netwtw|nvlddmkm|amdkmdag'
    } | Select-Object -First 500 TimeCreated,Id,ProviderName,LevelDisplayName,Message)
    $events | Export-Csv (Join-Path $caseDir 'relevant-system-events.csv') -NoTypeInformation -Encoding UTF8
} catch { $limitations.Add("Could not collect relevant events: $($_.Exception.Message)") }

$whea = @($events | Where-Object { $_.ProviderName -match 'WHEA' })
if ($whea.Count -gt 0) {
    Add-Finding -List $findings -Severity 'high' -Category 'hardware' -Title 'WHEA hardware-error events detected' -Evidence ($whea | Select-Object -First 8 | ConvertTo-Json -Compress) -Recommendation 'Run MSI/OEM memory and storage diagnostics; disable overclocking or undervolting during diagnosis.'
}
$storageErrors = @($events | Where-Object { $_.ProviderName -match 'disk|stor|nvme|iaStor' })
if ($storageErrors.Count -gt 0) {
    Add-Finding -List $findings -Severity 'high' -Category 'storage' -Title 'Storage-related errors detected' -Evidence ($storageErrors | Select-Object -First 10 | ConvertTo-Json -Compress) -Recommendation 'Check SSD firmware, chipset/storage-controller driver, and disk health. Back up data first.'
}
$displayErrors = @($events | Where-Object { $_.ProviderName -match 'Display|nvlddmkm|amdkmdag' })
if ($displayErrors.Count -gt 0) {
    Add-Finding -List $findings -Severity 'medium' -Category 'graphics' -Title 'Display-driver errors detected' -Evidence ($displayErrors | Select-Object -First 10 | ConvertTo-Json -Compress) -Recommendation 'Use the MSI/OEM graphics driver first; consider rollback if crashes began immediately after an update.'
}

Get-HotFix -ErrorAction SilentlyContinue | Sort-Object InstalledOn -Descending | Select-Object -First 30 HotFixID,Description,InstalledOn,InstalledBy |
    Export-Csv (Join-Path $caseDir 'recent-hotfixes.csv') -NoTypeInformation -Encoding UTF8

$has133 = @($bugchecks | Where-Object { $_.bugcheck -eq '0X133' }).Count -gt 0
if ($has133) {
    Add-Finding -List $findings -Severity 'high' -Category 'bugcheck' -Title 'DPC_WATCHDOG_VIOLATION (0x133) confirmed' -Evidence 'Windows recorded bugcheck 0x133.' -Recommendation 'Prioritize dump analysis and storage/NVMe, chipset, GPU, network, audio, and USB drivers. This identifies a cause class, not an exact guilty driver.'
}
if ($dumps.Count -eq 0) {
    Add-Finding -List $findings -Severity 'medium' -Category 'evidence' -Title 'No crash dump found' -Evidence 'Neither Minidump nor MEMORY.DMP was accessible.' -Recommendation 'Enable Small memory dump in Startup and Recovery, then rerun after the next crash.'
    $limitations.Add('Without a crash dump, exact ISR/DPC attribution is usually not reliable.')
} else {
    $dumpEvidence = $dumps | Select-Object -First 5 FullName,LastWriteTime,Length | ConvertTo-Json -Compress
    Add-Finding -List $findings -Severity 'info' -Category 'evidence' -Title 'Crash dump evidence is available' -Evidence $dumpEvidence -Recommendation 'Open the newest dump in WinDbg and run !analyze -v, lm t n, and !dpcs. Treat a named module as a lead requiring corroboration.'
}

$report = [pscustomobject]@{
    schema_version='1.0'; case_id="case-$timestamp"; scope='Read-only Windows BSOD and DPC watchdog triage'
    system=$system; bugcheck_count=$bugchecks.Count; dump_count=$dumps.Count
    findings=$findings; limitations=$limitations
    non_claims=@(
        'This tool does not prove that a named driver or device caused the crash.'
        'It does not modify drivers, firmware, BIOS, registry, services, or dump settings.'
        'A kernel dump plus WinDbg analysis is normally required for confident root-cause attribution.'
    )
}
$report | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $caseDir 'triage-report.json') -Encoding UTF8

$md = [System.Collections.Generic.List[string]]::new()
$md.Add('# Windows BSOD Triage Report')
$md.Add('')
$md.Add("- Case: **$($report.case_id)**")
$md.Add("- Computer: **$($system.manufacturer) $($system.model)**")
$md.Add("- Windows: **$($system.os_caption) build $($system.os_build)**")
$md.Add("- Bugcheck events: **$($report.bugcheck_count)**")
$md.Add("- Dump files: **$($report.dump_count)**")
$md.Add('')
$md.Add('## Findings')
foreach ($finding in $findings) {
    $md.Add('')
    $md.Add("### [$($finding.severity.ToUpperInvariant())] $($finding.title)")
    $md.Add("- Category: $($finding.category)")
    $md.Add("- Evidence: $($finding.evidence)")
    $md.Add("- Recommended next step: $($finding.recommendation)")
}
$md.Add('')
$md.Add('## Limitations')
foreach ($item in $limitations) { $md.Add("- $item") }
$md.Add('- Heuristic correlation is not proof of causation.')
$md.Add('- Exact DPC/ISR attribution usually requires a memory dump and WinDbg symbols.')
$md | Set-Content (Join-Path $caseDir 'triage-report.md') -Encoding UTF8

$zipPath = "$caseDir.zip"
Compress-Archive -Path (Join-Path $caseDir '*') -DestinationPath $zipPath -Force
Write-Host "`nTriage complete." -ForegroundColor Green
Write-Host "Report: $caseDir\triage-report.md"
Write-Host "Archive: $zipPath"
Write-Host 'No drivers, firmware, BIOS, registry settings, or services were changed.' -ForegroundColor Yellow
