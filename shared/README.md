# Shared

Cross-service configuration consumed by the **optional SaaS demo stack** (Supabase JWT + billing routes).

---

## Contents

| File | Purpose |
|------|---------|
| `plan_limits.json` | Free / pro / team monthly diagnosis limits for usage metering |

---

## Usage

Read by backend billing/usage code when Stripe and Supabase routes are enabled. **Not used** by the primary `python -m windows_network_toolkit` CLI or offline pytest fixtures.

---

## Safety boundaries

- Changing limits affects demo quota behavior only — does not change Windows endpoint policy gates.
- No secrets belong in this folder.

---

## Audit notes

When investigating quota denials (`429`), compare backend usage tables with `plan_limits.json` at deploy time — limits are not hot-reloaded unless your deployment process copies this file.
