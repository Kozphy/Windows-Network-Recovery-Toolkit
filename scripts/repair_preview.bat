@echo off
setlocal EnableExtensions

REM Windows Network Recovery Toolkit
REM Safe repair preview helper (no mutation).
REM --
REM Purpose: run layer diagnosis and print preview-only actions.
REM Privileges: standard user token.
REM Inputs: current host network/proxy state only.
REM Outputs: JSON diagnosis plus preview guidance text.
REM Side effects: same audit/report files as diagnose_layers.bat.
REM Safety boundary: this script never executes repair actions.
REM Idempotency: each run appends new audit/report artifacts only.
REM Recovery: if preview fails, run diagnose_layers.bat and inspect stderr for missing tools.
REM Example: scripts\repair_preview.bat

title Windows Network Recovery Toolkit - Repair Preview
cd /d "%~dp0.."
python -m failure_system.layer_decision
set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" exit /b %CODE%
echo.
echo Repair preview is advisory only.
echo Apply changes manually with explicit confirmation paths.
exit /b 0

