@echo off
setlocal EnableExtensions

REM Windows Network Recovery Toolkit
REM Layer-aware, read-only diagnosis entrypoint.
REM --
REM Purpose: classify failure by L1/L2, L3, L4, L7, Infra before repair.
REM Privileges: standard user token is sufficient for diagnosis.
REM Inputs: current host network/proxy state only (no interactive arguments).
REM Outputs: JSON to stdout; audit JSONL + markdown report files.
REM Side effects: appends logs\network_layer_audit.jsonl and writes reports\network_layer_diagnosis_<timestamp>.md.
REM Safety: no registry edits, no process kill, no firewall reset, no adapter disable.
REM Idempotency: read-only diagnosis, but each run appends a new audit row/report.
REM Recovery: if command fails, rerun after confirming Python path and command availability.
REM Example: scripts\diagnose_layers.bat

title Windows Network Recovery Toolkit - Diagnose Layers
cd /d "%~dp0.."
python -m failure_system.layer_decision
set "CODE=%ERRORLEVEL%"
echo.
if "%CODE%"=="0" (
  echo Layer diagnosis completed.
  echo Audit: logs\network_layer_audit.jsonl
  echo Report: reports\network_layer_diagnosis_*.md
) else (
  echo Layer diagnosis failed with code %CODE%.
)
exit /b %CODE%

