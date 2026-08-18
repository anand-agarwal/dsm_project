import { describe, expect, it, beforeEach } from "vitest";
import { handleCensusChat } from "./chatHandler";
import { checkChatRateLimit, resetChatRateLimit } from "./chatRateLimit";

describe("handleCensusChat", () => {
  beforeEach(() => resetChatRateLimit());
  it("rejects non-POST", async () => {
    const res = await handleCensusChat(new Request("http://localhost/api/chat", { method: "GET" }));
    expect(res.status).toBe(405);
  });

  it("returns 500 when GROQ_API_KEY is missing", async () => {
    const prev = process.env.GROQ_API_KEY;
    delete process.env.GROQ_API_KEY;
    try {
      const res = await handleCensusChat(
        new Request("http://localhost/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: [{ id: "1", role: "user", parts: [{ type: "text", text: "hi" }] }],
          }),
        }),
      );
      expect(res.status).toBe(500);
      const json = (await res.json()) as { error: string };
      expect(json.error).toMatch(/GROQ_API_KEY/);
    } finally {
      if (prev) process.env.GROQ_API_KEY = prev;
    }
  });

  it("returns 400 for an unknown model id", async () => {
    process.env.GROQ_API_KEY = process.env.GROQ_API_KEY || "test-token";
    const res = await handleCensusChat(
      new Request("http://localhost/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "Qwen/Qwen3-8B",
          messages: [{ id: "1", role: "user", parts: [{ type: "text", text: "hi" }] }],
        }),
      }),
    );
    expect(res.status).toBe(400);
    const json = (await res.json()) as { error: string };
    expect(json.error).toMatch(/Unknown model/);
  });

  it("returns 400 when messages are missing", async () => {
    process.env.GROQ_API_KEY = process.env.GROQ_API_KEY || "test-token";
    const res = await handleCensusChat(
      new Request("http://localhost/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      }),
    );
    expect(res.status).toBe(400);
  });

  it("returns 429 when the same network sends too many POSTs", async () => {
    process.env.GROQ_API_KEY = process.env.GROQ_API_KEY || "test-token";
    for (let i = 0; i < 20; i++) checkChatRateLimit("203.0.113.8");
    const res = await handleCensusChat(
      new Request("http://localhost/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-forwarded-for": "203.0.113.8" },
        body: JSON.stringify({
          messages: [{ id: "1", role: "user", parts: [{ type: "text", text: "hi" }] }],
        }),
      }),
    );
    expect(res.status).toBe(429);
  });
});
