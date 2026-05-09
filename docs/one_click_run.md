# One-Click Local Run

Use this when you want a Windows double-click workflow for the local demo stack.

## Start

Double-click:

```powershell
scripts\start_everything_safe.bat
```

Or run from PowerShell:

```powershell
scripts\start_everything_safe.ps1
```

The launcher:

- runs read-only proxy diagnostics;
- writes logs under `logs/`;
- starts FastAPI on `http://127.0.0.1:8000` when backend dependencies are installed;
- starts Next.js on `http://127.0.0.1:3000` when frontend dependencies are installed;
- opens minimized dev-server console windows so Windows keeps the local servers alive;
- sets local demo auth bypass environment variables for the backend process;
- does not run repair actions.

## First-Time Dependency Install

If dependencies are missing, run:

```powershell
scripts\start_everything_safe.ps1 -InstallDeps
```

This may need internet access:

- backend: `pip install -r backend\requirements.txt`
- frontend: `npm install` inside `frontend\`

If your endpoint proxy is broken, dependency installation can fail. The diagnostic logs will still be written.

## Stop

Double-click:

```powershell
scripts\stop_everything_safe.bat
```

Or run:

```powershell
scripts\stop_everything_safe.ps1
```

The stop script only targets PID files created by the one-click launcher:

- `logs\one_click_backend.pid`
- `logs\one_click_frontend.pid`

It stops the process tree rooted at those launcher-owned PIDs so child dev-server processes do not
keep ports open after the wrapper exits.

## Safety Boundary

The one-click launcher does not:

- kill arbitrary endpoint processes;
- delete certificates;
- reset firewall;
- disable adapters;
- mutate proxy registry values;
- run repair scripts.

It starts local developer services and runs observe-only diagnostics. Registry restore remains a separate,
explicitly confirmed remediation path.
