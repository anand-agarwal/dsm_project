import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ReactNode } from "react";
import { matchResearchSource } from "@/agent/researchSources";

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

function childText(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(childText).join("");
  if (node && typeof node === "object" && "props" in node) {
    return childText((node as { props?: { children?: ReactNode } }).props?.children);
  }
  return "";
}

function CitationLink({ href, children }: { href: string; children?: ReactNode }) {
  const label = childText(children);
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

const components: Components = {
  h1: ({ children }) => (
    <h2 className="mt-3 mb-1.5 text-base font-semibold text-ink first:mt-0">{children}</h2>
  ),
  h2: ({ children }) => (
    <h2 className="mt-3 mb-1.5 text-base font-semibold text-ink first:mt-0">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="mt-3 mb-1.5 text-[15px] font-semibold text-ink first:mt-0">{children}</h3>
  ),
  h4: ({ children }) => (
    <h4 className="mt-2.5 mb-1 text-sm font-semibold text-ink first:mt-0">{children}</h4>
  ),
  p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
  ul: ({ children }) => (
    <ul className="my-2 list-disc space-y-1.5 pl-5 marker:text-subtle first:mt-0 last:mb-0">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="my-2 list-decimal space-y-1.5 pl-5 marker:text-subtle first:mt-0 last:mb-0">
      {children}
    </ol>
  ),
  li: ({ children }) => <li className="leading-relaxed [&>p]:my-0">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  a: ({ href, children }) => {
    if (!href) return <>{children}</>;
    const url = tidyUrl(href);
    if (!/^https?:\/\//i.test(url)) return <>{children}</>;
    return <CitationLink href={url}>{children}</CitationLink>;
  },
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-2 border-edu-300 pl-3 text-subtle">{children}</blockquote>
  ),
  hr: () => <hr className="my-3 border-edu-100" />,
  code: ({ className, children }) => {
    const block = /language-/.test(className ?? "");
    if (block) {
      return (
        <code className="block overflow-x-auto rounded-lg bg-paper px-3 py-2 text-[12px] leading-relaxed">
          {children}
        </code>
      );
    }
    return (
      <code className="rounded bg-paper px-1 py-0.5 text-[12px]">{children}</code>
    );
  },
  pre: ({ children }) => <pre className="my-2 overflow-x-auto">{children}</pre>,
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto">
      <table className="w-full border-collapse text-left text-[13px]">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border-b border-edu-200 px-2 py-1.5 font-semibold">{children}</th>
  ),
  td: ({ children }) => <td className="border-b border-edu-100 px-2 py-1.5 align-top">{children}</td>,
};

export function ChatMarkdown({ text }: { text: string }) {
  return (
    <div className="chat-md text-sm leading-relaxed text-ink">
      <Markdown remarkPlugins={[remarkGfm]} skipHtml components={components}>
        {text}
      </Markdown>
    </div>
  );
}
