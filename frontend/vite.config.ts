import react from "@vitejs/plugin-react";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig, loadEnv } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";
import { censusChatApiPlugin } from "./vite.census-api";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // Chat /api runs in Node (this Vite plugin), not the browser bundle.
  // import.meta.env.VITE_* is not substituted in that path, so copy keys here.
  for (const key of [
    "HF_TOKEN",
    "HUGGINGFACE_API_KEY",
    "HF_BASE_URL",
    "QWEN_MODEL",
    "VITE_SUPABASE_URL",
    "VITE_SUPABASE_ANON_KEY",
    "FIRECRAWL_API_KEY",
  ]) {
    if (env[key] && !process.env[key]) process.env[key] = env[key];
  }

  return {
    plugins: [
      TanStackRouterVite({
        target: "react",
        autoCodeSplitting: true,
      }),
      react(),
      tailwindcss(),
      tsconfigPaths(),
      censusChatApiPlugin(),
    ],
  };
});
