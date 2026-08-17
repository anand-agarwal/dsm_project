import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import { Maximize2, Minimize2, Sparkles, X } from "lucide-react";
import { CensusChat } from "@/components/CensusChat";

const MIN_W = 320;
const DEFAULT_W = 420;
const STORAGE_W = "bachpan-agent-width";
const STORAGE_EXPANDED = "bachpan-agent-expanded";

type AgentChatContextValue = {
  open: boolean;
  setOpen: (open: boolean) => void;
};

const AgentChatContext = createContext<AgentChatContextValue | null>(null);

export function useAgentChat() {
  const ctx = useContext(AgentChatContext);
  if (!ctx) {
    throw new Error("useAgentChat must be used inside AgentChatProvider");
  }
  return ctx;
}

export function AgentChatProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (typeof window !== "undefined" && window.location.hash === "#ask") {
      setOpen(true);
    }
  }, []);
  return (
    <AgentChatContext.Provider value={{ open, setOpen }}>
      {children}
    </AgentChatContext.Provider>
  );
}

function maxPanelWidth() {
  if (typeof window === "undefined") return 720;
  return Math.min(1100, Math.max(MIN_W, window.innerWidth - 24));
}

function expandedPanelWidth() {
  if (typeof window === "undefined") return 720;
  return Math.min(960, Math.max(560, Math.round(window.innerWidth * 0.48)));
}

export function AgentDrawer() {
  const { open, setOpen } = useAgentChat();
  const [width, setWidth] = useState(DEFAULT_W);
  const [expanded, setExpanded] = useState(false);
  const widthRef = useRef(width);
  const expandedRef = useRef(expanded);
  const drag = useRef<{ startX: number; startW: number } | null>(null);

  widthRef.current = width;
  expandedRef.current = expanded;

  useEffect(() => {
    const storedW = sessionStorage.getItem(STORAGE_W);
    const storedExp = sessionStorage.getItem(STORAGE_EXPANDED);
    if (storedExp === "1") {
      setExpanded(true);
      setWidth(expandedPanelWidth());
      return;
    }
    if (storedW) {
      const n = Number(storedW);
      if (n >= MIN_W) setWidth(Math.min(n, maxPanelWidth()));
    }
  }, []);

  const persistWidth = useCallback((next: number, isExpanded: boolean) => {
    sessionStorage.setItem(STORAGE_W, String(next));
    sessionStorage.setItem(STORAGE_EXPANDED, isExpanded ? "1" : "0");
  }, []);

  const onPointerMove = useCallback((e: PointerEvent) => {
    if (!drag.current) return;
    const cap = maxPanelWidth();
    const next = Math.min(cap, Math.max(MIN_W, drag.current.startW + (drag.current.startX - e.clientX)));
    widthRef.current = next;
    expandedRef.current = false;
    setExpanded(false);
    setWidth(next);
  }, []);

  const onPointerUp = useCallback(() => {
    if (!drag.current) return;
    drag.current = null;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    persistWidth(widthRef.current, expandedRef.current);
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", onPointerUp);
  }, [onPointerMove, persistWidth]);

  const startDrag = (e: ReactPointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { startX: e.clientX, startW: widthRef.current };
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
  };

  useEffect(() => {
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    };
  }, [onPointerMove, onPointerUp]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setOpen]);

  const toggleExpanded = () => {
    const next = !expanded;
    const nextW = next ? expandedPanelWidth() : DEFAULT_W;
    setExpanded(next);
    setWidth(nextW);
    persistWidth(nextW, next);
  };

  return (
    <>
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Open census chat"
          className="fixed bottom-6 right-6 z-40 h-14 w-14 rounded-full bg-ink text-paper shadow-[0_12px_28px_oklch(0.25_0.03_50_/_0.28)] flex items-center justify-center hover:scale-105 hover:opacity-95 transition-transform"
        >
          <Sparkles className="h-6 w-6" strokeWidth={1.75} />
        </button>
      )}

      {open && (
        <button
          type="button"
          aria-label="Close agent"
          className="fixed inset-0 z-40 bg-ink/10"
          onClick={() => setOpen(false)}
        />
      )}

      <aside
        className="census-chat-shell fixed z-50 flex flex-col overflow-hidden rounded-[1.35rem] shadow-[0_20px_50px_oklch(0.3_0.04_50_/_0.18)]"
        style={{
          width,
          top: 12,
          right: 12,
          height: "calc(100dvh - 24px)",
          transform: open ? "translateX(0)" : "translateX(calc(100% + 24px))",
          pointerEvents: open ? "auto" : "none",
          transition: "transform 220ms ease-out",
        }}
        aria-hidden={!open}
      >
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize chat"
          onPointerDown={startDrag}
          className="absolute left-0 top-0 z-10 h-full w-3 cursor-col-resize touch-none"
        />
        <div className="flex items-center justify-between gap-3 px-5 pt-4 pb-3">
          <div className="min-w-0">
            <div className="eyebrow">Census agent</div>
            <div className="font-display text-[1.35rem] leading-tight text-ink">Ask the tables</div>
          </div>
          <div className="flex items-center gap-0.5 shrink-0 rounded-full bg-white/70 p-0.5 shadow-sm">
            <button
              type="button"
              onClick={toggleExpanded}
              aria-label={expanded ? "Restore chat width" : "Expand chat"}
              className="text-subtle hover:text-ink p-1.5 rounded-full"
            >
              {expanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </button>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
              className="text-subtle hover:text-ink p-1.5 rounded-full"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
        <p className="px-5 pb-2 text-xs text-subtle">
          2001 and 2011 C-series · rates from Postgres
        </p>
        <div className="flex-1 min-h-0 flex flex-col">
          <CensusChat />
        </div>
      </aside>
    </>
  );
}
