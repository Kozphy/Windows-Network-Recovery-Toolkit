@echo off
REM YouTube / Edge stall fix when IPv6 is broken but IPv4 works.
REM MUST fully quit Edge first: --disable-quic is ignored if Edge is already running.
cd /d "%~dp0"

echo === WNRT fix-youtube ===
echo [1/4] network-path-health (read-only)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\fix-network-path.ps1" -Json 2>nul

echo [2/4] Fully quitting Edge (required for --disable-quic to stick)...
taskkill /IM msedge.exe /F >nul 2>&1
taskkill /IM msedgewebview2.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul

echo [3/4] Flush DNS + clear Edge Network Persistent State...
ipconfig /flushdns >nul
del /f /q "%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Network\Network Persistent State" >nul 2>&1

set EDGE=
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe
if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe
if "%EDGE%"=="" (
  echo Edge not found.
  exit /b 1
)

echo [4/4] Starting Edge with --disable-quic (cold start)...
start "" "%EDGE%" --disable-quic --disable-features=AsyncDns,UseDnsHttpsSvcb,DnsOverHttps --no-first-run "https://www.youtube.com"
echo.
echo Use THIS new Edge window. QuicAllowed policy is off; Prefer-IPv4 is already applied.
echo If still spinning: fix-network-path.cmd /APPLY then re-run this script.
exit /b 0
