# Reproduce research benchmarks (fixture-safe, read-only)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$env:PYTHONPATH = (Get-Location).Path

Write-Host "==> Installing editable package (dev extras) if needed..."
python -m pip install -e ".[dev]" -q

Write-Host "==> Running research pipeline (classification + interactions + docs)..."
python -m experiments.run_all @args

Write-Host "==> Running research smoke tests..."
pytest -q tests/experiments tests/research/interactions

Write-Host "==> Done. See experiments/results/latest/ and docs/research/"
