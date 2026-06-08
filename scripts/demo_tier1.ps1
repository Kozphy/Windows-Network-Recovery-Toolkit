# Tier-1 verified demo — fixture-based, read-only (no registry / firewall / adapter / process mutation).
# Usage: .\scripts\demo_tier1.ps1
# Requires: pip install -e ".[dev]"

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot
$env:PYTHONPATH = $RepoRoot

Write-Host "=== Endpoint Reliability Platform — Tier-1 demo (read-only) ===" -ForegroundColor Cyan
Write-Host "Safety: fixtures only; no live registry writes; no process kill; no firewall reset." -ForegroundColor DarkGray
Write-Host ""

$steps = @(
    @{
        Name = "Fixture diagnosis (legacy v1 scoring)"
        Cmd  = @("python", "-m", "src", "diagnose", "--fixture", "tests/fixtures/features_healthy_signals.json")
    },
    @{
        Name = "Proxy timeline replay (markdown)"
        Cmd  = @(
            "python", "-m", "src", "proxy-timeline",
            "--fixture", "tests/fixtures/proxy_incidents/unknown_node_powershell_proxy.json",
            "--format", "markdown"
        )
    },
    @{
        Name = "Policy decision engine (fixture)"
        Cmd  = @(
            "python", "-m", "src", "proxy-policy",
            "--fixture", "tests/fixtures/proxy_incidents/suspicious_powershell_temp_proxy.json",
            "--format", "json"
        )
    },
    @{
        Name = "Evidence tree report (markdown)"
        Cmd  = @(
            "python", "-m", "src", "proxy-report",
            "--fixture", "tests/fixtures/proxy_incidents/unknown_node_powershell_proxy.json",
            "--format", "markdown"
        )
    },
    @{
        Name = "Public release audit (tracked files)"
        Cmd  = @("python", "tools/public_release_audit.py", "--tracked-only")
    },
    @{
        Name = "Safety contract tests"
        Cmd  = @(
            "python", "-m", "pytest", "-q",
            "tests/test_policy_safety_contract.py",
            "tests/test_api_dry_run_default.py",
            "tests/test_replay_determinism.py",
            "tests/test_audit_contract.py"
        )
    }
)

foreach ($step in $steps) {
    Write-Host ("--- " + $step.Name) -ForegroundColor Yellow
    & $step.Cmd[0] $step.Cmd[1..($step.Cmd.Length - 1)]
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Step failed: $($step.Name) (exit $LASTEXITCODE)"
    }
    Write-Host ""
}

Write-Host "=== Demo complete ===" -ForegroundColor Green
Write-Host "Docker stack (optional): docker compose up --build" -ForegroundColor DarkGray
Write-Host "  health:  http://localhost:8000/platform/health" -ForegroundColor DarkGray
Write-Host "  ready:   http://localhost:8000/platform/ready" -ForegroundColor DarkGray
Write-Host "  metrics: http://localhost:8000/metrics" -ForegroundColor DarkGray
Write-Host "Docs: docs/verified_demo.md" -ForegroundColor DarkGray
