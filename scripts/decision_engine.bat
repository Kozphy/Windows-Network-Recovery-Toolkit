@echo off
setlocal EnableExtensions

REM Windows Network Recovery Toolkit
REM Structured decision engine CLI (Python 3).
REM --
REM Purpose: Wrapper for `python -m src %*` from repo root (diagnose/explain/etc.).
REM Privileges: User-grade unless subcommands elevate (e.g. repair-safe --apply).
REM Outputs: reports\ and logs\ per Python CLI; see root README Decision Architecture section.
REM Side effects: Driven entirely by forwarded subcommand arguments.

title Windows Network Recovery Toolkit - Decision Architecture

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
pushd "%ROOT_DIR%" >nul 2>&1

where python >nul 2>&1
if not "%errorlevel%"=="0" (
    echo Python is required for the decision architecture.
    echo Install Python 3 and ensure `python` is on PATH.
    popd >nul
    exit /b 1
)

python -m src %*
set "EXIT_CODE=%ERRORLEVEL%"

popd >nul
exit /b %EXIT_CODE%
