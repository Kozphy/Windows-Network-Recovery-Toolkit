# ADR-016: Prefer-IPv4 blast radius

## Status

Accepted — 2026-08-15

## Context

Broken IPv6 with healthy IPv4 produces YouTube/Edge spin (Happy Eyeballs / QUIC) while WinINET is already direct. Mitigations include prefix policy Prefer-IPv4 (`DisabledComponents=0x20`) and disabling IPv6 on adapters. Wi-Fi-only disable is insufficient when WSL/`vEthernet` still has IPv6.

## Decision

1. Classification (`IPV6_BROKEN_IPV4_OK`, `HAPPY_EYEBALLS_STALL`, `IPV6_PARTIAL_MITIGATION`, `IPV6_BROKEN_MITIGATED`) is **path observation**, not ISP root-cause proof.
2. Live apply requires `PREFER_IPV4_OVER_IPV6` and is dry-run by default.
3. Default apply targets **all Up adapters** plus prefix policy. `--force` re-applies when already mitigated.
4. IPv6-only services may break until revert; that blast radius is documented in `limitations[]`.
5. Prefer-IPv4 does not change an already-running browser; QUIC stall uses a **separate** token (`RESTART_BROWSER_DISABLE_QUIC`).
6. Do not modify WinINET `ProxyEnable` from this control.

## Consequences

- Operator incident card treats path-degraded + proxy-off as **false-clear** risk (`sli_hints: false_clear_rate`).
- `--force` is explicit; mitigated class does not silently re-apply.

## What this does not prove

ISP misconfiguration, router firmware bugs, or that disabling IPv6 is the only correct long-term fix.
