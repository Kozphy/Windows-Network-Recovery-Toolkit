@echo off
setlocal EnableExtensions

REM Attribution helper: python -m src proxy-owner (listeners + heuristic process hints).
REM Privileges: standard user reads; some PIDs omit names without elevated tasklist quirks.
REM Side effects: read-only probes (subprocess stderr may appear); optional --json emits machine-parseable blobs.

pushd "%~dp0.." >nul 2>&1

echo ============================================
echo Local proxy port owner attribution
echo ============================================
python -m src proxy-owner
pause

popd >nul
exit /b 0
