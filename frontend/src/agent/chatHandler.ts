import { convertToModelMessages, stepCountIs, streamText, type UIMessage } from "ai";
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import type { IncomingMessage, ServerResponse } from "node:http";
import { censusAgentTools } from "./censusTools";
import { checkChatRateLimit, clientIpFromRequest } from "./chatRateLimit";

const SYSTEM = `You are Tathya, Bachpan's social-infographics chatbot for India.

Two jobs:
1. Retrieve Census of India C-series rates from Postgres. Today that is 2001 and 2011 only; more series will be added later. Never invent a C-series rate from memory or from web snippets.
2. Answer current, news, policy, law, and background questions with web_search. You are not limited to 2001/2011 as a topic - only the database years are limited.

When to call which tool:
- Any C-series NUMBER (literacy, currently-married share, population, school attendance) → run_census_query. Call lookup_schema first if you are unsure of the table or columns.
- Latest / current / recent / news / 2021 / 2026 / census operations or schedule / NFHS or other surveys / laws / schemes / definitions / "search" / anything not stored in the C-series tables → you MUST call web_search before answering. Do not skip the tool because you think you already know, and do not refuse with "my tools only support 2001 and 2011."
- After searching, you may still say the queryable C-series years are 2001 and 2011, then report what the search hits say about later rounds or other sources.
- If the user asks you to search, call web_search even if the question overlaps Census tables.

How to write:
- Cite search hits as markdown links like [UNICEF](https://www.unicef.org/...), never paste a raw URL.
- Do not treat snippets as Census C-table rates.
- web_search uses Firecrawl when FIRECRAWL_API_KEY is set, then DuckDuckGo, then OpenAlex. If it still fails, say the backends failed - do not claim that no research exists.

Census query rules (run_census_query):
- SC and ST are separate Postgres tables (raw_c_08_sc, not a caste column on raw_c_08).
- Literacy is C-08: literate count / total count (e.g. females_10 / females_4 for girls). There is no literacy column.
- Currently-married share is C-02 (current age). Atlas CMPR for the total population uses age-at-marriage tables (C-04+); do not call C-02 currently-married the same as atlas CMPR unless the question is about SC/ST currently-married prevalence.
- Pass state as a plain name only (Rajasthan, Odisha). Never pass "State - RAJASTHAN" or a full sentence. The tool already matches Census labels like "State - RAJASTHAN (08)".
- Omit ageBand unless the user named an age. Default is All ages. Do not put ST/SC/female/married into ageBand.
- When you report a rate, quote the percentage AND the numerator/denominator AND year, area (Total/Rural/Urban), sex, social group, and age band.
- If a tool returns ok:false or 0 rows, quote the tool error/hint. Do not invent causes such as a missing table or a "State - NAME" format mismatch.

Refuse only questions unrelated to India social statistics, demography, education, gender, caste/tribe, religion, child marriage, public health context, or related policy and data.`;

function env(name: string): string | undefined {
  return process.env[name]?.trim() || undefined;
}

export function getQwenModel() {
  const apiKey = env("HF_TOKEN") ?? env("HUGGINGFACE_API_KEY");
  if (!apiKey) {
    throw new Error("Missing HF_TOKEN. Add a Hugging Face token to frontend/.env.local (no VITE_ prefix).");
  }
  const provider = createOpenAICompatible({
    name: "huggingface",
    apiKey,
    baseURL: env("HF_BASE_URL") ?? "https://router.huggingface.co/v1",
  });
  const modelId = env("QWEN_MODEL") ?? "Qwen/Qwen3-8B";
  return provider.chatModel(modelId);
}

export async function handleCensusChat(request: Request): Promise<Response> {
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204 });
  }
  if (request.method !== "POST") {
    return Response.json({ error: "Method not allowed" }, { status: 405 });
  }

  const limit = checkChatRateLimit(clientIpFromRequest(request));
  if (!limit.allowed) {
    return Response.json(
      { error: "Too many questions from this network. Wait a few minutes and try again." },
      { status: 429, headers: { "Retry-After": String(limit.retryAfterSec) } },
    );
  }

  let model;
  try {
    model = getQwenModel();
  } catch (err) {
    return Response.json(
      { error: err instanceof Error ? err.message : "Model config error" },
      { status: 500 },
    );
  }

  let body: { messages?: UIMessage[] };
  try {
    body = (await request.json()) as { messages?: UIMessage[] };
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const uiMessages = Array.isArray(body.messages) ? body.messages : [];
  if (uiMessages.length === 0) {
    return Response.json({ error: "messages is required" }, { status: 400 });
  }

  const modelMessages = await convertToModelMessages(uiMessages, {
    tools: censusAgentTools,
    ignoreIncompleteToolCalls: true,
  });

  const result = streamText({
    model,
    system: SYSTEM,
    messages: modelMessages,
    tools: censusAgentTools,
    stopWhen: stepCountIs(8),
    temperature: 0.2,
    maxRetries: 1,
  });

  return result.toUIMessageStreamResponse();
}

export async function nodeRequestToWeb(
  req: IncomingMessage & { body?: unknown },
): Promise<Request> {
  const host = req.headers.host ?? "127.0.0.1";
  const url = `http://${host}${req.url ?? "/api/chat"}`;
  const headers = new Headers();
  for (const [key, value] of Object.entries(req.headers)) {
    if (value === undefined) continue;
    headers.set(key, Array.isArray(value) ? value.join(", ") : value);
  }
  const method = req.method ?? "GET";
  if (method === "GET" || method === "HEAD") {
    return new Request(url, { method, headers });
  }
  // Vercel may already parse JSON onto req.body before the stream is readable.
  if (req.body !== undefined && req.body !== null && !Buffer.isBuffer(req.body)) {
    const body = typeof req.body === "string" ? req.body : JSON.stringify(req.body);
    return new Request(url, { method, headers, body });
  }
  const chunks: Buffer[] = [];
  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return new Request(url, {
    method,
    headers,
    body: Buffer.concat(chunks),
  });
}

export async function writeWebResponseToNode(response: Response, res: ServerResponse) {
  res.statusCode = response.status;
  response.headers.forEach((value, key) => {
    res.setHeader(key, value);
  });
  if (!response.body) {
    res.end();
    return;
  }
  const reader = response.body.getReader();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      res.write(Buffer.from(value));
    }
  } finally {
    res.end();
  }
}

export async function handleCensusChatNode(
  req: IncomingMessage & { body?: unknown },
  res: ServerResponse,
) {
  try {
    const request = await nodeRequestToWeb(req);
    const response = await handleCensusChat(request);
    await writeWebResponseToNode(response, res);
  } catch (err: unknown) {
    if (res.headersSent) return;
    res.statusCode = 500;
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ error: err instanceof Error ? err.message : "Chat handler failed" }));
  }
}
