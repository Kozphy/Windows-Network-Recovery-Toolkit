# Script Reference

This document explains what each script does, when to run it, and what to expect.

## Summary

| Script | Changes Settings | Restart Needed | Recommended Use |
| --- | --- | --- | --- |
| `auto_diagnose.bat` | No | No | First step for most users. |
| `auto_fix.bat` | Only after confirmation | Sometimes | Guided diagnosis and repair. |
| `check_network.bat` | No | No | Simple manual connectivity check. |
| `check_connection_exhaustion.bat` | No | No | Detect socket leaks or ephemeral port exhaustion. |
| `reset_dns.bat` | Yes | Usually no | DNS cache or name lookup issues. |
| `reset_proxy.bat` | Yes | Usually no | Proxy errors or unwanted proxy settings. |
| `one_click_fix.bat` | Yes | Yes | Full fallback repair for stack issues. |
| `reset_firewall.bat` | Yes | Usually no | Manual last resort for firewall rules. |

## `auto_diagnose.bat`

Use this first when you are not sure what is wrong.

What it checks:

- Administrator permission
- Network adapter status
- DNS lookup
- TCP port 443
- HTTPS request
- WinHTTP proxy settings
- User proxy registry values

What it produces:

- A clear diagnosis in the Command Prompt window
- A recommendation such as `Run reset_dns.bat`
- A timestamped log in `logs/`

It does not change network settings.

## `auto_fix.bat`

Use this when you want the toolkit to recommend and run the correct repair.

Behavior:

1. Runs `auto_diagnose.bat`.
2. Reads the detected issue.
3. Shows the recommended repair.
4. Asks for confirmation.
5. Runs the matching repair script only if the user types `YES`.

Safety rule:

- It never runs `reset_firewall.bat` automatically.

## `check_network.bat`

Use this for a quick manual check.

It tests:

- Ping to `8.8.8.8`
- DNS lookup for `google.com`
- HTTP access with `curl`
- WinHTTP proxy state
- User proxy registry values

It does not change network settings.

## `check_connection_exhaustion.bat`

Use this when the network works at first but browsers or apps start timing out after heavy usage or long uptime.

It checks:

- `TIME_WAIT` connection count
- `ESTABLISHED` connection count
- Top processes using TCP connections
- IPv4 dynamic TCP port range

What it produces:

- Raw command output
- Human-readable interpretation
- Common causes
- Suggested actions

It does not change network settings.

## `reset_dns.bat`

Use this when DNS lookups fail or websites resolve inconsistently.

It runs:

- `ipconfig /flushdns`
- DNS configuration display commands

Expected result:

- Stale DNS cache is cleared.
- New DNS lookups are forced on the next request.

## `reset_proxy.bat`

Use this when browsers show proxy errors or proxy settings look wrong.

It resets:

- WinHTTP proxy
- User-level proxy enable flag
- `ProxyServer`
- `AutoConfigURL`

Expected result:

- WinHTTP should show direct access unless a managed proxy is configured.
- Browsers should stop trying to use a stale proxy.

## `one_click_fix.bat`

Use this when targeted fixes do not work or the problem looks like Winsock or TCP/IP corruption.

It resets:

- Winsock catalog
- TCP/IP stack
- DNS cache
- WinHTTP proxy
- Common user proxy settings

Restart Windows after running this script.

## `reset_firewall.bat`

Use this only when firewall rules are likely broken.

Important:

- This can remove custom firewall rules.
- It asks for confirmation.
- It is not called automatically by `auto_fix.bat`.

Expected result:

- Windows Firewall rules return to default settings.
