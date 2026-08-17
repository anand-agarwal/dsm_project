/** Closed sets the later census-query DSL will reuse. */

export const YEARS = [2001, 2011] as const;
export type Year = (typeof YEARS)[number];

export const SOCIAL_GROUPS = ["total", "sc", "st"] as const;
export type SocialGroup = (typeof SOCIAL_GROUPS)[number];

export const SEXES = ["persons", "male", "female"] as const;
export type Sex = (typeof SEXES)[number];

export const AREAS = ["Total", "Rural", "Urban"] as const;
export type Area = (typeof AREAS)[number];

export const METRIC_IDS = [
  "literacy_rate",
  "illiteracy_rate",
  "currently_married_share",
  "never_married_share",
  "age_at_marriage_count",
  "school_attendance_share",
  "not_attending_worker_share",
  "population",
] as const;
export type MetricId = (typeof METRIC_IDS)[number];

/** Persons / male / female count columns for one Census measure. */
export type SexedColumns = {
  persons: string;
  males: string;
  females: string;
};

export type MetricRecipe = {
  id: MetricId;
  label: string;
  /** Human formula, e.g. literate females / total females. */
  formula: string;
  numerator: SexedColumns;
  denominator: SexedColumns | null;
};

export type TableCard = {
  id: string;
  censusTable: string;
  postgresTable: string;
  socialGroup: SocialGroup | "religion";
  topic: string;
  purpose: string;
  /** What one row represents. */
  grain: string;
  filterColumns: {
    year: string;
    state: string;
    area: string;
    age: string | null;
    extra?: Record<string, string>;
  };
  metrics: MetricRecipe[];
  /** Twin tables for the same C-series (total / SC / ST). */
  twins: Partial<Record<SocialGroup, string>>;
  years: readonly Year[];
  caveats: string[];
  /** Search terms that should retrieve this card. */
  synonyms: string[];
};

export type LookupSchemaInput = {
  /** Natural-language hint from the user or the model. */
  query: string;
  socialGroup?: SocialGroup | "religion";
  metricId?: MetricId;
  /** Max cards to return. Default 3. */
  limit?: number;
};

export type RankedTableCard = TableCard & {
  score: number;
  matchedTerms: string[];
};

export type LookupSchemaResult = {
  query: string;
  detectedSocialGroup: SocialGroup | "religion" | null;
  detectedMetrics: MetricId[];
  cards: RankedTableCard[];
};
