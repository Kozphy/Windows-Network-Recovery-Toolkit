# Portfolio Case Study 2: WinINET / WinHTTP mismatch with business app failure

## Scenario

A line-of-business app using WinHTTP succeeds; Edge and other WinINET consumers fail HTTPS. Network team reports “all green” on ping/DNS.

## Evidence

- WinINET proxy enabled → `127.0.0.1:63489`
- WinHTTP `direct access` / no matching proxy
- Path proof: `wininet_winhttp_comparison` supported; proxied HTTPS probe fails

**Fixture:** `tests/fixtures/case_studies/case_2_wininet_winhttp_mismatch.json`

## Classification

**WININET_WINHTTP_MISMATCH**

## Proof tier

**T2_RUNTIME_CORROBORATION** — stack contrast and path probes align with hypothesis.

## Risk rating

Residual **medium** — inconsistent stacks create split-brain troubleshooting and false security escalations.

## Recommended action

`ALIGN_PROXY_STACK_PREVIEW` — align or disable WinINET proxy after human review; never silent cross-stack mutation.

## Safety boundary

- Inspect both stacks; do not remediate from WinINET-only tools alone
- AI may summarize; AI does not authorize registry changes

## Audit record

Decision record includes `secondary_signals`, forum mapping (`Endpoint reliability / Platform governance`), and mature control **CTRL-EPR-002 PASS**.

## Governance report excerpt

> Applications using different proxy stacks may behave inconsistently. Operational risk: difficult troubleshooting because ping/DNS may appear healthy.

## Interview talking point

“This is a **platform governance** problem: half the endpoint looks healthy because teams test the wrong stack. I document both layers and proof-tier the failure path before any remediation narrative.”
