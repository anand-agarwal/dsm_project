import { matchResearchSource } from "./researchSources";

const DDG_HTML = "https://html.duckduckgo.com/html/";
const MAX_RESULTS = 8;
const FETCH_MS = 12_000;
const UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36";

export type ResearchHit = {
  title: string;
  url: string;
  snippet: string;
  sourceId?: string;
  org?: string;
};

export type SearchResearchInput = {
  query: string;
  maxResults?: number;
};

export type SearchResearchResult = {
  ok: boolean;
  error?: string;
  query: string;
  ddgQuery: string;
  backend?: "firecrawl" | "duckduckgo" | "openalex";
  hits: ResearchHit[];
  dropped: number;
  note: string;
};

export type SearchFetcher = (url: string, init: RequestInit) => Promise<Response>;

function env(name: string): string | undefined {
  const meta = (import.meta as { env?: Record<string, string | undefined> }).env;
  return (meta?.[name] ?? process.env[name])?.trim() || undefined;
}

function firecrawlApiKey(): string | undefined {
  return env("FIRECRAWL_API_KEY");
}

async function fetchWithTimeout(
  fetchImpl: SearchFetcher,
  url: string,
  init: RequestInit,
  timeoutMs = FETCH_MS,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetchImpl(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

function decodeEntities(text: string): string {
  return text
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&apos;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)));
}

export function stripHtml(html: string): string {
  return decodeEntities(html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim());
}

export function unwrapDdgHref(href: string): string {
  try {
    const absolute = new URL(href, "https://html.duckduckgo.com/");
    const uddg = absolute.searchParams.get("uddg");
    if (uddg) return uddg;
    return absolute.href;
  } catch {
    return href;
  }
}

function isJunkUrl(url: string): boolean {
  let host = "";
  try {
    host = new URL(url).hostname.toLowerCase();
  } catch {
    return true;
  }
  if (!host || host === "duckduckgo.com" || host.endsWith(".duckduckgo.com")) return true;
  if (url.startsWith("javascript:")) return true;
  return false;
}

type RawHit = { title: string; url: string; snippet: string };

export function detectDdgChallenge(html: string, status?: number): boolean {
  if (status === 202 || status === 403 || status === 429) return true;
  return /anomaly-modal|cc=botnet|unfortunately,\s+bots/i.test(html);
}

/** Parse DuckDuckGo HTML search (same page duckduckgo-search / DDGS uses). */
export function parseDdgHtml(html: string): RawHit[] {
  if (detectDdgChallenge(html)) return [];
  const hits: RawHit[] = [];
  const blockRe =
    /<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>[\s\S]*?(?:class="[^"]*result__snippet[^"]*"[^>]*>([\s\S]*?)<\/(?:a|td|span)>|$)/gi;
  for (const match of html.matchAll(blockRe)) {
    const url = unwrapDdgHref(match[1]);
    const title = stripHtml(match[2]);
    const snippet = stripHtml(match[3] ?? "");
    if (!title || isJunkUrl(url)) continue;
    hits.push({ title, url, snippet });
  }
  if (hits.length > 0) return dedupeRaw(hits);

  const linkRe = /<a[^>]*rel="nofollow"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi;
  for (const match of html.matchAll(linkRe)) {
    const url = unwrapDdgHref(match[1]);
    const title = stripHtml(match[2]);
    if (!title || isJunkUrl(url)) continue;
    hits.push({ title, url, snippet: "" });
  }
  return dedupeRaw(hits);
}

function dedupeRaw(hits: RawHit[]): RawHit[] {
  const seen = new Set<string>();
  const out: RawHit[] = [];
  for (const h of hits) {
    if (seen.has(h.url)) continue;
    seen.add(h.url);
    out.push(h);
  }
  return out;
}

export function toResearchHits(raw: RawHit[]): ResearchHit[] {
  return raw.map((row) => {
    const source = matchResearchSource(row.url);
    return {
      title: row.title,
      url: row.url,
      snippet: row.snippet,
      sourceId: source?.id,
      org: source?.org,
    };
  });
}

async function fetchDdgHtml(
  ddgQuery: string,
  fetchImpl: SearchFetcher,
): Promise<{ html: string; status: number }> {
  const body = new URLSearchParams({ q: ddgQuery, kl: "in-en" });
  const res = await fetchWithTimeout(fetchImpl, DDG_HTML, {
    method: "POST",
    headers: {
      "User-Agent": UA,
      Accept: "text/html",
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
    redirect: "follow",
  });
  const html = await res.text();
  if (!res.ok && res.status !== 202) {
    throw new Error(`DuckDuckGo HTTP ${res.status}`);
  }
  return { html, status: res.status };
}

export function parseFirecrawlSearch(payload: unknown): RawHit[] {
  const root = payload as {
    data?: unknown;
    web?: Array<{ title?: string; url?: string; description?: string; markdown?: string }>;
  };
  let rows: Array<{ title?: string; url?: string; description?: string; markdown?: string }> = [];
  if (Array.isArray(root.data)) {
    rows = root.data as typeof rows;
  } else if (root.data && typeof root.data === "object" && Array.isArray((root.data as { web?: unknown }).web)) {
    rows = (root.data as { web: typeof rows }).web;
  } else if (Array.isArray(root.web)) {
    rows = root.web;
  }
  return dedupeRaw(
    rows
      .map((r) => ({
        title: stripHtml(r.title ?? ""),
        url: r.url ?? "",
        snippet: stripHtml(r.description || (r.markdown ?? "").slice(0, 400)),
      }))
      .filter((h) => h.title && h.url && !isJunkUrl(h.url)),
  );
}

export function parseOpenAlexWorks(payload: unknown): RawHit[] {
  const results = (payload as { results?: Array<Record<string, unknown>> }).results;
  if (!Array.isArray(results)) return [];
  const hits: RawHit[] = [];
  for (const work of results) {
    const title = String(work.display_name ?? "").trim();
    const doi = typeof work.doi === "string" ? work.doi : "";
    const id = typeof work.id === "string" ? work.id : "";
    const url = doi.startsWith("http") ? doi : doi ? `https://doi.org/${doi.replace(/^https?:\/\/doi.org\//, "")}` : id;
    if (!title || !url) continue;
    const year = work.publication_year ? String(work.publication_year) : "";
    const venue = (work.primary_location as { source?: { display_name?: string } } | undefined)?.source
      ?.display_name;
    hits.push({
      title,
      url,
      snippet: [year, venue].filter(Boolean).join(" · "),
    });
  }
  return dedupeRaw(hits);
}

async function searchFirecrawl(
  query: string,
  maxResults: number,
  fetchImpl: SearchFetcher,
  apiKey: string,
): Promise<RawHit[]> {
  const res = await fetchWithTimeout(fetchImpl, "https://api.firecrawl.dev/v1/search", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({ query, limit: maxResults, timeout: 20000 }),
  }, 25_000);
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Firecrawl HTTP ${res.status}${detail ? `: ${detail.slice(0, 180)}` : ""}`);
  }
  return parseFirecrawlSearch(await res.json()).slice(0, maxResults);
}

async function searchOpenAlex(
  query: string,
  maxResults: number,
  fetchImpl: SearchFetcher,
): Promise<RawHit[]> {
  const url = `https://api.openalex.org/works?search=${encodeURIComponent(query)}&per_page=${maxResults}`;
  const res = await fetchWithTimeout(fetchImpl, url, {
    headers: {
      Accept: "application/json",
      "User-Agent": "BachpanAtlas/1.0 (https://github.com; mailto:research@localhost)",
    },
  });
  if (!res.ok) throw new Error(`OpenAlex HTTP ${res.status}`);
  return parseOpenAlexWorks(await res.json()).slice(0, maxResults);
}

const NOTE = "Snippets are not Census C-table cells. Rates still come from run_census_query.";

export async function searchResearch(
  input: SearchResearchInput,
  deps?: { fetch?: SearchFetcher; firecrawlKey?: string | null },
): Promise<SearchResearchResult> {
  const query = input.query?.trim() ?? "";
  const maxResults = Math.min(MAX_RESULTS, Math.max(1, input.maxResults ?? MAX_RESULTS));
  const ddgQuery = query;

  if (!query) {
    return { ok: false, error: "query is required", query, ddgQuery, hits: [], dropped: 0, note: NOTE };
  }

  const fetchImpl = deps?.fetch ?? fetch;
  const errors: string[] = [];
  const key = deps?.firecrawlKey === null ? undefined : (deps?.firecrawlKey ?? firecrawlApiKey());

  if (key) {
    try {
      const hits = toResearchHits(await searchFirecrawl(query, maxResults, fetchImpl, key));
      if (hits.length > 0) {
        return {
          ok: true,
          query,
          ddgQuery,
          backend: "firecrawl",
          hits,
          dropped: 0,
          note: `${NOTE} Backend: Firecrawl search.`,
        };
      }
      errors.push("Firecrawl returned 0 hits");
    } catch (err) {
      errors.push(err instanceof Error ? err.message : String(err));
    }
  }

  try {
    const { html, status } = await fetchDdgHtml(ddgQuery, fetchImpl);
    if (detectDdgChallenge(html, status)) {
      errors.push("DuckDuckGo bot check");
    } else {
      const hits = toResearchHits(parseDdgHtml(html)).slice(0, maxResults);
      if (hits.length > 0) {
        return { ok: true, query, ddgQuery, backend: "duckduckgo", hits, dropped: 0, note: NOTE };
      }
      errors.push("DuckDuckGo returned 0 hits");
    }
  } catch (err) {
    errors.push(err instanceof Error ? err.message : String(err));
  }

  try {
    const hits = toResearchHits(await searchOpenAlex(query, maxResults, fetchImpl));
    if (hits.length > 0) {
      return {
        ok: true,
        query,
        ddgQuery,
        backend: "openalex",
        hits,
        dropped: 0,
        note: `${NOTE} Backend: OpenAlex scholarly works.`,
      };
    }
    errors.push("OpenAlex returned 0 hits");
  } catch (err) {
    errors.push(err instanceof Error ? err.message : String(err));
  }

  return {
    ok: false,
    error: errors.join("; "),
    query,
    ddgQuery,
    hits: [],
    dropped: 0,
    note: NOTE,
  };
}

export function formatSearchResearchForModel(result: SearchResearchResult) {
  return {
    ok: result.ok,
    error: result.error,
    query: result.query,
    backend: result.backend,
    hitCount: result.hits.length,
    note: result.note,
    hits: result.hits.map((h) => ({
      title: h.title,
      url: h.url,
      snippet: h.snippet.slice(0, 320),
      org: h.org,
      sourceId: h.sourceId,
    })),
  };
}
