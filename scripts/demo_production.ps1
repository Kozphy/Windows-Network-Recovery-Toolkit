# Production-shaped 5-minute demo — fixture-based, preview-only remediation.
# Usage: .\scripts\demo_production.ps1
# Optional: start API with $env:START_API=1 (requires uvicorn).

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot
$env:PYTHONPATH = $RepoRoot
$env:PLATFORM_SAFE_MODE = "1"

Write-Host "=== Endpoint Reliability Platform — production demo (read-only) ===" -ForegroundColor Cyan
Write-Host "Safety: fixtures only; observation != proof; no autonomous destructive remediation." -ForegroundColor DarkGray
Write-Host ""

function Invoke-DemoStep($Name, $Cmd) {
    Write-Host ("--- " + $Name) -ForegroundColor Yellow
    & @Cmd
    if ($LASTEXITCODE -ne 0) { throw "Step failed: $Name (exit $LASTEXITCODE)" }
    Write-Host ""
}

Invoke-DemoStep "Demo scenario — healthy (JSON + Markdown)" @(
    "python", "-m", "src", "demo-scenario", "healthy", "--format", "both"
)
Invoke-DemoStep "Demo scenario — proxy drift (correlated only)" @(
    "python", "-m", "src", "demo-scenario", "proxy-drift", "--format", "both"
)
Invoke-DemoStep "Demo scenario — final causation" @(
    "python", "-m", "src", "demo-scenario", "final-causation", "--format", "both"
)
Invoke-DemoStep "Seed fleet simulation (25 endpoints)" @(
    "python", "-m", "src", "fleet-simulate", "--scenario", "proxy-drift", "--endpoints", "25"
)
Invoke-DemoStep "Proxy drift timeline" @(
    "python", "-m", "src", "proxy-timeline",
    "--fixture", "tests/fixtures/proxy_incidents/unknown_node_powershell_proxy.json",
    "--format", "markdown"
)
Invoke-DemoStep "Final causation (fixture)" @(
    "python", "-m", "src", "proxy-causation",
    "--fixture", "tests/fixtures/proxy_causation/scenario1_proven_writer_port_owner",
    "--format", "markdown"
)
Invoke-DemoStep "Process classification + policy (YAML)" @(
    "python", "-m", "src", "proxy-policy",
    "--fixture", "tests/fixtures/proxy_incidents/suspicious_powershell_temp_proxy.json",
    "--policy", "config/policies/default.yaml",
    "--format", "json"
)
Invoke-DemoStep "Evidence tree report" @(
    "python", "-m", "src", "proxy-report",
    "--fixture", "tests/fixtures/proxy_incidents/unknown_node_powershell_proxy.json",
    "--format", "markdown"
)
Invoke-DemoStep "Incident review (case study 001)" @(
    "python", "-m", "src", "incident-review",
    "--incident-id", "001_proxy_drift_cursor_node",
    "--format", "markdown"
)
Invoke-DemoStep "Fleet report" @("python", "-m", "src", "fleet-report", "--format", "markdown")
Invoke-DemoStep "Policy validate (strict enterprise)" @(
    "python", "-m", "src", "policy-validate", "config/policies/strict_enterprise.yaml"
)
Invoke-DemoStep "Production upgrade tests" @(
    "python", "-m", "pytest", "-q",
    "tests/test_incident_review_generator.py",
    "tests/test_slo_metrics.py",
    "tests/test_fleet_simulation.py",
    "tests/test_policy_as_code.py",
    "tests/test_demo_production_contract.py",
    "tests/test_fixture_regression_demo.py",
    "tests/test_demo_replay_pipeline.py"
)

if ($env:START_API -eq "1") {
    Write-Host "--- Starting API (PLATFORM_FIXTURE_MODE=1) on :8000" -ForegroundColor Yellow
    $env:PLATFORM_FIXTURE_MODE = "1"
    python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
}

Write-Host "=== Demo complete ===" -ForegroundColor Green
Write-Host "Dashboard: set NEXT_PUBLIC_PLATFORM_API=http://127.0.0.1:8000 and open /platform/slo" -ForegroundColor DarkGray
