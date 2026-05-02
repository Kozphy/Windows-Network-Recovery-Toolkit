"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const base =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_PLATFORM_API
    ? process.env.NEXT_PUBLIC_PLATFORM_API.replace(/\/$/, "")
    : "";

export default function PlatformPage() {
  const [health, setHealth] = useState<object | null>(null);
  const [metrics, setMetrics] = useState<object | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    if (!base) {
      setError("Set NEXT_PUBLIC_PLATFORM_API (see frontend/.env.local.example)");
      return;
    }
    Promise.all([
      fetch(`${base}/platform/health`).then((r) => r.json()),
      fetch(`${base}/platform/metrics`).then((r) => r.json()),
    ])
      .then(([h, m]) => {
        setHealth(h);
        setMetrics(m);
      })
      .catch((e: unknown) => setError(String(e)));
  }, []);

  return (
    <main className="container" style={{ padding: "1rem", maxWidth: 900 }}>
      <h1>Endpoint Reliability Platform</h1>
      <p>
        Local-first dashboard (no auth). Runs against <code>{base || "(unset)"}</code>. Start backend:{" "}
        <code>uvicorn backend.main:app --host 127.0.0.1 --port 8000</code>
      </p>
      <p>
        High-risk remediation is blocked from execute; previews only. Safe mode is default.
      </p>
      {error ? <p style={{ color: "crimson" }}>{error}</p> : null}
      <section style={{ marginTop: "1.5rem" }}>
        <h2>Health</h2>
        <pre>{health ? JSON.stringify(health, null, 2) : "…loading"}</pre>
      </section>
      <section style={{ marginTop: "1.5rem" }}>
        <h2>Metrics</h2>
        <pre>{metrics ? JSON.stringify(metrics, null, 2) : "…loading"}</pre>
      </section>
      <p style={{ marginTop: "2rem" }}>
        <Link href="/">← Home</Link>
      </p>
    </main>
  );
}
