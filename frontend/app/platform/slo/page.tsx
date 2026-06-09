"use client";

import { useEffect, useState } from "react";
import { PlatformShell, platformFetch } from "../../../components/PlatformShell";

export default function PlatformSloPage() {
  const [slo, setSlo] = useState<Record<string, unknown> | null>(null);
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    Promise.all([
      platformFetch("/platform/slo").then((r) => r.json()),
      platformFetch("/platform/metrics").then((r) => r.json()),
    ]).then(([sloBody, metricsBody]) => {
      setSlo(sloBody);
      setMetrics(metricsBody);
    });
  }, []);

  const rel = (slo?.reliability || {}) as Record<string, unknown>;

  return (
    <PlatformShell
      title="SLO & reliability"
      subtitle="JSONL-derived KPIs — local-first, no cloud upload"
      active="/platform/slo"
    >
      {!slo ? <p>Loading…</p> : (
        <table style={{ borderCollapse: "collapse", fontSize: "0.9rem" }}>
          <tbody>
            {[
              ["Mean time to detect (s)", slo.mean_time_to_detect_seconds],
              ["Mean time to explain (s)", slo.mean_time_to_explain_seconds],
              ["Proxy drift incidents", slo.proxy_drift_incidents_total],
              ["Blocked high-risk actions", slo.blocked_high_risk_action_count],
              ["Remediation previews", slo.remediation_preview_count],
              ["Proof unavailable rate", slo.proof_unavailable_rate],
              ["Final causation rate", slo.final_causation_rate],
              ["Browser path success", rel.browser_path_success_rate],
              ["Remediation stickiness", rel.remediation_stickiness_rate],
            ].map(([label, val]) => (
              <tr key={String(label)}>
                <td style={{ padding: "6px 12px 6px 0", fontWeight: 600 }}>{label}</td>
                <td>{String(val ?? "—")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {metrics ? (
        <details style={{ marginTop: 24 }}>
          <summary>Raw /platform/metrics</summary>
          <pre style={{ fontSize: "0.78rem", overflow: "auto", maxHeight: 360 }}>
            {JSON.stringify(metrics, null, 2)}
          </pre>
        </details>
      ) : null}
    </PlatformShell>
  );
}
