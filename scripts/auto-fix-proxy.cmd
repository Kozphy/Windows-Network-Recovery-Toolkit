@echo off
setlocal
title WNRT Auto-Fix Dead Proxy
set "REPO_ROOT=%~dp0.."
pushd "%REPO_ROOT%" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0auto-fix-proxy.ps1" %*
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
