@echo off
setlocal EnableExtensions

REM Structured WinINET HKCU proxy disable preview/apply (python -m src proxy-disable).
REM Privileges: standard user writes current-user hive only; escalation not required unless policy blocks.
REM Inputs: forwarded CLI args (%*); omit args for guided confirmation phrase inside Python.
REM Outputs: stdout summary; audits append logs\repair_audit.jsonl on confirmed apply paths.
REM Side effects: modifies HKCU ProxyEnable/ProxyServer when apply confirms; skips WinHTTP by design.
REM Idempotency: disabling twice yields stable keys; reversing requires manual/policy steps.

pushd "%~dp0.." >nul 2>&1

echo This launches the structured proxy-disable command. Default is dry-run preview.
echo Live apply requires: python -m src proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY
python -m src proxy-disable %*
pause

popd >nul
exit /b 0
