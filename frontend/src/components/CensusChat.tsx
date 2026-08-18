import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { ArrowUp, ChevronDown } from "lucide-react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, isTextUIPart, isToolUIPart, type UIMessage } from "ai";
import { AGENT_NAME_HI } from "@/agent/identity";
import { DEFAULT_GROQ_MODEL, GROQ_CHAT_MODELS, isGroqChatModelId } from "@/agent/groqModels";
import { ChatMarkdown } from "@/components/ChatMarkdown";
import { TathyaMark } from "@/components/TathyaMark";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { messagesSignature } from "@/lib/tathyaThreads";

const MODEL_STORAGE_KEY = "tathya.groqModel";

function storedGroqModel() {
  try {
    const saved = localStorage.getItem(MODEL_STORAGE_KEY);
    if (saved && isGroqChatModelId(saved)) return saved;
  } catch {
    /* ignore */
  }
  return DEFAULT_GROQ_MODEL;
}

function textOf(message: UIMessage): string {
  return message.parts
    .filter(isTextUIPart)
    .map((p) => p.text)
    .join("")
    .replace(/^\s+/, "")
    .replace(/\s+$/, "");
}

function toolPills(message: UIMessage): Array<{ label: string; tone: "busy" | "done" | "error" }> {
  return message.parts.filter(isToolUIPart).map((part) => {
    const name = part.type.replace(/^tool-/, "").replaceAll("_", " ");
    const state = "state" in part ? String(part.state) : "";
    if (state.includes("error")) return { label: `${name} failed`, tone: "error" as const };
    if (state === "output-available" || state.includes("result") || state.includes("output")) {
      return { label: name, tone: "done" as const };
    }
    return { label: `${name}…`, tone: "busy" as const };
  });
}

type CensusChatProps = {
  chatId?: string;
  initialMessages?: UIMessage[];
  onMessagesChange?: (messages: UIMessage[]) => void;
  layout?: "drawer" | "page";
};

export function CensusChat({
  chatId,
  initialMessages,
  onMessagesChange,
  layout = "drawer",
}: CensusChatProps) {
  const [draft, setDraft] = useState("");
  const [modelId, setModelId] = useState(DEFAULT_GROQ_MODEL);
  const modelIdRef = useRef(modelId);
  modelIdRef.current = modelId;
  const primed = useRef(initialMessages);
  const persist = useRef(onMessagesChange);
  persist.current = onMessagesChange;
  const lastSaved = useRef(messagesSignature(primed.current ?? []));

  useEffect(() => {
    setModelId(storedGroqModel());
  }, []);

  const chatTransport = useMemo(
    () =>
      new DefaultChatTransport({
        api: "/api/chat",
        body: () => ({ model: modelIdRef.current }),
      }),
    [],
  );

  const { messages, sendMessage, status, error, stop } = useChat({
    id: chatId,
    messages: primed.current ?? [],
    transport: chatTransport,
  });
  const busy = status === "submitted" || status === "streaming";
  const selectedModel = GROQ_CHAT_MODELS.find((m) => m.id === modelId) ?? GROQ_CHAT_MODELS[0];

  const chooseModel = (id: string) => {
    if (!isGroqChatModelId(id)) return;
    setModelId(id);
    try {
      localStorage.setItem(MODEL_STORAGE_KEY, id);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    if (!persist.current || busy || messages.length === 0) return;
    const signature = messagesSignature(messages);
    if (signature === lastSaved.current) return;
    lastSaved.current = signature;
    persist.current(messages);
  }, [messages, busy]);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text || busy) return;
    setDraft("");
    void sendMessage({ text });
  };

  const examples = useMemo(
    () => [
      { title: "SC literacy, Odisha", body: "What is the literacy in Odisha for SC girls?" },
      { title: "Census 2026", body: "How is the Census of India progressing in 2026?" },
      { title: "School attendance", body: "School attendance among SC children in Bihar" },
    ],
    [],
  );

  const page = layout === "page";
  const col = page ? "max-w-[720px] mx-auto w-full" : "";
  const lastAssistantId = [...messages].reduce<string | undefined>(
    (id, msg) => (msg.role === "assistant" ? msg.id : id),
    undefined,
  );

  return (
    <div className="flex flex-col h-full min-h-0 font-body">
      <div className={`px-5 py-4 flex-1 min-h-0 overflow-y-auto space-y-4 ${page ? "px-6 md:px-10" : ""}`}>
        {messages.length === 0 && (
          <div className={`flex flex-col gap-3 ${col}`}>
            {page && (
              <div className="pt-6 pb-4 text-center">
                <div className="eyebrow mb-3">Social infographics · India</div>
                <div className="flex flex-col items-center justify-center gap-2">
                  <TathyaMark pose="wave" size={88} decorative={false} />
                  <h1
                    className="brand-hi text-5xl md:text-6xl font-semibold text-ink"
                    lang="hi"
                    aria-hidden
                  >
                    {AGENT_NAME_HI}
                  </h1>
                </div>
                <p className="mt-3 text-sm text-subtle leading-relaxed max-w-[42ch] mx-auto">
                  Census C-series rates from the database (2001 and 2011 today), and live search for news, policy, and later census rounds.
                </p>
              </div>
            )}
            <p className={`eyebrow ${page ? "text-center" : ""}`}>Try a question</p>
            {examples.map((q) => (
              <button
                key={q.body}
                type="button"
                className="census-chat-card text-left px-4 py-3 hover:opacity-90 transition"
                onClick={() => {
                  setDraft("");
                  void sendMessage({ text: q.body });
                }}
              >
                <div className="text-sm font-medium text-ink">{q.title}</div>
                <p className="mt-0.5 text-sm text-subtle leading-relaxed">{q.body}</p>
              </button>
            ))}
          </div>
        )}
        {messages.map((m) => {
          const text = textOf(m);
          const tools = toolPills(m);
          const mine = m.role === "user";
          const thinking = busy && !mine && m.id === lastAssistantId;
          if (!text && tools.length === 0 && !thinking) return null;
          return (
            <div
              key={m.id}
              className={`flex gap-2.5 ${col} ${mine ? "justify-end" : "justify-start"}`}
            >
              {!mine && (
                <TathyaMark
                  pose={thinking ? "think" : "idle"}
                  size={28}
                  animate={thinking}
                  className="mt-0.5"
                />
              )}
              <div className="min-w-0 max-w-[85%]">
                {tools.length > 0 && (
                  <p className="mb-1 text-[11px] text-subtle">
                    {tools.map((t) => t.label).join(" · ")}
                  </p>
                )}
                {text ? (
                  mine ? (
                    <div className="rounded-2xl rounded-br-md bg-ink text-paper px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap">
                      {text}
                    </div>
                  ) : (
                    <div className="rounded-2xl rounded-bl-md bg-white text-ink px-3.5 py-2.5 shadow-[0_8px_24px_oklch(0.35_0.03_50_/_0.07)]">
                      <ChatMarkdown text={text} />
                    </div>
                  )
                ) : thinking ? (
                  <div className="rounded-2xl rounded-bl-md bg-white px-3.5 py-2.5 text-sm text-subtle shadow-[0_8px_24px_oklch(0.35_0.03_50_/_0.07)]">
                    Looking that up…
                  </div>
                ) : null}
              </div>
            </div>
          );
        })}
        {busy && messages[messages.length - 1]?.role !== "assistant" && (
          <div className={`flex gap-2.5 justify-start ${col}`}>
            <TathyaMark pose="think" size={28} className="mt-0.5" />
            <div className="rounded-2xl rounded-bl-md bg-white px-3.5 py-2.5 text-sm text-subtle shadow-[0_8px_24px_oklch(0.35_0.03_50_/_0.07)]">
              Looking that up…
            </div>
          </div>
        )}
        {error && (
          <div className={`census-chat-card px-5 py-4 text-sm text-cmpr-700 ${col}`}>
            {error.message}
            {/GROQ_API_KEY/i.test(error.message)
              ? " Add GROQ_API_KEY to frontend/.env.local (server-only) and restart Vite."
              : null}
          </div>
        )}
      </div>

      <form onSubmit={onSubmit} className={`px-5 pb-5 pt-1 ${page ? "px-6 md:px-10" : ""}`}>
        <div className={`census-chat-card flex items-end gap-2 px-3 py-2 ${col}`}>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                disabled={busy}
                aria-label="Choose model"
                className="mb-0.5 flex max-w-[42%] shrink-0 items-center gap-1 rounded-full bg-paper px-2.5 py-1.5 text-left text-[11px] font-medium text-ink hover:bg-edu-50 disabled:opacity-50"
              >
                <span className="truncate">{selectedModel.label}</span>
                <ChevronDown className="h-3.5 w-3.5 shrink-0 text-subtle" strokeWidth={2} />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="start"
              side="top"
              className="w-[min(20rem,calc(100vw-3rem))] rounded-xl border-0 p-1 shadow-[0_8px_24px_oklch(0.35_0.03_50_/_0.12)]"
            >
              <DropdownMenuRadioGroup value={modelId} onValueChange={chooseModel}>
                {GROQ_CHAT_MODELS.map((m) => (
                  <DropdownMenuRadioItem
                    key={m.id}
                    value={m.id}
                    className="items-start rounded-lg py-2"
                  >
                    <span className="flex min-w-0 flex-col gap-0.5">
                      <span className="text-sm font-medium text-ink">{m.label}</span>
                      <span className="text-[11px] leading-snug text-subtle">{m.hint}</span>
                    </span>
                  </DropdownMenuRadioItem>
                ))}
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask about India - Census tables or the latest news…"
            className="min-w-0 flex-1 bg-transparent px-1 py-2 text-sm text-ink placeholder:text-subtle outline-none"
            disabled={busy}
          />
          {busy ? (
            <button
              type="button"
              onClick={() => stop()}
              className="text-xs font-medium text-subtle hover:text-ink px-2 py-2"
            >
              Stop
            </button>
          ) : (
            <button
              type="submit"
              aria-label="Send"
              className="h-9 w-9 shrink-0 rounded-full bg-ink text-paper flex items-center justify-center hover:opacity-90 disabled:opacity-30"
              disabled={!draft.trim()}
            >
              <ArrowUp className="h-4 w-4" strokeWidth={2.2} />
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
