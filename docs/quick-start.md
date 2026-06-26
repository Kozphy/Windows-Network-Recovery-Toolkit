# Quick Start

Install, configure, and verify the toolkit locally. Fixture demos require **no admin** and **no host mutation**.

## Install

```powershell
git clone <repo-url>
cd Windows-Network-Recovery-Toolkit
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = (Get-Location).Path
```

Editable install (recommended for demos and development):

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path
```

## Verify

```powershell
make demo                    # golden fixture replay (read-only, ~3 min)
pytest -q                    # full test suite
```

## Operator entrypoint

```powershell
python -m windows_network_toolkit <command>
```

New visitors: [START_HERE.md](START_HERE.md) · Install: [quick-start.md](quick-start.md) · Demos: [demo_5_min.md](demo_5_min.md) · [demo-commands-reference.md](demo-commands-reference.md)
