@echo off
REM =============================================================================
REM start_cursor_safe.bat — Diagnose → optional reset prompt → launch Cursor.exe
REM Tries %LOCALAPPDATA%\Programs\Cursor\Cursor.exe and %ProgramFiles%\Cursor\Cursor.exe
REM =============================================================================
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_cursor_safe.ps1"
set "ERR=%ERRORLEVEL%"
endlocal & exit /b %ERR%
