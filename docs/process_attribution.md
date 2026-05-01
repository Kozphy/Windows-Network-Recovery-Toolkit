# Process attribution (best-effort)

## Data sources

- `netstat -ano` LISTENING rows locate `(host, port, pid)`
- `tasklist /CSV` maps PID → image name quickly
- PowerShell `Get-CimInstance Win32_Process` (optional enrichment) exposes `CommandLine`, `ExecutablePath`, `ParentProcessId`

## Permission limits

Elevated tooling or hardened environments may withhold `CommandLine` or executable path fields—the attribution helpers set `permission_limited` rather than pretending the data exists.

## Parsing tests

Pure parsers live in `tests/test_port_owner_parse.py` using checked-in `netstat` fixtures so CI stays Windows-optional.
