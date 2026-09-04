const API_BASE = window.RISK_API_BASE || "http://127.0.0.1:8000";

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

function fmt(value, digits = 3) {
  return typeof value === "number" ? value.toFixed(digits) : "—";
}

async function checkHealth() {
  try {
    const health = await api("/api/health");
    $("apiStatus").textContent = health.metrics_present ? "API: ready" : "API: online, models not trained";
    $("apiStatus").classList.add("ok");
  } catch (error) {
    $("apiStatus").textContent = "API: offline";
    $("apiStatus").classList.add("bad");
  }
}

async function loadModels() {
  try {
    const data = await api("/api/models");
    if (!data.models?.length) return;
    const select = $("model");
    select.innerHTML = "";
    data.models.forEach((name) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      select.appendChild(option);
    });
  } catch (_) {}
}

async function loadMetrics() {
  const body = $("metricsBody");
  try {
    const data = await api("/api/metrics");
    const entries = Object.entries(data.models || {});
    if (!entries.length) {
      body.innerHTML = '<tr><td colspan="7" class="muted">Train models to populate benchmark metrics.</td></tr>';
      return;
    }
    const rank = new Map((data.ranking_by_f1 || []).map((name, index) => [name, index]));
    entries.sort(([a], [b]) => (rank.get(a) ?? 999) - (rank.get(b) ?? 999));
    body.innerHTML = entries.map(([name, m]) => `
      <tr>
        <td><strong>${name}</strong></td>
        <td>${fmt(m.f1)}</td>
        <td>${fmt(m.precision)}</td>
        <td>${fmt(m.recall)}</td>
        <td>${fmt(m.roc_auc)}</td>
        <td>${fmt(m.pr_auc)}</td>
        <td>${fmt(m.brier)}</td>
      </tr>`).join("");
  } catch (error) {
    body.innerHTML = `<tr><td colspan="7" class="muted">Unable to load metrics: ${error.message}</td></tr>`;
  }
}

$("predictionForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    model: $("model").value,
    proxy_mismatch: Number($("proxy_mismatch").value),
    dns_failure_rate: Number($("dns_failure_rate").value),
    tls_error_count: Number($("tls_error_count").value),
    adapter_reset_count: Number($("adapter_reset_count").value),
    winhttp_drift: Number($("winhttp_drift").value),
    network_profile: $("network_profile").value,
  };

  $("predictionMessage").textContent = "Running inference…";
  try {
    const result = await api("/api/predict", { method: "POST", body: JSON.stringify(payload) });
    $("riskScore").textContent = `${result.risk_score}/100`;
    $("riskProbability").textContent = `${(result.risk_probability * 100).toFixed(1)}%`;
    $("severity").textContent = result.severity.toUpperCase();
    $("modelName").textContent = result.model;
    $("recommendedAction").textContent = result.recommended_action;
    $("humanApproval").textContent = result.human_approval_required ? "Required" : "Not required";
    $("governanceNote").textContent = result.governance_note;
    $("predictionMessage").textContent = "Prediction completed from saved model artifact.";
  } catch (error) {
    $("predictionMessage").textContent = `Prediction unavailable: ${error.message}`;
  }
});

$("refreshMetrics").addEventListener("click", loadMetrics);

checkHealth();
loadModels();
loadMetrics();
