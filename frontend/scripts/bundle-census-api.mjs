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
  format: "cjs",
  target: "node20",
  logLevel: "info",
  define: {
    "import.meta.env": "process.env",
  },
};

await mkdir(path.join(repoRoot, "api"), { recursive: true });
await mkdir(path.join(frontendRoot, "api"), { recursive: true });

await esbuild.build({
  ...common,
  outfile: path.join(repoRoot, "api/_handler.js"),
});

await esbuild.build({
  ...common,
  outfile: path.join(frontendRoot, "api/_handler.js"),
});
