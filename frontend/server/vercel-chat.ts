import type { VercelRequest, VercelResponse } from "@vercel/node";
import { handleCensusChatNode } from "../src/agent/chatHandler";

export const config = {
  maxDuration: 60,
};

/** Bundled by `scripts/bundle-census-api.mjs` into `api/_handler.cjs` for Vercel. */
export default async function handler(req: VercelRequest, res: VercelResponse) {
  try {
    await handleCensusChatNode(req, res);
  } catch (err: unknown) {
    if (res.headersSent) return;
    res.statusCode = 500;
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ error: err instanceof Error ? err.message : "Chat handler failed" }));
  }
}
