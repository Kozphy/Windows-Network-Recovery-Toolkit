/**
 * @file Supabase browser singleton for the Next.js SaaS demo frontend.
 */
import { createClient } from "@supabase/supabase-js";

const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder.invalid";
const supabaseAnonKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "build-placeholder-anon-key";

/**
 * Shared Supabase browser client configured from Next.js public env vars.
 *
 * @remarks
 * Network: Uses anon key against `NEXT_PUBLIC_SUPABASE_URL`; all authorization
 * for backend API routes still flows through Bearer tokens handled in pages.
 *
 * Constraints: CI/static export may not provide Supabase variables. In that
 * case a non-routable placeholder client is created so prerendering succeeds;
 * runtime authentication still fails closed until real variables are supplied.
 */
export const supabase = createClient(supabaseUrl, supabaseAnonKey);
