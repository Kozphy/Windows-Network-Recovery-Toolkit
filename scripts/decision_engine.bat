@echo off
setlocal EnableExtensions

REM Windows Network Recovery Toolkit
REM Structured decision engine CLI (Python 3).

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
