# Interaction Effects — Research Report

> Machine-generated from `experiments/results/interaction_*.` artifacts. Do not hand-edit metric values.

## Purpose

Phase 1 tests whether combined fault factors produce outcomes beyond
the sum of individual main effects on controlled factorial fixtures.

- **Run timestamp:** 2026-09-02T10:45:53.663613+00:00
- **Git SHA:** `e09566bbffa7cbdc2e3d5d173e10493d0f0b52ee`
- **Cases:** 72
- **Experiments:** 6

## Model

```text
Y = β0 + β1·X1 + β2·X2 + β3·(X1 × X2)
```

Interaction contrast reported as: **Y11 − Y10 − Y01 + Y00** (cell means).

## Results

### proxy_x_firewall

**Factors:** proxy_fault × firewall_fault

Dead/misconfigured localhost proxy × outbound firewall filtering.

| Outcome | Main X1 | Main X2 | Interaction | n | 95% CI |
|---------|---------|---------|-------------|---|--------|
| y_severity | 0.4500 | 0.4000 | -0.0000 | 12 | -0.850–0.450 |
| y_failure | 0.5000 | 0.5000 | -1.0000 | 12 | -2.000–0.000 |
| y_platform_severity | 0.4040 | 0.3050 | -0.6100 | 12 | -1.574–0.354 |
| y_platform_failure | 0.5000 | 0.5000 | -1.0000 | 12 | -2.000–0.000 |

### proxy_x_tls

**Factors:** proxy_fault × tls_path_fault

Proxy misconfiguration × TLS/path certificate mismatch.

| Outcome | Main X1 | Main X2 | Interaction | n | 95% CI |
|---------|---------|---------|-------------|---|--------|
| y_severity | 0.5350 | 0.3850 | 0.0700 | 12 | -0.850–0.570 |
| y_failure | 0.5000 | 0.5000 | -1.0000 | 12 | -2.000–0.000 |
| y_platform_severity | 0.4040 | 0.3050 | -0.6100 | 12 | -1.574–0.354 |
| y_platform_failure | 0.5000 | 0.5000 | -1.0000 | 12 | -2.000–0.000 |

### wininet_x_winhttp

**Factors:** wininet_proxy_enabled × winhttp_direct_access

WinINET proxy state × WinHTTP direct-access stack mismatch.

| Outcome | Main X1 | Main X2 | Interaction | n | 95% CI |
|---------|---------|---------|-------------|---|--------|
| y_severity | 0.4250 | 0.3250 | 0.4500 | 12 | -0.300–0.650 |
| y_failure | 0.5000 | 0.5000 | 1.0000 | 12 | 0.000–1.000 |
| y_platform_severity | 0.2945 | 0.3245 | 0.6490 | 12 | -0.225–0.904 |
| y_platform_failure | 0.5000 | 0.5000 | 1.0000 | 12 | 0.000–1.000 |

### proxy_x_listener

**Factors:** proxy_enabled × listener_present

WinINET proxy enabled × localhost listener attribution present.

| Outcome | Main X1 | Main X2 | Interaction | n | 95% CI |
|---------|---------|---------|-------------|---|--------|
| y_severity | 0.3750 | -0.1250 | -0.3500 | 12 | -0.600–0.200 |
| y_failure | 0.5000 | -0.5000 | -1.0000 | 12 | -1.000–0.000 |
| y_platform_severity | 0.3395 | -0.3695 | -0.7390 | 12 | -0.994–0.225 |
| y_platform_failure | 0.5000 | -0.5000 | -1.0000 | 12 | -1.000–0.000 |

### dns_x_proxy

**Factors:** dns_fault × proxy_fault

DNS resolution failure × localhost proxy fault.

| Outcome | Main X1 | Main X2 | Interaction | n | 95% CI |
|---------|---------|---------|-------------|---|--------|
| y_severity | 0.4100 | 0.4700 | -0.0200 | 12 | -0.900–0.460 |
| y_failure | 0.5000 | 0.5000 | -1.0000 | 12 | -2.000–0.000 |
| y_platform_severity | 0.3050 | 0.4040 | -0.6100 | 12 | -1.574–0.354 |
| y_platform_failure | 0.5000 | 0.5000 | -1.0000 | 12 | -2.000–0.000 |

### listener_x_process

**Factors:** listener_present × trusted_process_attribution

Localhost listener present × trusted vs unknown process attribution.

| Outcome | Main X1 | Main X2 | Interaction | n | 95% CI |
|---------|---------|---------|-------------|---|--------|
| y_severity | -0.2500 | -0.1500 | -0.3000 | 12 | -0.850–0.250 |
| y_failure | -0.5000 | -0.5000 | -1.0000 | 12 | -2.000–0.000 |
| y_platform_severity | -0.7540 | 0.0150 | 0.0300 | 12 | -0.934–0.994 |
| y_platform_failure | -1.0000 | 0.0000 | 0.0000 | 12 | -1.000–1.000 |

## Limitations

- Synthetic factorial fixtures only.
- Small sample per experiment (12 cases with 3 replicates/cell).
- Bootstrap CIs are exploratory — not confirmatory significance tests.
- Platform outcomes may diverge from designed ground-truth severity.

## Reproduce

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m research.interactions
# or: make research-interactions
```
