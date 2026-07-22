# BSOD / DPC Watchdog Triage

`tools/Invoke-BsodTriage.ps1` is a read-only Windows evidence collector for blue-screen incidents, including `DPC_WATCHDOG_VIOLATION (0x133)`.

## What it collects

- Windows, MSI/OEM model, BIOS version, and boot time
- BugCheck Event ID 1001 records
- Kernel-Power 41 and unexpected shutdown 6008 events
- Minidump and `MEMORY.DMP` inventory
- Signed PnP driver inventory and old latency-sensitive drivers
- Physical-disk health and firmware metadata
- Storage, NVMe, display, WHEA, Kernel-PnP, and selected network-driver events
- Recently installed Windows hotfixes

It produces Markdown and JSON reports plus CSV evidence files in a timestamped ZIP archive.

## Safety boundary

The script does **not** update, disable, remove, or roll back drivers. It does not change firmware, BIOS, registry, services, or crash-dump settings. Its findings are correlations and triage leads—not proof that a device or driver caused the crash.

## Run

Open **Windows PowerShell as Administrator**, then run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\tools\Invoke-BsodTriage.ps1
```

To include copies of dump files in the ZIP:

```powershell
.\tools\Invoke-BsodTriage.ps1 -IncludeDumpCopies
```

Dump files may contain sensitive information. Review the archive before uploading or sharing it.

## Output

Default location:

```text
Desktop\BSOD-Triage\case-YYYYMMDD-HHMMSS\
Desktop\BSOD-Triage\case-YYYYMMDD-HHMMSS.zip
```

Start with `triage-report.md`. For a confirmed `0x133`, examine the newest dump in WinDbg and run:

```text
!analyze -v
lm t n
!dpcs
```

A module named by WinDbg is a lead requiring corroboration with event timing, driver version history, firmware state, and reproducibility.

## Interpretation order

1. Back up important data when disk health or storage events are abnormal.
2. Check for WHEA hardware-error events.
3. Correlate the crash time with storage, GPU, network, audio, chipset, and USB events.
4. Review drivers changed shortly before the first crash.
5. Use MSI/OEM-supported drivers before generic vendor packages on laptops.
6. Analyze the dump before making multiple changes at once.
