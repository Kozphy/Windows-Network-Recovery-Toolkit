# Windows Clipboard Diagnostics

A privacy-conscious PowerShell diagnostic toolkit for checking whether the Windows text clipboard can be written, read, and restored correctly.

## Design principles

- **No clipboard contents are logged by default.**
- Results contain hashes, lengths, timings, and status only.
- Existing text clipboard content is restored after testing when possible.
- A failed test is evidence of a clipboard reliability problem, **not proof of malware, surveillance, or compromise**.
- The diagnostic distinguishes Windows-wide failure from application-specific copy/paste problems.

## Requirements

- Windows 10 or Windows 11
- Windows PowerShell 5.1 or PowerShell 7+

## Run

The diagnostic temporarily replaces the text clipboard. It asks for confirmation unless `-ConfirmOverwrite` is supplied.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Test-Clipboard.ps1
```

Non-interactive use:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Test-Clipboard.ps1 `
  -ConfirmOverwrite `
  -JsonOutput .\clipboard-result.json
```

## Example output

```text
PASS: Clipboard text round-trip succeeded.
Clipboard restored: Yes
Duration: 41 ms
```

Example JSON evidence:

```json
{
  "schema_version": "1.0",
  "test": "clipboard_text_round_trip",
  "status": "PASS",
  "expected_sha256": "...",
  "actual_sha256": "...",
  "expected_length": 68,
  "actual_length": 68,
  "duration_ms": 41,
  "clipboard_restored": true,
  "timestamp_utc": "2026-07-11T12:00:00Z"
}
```

## Interpretation

| Result | Meaning |
|---|---|
| `PASS` | Windows successfully wrote and read the test text. |
| `FAIL` | The clipboard returned different content or no content. |
| `ERROR` | PowerShell or Windows reported an exception. |
| `SKIPPED` | The user did not consent to temporarily overwrite the clipboard. |

If this passes but copy/paste fails in one program, the likely cause is application-specific, focus-related, permissions-related, or a shortcut conflict.

## Tests

Pester tests are included under `tests/`:

```powershell
Invoke-Pester .\tests
```

## Security and privacy

See [SECURITY.md](SECURITY.md). This project deliberately avoids collecting the user's clipboard contents.

## License

MIT
