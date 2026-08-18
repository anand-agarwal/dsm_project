import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";

export function SiteLayout({
  children,
  footer = true,
  fill = false,
}: {
  children: ReactNode;
  footer?: boolean;
  fill?: boolean;
}) {
  return (
    <div className={`${fill ? "h-dvh overflow-hidden" : "min-h-screen"} flex flex-col text-foreground`}>
      <header className="border-b border-rule/80 shrink-0">
        <div className={`${fill ? "px-5" : "max-w-[1280px] mx-auto px-6"} py-3 md:py-4 flex items-baseline justify-between gap-6`}>
          <Link to="/" className="flex items-baseline gap-3 group">
            <span className="brand-hi text-3xl font-semibold tracking-tight">
              बचपन
            </span>
            <span className="hidden sm:inline eyebrow">India's Child Marriage Atlas</span>
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
              to="/ask"
              className="text-subtle hover:text-foreground transition-colors data-[status=active]:text-foreground data-[status=active]:font-medium"
            >
              Ask
            </Link>
            <Link
              to="/about"
              className="text-subtle hover:text-foreground transition-colors data-[status=active]:text-foreground data-[status=active]:font-medium"
            >
              About
            </Link>
            <Link
              to="/blog"
              className="text-subtle hover:text-foreground transition-colors data-[status=active]:text-foreground data-[status=active]:font-medium"
            >
              Blog
            </Link>
          </nav>
        </div>
      </header>
      <main className={`flex-1 ${fill ? "min-h-0 flex flex-col relative" : ""}`}>{children}</main>
      {footer && (
        <footer className="border-t border-rule/80 mt-16">
          <div className="max-w-[1280px] mx-auto px-6 py-8 text-xs text-subtle">
            © 2026, Anand Agarwal and Neha Palak
          </div>
        </footer>
      )}
    </div>
  );
}
