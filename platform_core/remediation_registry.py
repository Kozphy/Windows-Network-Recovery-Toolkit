"""Authorize and describe safe remediation paths for the Endpoint Reliability Platform.

**Responsibility**
  Hold the **canonical allowlist** of named remediation actions: risk tier,
  typed-confirmation phrases, optional ``scripts/*.bat`` basenames,
  deployment surface rules, and whether the FastAPI layer may spawn a subprocess.

**System placement**
  Sits **before** subprocess execution (**``policy``** reads summaries here) and
  alongside **``remediation.allowlisted_script``** (basename checks derive from this
  registry):

  ``FailureEvent + operator intent`` → **registry lookup** → ``policy.evaluate_action`` /
  ``policy.build_preview`` → ``backend.platform_routes`` execute path.

**Key invariants**
  - **`forbidden`** and **`high`** entries do not authorize API-bound repair
    (**``policy``** / routes enforce additional denial).
  - **Alias map** preserves backward-compatible action strings (**``reset_firewall``**, etc.).
  - Frozen **``RemediationActionDef``** rows prevent accidental mutation at runtime.

**Consumers**
  ``platform_core.policy``, ``platform_core.remediation`` (basename allowlists),
  and ``backend.platform_routes`` (execute gating).

**Engineering Notes**
  - YAML/JSON loaders were intentionally avoided — a code-defined registry trades
    hot-reload for **reviewable PRs**, **type-checked literals**, and **zero parse** startup cost.
  - **``manual_only=True``** + **``api_execute_allowed=False``** pairs express “explain in UI /
    playbook only,” separate from **`forbidden`** (explicitly abusive patterns).

**Audit Notes**
  - Broadening **`api_execute_allowed`** or shortening confirmation phrases materially
    widens blast radius — **detect** via code review of this file and **`tests/test_*`**.
  - **Recovery**: revert commit; no runtime migration is required beyond redeploy.

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RiskName = Literal["read_only", "low", "medium", "high", "forbidden"]
Surface = Literal["api", "cli", "dashboard"]


@dataclass(frozen=True)
class RemediationActionDef:
    """Static row describing one operator-facing remediation primitive.

    **Responsibility**
      Encode safety metadata so **policy**, **audit**, and **preview UIs** can reason
      about blast radius **without** reading batch file bodies.

    **Key attributes**
      action_name: Stable string key surfaced in previews and executions.
      script_path: Optional ``scripts/<basename>.bat``; ``None`` for read-only or manual-only flows.
      risk_level: Coarse **`read_only`** → **`forbidden`** tier used with org policy overlays.
      allowed_surfaces: Where preview/execute intents may originate (empty forbids **all** surfaces).
      api_execute_allowed: Whether **`POST /platform/remediation/execute`** may run a subprocess (still gated elsewhere).
      requires_confirmation: Whether operator policy mandates human acknowledgment (paired with **`confirmation_phrase`**).
      confirmation_phrase: Exact typed token for phrase matching (**empty** ⇒ no typed gate).
      dry_run_allowed: Whether dry-run executions are sensible for this action (portfolio default **True** except forbidden).
      manual_only: If **True**, real repair is **never** delegated to API subprocess — operator runbook path.
      rollback_plan: Redacted, human-readable narrative stored on **``RemediationPreview``** rows.

    **Interaction**
      Produced by **``get_remediation_action``**, consumed across **policy** previews and
      **`backend`** execution validation.

    **Engineering Notes**
      ``frozen=True`` rejects silent field mutation — update via new instances / registry edits only.

    **Audit Notes**
      Drift between **``script_path``** and filesystem contents surfaces as **executor 400**
      (**``script not allowlisted``**) — verify ``scripts/*.bat`` exists after registry edits.

    Attributes:
      action_name: Registry key identical to externally supplied action identifiers (post-alias).
      script_path: Basename under repository ``scripts/`` when subprocess repair is modeled.
      risk_level: Platform risk tier fused with **`RemediationPolicy.allowed_risk_levels`**.
      allowed_surfaces: Tuple of **`api`**, **`cli`**, **`dashboard`** allowances.
      api_execute_allowed: FastAPI-managed repair eligibility flag.
      requires_confirmation: Mirrors org-level **`requires_confirmation`** for medium/low automation.
      confirmation_phrase: Token required when phrase gating applies.
      dry_run_allowed: Permits no-op execution records when **True**.
      manual_only: Disables delegated repair despite medium/low tiering.
      rollback_plan: Free-text operational guidance (**not executed**).

    Raises:
      None directly from instantiation (dataclass validation is structural only).

    """

    action_name: str
    script_path: str | None
    risk_level: RiskName
    allowed_surfaces: tuple[Surface, ...]
    api_execute_allowed: bool
    requires_confirmation: bool
    confirmation_phrase: str
    dry_run_allowed: bool
    manual_only: bool
    rollback_plan: str


def _all_surfaces() -> tuple[Surface, ...]:
    """Return the triple of supported request surfaces used by benign registry rows.

    **Decision intent**
      Centralize repetition so widening **CLI** vs **dashboard** coverage is a single edit.

    **Output guarantees**
      Always **``("api","cli","dashboard")``** — deterministic, allocation-free tuples are reused.

    **Side effects:** None.

    **Idempotency:** Every call yields an equal tuple value.

    Returns:
        Tuple of literals naming supported caller surfaces.

    Raises:
        None.

    """

    return ("api", "cli", "dashboard")


# Canonical registry keys match stable API / CLI action strings.
_REMEDIATION_REGISTRY: dict[str, RemediationActionDef] = {
    "inspect_proxy": RemediationActionDef(
        action_name="inspect_proxy",
        script_path=None,
        risk_level="read_only",
        allowed_surfaces=_all_surfaces(),
        api_execute_allowed=False,
        requires_confirmation=False,
        confirmation_phrase="",
        dry_run_allowed=True,
        manual_only=False,
        rollback_plan="N/A (read-only inspection).",
    ),
    "preview_dns_flush": RemediationActionDef(
        action_name="preview_dns_flush",
        script_path=None,
        risk_level="read_only",
        allowed_surfaces=_all_surfaces(),
        api_execute_allowed=False,
        requires_confirmation=False,
        confirmation_phrase="",
        dry_run_allowed=True,
        manual_only=False,
        rollback_plan="N/A (preview only).",
    ),
    "export_report": RemediationActionDef(
        action_name="export_report",
        script_path=None,
        risk_level="read_only",
        allowed_surfaces=_all_surfaces(),
        api_execute_allowed=False,
        requires_confirmation=False,
        confirmation_phrase="",
        dry_run_allowed=True,
        manual_only=False,
        rollback_plan="Re-run collector; reports are non-destructive.",
    ),
    "reset_dns": RemediationActionDef(
        action_name="reset_dns",
        script_path="reset_dns.bat",
        risk_level="medium",
        allowed_surfaces=_all_surfaces(),
        api_execute_allowed=True,
        requires_confirmation=True,
        confirmation_phrase="RUN_DNS_RESET",
        dry_run_allowed=True,
        manual_only=False,
        rollback_plan="Restore prior DNS servers from backup notes if applicable.",
    ),
    "reset_proxy": RemediationActionDef(
        action_name="reset_proxy",
        script_path="reset_proxy.bat",
        risk_level="medium",
        allowed_surfaces=_all_surfaces(),
        api_execute_allowed=True,
        requires_confirmation=True,
        confirmation_phrase="RUN_PROXY_RESET",
        dry_run_allowed=True,
        manual_only=False,
        rollback_plan="Reconfigure WinHTTP/user proxy per policy documentation.",
    ),
    "winsock_reset": RemediationActionDef(
        action_name="winsock_reset",
        script_path=None,
        risk_level="medium",
        allowed_surfaces=_all_surfaces(),
        api_execute_allowed=False,
        requires_confirmation=True,
        confirmation_phrase="RUN_WINSOCK_RESET",
        dry_run_allowed=True,
        manual_only=True,
        rollback_plan="Requires reboot planning; follow enterprise change windows.",
    ),
    "tcpip_reset": RemediationActionDef(
        action_name="tcpip_reset",
        script_path=None,
        risk_level="medium",
        allowed_surfaces=_all_surfaces(),
        api_execute_allowed=False,
        requires_confirmation=True,
        confirmation_phrase="RUN_TCPIP_RESET",
        dry_run_allowed=True,
        manual_only=True,
        rollback_plan="Document interface settings before stack reset.",
    ),
    "firewall_reset_manual_only": RemediationActionDef(
        action_name="firewall_reset_manual_only",
        script_path="reset_firewall.bat",
        risk_level="high",
        allowed_surfaces=_all_surfaces(),
        api_execute_allowed=False,
        requires_confirmation=True,
        confirmation_phrase="RUN_FIREWALL_RESET",
        dry_run_allowed=True,
        manual_only=True,
        rollback_plan="Manual restore of firewall profiles from backup or GPO.",
    ),
    "arbitrary_command_forbidden": RemediationActionDef(
        action_name="arbitrary_command_forbidden",
        script_path=None,
        risk_level="forbidden",
        allowed_surfaces=(),
        api_execute_allowed=False,
        requires_confirmation=False,
        confirmation_phrase="",
        dry_run_allowed=False,
        manual_only=False,
        rollback_plan="Not applicable.",
    ),
    "adapter_disable_forbidden": RemediationActionDef(
        action_name="adapter_disable_forbidden",
        script_path=None,
        risk_level="forbidden",
        allowed_surfaces=(),
        api_execute_allowed=False,
        requires_confirmation=False,
        confirmation_phrase="",
        dry_run_allowed=False,
        manual_only=False,
        rollback_plan="Not applicable.",
    ),
}


# Legacy / CLI aliases → canonical registry keys (backward compatibility).
_ACTION_ALIASES: dict[str, str] = {
    "reset_winsock": "winsock_reset",
    "reset_tcpip": "tcpip_reset",
    "reset_firewall": "firewall_reset_manual_only",
    "arbitrary_command": "arbitrary_command_forbidden",
    "arbitrary_command_forbidden": "arbitrary_command_forbidden",
}


def canonical_action_name(action_name: str) -> str:
    """Map historically stable alias strings onto canonical registry keys.

    **What it does**
      Normalizes externally supplied **`action_name`** values (CLI strings, previews,
      tests) so lookups hit a **single authoritative** ``_REMEDIATION_REGISTRY`` row.

    **Decision intent**
      Prevents duplication of remediation rows when renaming keys between releases.

    **Input data assumptions**
      ``action_name`` is trimmed by callers; stray whitespace should be stripped upstream.

    **Output guarantees**
      Returns either the unchanged canonical key **or** the alias target that exists in
      **``_REMEDIATION_REGISTRY``** once resolved via **`get_remediation_action`**.

    **Side effects:** None.

    **Idempotency:** ``canonical_action_name(canonical_action_name(x))`` == ``canonical_action_name(x)`` for aliases.

    Args:
        action_name: Raw remediation label from CLI/API/policy.

    Returns:
        Registry key suitable for **`_REMEDIATION_REGISTRY`** lookup (**may be absent**).

    Raises:
        None.

    Example:
        >>> canonical_action_name("reset_firewall") == "firewall_reset_manual_only"
        True
    """

    return _ACTION_ALIASES.get(action_name, action_name)


def get_remediation_action(action_name: str) -> RemediationActionDef | None:
    """Look up **`RemediationActionDef`** after resolving legacy aliases.

    **What it does**
      Answers “what structured safety metadata applies to **`action_name`**?” for previews,
      policy evaluation, and execute-time allowlisting.

    **Constraints / limitations**
      Unknown identifiers return **``None``** — callers (**``policy``**) treat that as **`unknown_action`**.

    **Schema expectations**
      ``action_name`` is a lowercase identifier string (**ASCII** expectation; not enforced here).

    **Side effects:** None.

    **Idempotency:** Read-only memo-free — repeated calls identical for identical registry build.

    Args:
        action_name: External remediation key (**may be alias**).

    Returns:
        Frozen definition matching the canonical registry entry, **or** **`None`** if unknown.

    Raises:
        None.

    """

    key = canonical_action_name(action_name)
    return _REMEDIATION_REGISTRY.get(key)


def list_script_basenames() -> frozenset[str]:
    """Collect unique ``scripts/*.bat`` basenames referenced for automated repair primitives.

    **What it does**
      Derives subprocess allowlisting material (**``frozenset``**) from registry rows carrying
      **non-null ``script_path``**.

    **Output guarantees**
      Deterministic set membership for a given deployed registry body; alphabetical order **not implied**.

    **Performance**
      Linear in registry cardinality (~10 rows portfolio scale — trivial).

    **Side effects:** None.

    **Idempotency:** Yes.

    Returns:
        Immutable set of basename strings (filenames **only**, no directories).

    Raises:
        None.

    """

    out: set[str] = set()
    for d in _REMEDIATION_REGISTRY.values():
        if d.script_path:
            out.add(d.script_path)
    return frozenset(out)


def to_policy_meta(defn: RemediationActionDef) -> dict[str, object]:
    """Project a **`RemediationActionDef`** into legacy ``ACTION_REGISTRY`` dictionaries.

    **What it does**
      Supplies compatibility fields consumed by transitional helpers that still iterate
      string-keyed blobs (**``risk``**, **``script``**, **``phrase``**).

    **Schema expectations**
      Output keys (**``risk``**, **``script``**, **``phrase``**, etc.) mirror historical
      **`ACTION_REGISTRY`** consumers in **`platform_core.policy`** tests/API glue.

    **Side effects:** None.

    **Idempotency:** Yes for frozen input **``defn``**.

    Args:
        defn: Source frozen remediation row.

    Returns:
        Shallow **`dict`** of JSON-serializable primitives (**``tuple``** surfaces retained).

    Raises:
        None.

    """

    return {
        "risk": defn.risk_level,
        "script": defn.script_path,
        "phrase": defn.confirmation_phrase,
        "allowed_surfaces": defn.allowed_surfaces,
        "api_execute_allowed": defn.api_execute_allowed,
        "manual_only": defn.manual_only,
    }


def build_action_registry_legacy_dict() -> dict[str, dict[str, object]]:
    """Materialize flattened alias-expanded maps for transitional policy imports.

    **What it does**
      Builds **`dict[actionAlias, legacyMeta]`**, duplicating **`to_policy_meta`** rows for
      every canonical key **plus** every entry in **`_ACTION_ALIASES`**.

    **Decision intent**
      Keeps **`ACTION_REGISTRY`** assignment in **`policy`** a single import-friendly constant
      while **preventing divergence** between canonical and aliased lookups.

    **Output guarantees**
      Keys include both canonical (**``reset_proxy``**) and alias (**``reset_firewall``**) forms;
      collisions **should not occur** unless alias definitions regress in review.

    **Side effects:** None (**new dict** allocated each call — acceptable at import/test time).

    **Idempotency:** Deterministic across process lifetime until module reload.

    Returns:
        Legacy-compatible mapping suitable for **`policy.ACTION_REGISTRY`**.

    Raises:
        None.

    **Engineering Notes**
      Prefer **`get_remediation_action`** in new logic — this shim exists for readability of
      old tests/dashboard assumptions.

    **Audit Notes**
      Divergence between shim output and **`_REMEDIATION_REGISTRY`** indicates refactor bug —
      **`pytest`** should fail if rows desync.

    """

    flat: dict[str, dict[str, object]] = {}
    for key, defn in _REMEDIATION_REGISTRY.items():
        flat[key] = to_policy_meta(defn)
    for alias, target in _ACTION_ALIASES.items():
        base = _REMEDIATION_REGISTRY.get(target)
        if base:
            flat[alias] = to_policy_meta(base)
    return flat
