# Case study 003: Remediation not sticky

## Summary

An operator ran an approved proxy-disable preview/execute path, but proxy settings reverted within minutes — likely an active reverter (IDE, sync tool, or malware). Platform records **stickiness failure** and blocks repeat execute without new confirmation.

## Outcome

- **Detection:** post-remediation proxy_change_detected within 5 minutes
- **Signal:** `remediation_stickiness_failed`
- **Policy:** `require_confirmation` for repeat action; escalate review

## Reproduce

```powershell
python -m src incident-review --incident-id 003_remediation_not_sticky --format markdown
```
