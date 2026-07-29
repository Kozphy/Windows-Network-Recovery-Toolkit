@echo off
REM =============================================================================
REM enable-proxy-autofix.cmd — one-shot set-and-forget WinINET prefer-direct
REM =============================================================================
REM Installs the 15s hold-direct guardian (+ Cursor no-proxy). After this, you
REM should NOT need manual clear / agent monitoring when localhost proxy rewrites.
REM
REM Examples:
REM   enable-proxy-autofix.cmd
REM   enable-proxy-autofix.cmd uninstall
REM =============================================================================
cd /d "%~dp0"
if /I "%~1"=="uninstall" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install-dead-proxy-guardian.ps1" -Uninstall
  exit /b %ERRORLEVEL%
)

echo === WNRT prefer-direct autofix (set and forget) ===
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\configure-cursor-no-proxy.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\emergency-clear-wininet-proxy.ps1" -Force
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install-dead-proxy-guardian.ps1" -IntervalSeconds 15
echo.
echo Optional DNS repair for DNS_PROBE_FINISHED_BAD_CONFIG (UAC prompt):
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\fix-dns-wifi.ps1"
echo.
echo Autofix installed: clears localhost WinINET rewrites every 15s.
echo Heartbeat: reports\proxy_guardian_heartbeat.json
echo DNS-only: fix-dns.cmd
echo If rewrite keeps returning (suspicious scheduled task / system32 payload):
echo   contain-localhost-rewriter.cmd
echo   contain-localhost-rewriter.cmd /APPLY
echo Uninstall: enable-proxy-autofix.cmd uninstall
exit /b %ERRORLEVEL%
