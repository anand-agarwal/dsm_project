import sources from "./researchSources.json";

export type ResearchBucket = "official-statistics" | "official-policy" | "law" | "un" | "research-ngo";

export type ResearchSource = {
  id: string;
  host: string;
  org: string;
  bucket: ResearchBucket;
  useFor: string[];
  alsoHosts?: string[];
  caveat?: string;
};

export const RESEARCH_SOURCE_CATALOG = sources;

export const RESEARCH_SOURCES = sources.sources as ResearchSource[];

export const DENIED_RESEARCH_HOSTS = sources.deniedHosts as string[];

export function allAllowedHosts(): string[] {
  const hosts = new Set<string>();
  for (const s of RESEARCH_SOURCES) {
    hosts.add(s.host.toLowerCase());
    for (const extra of s.alsoHosts ?? []) hosts.add(extra.toLowerCase());
  }
  return [...hosts];
}

function hostOf(urlOrHost: string): string {
  try {
    const withProto = urlOrHost.includes("://") ? urlOrHost : `https://${urlOrHost}`;
    return new URL(withProto).hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return urlOrHost.replace(/^www\./, "").toLowerCase();
  }
}

export function isDeniedResearchHost(urlOrHost: string): boolean {
  const host = hostOf(urlOrHost);
  return DENIED_RESEARCH_HOSTS.some((d) => host === d || host.endsWith(`.${d}`));
}

export function matchResearchSource(urlOrHost: string): ResearchSource | null {
  if (isDeniedResearchHost(urlOrHost)) return null;
  const host = hostOf(urlOrHost);
  for (const s of RESEARCH_SOURCES) {
    const aliases = [s.host, ...(s.alsoHosts ?? [])].map((h) => h.toLowerCase());
    if (aliases.some((a) => host === a || host.endsWith(`.${a}`))) return s;
  }
  return null;
}

/** site: clauses for a DuckDuckGo query scoped to one bucket. */
export function duckDuckGoSiteFilter(bucket?: ResearchBucket): string {
  const hosts = RESEARCH_SOURCES.filter((s) => !bucket || s.bucket === bucket).flatMap((s) => [
    s.host,
    ...(s.alsoHosts ?? []),
  ]);
  const unique = [...new Set(hosts)];
  if (unique.length === 0) return "";
  return unique.map((h) => `site:${h}`).join(" OR ");
}
