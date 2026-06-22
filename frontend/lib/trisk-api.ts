/**
 * /v1 technology-risk API client (demo token auth).
 */

export const TRISK_API_BASE =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE
    ? process.env.NEXT_PUBLIC_API_BASE.replace(/\/$/, "")
    : "http://localhost:8000";

export const TRISK_TOKEN_KEY = "TRISK_API_TOKEN";
export const TRISK_ROLE_KEY = "TRISK_API_ROLE";

export function triskHeaders(): HeadersInit {
  if (typeof window === "undefined") {
    return {
      "X-Api-Token": process.env.NEXT_PUBLIC_TRISK_TOKEN || "dev-trisk-token",
      "X-Api-Role": "auditor_readonly",
    };
  }
  return {
    "X-Api-Token": localStorage.getItem(TRISK_TOKEN_KEY) || "dev-trisk-token",
    "X-Api-Role": localStorage.getItem(TRISK_ROLE_KEY) || "auditor_readonly",
    "Content-Type": "application/json",
  };
}

export async function triskFetch(path: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers || {});
  const base = triskHeaders();
  Object.entries(base).forEach(([k, v]) => headers.set(k, String(v)));
  const resp = await fetch(`${TRISK_API_BASE}${path}`, { ...options, headers });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Trisk API ${resp.status}: ${text}`);
  }
  return resp.json();
}
