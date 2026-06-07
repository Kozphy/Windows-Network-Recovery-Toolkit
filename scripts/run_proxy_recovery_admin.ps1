[CmdletBinding()]
param(
    [double]$SoakMinutes = 15
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
    $argList = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $PSCommandPath
    )
    if ($SoakMinutes -ne 15) {
        $argList += "-SoakMinutes", $SoakMinutes
    }
    Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $argList | Out-Null
    exit $LASTEXITCODE
}

Set-Location $RepoRoot

function Invoke-WnrtProxy {
    param(
        [Parameter(Mandatory = $true)][string[]]$Args
    )
    & python -m src @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed (exit $LASTEXITCODE): python -m src $($Args -join ' ')"
    }
}

Write-Host "[WNRT] Proxy recovery (Administrator) — repo: $RepoRoot"

Write-Host "[WNRT] Step 1/4: proxy-owner (attribution)"
Invoke-WnrtProxy -Args @("proxy-owner")

Write-Host "[WNRT] Step 2/4: proxy-stop-reverter"
Invoke-WnrtProxy -Args @(
    "proxy-stop-reverter",
    "--dry-run", "false",
    "--confirm", "STOP_PROXY_REVERTER"
)

Write-Host "[WNRT] Step 3/4: proxy-stop-listener"
Invoke-WnrtProxy -Args @(
    "proxy-stop-listener",
    "--dry-run", "false",
    "--confirm", "STOP_PROXY_LISTENER"
)

Write-Host "[WNRT] Step 4/4: proxy-disable + soak ($SoakMinutes min)"
Invoke-WnrtProxy -Args @(
    "proxy-disable",
    "--dry-run", "false",
    "--confirm", "DISABLE_WININET_PROXY",
    "--soak-minutes", "$SoakMinutes"
)

Write-Host "[WNRT] Proxy recovery completed — soak STABLE."
exit 0
