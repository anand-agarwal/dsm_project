import { mkdir, rm } from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const frontendRoot = fileURLToPath(new URL("..", import.meta.url));
const repoRoot = path.join(frontendRoot, "..");
const entry = path.join(frontendRoot, "server/vercel-chat.ts");
const require = createRequire(path.join(frontendRoot, "package.json"));
const esbuild = require("esbuild");

// CJS + .cjs is required: frontend/package.json is "type": "module", so a
// .js bundle is loaded as ESM on Vercel. @vercel/oidc (via `ai` → gateway)
// then hits esbuild's ESM shim: Dynamic require of "path" is not supported.
const common = {
  absWorkingDir: frontendRoot,
  entryPoints: [entry],
  bundle: true,
  platform: "node",
  format: "cjs",
  target: "node20",
  logLevel: "info",
  define: {
    "import.meta.env": "process.env",
  },
};

const stale = [
  path.join(repoRoot, "api/_handler.js"),
  path.join(frontendRoot, "api/_handler.js"),
];
await Promise.all(stale.map((file) => rm(file, { force: true })));

await mkdir(path.join(repoRoot, "api"), { recursive: true });
await mkdir(path.join(frontendRoot, "api"), { recursive: true });

await esbuild.build({
  ...common,
  outfile: path.join(repoRoot, "api/_handler.cjs"),
});

await esbuild.build({
  ...common,
  outfile: path.join(frontendRoot, "api/_handler.cjs"),
});
