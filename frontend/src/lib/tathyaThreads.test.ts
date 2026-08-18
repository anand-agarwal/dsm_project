import { describe, expect, it } from "vitest";
import type { UIMessage } from "ai";
import {
  restoreActiveThreadId,
  snapshotEndedMessages,
  titleFromMessages,
  upsertTathyaThread,
} from "./tathyaThreads";

function userMsg(id: string, text: string): UIMessage {
  return { id, role: "user", parts: [{ type: "text", text }] };
}

describe("tathyaThreads", () => {
  it("titles a thread from the first user message", () => {
    expect(titleFromMessages([userMsg("1", "Literacy in Odisha for SC girls?")])).toBe(
      "Literacy in Odisha for SC girls?",
    );
  });

  it("returns the same array when the thread content is unchanged", () => {
    const messages = [userMsg("1", "hi")];
    const threads = [{ id: "a", title: "hi", updatedAt: 1, messages }];
    expect(upsertTathyaThread(threads, "a", messages)).toBe(threads);
  });

  it("restores the saved thread when it still exists", () => {
    const threads = [
      { id: "old", title: "Old", updatedAt: 1, messages: [userMsg("1", "hi")] },
      { id: "open", title: "Open", updatedAt: 2, messages: [userMsg("2", "hello")] },
    ];
    expect(restoreActiveThreadId(threads, "open")).toBe("open");
  });

  it("falls back to the most recent thread if the saved id is gone", () => {
    const threads = [{ id: "only", title: "Only", updatedAt: 1, messages: [userMsg("1", "hi")] }];
    expect(restoreActiveThreadId(threads, "missing")).toBe("only");
    expect(restoreActiveThreadId([], "missing")).toBeNull();
  });

  it("snapshots a finished turn as user + assistant text only", () => {
    const assistant = {
      id: "2",
      role: "assistant" as const,
      parts: [
        { type: "step-start" },
        { type: "text", text: "The next Census round is underway." },
      ],
    } as UIMessage;
    const ended = snapshotEndedMessages([userMsg("1", "How is Census 2026 progressing?"), assistant]);
    expect(ended).toHaveLength(2);
    expect(ended[1].parts).toEqual([{ type: "text", text: "The next Census round is underway." }]);
  });
});
