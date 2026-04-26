import { createClient } from "@supabase/supabase-js";

const rawSupabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const rawSupabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

const supabaseUrl = rawSupabaseUrl?.trim().replace(/\/+$/, "");
const supabaseAnonKey = rawSupabaseAnonKey?.trim();

function isValidHttpUrl(url: string) {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:";
  } catch {
    return false;
  }
}

export const supabase =
  supabaseUrl && supabaseAnonKey && isValidHttpUrl(supabaseUrl)
    ? createClient(supabaseUrl, supabaseAnonKey)
    : null;

export const hasSupabaseEnv = Boolean(
  supabaseUrl && supabaseAnonKey && isValidHttpUrl(supabaseUrl),
);
