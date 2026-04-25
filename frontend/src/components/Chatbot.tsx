import { useState } from "react";

export function Chatbot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<{ role: "user" | "bot"; text: string }[]>([
    {
      role: "bot",
      text: "Hi — ask me about any state. e.g. 'Why is CMPR higher in Bihar?' or 'Compare SC vs total in Rajasthan'.",
    },
  ]);
  const [input, setInput] = useState("");

  const send = () => {
    const t = input.trim();
    if (!t) return;
    setMessages((m) => [
      ...m,
      { role: "user", text: t },
      {
        role: "bot",
        text:
          "I'll be live once Lovable AI is wired up. Soon I'll answer with figures from the C-02 to C-12 tables and inline charts.",
      },
    ]);
    setInput("");
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-5 right-5 z-40 h-12 w-12 rounded-full bg-ink text-paper shadow-lg flex items-center justify-center hover:scale-105 transition-transform"
        aria-label="Open assistant"
      >
        <span className="font-display text-lg">A</span>
      </button>

      {open && (
        <div className="fixed bottom-20 right-5 z-40 w-[360px] max-w-[calc(100vw-2rem)] h-[460px] bg-card border border-rule rounded-lg shadow-2xl flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-rule flex items-baseline justify-between">
            <div>
              <div className="eyebrow">Assistant</div>
              <div className="font-display text-sm font-semibold">Ask the atlas</div>
            </div>
            <button onClick={() => setOpen(false)} className="text-subtle hover:text-foreground text-sm">
              ✕
            </button>
          </div>
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 text-sm">
            {messages.map((m, i) => (
              <div
                key={i}
                className={
                  m.role === "user"
                    ? "ml-auto max-w-[80%] bg-ink text-paper rounded-lg px-3 py-2"
                    : "mr-auto max-w-[85%] bg-muted rounded-lg px-3 py-2"
                }
              >
                {m.text}
              </div>
            ))}
          </div>
          <form
            onSubmit={(e) => { e.preventDefault(); send(); }}
            className="border-t border-rule p-2 flex gap-2"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about a state…"
              className="flex-1 bg-transparent text-sm px-2 py-1.5 outline-none placeholder:text-subtle"
            />
            <button className="text-xs eyebrow text-subtle hover:text-foreground" type="submit">
              Send
            </button>
          </form>
        </div>
      )}
    </>
  );
}
