const apiBaseInput = document.getElementById("apiBase");
const runDiagnosisBtn = document.getElementById("runDiagnosisBtn");
const diagnoseStatus = document.getElementById("diagnoseStatus");
const resultsEmpty = document.getElementById("resultsEmpty");
const resultsPanel = document.getElementById("resultsPanel");
const reportIdText = document.getElementById("reportIdText");
const issueText = document.getElementById("issueText");
const confidenceText = document.getElementById("confidenceText");
const actionText = document.getElementById("actionText");
const evidenceList = document.getElementById("evidenceList");
const previewBtn = document.getElementById("previewBtn");
const executeBtn = document.getElementById("executeBtn");
const previewPanel = document.getElementById("previewPanel");
const previewJson = document.getElementById("previewJson");
const confirmCheckbox = document.getElementById("confirmCheckbox");
const executePanel = document.getElementById("executePanel");
const executeJson = document.getElementById("executeJson");
const reportIdInput = document.getElementById("reportIdInput");
const loadReportBtn = document.getElementById("loadReportBtn");
const reportViewer = document.getElementById("reportViewer");

let latestDiagnosis = null;
let latestPreview = null;

function baseUrl() {
  return apiBaseInput.value.trim().replace(/\/+$/, "");
}

async function callApi(path, options = {}) {
  const response = await fetch(`${baseUrl()}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload, null, 2));
  }
  return payload;
}

function renderDiagnosis(data) {
  const top = (data.diagnosis || [])[0];
  if (!top) {
    diagnoseStatus.textContent = "No diagnosis returned.";
    return;
  }

  latestDiagnosis = data;
  latestPreview = null;
  confirmCheckbox.checked = false;
  previewPanel.classList.add("hidden");
  executePanel.classList.add("hidden");
  executeBtn.disabled = true;
  previewBtn.disabled = false;

  reportIdText.textContent = data.report_id || "-";
  issueText.textContent = top.issue || "-";
  confidenceText.textContent = String(top.confidence ?? "-");
  actionText.textContent = top.recommended_action || "-";

  evidenceList.innerHTML = "";
  for (const ev of top.evidence || []) {
    const li = document.createElement("li");
    li.textContent = ev;
    evidenceList.appendChild(li);
  }

  resultsEmpty.classList.add("hidden");
  resultsPanel.classList.remove("hidden");
}

runDiagnosisBtn.addEventListener("click", async () => {
  diagnoseStatus.textContent = "Running diagnosis...";
  try {
    const data = await callApi("/diagnose", { method: "POST" });
    renderDiagnosis(data);
    diagnoseStatus.textContent = "Diagnosis complete.";
    reportIdInput.value = data.report_id || "";
  } catch (error) {
    diagnoseStatus.textContent = `Diagnosis failed: ${error.message}`;
  }
});

previewBtn.addEventListener("click", async () => {
  if (!latestDiagnosis) {
    return;
  }
  const top = latestDiagnosis.diagnosis[0];
  if (!top || !top.recommended_action) {
    return;
  }
  diagnoseStatus.textContent = "Loading repair preview...";
  try {
    const preview = await callApi("/repair/preview", {
      method: "POST",
      body: JSON.stringify({ action: top.recommended_action }),
    });
    latestPreview = preview;
    previewJson.textContent = JSON.stringify(preview, null, 2);
    previewPanel.classList.remove("hidden");
    executePanel.classList.add("hidden");
    executeBtn.disabled = false;
    diagnoseStatus.textContent = "Preview loaded. Confirm before execute.";
  } catch (error) {
    diagnoseStatus.textContent = `Preview failed: ${error.message}`;
  }
});

executeBtn.addEventListener("click", async () => {
  if (!latestDiagnosis || !latestPreview) {
    diagnoseStatus.textContent = "Run diagnosis and preview first.";
    return;
  }
  if (!confirmCheckbox.checked) {
    diagnoseStatus.textContent = "Please tick explicit confirmation before execute.";
    return;
  }
  const top = latestDiagnosis.diagnosis[0];
  const action = top?.recommended_action;
  if (!action) {
    return;
  }

  const allow = window.confirm(
    "Final warning: this will run repair commands on your machine. Continue?"
  );
  if (!allow) {
    diagnoseStatus.textContent = "Execution cancelled.";
    return;
  }

  diagnoseStatus.textContent = "Executing repair...";
  try {
    const result = await callApi("/repair/execute", {
      method: "POST",
      body: JSON.stringify({ action, confirm: true }),
    });
    executeJson.textContent = JSON.stringify(result, null, 2);
    executePanel.classList.remove("hidden");
    diagnoseStatus.textContent = "Repair execution finished.";
  } catch (error) {
    diagnoseStatus.textContent = `Execution failed: ${error.message}`;
  }
});

loadReportBtn.addEventListener("click", async () => {
  const reportId = reportIdInput.value.trim();
  if (!reportId) {
    reportViewer.textContent = "Enter a report_id first.";
    return;
  }
  reportViewer.textContent = "Loading report...";
  try {
    const report = await callApi(`/reports/${encodeURIComponent(reportId)}`, {
      method: "GET",
    });
    reportViewer.textContent = JSON.stringify(report, null, 2);
  } catch (error) {
    reportViewer.textContent = `Failed to load report: ${error.message}`;
  }
});
