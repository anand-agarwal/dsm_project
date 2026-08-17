import { TABLE_CARDS } from "./catalog";
import type {
  LookupSchemaInput,
  LookupSchemaResult,
  MetricId,
  RankedTableCard,
  SocialGroup,
  TableCard,
} from "./types";

const DEFAULT_LIMIT = 3;
const MIN_SCORE = 4;

const STOPWORDS = new Set([
  "a",
  "an",
  "the",
  "in",
  "for",
  "of",
  "and",
  "or",
  "to",
  "is",
  "what",
  "whats",
  "how",
  "many",
  "much",
  "show",
  "me",
  "please",
  "india",
  "indian",
  "state",
  "year",
  "2001",
  "2011",
  "total",
  "rural",
  "urban",
  "girls",
  "boys",
  "women",
  "men",
  "female",
  "male",
  "persons",
]);

const STATE_HINTS = [
  "andhra",
  "arunachal",
  "assam",
  "bihar",
  "chhattisgarh",
  "goa",
  "gujarat",
  "haryana",
  "himachal",
  "jammu",
  "jharkhand",
  "karnataka",
  "kerala",
  "madhya",
  "maharashtra",
  "manipur",
  "meghalaya",
  "mizoram",
  "nagaland",
  "odisha",
  "orissa",
  "punjab",
  "rajasthan",
  "sikkim",
  "tamil",
  "telangana",
  "tripura",
  "uttar",
  "uttarakhand",
  "bengal",
  "delhi",
  "chandigarh",
  "puducherry",
  "andaman",
  "ladakh",
  "lakshadweep",
  "daman",
  "dadra",
];

const METRIC_SYNONYMS: Record<MetricId, string[]> = {
  literacy_rate: [
    "literacy",
    "literate",
    "can read",
    "reading",
    "read",
    "educated",
  ],
  illiteracy_rate: ["illiteracy", "illiterate", "cannot read", "can't read"],
  currently_married_share: [
    "currently married",
    "married",
    "cmpr",
    "child marriage",
    "child marriages",
    "early marriage",
    "prevalence",
  ],
  never_married_share: ["never married", "unmarried"],
  age_at_marriage_count: ["age at marriage", "ever married", "duration of marriage"],
  school_attendance_share: [
    "school attendance",
    "attending school",
    "in school",
    "enrolment",
    "enrollment",
  ],
  not_attending_worker_share: [
    "child labour",
    "child labor",
    "out of school",
    "not attending",
  ],
  population: ["population", "how many people", "headcount"],
};

const SOCIAL_SYNONYMS: Record<SocialGroup | "religion", string[]> = {
  sc: ["sc", "scheduled caste", "scheduled castes", "dalit"],
  st: ["st", "scheduled tribe", "scheduled tribes", "adivasi", "tribal", "tribe"],
  total: [],
  religion: [
    "religion",
    "hindu",
    "muslim",
    "christian",
    "sikh",
    "buddhist",
    "jain",
  ],
};

function normalize(text: string): string {
  return text
    .toLowerCase()
    .replace(/['’]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function includesPhrase(haystack: string, phrase: string): boolean {
  const h = ` ${normalize(haystack)} `;
  const p = ` ${normalize(phrase)} `;
  return h.includes(p);
}

export function detectSocialGroup(
  query: string,
): SocialGroup | "religion" | null {
  const q = normalize(query);
  if (SOCIAL_SYNONYMS.sc.some((s) => includesPhrase(q, s))) return "sc";
  if (SOCIAL_SYNONYMS.st.some((s) => includesPhrase(q, s))) return "st";
  if (SOCIAL_SYNONYMS.religion.some((s) => includesPhrase(q, s))) return "religion";
  return null;
}

export function detectMetrics(query: string): MetricId[] {
  const hits: MetricId[] = [];
  for (const [id, phrases] of Object.entries(METRIC_SYNONYMS) as [MetricId, string[]][]) {
    if (phrases.some((p) => includesPhrase(query, p))) hits.push(id);
  }
  return hits;
}

function queryTerms(query: string): string[] {
  const n = normalize(query);
  const tokens = n.split(" ").filter((t) => t.length > 1 && !STOPWORDS.has(t) && !STATE_HINTS.includes(t));
  const phrases: string[] = [];
  for (let i = 0; i < tokens.length - 1; i++) {
    phrases.push(`${tokens[i]} ${tokens[i + 1]}`);
  }
  return [...phrases, ...tokens];
}

function cardSearchBlob(card: TableCard): string {
  return [
    card.id,
    card.censusTable,
    card.postgresTable,
    card.topic,
    card.purpose,
    ...card.synonyms,
    ...card.metrics.map((m) => `${m.id} ${m.label}`),
  ].join(" ");
}

function mentionedCensusTables(query: string): string[] {
  const found: string[] = [];
  const codes: Array<[string, string]> = [
    ["02", "C-02"],
    ["03", "C-03"],
    ["04", "C-04"],
    ["05", "C-05"],
    ["06", "C-06"],
    ["07", "C-07"],
    ["08", "C-08"],
    ["09", "C-09"],
    ["12", "C-12"],
  ];
  for (const [num, name] of codes) {
    if (new RegExp(`\\bc[-\\s]?${num}\\b`, "i").test(query)) found.push(name);
  }
  return found;
}

function scoreCard(
  card: TableCard,
  query: string,
  terms: string[],
  social: SocialGroup | "religion" | null,
  metrics: MetricId[],
  mentioned: string[],
): { score: number; matchedTerms: string[] } {
  const blob = cardSearchBlob(card);
  const matchedTerms: string[] = [];
  let score = 0;

  for (const term of terms) {
    if (term.length < 2) continue;
    if (includesPhrase(blob, term) || includesPhrase(card.postgresTable.replaceAll("_", " "), term)) {
      score += term.includes(" ") ? 4 : 2;
      matchedTerms.push(term);
    }
  }

  if (metrics.length > 0) {
    const cardMetricIds = new Set(card.metrics.map((m) => m.id));
    const overlap = metrics.filter((m) => cardMetricIds.has(m));
    if (overlap.length > 0) {
      score += 10 * overlap.length;
      matchedTerms.push(...overlap);
    } else if (mentioned.length === 0) {
      score -= 16;
    }
  }

  if (social) {
    if (card.socialGroup === social) score += 8;
    else score -= 6;
  } else if (card.socialGroup === "sc" || card.socialGroup === "st") {
    score -= 2;
  } else if (card.socialGroup === "religion") {
    score -= 1;
  }

  if (mentioned.length > 0) {
    if (mentioned.some((name) => card.censusTable === name || card.censusTable.startsWith(name))) {
      score += 12;
    } else {
      score -= 8;
    }
  }

  if (/\bappendix\b/i.test(query) && card.censusTable.toLowerCase().includes("appendix")) {
    score += 8;
  }

  return { score, matchedTerms: [...new Set(matchedTerms)] };
}

/**
 * Keyword schema linking: retrieve 1–3 census table cards for a question.
 * No LLM, no network. Later wired as the lookup_schema agent tool.
 */
export function lookupSchema(input: LookupSchemaInput): LookupSchemaResult {
  const query = input.query?.trim() ?? "";
  const limit = input.limit ?? DEFAULT_LIMIT;
  const detectedSocialGroup = input.socialGroup ?? detectSocialGroup(query);
  const detectedMetrics = input.metricId ? [input.metricId] : detectMetrics(query);

  if (!query && !input.socialGroup && !input.metricId) {
    return { query, detectedSocialGroup: null, detectedMetrics: [], cards: [] };
  }

  const terms = query ? queryTerms(query) : [];
  const mentioned = query ? mentionedCensusTables(query) : [];
  const ranked: RankedTableCard[] = TABLE_CARDS.map((card) => {
    const { score, matchedTerms } = scoreCard(
      card,
      query,
      terms,
      detectedSocialGroup,
      detectedMetrics,
      mentioned,
    );
    return { ...card, score, matchedTerms };
  })
    .filter((c) => c.score >= MIN_SCORE)
    .sort((a, b) => b.score - a.score || a.id.localeCompare(b.id))
    .slice(0, Math.max(1, limit));

  return {
    query,
    detectedSocialGroup,
    detectedMetrics,
    cards: ranked,
  };
}

/** Compact payload the model should see (no synonym lists). */
export function formatLookupSchemaForModel(result: LookupSchemaResult) {
  return {
    query: result.query,
    detectedSocialGroup: result.detectedSocialGroup,
    detectedMetrics: result.detectedMetrics,
    cards: result.cards.map((c) => ({
      id: c.id,
      censusTable: c.censusTable,
      postgresTable: c.postgresTable,
      socialGroup: c.socialGroup,
      topic: c.topic,
      purpose: c.purpose,
      grain: c.grain,
      filterColumns: c.filterColumns,
      metrics: c.metrics,
      twins: c.twins,
      caveats: c.caveats,
      score: c.score,
    })),
  };
}
