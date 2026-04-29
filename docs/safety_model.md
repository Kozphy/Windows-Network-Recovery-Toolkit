# Safety Model

This project is designed for beginner users, so safety is more important than aggressive repair.

## Safety Principles

- Diagnose before changing settings.
- Prefer targeted fixes over full reset.
- Ask before applying repairs.
- Avoid actions that can disconnect the user unexpectedly.
- Keep firewall reset manual.
- Keep logs local.

## Read-Only Operations

These actions do not change network settings:

- Showing network adapters
- Running `ping`
- Running `nslookup`
- Running `Test-NetConnection`
- Running `curl`
- Showing WinHTTP proxy settings
- Reading user proxy registry values

`auto_diagnose.bat` only performs read-only operations.

## Repair Operations

These actions change settings:

- Flushing DNS cache
- Resetting Winsock
- Resetting TCP/IP
- Resetting WinHTTP proxy
- Updating user proxy registry values
- Resetting Windows Firewall

Repair scripts require Administrator permission.

## Explicit Non-Goals

The toolkit does not:

- Disable network adapters
- Disable network adapter bindings
- Remove VPN software
- Remove antivirus software
- Change router settings
- Change ISP settings
- Reset firewall automatically
- Bypass enterprise policies

## Restart Requirements

Some Windows network resets do not fully apply until reboot.

Restart after:

- `one_click_fix.bat`
- Any guided repair that runs `one_click_fix.bat`

## Managed Devices

Work or school computers may use policy-managed proxy, firewall, or VPN settings.

On managed devices:

- Ask IT before resetting proxy settings.
- Ask IT before resetting firewall settings.
- Expect some settings to return automatically after reboot or sign-in.
