import type { VercelRequest, VercelResponse } from "@vercel/node";
import { handleCensusChatNode } from "../src/agent/chatHandler";

export const config = {
  maxDuration: 60,
};

/** Vercel Node serverless entry for POST /api/chat (AI SDK UI message stream). */
export default async function handler(req: VercelRequest, res: VercelResponse) {
  await handleCensusChatNode(req, res);
}
