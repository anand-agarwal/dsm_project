import { describe, expect, it } from "vitest";
import {
  DEFAULT_GROQ_MODEL,
  groqProviderOptions,
  resolveGroqModelId,
  sanitizeGroqChatBody,
} from "./groqModels";

describe("resolveGroqModelId", () => {
  it("defaults to Qwen 3.6 27B", () => {
    expect(resolveGroqModelId()).toBe(DEFAULT_GROQ_MODEL);
    expect(resolveGroqModelId("")).toBe("qwen/qwen3.6-27b");
  });

  it("accepts the allowlisted Groq models", () => {
    expect(resolveGroqModelId("openai/gpt-oss-20b")).toBe("openai/gpt-oss-20b");
    expect(resolveGroqModelId("openai/gpt-oss-120b")).toBe("openai/gpt-oss-120b");
  });

  it("rejects unknown ids", () => {
    expect(() => resolveGroqModelId("Qwen/Qwen3-8B")).toThrow(/Unknown model/);
  });

  it("disables Qwen thinking and strips reasoning_content", () => {
    expect(groqProviderOptions("qwen/qwen3.6-27b").groq.reasoningEffort).toBe("none");
    const cleaned = sanitizeGroqChatBody({
      messages: [
        { role: "assistant", content: null, reasoning_content: "think", tool_calls: [] },
      ],
    });
    expect(cleaned.messages?.[0]).toEqual({ role: "assistant", content: null, tool_calls: [] });
    expect(cleaned.parallel_tool_calls).toBe(false);
  });
});
