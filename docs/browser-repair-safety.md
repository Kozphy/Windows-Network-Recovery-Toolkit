# Browser repair safety

## Defaults

- `browser-profile repair-preview` is **PREVIEW only**.
- Prefer **site-scoped** cleanup over resetting the whole profile.
- Export non-secret site-state metadata before any apply.

## Confirm token

```text
BROWSER_SITE_REPAIR_APPLY
```

```powershell
python -m windows_network_toolkit browser-profile repair-apply <preview-id> --confirm BROWSER_SITE_REPAIR_APPLY
```

Automated Chromium DB mutation may remain **blocked** (`apply_not_implemented_use_browser_ui`) — use Edge/Chrome **Site settings → Clear data** for the domain when apply is not implemented.

## Domain guard

Actions must target the diagnosed domain only. Clearing `linkedin.com` when diagnosing `104.com.tw` is forbidden by matching helpers.

## Never do during diagnosis

- Delete cookies automatically
- Disable extensions automatically
- Kill browser processes
- Print cookie values

## Audit

Events append to `.audit/browser-diff.jsonl`: collect, compare, classify, preview, apply/block.
