@echo off
REM =============================================================================
REM fix-linkedin-proxy.cmd — repo-root one-shot LinkedIn / WinINET prefer-direct
REM =============================================================================
REM Purpose:
REM   Clear broken/active localhost WinINET proxy + Cursor no-proxy + guardian.
REM Examples:
REM   fix-linkedin-proxy.cmd
REM   fix-linkedin-proxy.cmd dry-run
REM =============================================================================
cd /d "%~dp0"
if /I "%~1"=="dry-run" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\fix-linkedin-proxy.ps1" -DryRun
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\fix-linkedin-proxy.ps1"
)
exit /b %ERRORLEVEL%
