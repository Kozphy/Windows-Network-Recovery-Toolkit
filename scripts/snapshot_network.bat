@echo off
setlocal EnableExtensions

REM Persist JSON snapshot via python -m src snapshot → reports\snapshots\ timestamps.
REM Read-only probes except writing the snapshot/report files listed in CLI banner.

pushd "%~dp0.." >nul 2>&1

python -m src snapshot
pause

popd >nul
exit /b 0
