import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { z } from "zod";
import { CARD_BY_ID, CARD_BY_POSTGRES, TABLE_CARDS } from "./catalog";
import { resolveAgeLabels } from "./ageBrackets";
import type { MetricId, Sex, SocialGroup, TableCard, Year } from "./types";
import { METRIC_IDS } from "./types";
import { STATES, canonicalStateName } from "../data/states";

const IDENT = /^[a-z][a-z0-9_]*$/;
const TABLE_NAME = /^raw_c_[a-z0-9_]+$/;
const MAX_LIMIT = 200;
const DEFAULT_LIMIT = 50;
const STATE_LEVEL_CODES = ["000", "00", "0"];

const DEFAULT_CARD: Record<MetricId, Partial<Record<SocialGroup | "religion", string>>> = {
  literacy_rate: { total: "c08_total", sc: "c08_sc", st: "c08_st", religion: "c09_religion" },
  illiteracy_rate: { total: "c08_total", sc: "c08_sc", st: "c08_st", religion: "c09_religion" },
  currently_married_share: {
    total: "c02_total",
    sc: "c02_sc",
    st: "c02_st",
    religion: "c03_appendix_religion",
  },
  never_married_share: {
    total: "c02_total",
    sc: "c02_sc",
    st: "c02_st",
    religion: "c03_appendix_religion",
  },
  age_at_marriage_count: {
    total: "c04_total",
    sc: "c04_total",
    st: "c04_total",
    religion: "c05_religion",
  },
  school_attendance_share: { total: "c12_total", sc: "c12_sc", st: "c12_st" },
  not_attending_worker_share: { total: "c12_total", sc: "c12_sc", st: "c12_st" },
  population: { total: "c08_total", sc: "c08_sc", st: "c08_st", religion: "c09_religion" },
};

/** Model tool calls send year as a JSON number or string; both are valid. */
export const censusYearInputSchema = z.union([
  z.literal(2001),
  z.literal(2011),
  z.literal("2001"),
  z.literal("2011"),
]);

export const censusQueryDslSchema = z.object({
  cardId: z.string().min(1).optional(),
  year: censusYearInputSchema.transform((v) => Number(v) as Year),
  state: z.string().min(1),
  area: z.enum(["Total", "Rural", "Urban"]).default("Total"),
  sex: z.enum(["persons", "male", "female"]).default("female"),
  socialGroup: z.enum(["total", "sc", "st", "religion"]).optional(),
  metric: z.enum(METRIC_IDS),
  ageBand: z.string().min(1).default("all"),
  religion: z.string().min(1).optional(),
  limit: z.number().int().min(1).max(MAX_LIMIT).default(DEFAULT_LIMIT),
});

export type CensusQueryDsl = z.infer<typeof censusQueryDslSchema>;

export type FilterOp =
  | { op: "eq"; column: string; value: string | number }
  | { op: "in"; column: string; values: Array<string | number> }
  | { op: "ilike"; column: string; value: string };

export type CompiledCensusQuery = {
  postgresTable: string;
  select: string[];
  filters: FilterOp[];
  limit: number;
  card: TableCard;
  dsl: CensusQueryDsl;
  ageNote?: string;
  aggregateAgeLabels: string[] | null;
};

export type ComputedMetric = {
  metric: MetricId;
  sex: Sex;
  numerator: number | null;
  denominator: number | null;
  /** Percent (0–100), matching the Python index builders. Null if not a rate or den is 0. */
  value: number | null;
  numeratorColumn: string;
  denominatorColumn: string | null;
  sourceRowCount: number;
};

export type CensusQueryResult = {
  ok: boolean;
  error?: string;
  hint?: string;
  compiled: CompiledCensusQuery | null;
  rows: Record<string, unknown>[];
  computed: ComputedMetric | null;
  filtersUsed: FilterOp[];
};

export class CensusQueryError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CensusQueryError";
  }
}

export type CensusRowFetcher = (compiled: CompiledCensusQuery) => Promise<Record<string, unknown>[]>;

function assertIdent(name: string, kind: string) {
  if (!IDENT.test(name)) {
    throw new CensusQueryError(`Refusing to use ${kind} '${name}'`);
  }
}

function env(name: string): string | undefined {
  const meta = (import.meta as { env?: Record<string, string | undefined> }).env;
  return meta?.[name] ?? process.env[name];
}

export function createCensusSupabaseClient(): SupabaseClient | null {
  const url = env("VITE_SUPABASE_URL")?.trim().replace(/\/+$/, "");
  const key = env("VITE_SUPABASE_ANON_KEY")?.trim();
  if (!url || !key) return null;
  return createClient(url, key);
}

function censusStateToken(name: string): string {
  return name.replace(/&/g, "and").toUpperCase();
}

function stripCensusAreaDecorations(input: string): string {
  return input
    .replace(/^state\s*-\s*/i, "")
    .replace(/\(\s*\d+\s*\)\s*$/g, "")
    .replace(/\s+\d{1,2}\s*$/g, "")
    .trim();
}

const NON_AGE_BANDS = new Set([
  "st",
  "sc",
  "female",
  "females",
  "male",
  "males",
  "girls",
  "women",
  "persons",
  "total",
  "rural",
  "urban",
  "married",
  "currently married",
]);

/** Models sometimes dump sex/group into ageBand. Treat those as All ages. */
export function sanitizeAgeBand(ageBand: string): string {
  const raw = ageBand.trim();
  if (!raw) return "all";
  const key = raw.toLowerCase().replace(/[_-]+/g, " ").replace(/\s+/g, " ");
  if (NON_AGE_BANDS.has(key)) return "all";
  if (!/\d/.test(raw) && !/^all\b/i.test(raw) && !/^age_/i.test(raw) && !/less than/i.test(raw)) {
    return "all";
  }
  return raw;
}

export function resolveCensusState(input: string): { canonical: string; searchToken: string } {
  const trimmed = stripCensusAreaDecorations(input.trim());
  const aliasHit = canonicalStateName(trimmed);
  const lower = aliasHit.toLowerCase();
  const exact = STATES.find((s) => s.name.toLowerCase() === lower);
  if (exact) {
    return { canonical: exact.name, searchToken: censusStateToken(exact.name) };
  }
  if (/^india$/i.test(trimmed) || /^all india$/i.test(trimmed)) {
    return { canonical: "India", searchToken: "INDIA" };
  }

  const haystack = ` ${lower.replace(/&/g, "and")} `;
  const byLength = [...STATES].sort((a, b) => b.name.length - a.name.length);
  const embedded = byLength.find((s) =>
    haystack.includes(` ${s.name.toLowerCase().replace(/&/g, "and")} `),
  );
  if (embedded) {
    return { canonical: embedded.name, searchToken: censusStateToken(embedded.name) };
  }

  return {
    canonical: aliasHit,
    searchToken: censusStateToken(aliasHit),
  };
}

export function resolveCard(dsl: Pick<CensusQueryDsl, "cardId" | "socialGroup" | "metric">): TableCard {
  const group = dsl.socialGroup ?? "total";
  let card: TableCard | undefined;

  if (dsl.cardId) {
    card = CARD_BY_ID.get(dsl.cardId);
    if (!card) {
      throw new CensusQueryError(`Unknown cardId '${dsl.cardId}'`);
    }
  } else {
    const id = DEFAULT_CARD[dsl.metric]?.[group];
    card = id ? CARD_BY_ID.get(id) : undefined;
    if (!card) {
      card = TABLE_CARDS.find(
        (c) => c.socialGroup === group && c.metrics.some((m) => m.id === dsl.metric),
      );
    }
  }

  if (!card) {
    throw new CensusQueryError(
      `No catalog card for metric '${dsl.metric}' and socialGroup '${group}'`,
    );
  }
  if (group !== "religion" && group !== card.socialGroup && card.twins[group]) {
    const twin = CARD_BY_POSTGRES.get(card.twins[group]!);
    if (twin) card = twin;
  }
  if (!card.metrics.some((m) => m.id === dsl.metric)) {
    throw new CensusQueryError(
      `Card ${card.id} cannot compute metric '${dsl.metric}'`,
    );
  }
  if (!TABLE_NAME.test(card.postgresTable) || !CARD_BY_POSTGRES.has(card.postgresTable)) {
    throw new CensusQueryError(`Table '${card.postgresTable}' is not allowlisted`);
  }
  return card;
}

function sexColumn(
  sexed: { persons: string; males: string; females: string },
  sex: Sex,
): string {
  if (sex === "female") return sexed.females;
  if (sex === "male") return sexed.males;
  return sexed.persons;
}

export function parseCensusNumber(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const s = String(value).trim().replace(/,/g, "");
  if (!s || s === "-" || s === "NA" || s === "N/A") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

export function computeRate(numerator: number | null, denominator: number | null): number | null {
  if (numerator === null || denominator === null || denominator === 0) return null;
  return Number(((numerator / denominator) * 100).toFixed(4));
}

function uniqueIdents(names: Array<string | null | undefined>): string[] {
  const out: string[] = [];
  for (const name of names) {
    if (!name) continue;
    assertIdent(name, "column");
    if (!out.includes(name)) out.push(name);
  }
  return out;
}

export function compileCensusQuery(input: unknown): CompiledCensusQuery {
  const parsed = censusQueryDslSchema.safeParse(input);
  if (!parsed.success) {
    const msg = parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ");
    throw new CensusQueryError(`Invalid census query: ${msg}`);
  }
  const dsl = { ...parsed.data, ageBand: sanitizeAgeBand(parsed.data.ageBand) };
  const card = resolveCard(dsl);

  if (card.filterColumns.extra?.religion && !dsl.religion) {
    throw new CensusQueryError(
      `Card ${card.id} requires a religion filter (e.g. Hindu, Muslim)`,
    );
  }

  const recipe = card.metrics.find((m) => m.id === dsl.metric)!;
  const numCol = sexColumn(recipe.numerator, dsl.sex);
  const denCol = recipe.denominator ? sexColumn(recipe.denominator, dsl.sex) : null;
  assertIdent(card.filterColumns.year, "column");
  assertIdent(card.filterColumns.state, "column");
  assertIdent(card.filterColumns.area, "column");

  const ageCol = card.filterColumns.age;
  const age = ageCol
    ? resolveAgeLabels(card.censusTable, dsl.ageBand)
    : { labels: null, approximate: false, note: undefined };
  if (age.labels && age.labels.length === 0) {
    throw new CensusQueryError(age.note ?? `No age labels for ${dsl.ageBand} on ${card.censusTable}`);
  }
  if (ageCol) assertIdent(ageCol, "column");

  const { searchToken } = resolveCensusState(dsl.state);

  const select = uniqueIdents([
    "year",
    "state_code",
    "distt_code",
    card.filterColumns.state,
    card.filterColumns.area,
    ageCol,
    card.filterColumns.extra?.religion,
    numCol,
    denCol,
  ]);

  const filters: FilterOp[] = [
    { op: "eq", column: card.filterColumns.year, value: dsl.year },
    { op: "eq", column: card.filterColumns.area, value: dsl.area },
    { op: "ilike", column: card.filterColumns.state, value: `%${searchToken}%` },
    { op: "in", column: "distt_code", values: STATE_LEVEL_CODES },
  ];

  if (ageCol && age.labels) {
    filters.push(
      age.labels.length === 1
        ? { op: "eq", column: ageCol, value: age.labels[0] }
        : { op: "in", column: ageCol, values: age.labels },
    );
  }

  const religionCol = card.filterColumns.extra?.religion;
  if (religionCol && dsl.religion) {
    assertIdent(religionCol, "column");
    filters.push({ op: "ilike", column: religionCol, value: `%${dsl.religion.trim()}%` });
  }

  for (const f of filters) assertIdent(f.column, "column");

  return {
    postgresTable: card.postgresTable,
    select,
    filters,
    limit: dsl.limit,
    card,
    dsl,
    ageNote: age.note,
    aggregateAgeLabels: age.labels && age.labels.length > 1 ? age.labels : null,
  };
}

export function computeMetricFromRows(
  compiled: CompiledCensusQuery,
  rows: Record<string, unknown>[],
): ComputedMetric {
  const recipe = compiled.card.metrics.find((m) => m.id === compiled.dsl.metric)!;
  const numCol = sexColumn(recipe.numerator, compiled.dsl.sex);
  const denCol = recipe.denominator ? sexColumn(recipe.denominator, compiled.dsl.sex) : null;

  let numerator = 0;
  let denominator = 0;
  let numSeen = false;
  let denSeen = false;
  for (const row of rows) {
    const n = parseCensusNumber(row[numCol]);
    if (n !== null) {
      numerator += n;
      numSeen = true;
    }
    if (denCol) {
      const d = parseCensusNumber(row[denCol]);
      if (d !== null) {
        denominator += d;
        denSeen = true;
      }
    }
  }

  const num = numSeen ? numerator : null;
  const den = denCol ? (denSeen ? denominator : null) : null;
  const value = denCol ? computeRate(num, den) : num;

  return {
    metric: compiled.dsl.metric,
    sex: compiled.dsl.sex,
    numerator: num,
    denominator: den,
    value,
    numeratorColumn: numCol,
    denominatorColumn: denCol,
    sourceRowCount: rows.length,
  };
}

export function dedupeRows(rows: Record<string, unknown>[]): Record<string, unknown>[] {
  const seen = new Set<string>();
  const out: Record<string, unknown>[] = [];
  for (const row of rows) {
    const key = JSON.stringify(row);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(row);
  }
  return out;
}

export async function fetchCompiledRows(
  compiled: CompiledCensusQuery,
  client: SupabaseClient,
): Promise<Record<string, unknown>[]> {
  let q = client.from(compiled.postgresTable).select(compiled.select.join(","));
  for (const f of compiled.filters) {
    if (f.op === "eq") q = q.eq(f.column, f.value);
    else if (f.op === "in") q = q.in(f.column, f.values);
    else q = q.ilike(f.column, f.value);
  }
  q = q.limit(compiled.limit);
  const { data, error } = await q;
  if (error) {
    throw new CensusQueryError(error.message);
  }
  return (data ?? []) as unknown as Record<string, unknown>[];
}

/**
 * Typed census query: Zod DSL → allowlisted PostgREST filters → rate in TypeScript.
 * Pass `fetchRows` in tests. Production uses the Supabase anon client (read-only tables).
 */
export async function runCensusQuery(
  input: unknown,
  deps?: { fetchRows?: CensusRowFetcher; client?: SupabaseClient | null },
): Promise<CensusQueryResult> {
  let compiled: CompiledCensusQuery;
  try {
    compiled = compileCensusQuery(input);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      ok: false,
      error: message,
      compiled: null,
      rows: [],
      computed: null,
      filtersUsed: [],
    };
  }

  const fetchRows =
    deps?.fetchRows ??
    (async (c) => {
      const client = deps?.client ?? createCensusSupabaseClient();
      if (!client) {
        throw new CensusQueryError(
          "Missing Supabase env. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.",
        );
      }
      return fetchCompiledRows(c, client);
    });

  try {
    const fetched = await fetchRows(compiled);
    const rows = dedupeRows(fetched);
    if (rows.length === 0) {
      return {
        ok: true,
        hint: [
          `0 rows from ${compiled.postgresTable}.`,
          `Filters: year=${compiled.dsl.year}, area=${compiled.dsl.area}, area_name ilike %${resolveCensusState(compiled.dsl.state).searchToken}%, distt_code in ${STATE_LEVEL_CODES.join("/")}, ageBand=${compiled.dsl.ageBand}${compiled.ageNote ? ` (${compiled.ageNote})` : ""}.`,
          "The tool already matches Census labels like 'State - RAJASTHAN (08)'. Retry with a plain state name and ageBand 'all' unless the user named an age.",
        ].join(" "),
        compiled,
        rows: [],
        computed: null,
        filtersUsed: compiled.filters,
      };
    }
    const computed = computeMetricFromRows(
      compiled,
      !compiled.aggregateAgeLabels && rows.length > 1 ? [rows[0]] : rows,
    );
    const extraHint =
      !compiled.aggregateAgeLabels && rows.length > 1
        ? `${rows.length} matching rows after filters; using the first instead of summing (All-ages rows must not be added together).`
        : compiled.ageNote;
    return {
      ok: true,
      hint: extraHint,
      compiled,
      rows,
      computed,
      filtersUsed: compiled.filters,
    };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      ok: false,
      error: message,
      compiled,
      rows: [],
      computed: null,
      filtersUsed: compiled.filters,
    };
  }
}

export function formatCensusQueryForModel(result: CensusQueryResult) {
  return {
    ok: result.ok,
    error: result.error,
    hint: result.hint,
    table: result.compiled?.postgresTable,
    censusTable: result.compiled?.card.censusTable,
    filters: result.filtersUsed,
    computed: result.computed,
    caveats: result.compiled?.card.caveats,
    rowCount: result.rows.length,
    sampleRows: result.rows.slice(0, 5),
  };
}
