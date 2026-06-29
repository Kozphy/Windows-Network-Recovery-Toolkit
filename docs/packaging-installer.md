# Packaging and installer strategy (Phase 6)

**Status:** Documentation and CLI packaging contracts — no silent auto-start or default background services.

**Related:** [enterprise-hardening-roadmap.md](enterprise-hardening-roadmap.md) · [agent-deployment.md](agent-deployment.md) · [ONBOARDING.md](../ONBOARDING.md)

---

## Principles (non-negotiable)

| Principle | Implementation |
|-----------|----------------|
| No auto-start by default | Installers and service units are **opt-in** and documented only |
| No background service by default | Agent loop and API server require explicit operator command |
| Read-only commands work without admin | `version`, `principles`, `agent once --fixture`, analytics on fixtures |
| Dangerous actions stay policy-gated | `proxy-disable` dry-run default + typed confirmation for apply |
| Honest packaging | Version comes from `pyproject.toml` / wheel metadata |

---

## Distribution artifacts

| Artifact | Audience | Admin required? |
|----------|----------|-----------------|
| **Wheel** (`.whl`) | Developers, CI, pip/pipx | No for read-only CLI |
| **pip / pipx install** | Operator workstations | No for read-only CLI |
| **Windows zip** | Air-gapped / no-pip environments | No for read-only CLI |
| **Optional service wrappers** | Long-running agent/API | Yes — explicit install step |

---

## Python version

- **Requires:** Python ≥ 3.11 (`pyproject.toml`)
- **Recommended:** CPython 3.11 or 3.12 on Windows for WinINET observation paths

---

## Wheel build (local)

From repository root:

```powershell
python -m pip install --upgrade build
python -m build --wheel
# Output: dist/windows_network_recovery_toolkit-0.2.0-py3-none-any.whl
```

Verify wheel imports (smoke):

```powershell
python -m pip install ./dist/windows_network_recovery_toolkit-*.whl
wnrt version
python -m pip uninstall -y windows-network-recovery-toolkit
```

---

## pip install (editable dev)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q tests/packaging/
```

Read-only smoke:

```powershell
python -m windows_network_toolkit version
python -m windows_network_toolkit principles explain
python -m windows_network_toolkit agent once --fixture tests/fixtures/agent/sample_evidence_bundle.json
```

---

## pipx install (isolated operator CLI)

[pipx](https://pipx.pypa.io/) installs the CLI in an isolated venv with console scripts on PATH.

```powershell
pip install pipx
pipx ensurepath

# From PyPI when published:
# pipx install windows-network-recovery-toolkit

# From local wheel:
pipx install dist/windows_network_recovery_toolkit-0.2.0-py3-none-any.whl

wnrt version
wnrt agent health
```

**API server (optional, foreground only):**

```powershell
pipx runpip windows-network-recovery-toolkit install uvicorn[standard]
pipx run windows-network-recovery-toolkit wnrt-api
# Or: python -m backend  (after pip install)
```

`wnrt-api` binds `127.0.0.1:8000` by default — not installed as a Windows Service unless operator follows the optional plan below.

---

## Console entry points

Defined in `pyproject.toml`:

| Script | Module | Purpose |
|--------|--------|---------|
| `wnrt` | `windows_network_toolkit.cli:console_main` | Main operator CLI |
| `wnrt-api` | `backend.__main__:main` | FastAPI uvicorn launcher |

Module invocation (equivalent, no PATH entry required):

```powershell
python -m windows_network_toolkit version
python -m backend
```

---

## Version command

```powershell
wnrt version
python -m windows_network_toolkit version
```

Example output:

```json
{
  "package": "windows-network-recovery-toolkit",
  "version": "0.2.0",
  "service": "endpoint-reliability-decision-platform",
  "read_only": true,
  "requires_admin": false
}
```

Version resolves from installed distribution metadata (`importlib.metadata`) with fallback for editable trees.

---

## Windows zip release plan

**Goal:** Portable folder for operators who cannot use pip on target hosts.

### Build steps (release maintainer)

1. Build wheel: `python -m build --wheel`
2. Create staging directory `wnrt-portable-win64/`
3. Copy:
   - `dist/*.whl`
   - `README.md`, `LICENSE`, `docs/packaging-installer.md`, `docs/ONBOARDING.md`
   - `tests/fixtures/` (optional demo subset)
   - `scripts/run-portable-wnrt.ps1` (below)
4. Zip: `windows-network-recovery-toolkit-0.2.0-win64-portable.zip`

### Portable launcher script (operator)

Create `scripts/run-portable-wnrt.ps1` at install time or ship in zip:

```powershell
# Requires Python 3.11+ on PATH — does not install a service
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Wheel = Get-ChildItem "$Root\dist\*.whl" | Select-Object -First 1
python -m pip install --user --force-reinstall $Wheel.FullName
python -m windows_network_toolkit @args
```

**Non-goals for zip release v1:**

- No MSI / Authenticode signing (document as future work)
- No scheduled task or service registration
- No elevation prompt for read-only commands

---

## Optional: Windows Service wrapper (opt-in)

**Not installed by default.** For teams that want a supervised read-only agent loop:

### Design

| Component | Role |
|-----------|------|
| Service name | `WNRTReadOnlyAgent` (example) |
| Binary | `python.exe` or embedded Python from venv |
| Arguments | `-m windows_network_toolkit agent run --interval 60` |
| Account | `NT AUTHORITY\LOCAL SERVICE` or dedicated gMSA |
| Start type | **Manual** or **Automatic (Delayed)** — operator choice |
| Recovery | Restart on failure (optional) |

### Install sketch (admin — operator must run explicitly)

```powershell
# Example only — not executed by pip install
$Python = (Get-Command python).Source
sc.exe create WNRTReadOnlyAgent binPath= "`"$Python`" -m windows_network_toolkit agent run" start= demand
sc.exe description WNRTReadOnlyAgent "WNRT read-only evidence agent (no auto remediation)"
```

**Safety:**

- Service must use read-only agent mode only — no `proxy-disable` in service argv
- Remediation remains interactive CLI with confirmation tokens
- Uninstall: `sc.exe delete WNRTReadOnlyAgent`

---

## Optional: systemd unit (Linux, opt-in)

**Not enabled by default.**

`/etc/systemd/system/wnrt-agent.service` (example):

```ini
[Unit]
Description=WNRT read-only evidence agent
After=network-online.target

[Service]
Type=simple
User=wnrt
Group=wnrt
ExecStart=/usr/local/bin/wnrt agent run --interval 60
Restart=on-failure
# No registry remediation — read-only agent path only

[Install]
WantedBy=multi-user.target
```

Enable only when operator runs:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now wnrt-agent.service   # explicit opt-in
```

Linux collectors are **PARTIAL** — see [cross-platform-support.md](cross-platform-support.md).

---

## Optional: macOS launchd (opt-in)

**Not loaded by default.**

`~/Library/LaunchAgents/com.kozphy.wnrt.agent.plist` (example):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.kozphy.wnrt.agent</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/wnrt</string>
    <string>agent</string>
    <string>run</string>
    <string>--interval</string>
    <string>60</string>
  </array>
  <key>RunAtLoad</key>
  <false/>
  <key>KeepAlive</key>
  <false/>
</dict>
</plist>
```

`RunAtLoad=false` — no auto-start on login unless operator sets `true` and runs `launchctl load`.

---

## Privilege matrix

| Command class | Admin / elevation |
|---------------|-------------------|
| `version`, `principles`, `audit verify`, analytics on fixtures | **Not required** |
| `agent once`, `agent health`, `agent spool-status` | **Not required** |
| `proxy-status`, `proxy-health` (read-only) | Usually not required |
| `proxy-disable` apply (live registry) | **Required** + typed confirmation |
| Service install (Windows/Linux/macOS) | **Required** — operator opt-in |

---

## Smoke tests (CI)

```powershell
pytest -q tests/packaging/test_entrypoint_smoke.py
```

Covers:

- `python -m windows_network_toolkit version` JSON contract
- Version matches `pyproject.toml`
- Read-only `principles explain` and `agent once --fixture`
- `backend.main:app` import
- Optional `wnrt` on PATH when installed

---

## Explicit non-claims

- Not a signed MSI or enterprise software catalog entry (v1)
- pip/pipx install does **not** register services or scheduled tasks
- Portable zip does not bundle a private Python runtime (operator supplies 3.11+)
- Packaging does not weaken `windows_network_toolkit/safety.py` policy gates

---

## Future work (out of Phase 6 scope)

- Authenticode-signed MSI with optional service checkbox (default **off**)
- SBOM generation (`pip-audit`, CycloneDX) in release pipeline
- Embedded Python embeddable distro in Windows zip
- Intune / GPO deployment guides
