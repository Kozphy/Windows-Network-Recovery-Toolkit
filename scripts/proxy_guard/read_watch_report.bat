@echo off
setlocal
REM Read human-readable tail of reports\proxy_guard_watch.jsonl
cd /d "%~dp0..\.."
if "%~1"=="" (set "TAIL=5") else (set "TAIL=%~1")
python -m src proxy-watch-report --tail %TAIL%
endlocal & exit /b %ERRORLEVEL%
