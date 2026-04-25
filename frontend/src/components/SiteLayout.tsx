import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { Chatbot } from "./Chatbot";

export function SiteLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <header className="border-b border-rule">
        <div className="max-w-[1280px] mx-auto px-6 py-4 flex items-baseline justify-between gap-6">
          <Link to="/" className="flex items-baseline gap-3 group">
            <span className="font-display text-2xl font-semibold tracking-tight">
              Bharat<span className="text-cmpr-700">.</span>Census
            </span>
            <span className="hidden sm:inline eyebrow">An India child-marriage atlas</span>
          </Link>
          <nav className="flex items-center gap-5 text-sm">
            <Link
              to="/"
              activeOptions={{ exact: true }}
              className="text-subtle hover:text-foreground transition-colors data-[status=active]:text-foreground data-[status=active]:font-medium"
            >
              Atlas
            </Link>
            <Link
              to="/explore"
              className="text-subtle hover:text-foreground transition-colors data-[status=active]:text-foreground data-[status=active]:font-medium"
            >
              Raw tables
            </Link>
            <Link
              to="/about"
              className="text-subtle hover:text-foreground transition-colors data-[status=active]:text-foreground data-[status=active]:font-medium"
            >
              About
            </Link>
          </nav>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t border-rule mt-16">
        <div className="max-w-[1280px] mx-auto px-6 py-8 text-xs text-subtle flex flex-wrap gap-x-6 gap-y-2">
          <span>Census of India · 2001 & 2011</span>
          <span>Tables C-02 → C-12</span>
          <span className="ml-auto">Synthetic dataset for demonstration</span>
        </div>
      </footer>
      <Chatbot />
    </div>
  );
}
