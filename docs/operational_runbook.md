# Operational Runbook

This runbook is for troubleshooting a Windows machine with broken or inconsistent internet access.

## Scope

Use this runbook for:

- Proxy browser errors
- DNS lookup failures
- Ping works but browser or `curl` fails
- Suspected Winsock or TCP/IP corruption
- Network problems after VPN, proxy, antivirus, or cleanup tools

Do not use this runbook for:

- Physical cable damage
- Router firmware issues
- ISP outages
- Enterprise devices where IT policy controls proxy or firewall settings

## First Response

1. Confirm the user is on Windows 10 or Windows 11.
2. Confirm the user can run scripts as Administrator.
3. Ask whether the device is personal, work, school, or managed.
4. If it is managed, check with IT before resetting proxy or firewall settings.

## Standard Flow

1. Run `scripts\auto_diagnose.bat` as Administrator.
2. Save or review the generated log in `logs/`.
3. Follow the recommendation.
4. Prefer targeted fixes before full repair.
5. Restart Windows after `one_click_fix.bat`.
6. Test again after restart.

## Validation Commands

After repair, check:

```bat
ping 8.8.8.8
nslookup google.com
curl https://www.google.com --max-time 10
```

Expected results:

- Ping receives replies.
- DNS returns addresses.
- `curl` receives an HTTP response.

## Escalation Paths

If the issue remains after the recommended repair:

- Try a mobile hotspot to rule out router or ISP problems.
- Disable VPN temporarily and test again.
- Check antivirus web protection or HTTPS inspection.
- Check browser extensions and browser proxy settings.
- Check whether Windows proxy settings are managed by policy.
- Restart router or modem.

## Manual Firewall Reset

Only use `scripts\reset_firewall.bat` if there is strong evidence that firewall rules are broken.

Examples:

- Multiple apps are blocked after firewall rule changes.
- Windows Firewall rules are known to be corrupted.
- A security product removed or changed many firewall rules.

Do not run firewall reset automatically.

## Information To Capture

If asking for help, include:

- Windows version
- Whether the device is managed by work or school
- The generated diagnosis log
- Whether VPN or antivirus software is installed
- Whether another network works
- Which repair scripts were already run
