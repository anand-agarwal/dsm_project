import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL(".", import.meta.url));
const env = loadEnv("development", root, "");

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
    env,
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
