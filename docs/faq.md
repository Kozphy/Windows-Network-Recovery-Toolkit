# FAQ

## Do I need Administrator access?

Yes for repair scripts. Windows requires Administrator permission for network stack, proxy, DNS, and firewall changes.

`auto_diagnose.bat` is read-only, but it also checks for Administrator permission so users follow the same safe workflow.

## Will this fix my router?

No. The toolkit only changes Windows settings on the local computer.

If the same issue happens on every device, check the router, modem, or ISP.

## Will this remove my VPN?

No. The toolkit does not uninstall VPN software.

VPN software can still reapply proxy or network settings after reboot. If settings keep coming back, check the VPN client.

## Why does the full repair require a restart?

Winsock and TCP/IP resets are low-level Windows network changes. Windows may not fully reload those components until reboot.

## Is `reset_firewall.bat` safe?

It uses a built-in Windows command, but it can remove custom firewall rules.

Use it only when firewall rules are likely broken. `auto_fix.bat` never runs it automatically.

## What should I do if proxy settings return after reset?

Check for:

- VPN software
- Work or school device policies
- Antivirus web protection
- Browser extensions
- Startup applications

## What if the diagnosis says browser-specific problem?

Try:

- Another browser
- Clearing browser proxy settings
- Disabling suspicious extensions
- Resetting Edge or Chrome settings

If only one browser fails, Windows networking may already be working.

For **one site timing out** while others work (e.g. LinkedIn `ERR_TIMED_OUT`), see
[troubleshooting_site_specific.md](troubleshooting_site_specific.md) and run
`python -m src proxy-status` plus `python -m src proxy-path-status` while the site fails.

## Are logs uploaded anywhere?

No. Logs are written locally to the `logs` folder and are ignored by Git.
