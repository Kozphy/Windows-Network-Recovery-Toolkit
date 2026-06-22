# RBAC model — `/v1` API

Demo token authentication via headers:

- `X-Api-Token` — must match `TRISK_API_TOKEN` (default `dev-trisk-token` in compose)
- `X-Api-Role` — one of: `admin`, `operator`, `risk_reviewer`, `auditor_readonly`, `demo_viewer`

## Permission matrix

| Role | Ingest evidence | Review incidents | Read incidents | Audit / executive report |
|------|-----------------|------------------|----------------|--------------------------|
| operator | yes | no | yes | no |
| risk_reviewer | no | yes | yes | yes |
| auditor_readonly | no | no | yes | yes |
| demo_viewer | no | no | yes (demo) | yes |
| admin | yes | yes | yes | yes |

## Hard safety (all roles)

- No `/v1` remediation or registry mutation endpoints
- Policy registry still blocks process kill, firewall reset, adapter disable
- AI cannot approve review actions (`human_review` module)

## Enterprise gap

- No Entra ID / OAuth2 / mTLS — document as production requirement
- `/platform/*` routes continue using `X-Operator-*` headers via [platform_core/rbac.py](../platform_core/rbac.py)
