import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import { ArrowUp, Sparkles } from "lucide-react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, isTextUIPart, isToolUIPart, type UIMessage } from "ai";
import { matchResearchSource } from "@/agent/researchSources";

const chatTransport = new DefaultChatTransport({ api: "/api/chat" });

function textOf(message: UIMessage): string {
  return message.parts
    .filter(isTextUIPart)
    .map((p) => p.text)
    .join("")
    .replace(/^\s+/, "")
    .replace(/\s+$/, "");
}

function citationLabel(url: string, markdownLabel?: string): string {
  const known = matchResearchSource(url);
  if (known?.org) return known.org;
  const label = markdownLabel?.trim() ?? "";
  if (label && !/^https?:\/\//i.test(label) && label.length <= 80) return label;
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return label || "Source";
  }
}

function tidyUrl(raw: string): string {
  return raw.replace(/[).,;:]+$/g, "");
}

function CitationLink({ href, label }: { href: string; label?: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="font-semibold text-edu-700 underline decoration-edu-300 underline-offset-2 hover:text-edu-900"
    >
      {citationLabel(href, label)}
    </a>
  );
}

function renderMessageText(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern =
    /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)|\*\*([^*]+)\*\*|(https?:\/\/[^\s<>\]]+)/g;
  let last = 0;
  let key = 0;
  for (const match of text.matchAll(pattern)) {
    const start = match.index ?? 0;
    if (start > last) nodes.push(text.slice(last, start));
    if (match[1] && match[2]) {
      nodes.push(<CitationLink key={key++} href={tidyUrl(match[2])} label={match[1]} />);
    } else if (match[3]) {
      nodes.push(
        <strong key={key++} className="font-semibold text-ink">
          {match[3]}
        </strong>,
      );
    } else if (match[4]) {
      nodes.push(<CitationLink key={key++} href={tidyUrl(match[4])} />);
    }
    last = start + match[0].length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
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

const PILL: Record<"busy" | "done" | "error" | "you", string> = {
  busy: "bg-edu-50 text-edu-700",
  done: "bg-[oklch(0.95_0.03_150)] text-tea",
  error: "bg-cmpr-50 text-cmpr-700",
  you: "bg-secondary text-subtle",
};

export function CensusChat() {
  const [draft, setDraft] = useState("");
  const { messages, sendMessage, status, error, stop } = useChat({
    transport: chatTransport,
  });
  const busy = status === "submitted" || status === "streaming";

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
      { title: "ST currently married", body: "Currently married share for ST females in Rajasthan, 2011" },
      { title: "School attendance", body: "School attendance among SC children in Bihar" },
    ],
    [],
  );

  return (
    <div className="flex flex-col h-full min-h-0 font-body">
      <div className="px-5 py-4 flex-1 min-h-0 overflow-y-auto space-y-3">
        {messages.length === 0 && (
          <div className="flex flex-col gap-3">
            <p className="eyebrow">Try a question</p>
            {examples.map((q) => (
              <button
                key={q.body}
                type="button"
                className="census-chat-card text-left px-5 py-4 hover:brightness-[0.99] transition"
                onClick={() => {
                  setDraft("");
                  void sendMessage({ text: q.body });
                }}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-edu-500" />
                  <span className="font-display text-[15px] text-ink leading-tight">{q.title}</span>
                </div>
                <p className="text-sm text-subtle leading-relaxed">{q.body}</p>
                <div className="mt-3 flex items-center justify-between">
                  <span className={`text-[10px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded-full ${PILL.you}`}>
                    Census
                  </span>
                  <span className="text-xs text-subtle">Open →</span>
                </div>
                <div className="mt-3 h-0.5 rounded-full bg-edu-300/80" />
              </button>
            ))}
          </div>
        )}
        {messages.map((m) => {
          const text = textOf(m);
          const tools = toolPills(m);
          const mine = m.role === "user";
          if (!text && tools.length === 0) return null;
          return (
            <article key={m.id} className="census-chat-card px-5 pt-4 pb-3">
              <div className="flex items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${mine ? "bg-edu-500" : "bg-tea"}`} />
                  <span className="font-display text-[15px] text-ink leading-tight">
                    {mine ? "You" : "Census agent"}
                  </span>
                </div>
                <span className={`text-[10px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded-full ${mine ? PILL.you : PILL.done}`}>
                  {mine ? "Query" : "Reply"}
                </span>
              </div>
              {tools.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {tools.map((t) => (
                    <span
                      key={t.label}
                      className={`text-[10px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded-full ${PILL[t.tone]}`}
                    >
                      {t.label}
                    </span>
                  ))}
                </div>
              )}
              {text ? (
                <div className="text-sm text-[oklch(0.38_0.02_60)] whitespace-pre-wrap leading-relaxed">
                  {renderMessageText(text)}
                </div>
              ) : null}
              <div className={`mt-3 h-0.5 rounded-full ${mine ? "bg-edu-400" : "bg-tea/70"}`} />
            </article>
          );
        })}
        {busy && (
          <div className="flex items-center gap-2 px-1 text-xs text-subtle">
            <Sparkles className="h-3.5 w-3.5 animate-pulse" />
            Looking up Census tables…
          </div>
        )}
        {error && (
          <div className="census-chat-card px-5 py-4 text-sm text-cmpr-700">
            {error.message}. Set HF_TOKEN in frontend/.env.local (server-only) and restart Vite.
          </div>
        )}
      </div>

      <form onSubmit={onSubmit} className="px-5 pb-5 pt-1">
        <div className="census-chat-card flex items-end gap-2 px-3 py-2">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask about Census 2001 or 2011…"
            className="flex-1 bg-transparent px-2 py-2 text-sm text-ink placeholder:text-subtle outline-none"
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
