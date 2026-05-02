@echo off
REM Safe offline demo — runs python -m platform_core.demo (fixtures + policy only; no network repair).
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%"
python -m platform_core.demo
endlocal
