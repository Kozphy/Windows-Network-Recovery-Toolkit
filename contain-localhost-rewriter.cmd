@echo off
REM =============================================================================
REM contain-localhost-rewriter.cmd — one-command rewriter persistence containment
REM =============================================================================
REM Preview (default):  contain-localhost-rewriter.cmd
REM Live apply:         contain-localhost-rewriter.cmd /APPLY
REM
REM Use when hold-direct guardian keeps clearing localhost WinINET but a Session-0
REM scheduled task / system32 payload keeps rewriting (e.g. VersionUpdaterV12-*).
REM Requires elevation for task delete / system32 quarantine.
REM =============================================================================
cd /d "%~dp0"

net session >nul 2>&1
if errorlevel 1 (
  echo WARNING: Not elevated. Task delete / system32 quarantine may fail.
  echo Right-click Command Prompt -^> Run as administrator, then re-run.
  echo.
)

if /I "%~1"=="/APPLY" goto APPLY
if /I "%~1"=="APPLY" goto APPLY
if /I "%~1"=="-Apply" goto APPLY

echo === PREVIEW contain-localhost-rewriter (no changes) ===
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\contain-localhost-rewriter.ps1" -Json
echo.
echo To apply containment: contain-localhost-rewriter.cmd /APPLY
exit /b %ERRORLEVEL%

:APPLY
echo === APPLY contain-localhost-rewriter ===
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\contain-localhost-rewriter.ps1" -Apply -Json
exit /b %ERRORLEVEL%
