# Run `python -m src` with the project .venv (creates venv + installs deps if needed).
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[WNRT] Creating .venv ..."
    python -m venv (Join-Path $RepoRoot ".venv")
}

& $VenvPython -m pip install -q -r (Join-Path $RepoRoot "requirements.txt")
$env:PYTHONPATH = $RepoRoot
& $VenvPython -m src @CliArgs
exit $LASTEXITCODE
