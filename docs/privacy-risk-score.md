# Privacy Risk Score

Transparent ordinal score for home/SOHO LAN privacy governance.

## Formula

```
Privacy Risk Score =
    Discovery Breadth          (0–20)
  + Probe Frequency            (0–20)
  + Unknown Vendor Weight      (0–15)
  + External Domain Risk       (0–25)   # router DNS only
  + Recurrence                 (0–20)
  - Evidence Confidence Discount (0–30)
```

Clamped to **0–100**.

## Bands

| Band | Range |
|------|-------|
| LOW | &lt; 35 |
| MEDIUM | 35–69 |
| HIGH | ≥ 70 |

## Output fields

- `numeric_score`, `risk_level`
- `evidence_tier` (T0–T2 for LAN contexts)
- `components` — per-factor score and rationale
- `explanation`, `limitations[]`
- `evidence_sources_present[]`
- `human_review_recommended` when HIGH or recon classifications

## CLI

```powershell
python -m windows_network_toolkit lan-risk-score --fixture examples/lan/executive_bundle.json
```

## Important

Score is **governance input**, not probability of compromise or proof of surveillance.
