import { describe, expect, it, beforeEach } from "vitest";
import { checkChatRateLimit, resetChatRateLimit } from "./chatRateLimit";

describe("checkChatRateLimit", () => {
  beforeEach(() => resetChatRateLimit());

  it("allows a burst under the cap", () => {
    for (let i = 0; i < 5; i++) {
      expect(checkChatRateLimit("a", 1_000, 5, 10_000).allowed).toBe(true);
    }
    const blocked = checkChatRateLimit("a", 1_000, 5, 10_000);
    expect(blocked.allowed).toBe(false);
    if (!blocked.allowed) expect(blocked.retryAfterSec).toBeGreaterThan(0);
  });

  it("tracks keys separately", () => {
    expect(checkChatRateLimit("one", 1_000, 1, 10_000).allowed).toBe(true);
    expect(checkChatRateLimit("two", 1_000, 1, 10_000).allowed).toBe(true);
    expect(checkChatRateLimit("one", 1_000, 1, 10_000).allowed).toBe(false);
  });

  it("frees a slot after the window", () => {
    expect(checkChatRateLimit("a", 1_000, 1, 10_000).allowed).toBe(true);
    expect(checkChatRateLimit("a", 1_000, 1, 10_000).allowed).toBe(false);
    expect(checkChatRateLimit("a", 12_000, 1, 10_000).allowed).toBe(true);
  });
});
