# Browser evidence model

Typed models live in `windows_network_toolkit/diagnostics/browser_profile/models.py`.

| Model | Role |
|-------|------|
| `RawNetworkBaseline` | OS DNS/TCP/TLS/HTTP + proxy env (no browser cookies) |
| `BrowserProfileEvidence` | Profile id/name/path/open hint |
| `BrowserSiteStateEvidence` | Cookie **count/meta**, SW/cache flags |
| `BrowserExtensionEvidence` | Id/name/enabled/permissions (not malware) |
| `BrowserPolicyEvidence` | Managed policy key summaries |
| `BrowserNetworkPreferenceEvidence` | Secure DNS / proxy prefs |
| `HarRequestEvidence` / `HarComparisonEvidence` | Redacted HAR differential |
| `BrowserRepairPreview` | Gated remediation preview |
| `BrowserDifferentialResult` | Operator JSON + text report |

Every evidence item carries `EvidenceMeta`: source, timestamp, method, reliability tier, redaction status, error, admin flag.

## Epistemic levels

`observation` → `hypothesis` → `probable_cause` → `proven_cause`

Classifications never claim “Windows is completely safe” — only what was tested.
