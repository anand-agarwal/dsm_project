import { useCallback, useEffect, useMemo, useState } from "react";
import type { UIMessage } from "ai";
import { Menu, Plus, Search, Trash2, X } from "lucide-react";
import { CensusChat } from "@/components/CensusChat";
import { TathyaMark } from "@/components/TathyaMark";
import { AGENT_NAME } from "@/agent/identity";
import {
  groupThreads,
  loadActiveThreadId,
  loadTathyaThreads,
  restoreActiveThreadId,
  saveActiveThreadId,
  saveTathyaThreads,
  upsertTathyaThread,
  type TathyaThread,
} from "@/lib/tathyaThreads";

function newId() {
  return crypto.randomUUID();
}

export function TathyaWorkspace() {
  const [threads, setThreads] = useState<TathyaThread[]>([]);
  const [activeId, setActiveId] = useState<string>("");
  const [ready, setReady] = useState(false);
  const [query, setQuery] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    const loaded = loadTathyaThreads();
    const restored = restoreActiveThreadId(loaded, loadActiveThreadId()) ?? newId();
    setThreads(loaded);
    setActiveId(restored);
    saveActiveThreadId(restored);
    setReady(true);
  }, []);

  const selectThread = (id: string) => {
    setActiveId(id);
    saveActiveThreadId(id);
    setSidebarOpen(false);
  };

  const persist = useCallback((next: TathyaThread[]) => {
    setThreads(next);
    saveTathyaThreads(next);
  }, []);

  const active = threads.find((t) => t.id === activeId);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return threads;
    return threads.filter((t) => t.title.toLowerCase().includes(q));
  }, [threads, query]);
  const groups = useMemo(() => groupThreads(filtered), [filtered]);

  const startNew = () => {
    selectThread(newId());
  };

  const onMessagesChange = useCallback((messages: UIMessage[]) => {
    setThreads((prev) => {
      const next = upsertTathyaThread(prev, activeId, messages);
      if (next === prev) return prev;
      saveTathyaThreads(next);
      return next;
    });
  }, [activeId]);

  const removeThread = (id: string) => {
    const next = threads.filter((t) => t.id !== id);
    persist(next);
    if (id === activeId) {
      const fallback = restoreActiveThreadId(next, null) ?? newId();
      setActiveId(fallback);
      saveActiveThreadId(fallback);
    }
  };

  return (
    <div className="relative flex flex-1 min-h-0">
      {sidebarOpen && (
        <button
          type="button"
          className="absolute inset-0 z-30 bg-ink/20 md:hidden"
          aria-label="Close chats"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`absolute md:static z-40 md:z-0 inset-y-0 left-0 w-[280px] shrink-0 flex flex-col border-r border-rule/80 bg-paper/95 backdrop-blur-sm transition-transform md:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between gap-2 px-4 pt-4 pb-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <TathyaMark pose="idle" size={40} />
            <div className="min-w-0">
              <div className="eyebrow">{AGENT_NAME}</div>
              <div className="font-display text-xl leading-tight text-ink">Chats</div>
            </div>
          </div>
          <button
            type="button"
            className="md:hidden text-subtle hover:text-ink p-1.5 rounded-full"
            aria-label="Close sidebar"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-3 pb-3">
          <button
            type="button"
            onClick={startNew}
            className="w-full flex items-center justify-center gap-2 rounded-full bg-ink text-paper text-sm py-2 hover:opacity-90"
          >
            <Plus className="h-4 w-4" strokeWidth={2.2} />
            New chat
          </button>
        </div>

        <div className="px-3 pb-3">
          <label className="flex items-center gap-2 rounded-full bg-white/80 px-3 py-1.5 shadow-sm">
            <Search className="h-3.5 w-3.5 text-subtle shrink-0" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search chats"
              className="w-full bg-transparent text-sm outline-none placeholder:text-subtle"
            />
          </label>
        </div>

        <nav className="flex-1 min-h-0 overflow-y-auto px-2 pb-2">
          {threads.length === 0 && (
            <div className="px-3 py-8 flex flex-col items-center text-center gap-2">
              <TathyaMark pose="grow" size={88} />
              <p className="text-xs text-subtle leading-relaxed">Start a chat to see it here.</p>
            </div>
          )}
          {groups.map((group) => (
            <div key={group.label} className="mb-4">
              <div className="px-3 py-1.5 eyebrow">{group.label}</div>
              <ul className="space-y-0.5">
                {group.items.map((t) => {
                  const selected = t.id === activeId;
                  return (
                    <li key={t.id} className="group relative">
                      <button
                        type="button"
                        onClick={() => selectThread(t.id)}
                        className={`w-full text-left rounded-xl px-3 py-2 pr-8 transition ${
                          selected ? "bg-white shadow-sm" : "hover:bg-white/60"
                        }`}
                      >
                        <div className="text-sm text-ink leading-snug line-clamp-2">{t.title}</div>
                      </button>
                      <button
                        type="button"
                        aria-label={`Delete ${t.title}`}
                        onClick={() => removeThread(t.id)}
                        className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 rounded-full text-subtle opacity-0 group-hover:opacity-100 hover:text-cmpr-700"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
      </aside>

      <section className="flex-1 min-w-0 min-h-0 flex flex-col census-chat-shell">
        <div className="flex items-center gap-3 px-4 pt-3 pb-1 md:hidden">
          <button
            type="button"
            className="text-subtle hover:text-ink p-1.5 rounded-full"
            aria-label="Open chats"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>
        </div>
        <div className="flex-1 min-h-0 flex flex-col">
          {ready && activeId ? (
            <CensusChat
              key={activeId}
              chatId={activeId}
              layout="page"
              initialMessages={active?.messages}
              onMessagesChange={onMessagesChange}
            />
          ) : null}
        </div>
      </section>
    </div>
  );
}
