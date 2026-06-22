#Requires -Version 5.1
$ErrorActionPreference = 'SilentlyContinue'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}
Set-Location -LiteralPath $RepoRoot
while ($true) {
    & $Python -m windows_network_toolkit proxy-guardian --once | Out-Null
    Start-Sleep -Seconds 300
}
