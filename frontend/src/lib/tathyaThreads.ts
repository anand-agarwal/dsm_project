import type { UIMessage } from "ai";

export type TathyaThread = {
  id: string;
  title: string;
  updatedAt: number;
  messages: UIMessage[];
};

const STORAGE_KEY = "bachpan-tathya-threads";
const ACTIVE_KEY = "bachpan-tathya-active-id";

function browserStorage(): Storage | null {
  try {
    if (typeof localStorage === "undefined") return null;
    return localStorage;
  } catch {
    return null;
  }
}

export function loadTathyaThreads(): TathyaThread[] {
  const storage = browserStorage();
  if (!storage) return [];
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as TathyaThread[];
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((t) => t && typeof t.id === "string" && Array.isArray(t.messages))
      .map((t) => ({ ...t, messages: snapshotEndedMessages(t.messages) }));
  } catch {
    return [];
  }
}

export function saveTathyaThreads(threads: TathyaThread[]) {
  const storage = browserStorage();
  if (!storage) return;
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(threads));
  } catch {
    // Quota or private-mode write failures should not crash the chat UI.
  }
}

function textPartsOf(message: UIMessage): Array<{ type: "text"; text: string }> {
  return message.parts
    .filter((p): p is { type: "text"; text: string } => p.type === "text")
    .map((p) => ({ type: "text" as const, text: p.text }));
}

/** Keep the finished visible transcript: user + assistant text, no live tool parts. */
export function snapshotEndedMessages(messages: UIMessage[]): UIMessage[] {
  const out: UIMessage[] = [];
  for (const message of messages) {
    if (message.role !== "user" && message.role !== "assistant") continue;
    const parts = textPartsOf(message);
    const text = parts.map((p) => p.text).join("").trim();
    if (!text) continue;
    out.push({ id: message.id, role: message.role, parts });
  }
  return out;
}

export function loadActiveThreadId(): string | null {
  const storage = browserStorage();
  if (!storage) return null;
  return storage.getItem(ACTIVE_KEY);
}

export function saveActiveThreadId(id: string) {
  const storage = browserStorage();
  if (!storage) return;
  storage.setItem(ACTIVE_KEY, id);
}

export function titleFromMessages(messages: UIMessage[]): string {
  const firstUser = messages.find((m) => m.role === "user");
  if (!firstUser) return "New chat";
  const text = firstUser.parts
    .filter((p): p is { type: "text"; text: string } => p.type === "text")
    .map((p) => p.text)
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
  if (!text) return "New chat";
  return text.length > 52 ? `${text.slice(0, 49).trim()}…` : text;
}

export function messagesSignature(messages: UIMessage[]): string {
  return messages
    .map((m) => {
      const text = m.parts
        .filter((p): p is { type: "text"; text: string } => p.type === "text")
        .map((p) => p.text)
        .join("");
      const tools = m.parts.map((p) => p.type).join(",");
      return `${m.id}:${m.role}:${tools}:${text.length}:${text.slice(-24)}`;
    })
    .join("|");
}

export function upsertTathyaThread(
  threads: TathyaThread[],
  id: string,
  messages: UIMessage[],
): TathyaThread[] {
  const ended = snapshotEndedMessages(messages);
  if (ended.length === 0) return threads;
  const existing = threads.find((t) => t.id === id);
  if (existing && messagesSignature(existing.messages) === messagesSignature(ended)) {
    return threads;
  }
  const next: TathyaThread = {
    id,
    title: titleFromMessages(ended),
    updatedAt: Date.now(),
    messages: ended,
  };
  const without = threads.filter((t) => t.id !== id);
  return [next, ...without].sort((a, b) => b.updatedAt - a.updatedAt);
}

export function restoreActiveThreadId(threads: TathyaThread[], savedId: string | null): string | null {
  if (savedId && threads.some((t) => t.id === savedId)) return savedId;
  return threads[0]?.id ?? null;
}

export function groupThreads(threads: TathyaThread[]): Array<{ label: string; items: TathyaThread[] }> {
  const now = new Date();
  const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const yesterday = startOfDay - 86_400_000;
  const week = startOfDay - 7 * 86_400_000;

  const buckets: Record<string, TathyaThread[]> = {
    Today: [],
    Yesterday: [],
    "Previous 7 days": [],
    Older: [],
  };

  for (const t of threads) {
    if (t.updatedAt >= startOfDay) buckets.Today.push(t);
    else if (t.updatedAt >= yesterday) buckets.Yesterday.push(t);
    else if (t.updatedAt >= week) buckets["Previous 7 days"].push(t);
    else buckets.Older.push(t);
  }

  return Object.entries(buckets)
    .filter(([, items]) => items.length > 0)
    .map(([label, items]) => ({ label, items }));
}
