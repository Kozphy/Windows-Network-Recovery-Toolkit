@echo off
setlocal EnableExtensions

REM Windows Network Recovery Toolkit — Proxy Guard (read-only).
REM Purpose: summarize HKCU WinINET proxy registry via python -m src proxy-status.
REM Privileges: standard user sufficient for HKCU reads.
REM Side effects: none on disk/registry; prints to console only.
REM Idempotent: reruns reproduce current state.
REM Recovery: rerun after toggling proxies in Settings UI.

pushd "%~dp0.." >nul 2>&1

echo ============================================
echo Proxy status (HKCU WinINET summary)
echo ============================================
python -m src proxy-status
if errorlevel 1 (
    echo Python or module error. Ensure Python is on PATH and repo root contains src\ .
)
pause

popd >nul
exit /b 0
