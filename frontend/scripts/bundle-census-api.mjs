import { mkdir } from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const frontendRoot = fileURLToPath(new URL("..", import.meta.url));
const repoRoot = path.join(frontendRoot, "..");
const entry = path.join(frontendRoot, "server/vercel-chat.ts");
const require = createRequire(path.join(frontendRoot, "package.json"));
const esbuild = require("esbuild");

const common = {
  absWorkingDir: frontendRoot,
  entryPoints: [entry],
  bundle: true,
  platform: "node",
  target: "node20",
  logLevel: "info",
  define: {
    "import.meta.env": "process.env",
  },
};

await mkdir(path.join(repoRoot, "api"), { recursive: true });
await mkdir(path.join(frontendRoot, "api"), { recursive: true });

// Imported by api/chat.ts. CJS because the repo root has no "type": "module".
await esbuild.build({
  ...common,
  format: "cjs",
  outfile: path.join(repoRoot, "api/_handler.js"),
});

// Imported by frontend/api/chat.ts. ESM to match frontend/package.json.
await esbuild.build({
  ...common,
  format: "esm",
  outfile: path.join(frontendRoot, "api/_handler.js"),
});
