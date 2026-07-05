# Run pytest with the project .venv (avoids system Python missing sqlmodel).
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[WNRT] Creating .venv ..."
    python -m venv (Join-Path $RepoRoot ".venv")
}

& $VenvPython -m pip install -q -r (Join-Path $RepoRoot "requirements.txt")
& $VenvPython -m pytest @PytestArgs
