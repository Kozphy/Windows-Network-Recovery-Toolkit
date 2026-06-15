async function fetchJson(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(`${url} -> ${r.status}`);
  return r.json();
}

function setPanel(id, data, emptyMsg) {
  const section = document.getElementById(id);
  if (!section) return;
  const target = section.querySelector(".panel") || section;
  if (!data || (Array.isArray(data) && data.length === 0)) {
    target.textContent = emptyMsg || "No data.";
    target.classList.add("empty");
    return;
  }
  target.classList.remove("empty");
  target.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

const FLEET_FIXTURE = "tests/fixtures/fleet/fleet_100_endpoints.jsonl";

async function loadFleetSummary() {
  try {
    const s = await fetchJson(`/platform/fleet/summary?fixture=${encodeURIComponent(FLEET_FIXTURE)}`);
    setPanel("fleet", s);
    setPanel("classifications", s.classifications || {}, "No classifications.");
    setPanel("tiers", s.evidence_tiers || {}, "No tiers.");
    setPanel("policies", s.policy_decisions || {}, "No policy rows.");
    setPanel("timeline", s.latest_timeline || [], "No timeline.");
    setPanel("remediation", s.remediation_preview_status || {}, "No preview status.");
    setPanel("audit-chain", s.audit_chain || {}, "No chain status.");
  } catch (e) {
    setPanel("fleet", { error: String(e) });
  }
}

async function loadCaseStudies() {
  try {
    const cs = await fetchJson("/platform/demo/case-studies");
    setPanel("case-studies", cs);
  } catch (e) {
    setPanel("case-studies", { error: String(e) });
  }
}

async function loadHealth() {
  try {
    const h = await fetchJson("/health");
    setPanel("health", h);
  } catch (e) {
    setPanel("health", { error: String(e) });
  }
}

async function loadAudit() {
  try {
    const a = await fetchJson("/platform/audit/logs?limit=10");
    setPanel("audit", a.logs || [], "No audit rows yet.");
  } catch (e) {
    setPanel("audit", { note: "Audit tail optional in fixture demo mode." });
  }
}

async function runFleetReplay() {
  const out = document.getElementById("replay-out");
  out.textContent = "Replaying fleet fixture…";
  try {
    const body = await fetchJson("/platform/fleet/replay", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fixture_path: FLEET_FIXTURE, dry_run: true }),
    });
    out.textContent = JSON.stringify(body, null, 2);
    out.classList.remove("empty");
  } catch (e) {
    out.textContent = String(e);
  }
}

async function runCaseReplay() {
  const out = document.getElementById("replay-out");
  out.textContent = "Loading case study 1 fixture…";
  try {
    const cs = await fetchJson("/platform/demo/case-studies");
    const first = (cs.items || [])[0];
    out.textContent = JSON.stringify(first, null, 2);
    out.classList.remove("empty");
  } catch (e) {
    out.textContent = String(e);
  }
}

async function loadGovernanceRisk() {
  try {
    const g = await fetchJson(
      "/platform/risk-analytics/governance-dashboard?fixture=tests/fixtures/case_studies/case_1_dead_wininet_proxy.json"
    );
    setPanel("governance-risk", g);
  } catch (e) {
    setPanel("governance-risk", { note: "Risk analytics optional", error: String(e) });
  }
}

document.getElementById("btn-fleet-replay").addEventListener("click", runFleetReplay);
document.getElementById("btn-case-replay").addEventListener("click", runCaseReplay);
loadFleetSummary();
loadCaseStudies();
loadHealth();
loadAudit();
loadGovernanceRisk();
