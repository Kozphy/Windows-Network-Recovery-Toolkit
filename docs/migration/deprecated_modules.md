# Deprecated Modules

## `src/platform/*` (multi-domain MDP)

**Status:** Retained for multi-domain fixtures; Windows path uses `src/platform_core`.

**Shim:** `src/platform/compat/decision_platform_shim.py` maps legacy MDP types.

**Removal:** When all MDP fixtures use `run_decision_pipeline` from `src.platform_core`.

## `src/platform_core/` (canonical)

**Status:** **Canonical** decision engine. Use for new integrations.

**Entry:** `run_decision_pipeline`, `/v1/*` API, `python -m toolkit replay-certify`.

## Root `platform_core/`

**Status:** Legacy endpoint reliability package (still used by backend).

**Shim:** `platform_core/canonical_bridge.py` re-exports evidence tier guards from `src.platform_core`.

**Removal:** When all callers migrate audit + policy to `src.platform_core`.

## `platform_core/decision_platform/`

**Status:** Deprecated docstring; fixture-based multi-domain demos.

**Removal:** After `src/platform_core` pipeline covers Windows endpoint path end-to-end.

## `backend/decision_intelligence/`

**Status:** Retained API surface; migrate callers to canonical routes.

**Removal:** When `/v1/decisions` canonical routes reach parity.

## Root `proxy_guard/`

**Status:** Legacy CLI; prefer `src/proxy_guard/`.

**Removal:** When no imports reference root package.

## `windows_network_toolkit/decision/`

**Status:** Portfolio facade; delegates to `src.platform_core` where possible.

**Removal:** Never required — thin Windows-facing API layer.
