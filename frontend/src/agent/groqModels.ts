/** Groq chat models with the same free-tier caps as Qwen 3.6 27B (1k req/day). */
export const GROQ_CHAT_MODELS = [
  {
    id: "qwen/qwen3.6-27b",
    label: "Qwen 3.6 27B",
    hint: "Default · same family as before",
  },
  {
    id: "openai/gpt-oss-20b",
    label: "GPT-OSS 20B",
    hint: "Faster · cheaper if you go paid",
  },
  {
    id: "openai/gpt-oss-120b",
    label: "GPT-OSS 120B",
    hint: "Stronger · same free daily cap",
  },
] as const;

export type GroqChatModelId = (typeof GROQ_CHAT_MODELS)[number]["id"];

export const DEFAULT_GROQ_MODEL: GroqChatModelId = GROQ_CHAT_MODELS[0].id;

const ALLOWED = new Set<string>(GROQ_CHAT_MODELS.map((m) => m.id));

export function isGroqChatModelId(value: string): value is GroqChatModelId {
  return ALLOWED.has(value);
}

export function resolveGroqModelId(requested?: string | null): GroqChatModelId {
  const trimmed = requested?.trim();
  if (!trimmed) return DEFAULT_GROQ_MODEL;
  if (!isGroqChatModelId(trimmed)) {
    throw new Error(
      `Unknown model "${trimmed}". Use one of: ${GROQ_CHAT_MODELS.map((m) => m.id).join(", ")}`,
    );
  }
  return trimmed;
}

/** Qwen 3.6 thinks by default; Groq then fails tool JSON and rejects reasoning_content. */
export function groqProviderOptions(modelId: GroqChatModelId) {
  if (modelId.startsWith("qwen/")) {
    return { groq: { reasoningEffort: "none" as const } };
  }
  return { groq: { reasoningEffort: "low" as const, include_reasoning: false } };
}

type GroqChatBody = {
  messages?: Array<Record<string, unknown>>;
  [key: string]: unknown;
};

/** Groq chat completions reject assistant.reasoning_content on the next tool-loop turn. */
export function sanitizeGroqChatBody(body: GroqChatBody): GroqChatBody {
  const messages = body.messages?.map((message) => {
    if (!message || typeof message !== "object" || !("reasoning_content" in message)) {
      return message;
    }
    const { reasoning_content: _drop, ...rest } = message;
    return rest;
  });
  return {
    ...body,
    parallel_tool_calls: false,
    ...(messages ? { messages } : {}),
  };
}
