import { describe, expect, it } from "vitest";
import { handleCensusChat } from "./chatHandler";

describe("handleCensusChat", () => {
  it("rejects non-POST", async () => {
    const res = await handleCensusChat(new Request("http://localhost/api/chat", { method: "GET" }));
    expect(res.status).toBe(405);
  });

  it("returns 500 when HF_TOKEN is missing", async () => {
    const prev = process.env.HF_TOKEN;
    const prev2 = process.env.HUGGINGFACE_API_KEY;
    delete process.env.HF_TOKEN;
    delete process.env.HUGGINGFACE_API_KEY;
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
      expect(json.error).toMatch(/HF_TOKEN/);
    } finally {
      if (prev) process.env.HF_TOKEN = prev;
      if (prev2) process.env.HUGGINGFACE_API_KEY = prev2;
    }
  });

  it("returns 400 when messages are missing", async () => {
    process.env.HF_TOKEN = process.env.HF_TOKEN || "test-token";
    const res = await handleCensusChat(
      new Request("http://localhost/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      }),
    );
    expect(res.status).toBe(400);
  });
});
