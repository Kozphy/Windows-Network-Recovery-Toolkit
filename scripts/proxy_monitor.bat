@echo off
setlocal EnableExtensions

REM Poll HKCU WinINET proxy keys on an interval via python -m src proxy-monitor.
REM Privileges: user-level registry reads; append JSONL when second arg specifies a path.
REM Side effects: optional append-only logs\proxy_guard_events.jsonl rows at chosen path.
REM Examples:
REM   proxy_monitor.bat
REM   proxy_monitor.bat 5 logs\proxy_guard_events.jsonl

pushd "%~dp0.." >nul 2>&1

set INTERVAL=%~1
set JSONL=%~2
if "%INTERVAL%"=="" set INTERVAL=5

echo Monitoring proxy registry interval=%INTERVAL% seconds.
echo Press Ctrl+C to stop.
if "%JSONL%"=="" (
    python -m src proxy-monitor --interval %INTERVAL%
) else (
    python -m src proxy-monitor --interval %INTERVAL% --jsonl "%JSONL%"
)

pause

popd >nul
exit /b 0
