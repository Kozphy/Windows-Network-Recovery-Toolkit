[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path $env:USERPROFILE "Desktop\BSOD-Triage"),
    [int]$Days = 14,
    [switch]$IncludeDumpCopies
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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
        severity       = $Severity
        category       = $Category
        title          = $Title
        evidence       = $Evidence
        recommendation = $Recommendation
    })
}

function Convert-BugcheckCode {
    param([object]$Value)
    if ($null -eq $Value) { return $null }
    $text = [string]$Value
    if ($text -match '^0x') { return $text.ToUpperInvariant() }
    try { return ('0x{0:X}' -f [uint64]$Value) } catch { return $text }
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$caseDir = Join-Path $OutputDirectory "case-$timestamp"
New-Item -ItemType Directory -Path $caseDir -Force | Out-Null

$findings = [System.Collections.Generic.List[object]]::new()
$limitations = [System.Collections.Generic.List[string]]::new()
$startTime = (Get-Date).AddDays(-1 * [math]::Abs($Days))

Write-Host "Collecting read-only Windows crash evidence..." -ForegroundColor Cyan

# System and firmware
$computer = Get-CimInstance Win32_ComputerSystem
$os = Get-CimInstance Win32_OperatingSystem
$bios = Get-CimInstance Win32_BIOS
$baseboard = Get-CimInstance Win32_BaseBoard
$system = [pscustomobject]@{
    collected_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    computer_name    = $env:COMPUTERNAME
    manufacturer     = $computer.Manufacturer
    model            = $computer.Model
    os_caption       = $os.Caption
    os_version       = $os.Version
    os_build         = $os.BuildNumber
    last_boot        = $os.LastBootUpTime
    bios_version     = ($bios.SMBIOSBIOSVersion -join ', ')
    bios_date        = $bios.ReleaseDate
    baseboard        = "$($baseboard.Manufacturer) $($baseboard.Product)"
}
$system | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $caseDir 'system.json') -Encoding UTF8

# Bugcheck events (Event ID 1001) and unexpected shutdowns (41/6008)
$bugchecks = @()
try {
    $bugchecks = Get-WinEvent -FilterHashtable @{LogName='System'; Id=1001; StartTime=$startTime} -ErrorAction Stop |
        ForEach-Object {
            $code = $null
            if ($_.Message -match '(?i)bugcheck(?: was)?:\s*(0x[0-9a-f]+)') { $code = $matches[1].ToUpperInvariant() }
            [pscustomobject]@{
                time_created = $_.TimeCreated
                event_id     = $_.Id
                provider     = $_.ProviderName
                bugcheck     = $code
                message      = $_.Message
            }
        }
} catch {
    $limitations.Add("Could not read BugCheck events: $($_.Exception.Message)")
}
$bugchecks | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $caseDir 'bugchecks.json') -Encoding UTF8

$shutdownEvents = @()
try {
    $shutdownEvents = Get-WinEvent -FilterHashtable @{LogName='System'; Id=41,6008; StartTime=$startTime} -ErrorAction Stop |
        Select-Object TimeCreated, Id, ProviderName, LevelDisplayName, Message
} catch {
    $limitations.Add("Could not read shutdown events: $($_.Exception.Message)")
}
$shutdownEvents | Export-Csv (Join-Path $caseDir 'unexpected-shutdowns.csv') -NoTypeInformation -Encoding UTF8

# Dump inventory
$dumpPaths = @(
    Join-Path $env:SystemRoot 'Minidump',
    Join-Path $env:SystemRoot 'MEMORY.DMP'
)
$dumps = foreach ($path in $dumpPaths) {
    if (Test-Path $path -PathType Container) {
        Get-ChildItem $path -Filter '*.dmp' -File -ErrorAction SilentlyContinue
    } elseif (Test-Path $path -PathType Leaf) {
        Get-Item $path
    }
}
$dumps = @($dumps | Sort-Object LastWriteTime -Descending)
$dumps | Select-Object FullName, Length, CreationTime, LastWriteTime |
    Export-Csv (Join-Path $caseDir 'dump-inventory.csv') -NoTypeInformation -Encoding UTF8

if ($IncludeDumpCopies -and $dumps.Count -gt 0) {
    $dumpDir = Join-Path $caseDir 'dumps'
    New-Item -ItemType Directory -Path $dumpDir -Force | Out-Null
    foreach ($dump in $dumps) {
        try { Copy-Item $dump.FullName $dumpDir -Force }
        catch { $limitations.Add("Could not copy dump $($dump.FullName): $($_.Exception.Message)") }
    }
}

# Driver inventory with age and likely DPC-related classes
$drivers = Get-CimInstance Win32_PnPSignedDriver -ErrorAction SilentlyContinue |
    Where-Object { $_.DeviceName -and $_.DriverVersion } |
    ForEach-Object {
        $date = $null
        try { $date = [Management.ManagementDateTimeConverter]::ToDateTime($_.DriverDate) } catch {}
        [pscustomobject]@{
            device_name  = $_.DeviceName
            device_class = $_.DeviceClass
            manufacturer = $_.Manufacturer
            provider     = $_.DriverProviderName
            driver_date  = $date
            version      = $_.DriverVersion
            inf_name     = $_.InfName
            signer       = $_.Signer
        }
    }
$drivers | Sort-Object device_class, device_name |
    Export-Csv (Join-Path $caseDir 'drivers.csv') -NoTypeInformation -Encoding UTF8

$priorityClasses = @('DISPLAY','HDC','SCSIADAPTER','NET','MEDIA','SYSTEM')
$staleCutoff = (Get-Date).AddYears(-3)
$priorityDrivers = @($drivers | Where-Object {
    ($priorityClasses -contains ([string]$_.device_class).ToUpperInvariant()) -and
    $_.driver_date -and $_.driver_date -lt $staleCutoff
})
if ($priorityDrivers.Count -gt 0) {
    Add-Finding $findings 'medium' 'driver' 'Old latency-sensitive drivers detected' \
        (($priorityDrivers | Select-Object -First 12 device_name, device_class, provider, driver_date, version | ConvertTo-Json -Compress)) \
        'Update only from the laptop/OEM, GPU, network, or storage vendor. Create a restore point first; do not use generic driver-updater utilities.'
}

# Storage controllers and disks
$storageControllers = Get-CimInstance Win32_PnPEntity -ErrorAction SilentlyContinue |
    Where-Object { $_.PNPClass -in @('SCSIAdapter','HDC','Storage') } |
    Select-Object Name, Manufacturer, PNPClass, Status, DeviceID
$storageControllers | Export-Csv (Join-Path $caseDir 'storage-controllers.csv') -NoTypeInformation -Encoding UTF8

$physicalDisks = @()
try {
    $physicalDisks = Get-PhysicalDisk | Select-Object FriendlyName, Manufacturer, Model, MediaType, BusType, HealthStatus, OperationalStatus, FirmwareVersion, Size
    $physicalDisks | Export-Csv (Join-Path $caseDir 'physical-disks.csv') -NoTypeInformation -Encoding UTF8
    $unhealthy = @($physicalDisks | Where-Object { $_.HealthStatus -and $_.HealthStatus -ne 'Healthy' })
    if ($unhealthy.Count -gt 0) {
        Add-Finding $findings 'high' 'storage' 'Storage health is not Healthy' \
            (($unhealthy | ConvertTo-Json -Compress)) \
            'Back up important data immediately and run the OEM storage diagnostic before firmware or driver changes.'
    }
} catch {
    $limitations.Add("Get-PhysicalDisk unavailable: $($_.Exception.Message)")
}

# Reliability-relevant event providers
$eventRows = @()
try {
    $eventRows = Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=$startTime; Level=1,2,3} -ErrorAction Stop |
        Where-Object { $_.ProviderName -match 'disk|stor|nvme|iaStor|stornvme|Display|WHEA|Kernel-PnP|Netwtw|nvlddmkm|amdkmdag' } |
        Select-Object -First 500 TimeCreated, Id, ProviderName, LevelDisplayName, Message
    $eventRows | Export-Csv (Join-Path $caseDir 'relevant-system-events.csv') -NoTypeInformation -Encoding UTF8
} catch {
    $limitations.Add("Could not collect relevant system events: $($_.Exception.Message)")
}

$whea = @($eventRows | Where-Object { $_.ProviderName -match 'WHEA' })
if ($whea.Count -gt 0) {
    Add-Finding $findings 'high' 'hardware' 'WHEA hardware-error events detected' \
        (($whea | Select-Object -First 8 TimeCreated, Id, Message | ConvertTo-Json -Compress)) \
        'Run MSI/OEM memory and storage diagnostics. Avoid BIOS overclocking or undervolting while diagnosing.'
}

$storageErrors = @($eventRows | Where-Object { $_.ProviderName -match 'disk|stor|nvme|iaStor' })
if ($storageErrors.Count -gt 0) {
    Add-Finding $findings 'high' 'storage' 'Storage-related errors occurred near the crash window' \
        (($storageErrors | Select-Object -First 10 TimeCreated, Id, ProviderName, Message | ConvertTo-Json -Compress)) \
        'Check SSD firmware, chipset/storage controller driver, and disk health. Back up data before changes.'
}

$displayErrors = @($eventRows | Where-Object { $_.ProviderName -match 'Display|nvlddmkm|amdkmdag' })
if ($displayErrors.Count -gt 0) {
    Add-Finding $findings 'medium' 'graphics' 'Display-driver errors detected' \
        (($displayErrors | Select-Object -First 10 TimeCreated, Id, ProviderName, Message | ConvertTo-Json -Compress)) \
        'Use the MSI/OEM recommended graphics driver first; if the issue began after an update, consider a clean rollback.'
}

# Recent Windows hotfixes
$hotfixes = Get-HotFix -ErrorAction SilentlyContinue | Sort-Object InstalledOn -Descending |
    Select-Object -First 30 HotFixID, Description, InstalledOn, InstalledBy
$hotfixes | Export-Csv (Join-Path $caseDir 'recent-hotfixes.csv') -NoTypeInformation -Encoding UTF8

# Detection specifically for 0x133
$has133 = @($bugchecks | Where-Object { $_.bugcheck -eq '0X133' -or $_.bugcheck -eq '0x133' }).Count -gt 0
if ($has133) {
    Add-Finding $findings 'high' 'bugcheck' 'DPC_WATCHDOG_VIOLATION (0x133) confirmed in Event Log' \
        'The operating system recorded bugcheck 0x133.' \
        'Prioritize dump analysis and latency-sensitive drivers: storage/NVMe, chipset, GPU, network, audio, and USB. This finding identifies a class of causes, not the exact faulty driver.'
}

if ($dumps.Count -eq 0) {
    Add-Finding $findings 'medium' 'evidence' 'No memory dump was found' \
        'Neither Windows Minidump nor MEMORY.DMP was accessible.' \
        'Enable Small memory dump (256 KB) in System Properties > Startup and Recovery, then rerun after the next crash.'
    $limitations.Add('Without a crash dump, the exact blocked ISR/DPC routine usually cannot be identified reliably.')
} else {
    Add-Finding $findings 'info' 'evidence' 'Crash dump evidence is available' \
        (($dumps | Select-Object -First 5 FullName, LastWriteTime, Length | ConvertTo-Json -Compress)) \
        'Open the newest dump in WinDbg and run: !analyze -v, lm t n, and !dpcs. Treat MODULE_NAME as a lead that requires corroboration.'
}

$report = [pscustomobject]@{
    schema_version = '1.0'
    case_id        = "case-$timestamp"
    scope          = 'Read-only Windows BSOD and DPC watchdog triage'
    system         = $system
    bugcheck_count = @($bugchecks).Count
    dump_count     = $dumps.Count
    findings       = $findings
    limitations    = $limitations
    non_claims     = @(
        'This tool does not prove that a named driver or device caused the crash.',
        'It does not modify drivers, firmware, BIOS, registry, or crash-dump settings.',
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
Write-Host "No drivers, firmware, BIOS, registry settings, or services were changed." -ForegroundColor Yellow
