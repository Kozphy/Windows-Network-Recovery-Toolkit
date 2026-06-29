# Portable WNRT launcher — does not install services or enable auto-start.
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $Root "..")
$Wheel = Get-ChildItem -Path (Join-Path $RepoRoot "dist\*.whl") -ErrorAction SilentlyContinue | Select-Object -First 1

if (-not $Wheel) {
    Write-Error "No wheel in dist/. Run: python -m build --wheel"
}

python -m pip install --user --force-reinstall $Wheel.FullName | Out-Null
python -m windows_network_toolkit @CliArgs
