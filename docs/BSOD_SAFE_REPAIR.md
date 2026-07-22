# BSOD Safe Repair

`tools/Invoke-BsodSafeRepair.ps1` provides a staged Windows workflow for recurring blue/black-screen crashes, including `DPC_WATCHDOG_VIOLATION (0x133)`.

It is intentionally conservative. It can assess the machine, repair Windows component and protected-file corruption, run an online disk scan, and verify the result. It does **not** automatically flash BIOS/firmware, replace storage drivers, uninstall devices, or claim that a hardware fault has been fixed.

## Requirements

- Windows 10 or Windows 11
- Windows PowerShell 5.1 or PowerShell 7
- Run PowerShell as Administrator
- Back up important files before repair work

## 1. Assess without changing the system

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\tools\Invoke-BsodSafeRepair.ps1 -Mode Assess
```

This collects recent BugCheck, storage, WHEA, driver, disk-health, and dump information.

## 2. Apply bounded Windows repairs

```powershell
.\tools\Invoke-BsodSafeRepair.ps1 -Mode Repair -EnableSmallMemoryDumps
```

Repair mode runs:

```text
DISM /Online /Cleanup-Image /RestoreHealth
sfc /scannow
chkdsk C: /scan
```

These steps can repair Windows image or file-system corruption. They cannot repair failing SSD/RAM, overheating, defective firmware, or a bad kernel driver.

Use `-WhatIf` to preview registry-changing actions:

```powershell
.\tools\Invoke-BsodSafeRepair.ps1 -Mode Repair -EnableSmallMemoryDumps -WhatIf
```

Optional skips:

```powershell
.\tools\Invoke-BsodSafeRepair.ps1 -Mode Repair -SkipDISM
.\tools\Invoke-BsodSafeRepair.ps1 -Mode Repair -SkipSFC
.\tools\Invoke-BsodSafeRepair.ps1 -Mode Repair -SkipDiskScan
```

## 3. Verify after restarting

```powershell
.\tools\Invoke-BsodSafeRepair.ps1 -Mode Verify
```

Reports are written to:

```text
Desktop\BSOD-Safe-Repair\<timestamp>\
```

The directory contains `REPORT.md` and `result.json`.

## Escalate instead of repeatedly repairing when

- Windows cannot boot or the computer crashes during DISM/SFC/CHKDSK
- disk, `stornvme`, `storahci`, NTFS, or WHEA errors keep returning
- SMART/physical-disk health is not healthy
- crashes began after a BIOS, firmware, storage, chipset, or display-driver change
- the device overheats, powers off abruptly, or shows memory-test errors

In those cases, preserve the report and crash dumps, back up data, and use MSI/vendor support or a qualified technician. Do not repeatedly force power-off unless Windows is fully frozen.