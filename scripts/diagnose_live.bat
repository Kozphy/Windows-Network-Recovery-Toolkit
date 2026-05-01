@echo off
setlocal EnableExtensions

REM Runs python -m src diagnose-live — live snapshot scoring + artefact writes.
REM Privileges: user (subprocess probes use standard tools already on PATH).
REM Outputs: refreshes reports\last_diagnosis_live.json plus JSONL audits per CLI mapping.

pushd "%~dp0.." >nul 2>&1

echo Running diagnose-live...
python -m src diagnose-live
pause

popd >nul
exit /b 0
