# Windows Network Recovery Toolkit

Beginner-friendly Windows 10/11 network diagnosis and repair scripts for common issues such as proxy failures, DNS cache problems, Winsock corruption, and cases where ping works but browsers or `curl` fail.

## Project Status

- Platform: Windows 10 and Windows 11
- Dependencies: built-in Windows commands only
- Primary interface: `.bat` scripts
- Default mode: diagnose first, repair only after confirmation
- Safety boundary: does not disable adapter bindings and does not reset firewall automatically

## Quick Start

1. Download the repository as a ZIP file or clone it with Git.
2. Open the `scripts` folder.
3. Right-click `auto_diagnose.bat`.
4. Select **Run as administrator**.
5. Read the diagnosis and recommendation.
6. To apply a guided repair, right-click `auto_fix.bat` and select **Run as administrator**.
7. Restart Windows if the script tells you to.

## Recommended Workflow

Use the smallest safe action that matches the diagnosis.

1. Diagnose: run `auto_diagnose.bat`.
2. Repair with guidance: run `auto_fix.bat`.
3. Repair manually: run a targeted script such as `reset_dns.bat` or `reset_proxy.bat`.
4. Fallback repair: run `one_click_fix.bat` when the issue points to Winsock, TCP/IP, or an unclear stack problem.
5. Manual last resort: run `reset_firewall.bat` only when firewall rules are likely broken.

## Automatic Diagnosis Mode

`auto_diagnose.bat` is read-only. It collects evidence, classifies the likely problem, and writes a timestamped log to `logs/`.

It checks:

- Current network adapters
- DNS with `nslookup google.com`
- TCP 443 with PowerShell `Test-NetConnection`
- HTTPS with `curl https://www.google.com`
- WinHTTP proxy configuration
- User proxy registry values

`auto_fix.bat` runs the diagnosis first, shows the recommendation, asks for confirmation, and then calls the matching repair script. It never runs `reset_firewall.bat` automatically.

## When To Use This

Use this toolkit when Windows says the network is connected, but internet access is still broken or inconsistent.

Common examples:

- Browser shows `ERR_PROXY_CONNECTION_FAILED`
- `ping 8.8.8.8` works, but websites do not load
- `curl` fails even though Wi-Fi or Ethernet is connected
- DNS lookups fail or behave inconsistently
- Problems start after VPN, proxy, antivirus, or cleanup tools
- Some apps connect while browsers fail

## Script Reference

| Script | Mode | Use Case |
| --- | --- | --- |
| `auto_diagnose.bat` | Read-only | Collect evidence and recommend the likely fix. |
| `auto_fix.bat` | Guided repair | Diagnose first, then ask before running the recommended repair. |
| `check_network.bat` | Read-only | Run a simpler manual connectivity check. |
| `reset_dns.bat` | Targeted repair | Flush DNS cache and show DNS configuration. |
| `reset_proxy.bat` | Targeted repair | Clear WinHTTP and user-level proxy settings. |
| `one_click_fix.bat` | Full repair | Reset Winsock, TCP/IP, DNS cache, and proxy settings. |
| `reset_firewall.bat` | Manual repair | Reset Windows Firewall rules to defaults after confirmation. |

## Expected Outcomes

After the correct repair and restart when required:

- Browsers load websites again.
- `curl` can reach HTTPS websites.
- DNS lookups succeed.
- WinHTTP proxy shows direct access when no proxy is required.
- Proxy-related browser errors stop appearing.

## Safety Model

This project follows conservative repair defaults.

- Administrator access is required for repair scripts.
- Diagnosis is read-only.
- Guided repair asks before making changes.
- Firewall reset is never automatic.
- Full stack repair reminds the user to restart.
- Logs are written locally and ignored by Git (see `.gitignore`).

For more detail, read `docs/safety_model.md`.

## Documentation

- `docs/script_reference.md`: detailed script behavior and expected output.
- `docs/diagnosis_decision_tree.md`: how automatic diagnosis maps symptoms to recommendations.
- `docs/operational_runbook.md`: step-by-step runbook for real troubleshooting.
- `docs/design_principles.md`: design goals, safety boundaries, and tradeoffs.
- `docs/faq.md`: beginner-friendly answers to common questions.
- `docs/troubleshooting_flow.md`: manual troubleshooting flow.
- `docs/proxy_error.md`: `ERR_PROXY_CONNECTION_FAILED` explanation and fixes.
- `docs/ping_ok_but_browser_fails.md`: why ping can work while browsers fail.

## Repository Layout

```text
Windows-Network-Recovery-Toolkit/
├── README.md
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── .gitignore
├── docs/
├── logs/
└── scripts/
```

## Portfolio Value

This project demonstrates practical engineering skills:

- Debugging: separates DNS, proxy, TCP, HTTPS, browser, and firewall symptoms.
- Automation: turns repeated Windows repair commands into guided workflows.
- Product thinking: supports non-expert users with clear messages and safe defaults.
- Documentation: includes runbooks, decision trees, safety notes, and contribution guidance.

## Compatibility

- Windows 10
- Windows 11
- Command Prompt or PowerShell
- Administrator permissions for repair scripts

## License

This project is licensed under the MIT License. See `LICENSE` for details.
