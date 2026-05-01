/**
 * Shared API client helpers for the Next.js frontend.
 *
 * The module centralizes bearer-authenticated JSON requests to the backend API
 * so page-level components can remain focused on rendering and workflow state.
 *
 * Audit Notes:
 * Failures strip response bodies into thrown Errors — log or surface `message`
 * in UI when triaging quota (429) versus auth (401/403) issues.
 */
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

/**
 * Perform an authenticated JSON request against the backend API.
 *
 * @param path Relative API path such as `/diagnose` or `/usage`.
 * @param token Access token passed as a Bearer authorization header.
 * @param options Standard fetch options (method/body/etc.).
 * @returns Parsed JSON response from the API.
 * @throws {Error} When the API responds with a non-2xx status code.
 *
 * @remarks
 * Side effects: network call to `API_BASE`.
 * Idempotency depends on target endpoint semantics.
 */
export async function authFetch(path: string, token: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${token}`);
  headers.set("Content-Type", "application/json");
  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`API ${resp.status}: ${text}`);
  }
  return resp.json();
}
