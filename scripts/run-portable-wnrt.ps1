# Portable WNRT launcher — installs wheel from dist/ and forwards CLI args.
#
# Purpose:
#   Run windows_network_toolkit from a built wheel without editable install.
#
# Prerequisites:
#   python -m build --wheel  (creates dist/*.whl)
#
# Privileges:
#   User-level pip install (--user). Some CLI subcommands require Administrator
#   on Windows — this script does not elevate.
#
# Side effects:
#   pip install --user --force-reinstall on the wheel each invocation.
#   Does NOT install Windows services or enable auto-start.
#
# Safety:
#   Forwards all remaining args to `python -m windows_network_toolkit` unchanged.
#   Destructive subcommands still require their own typed confirmation flags.
#
# Example:
#   .\scripts\run-portable-wnrt.ps1 version
#   .\scripts\run-portable-wnrt.ps1 proxy-status --fixture examples/evidence/DEAD_PROXY_CONFIG.json
#
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
