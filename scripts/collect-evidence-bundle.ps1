#Requires -Version 5.1
param(
    [string]$OutDir = "",
    [int]$DurationSeconds = 30,
    [int]$IntervalSeconds = 2
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}

Set-Location -LiteralPath $RepoRoot
$env:PYTHONPATH = $RepoRoot

$args = @("-m", "src", "collect-evidence-bundle", "--duration", "$DurationSeconds", "--interval", "$IntervalSeconds")
if ($OutDir) {
    $args += @("--out-dir", $OutDir)
}
& $Python @args
exit $LASTEXITCODE
