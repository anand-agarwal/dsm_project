/** Atlas age brackets → Census row labels, copied from the Python builders. */

export const ATLAS_AGE_BANDS = [
  "age_below10",
  "age_10_13",
  "age_14_17",
  "age_18_21",
  "age_22_25",
  "age_26_29",
  "age_30_33",
  "age_34_plus",
] as const;

export type AtlasAgeBand = (typeof ATLAS_AGE_BANDS)[number];

export type AgeResolution = {
  /** Census labels to fetch. Empty means "do not filter age" (no age column). */
  labels: string[] | null;
  /** True when the Python pipeline marks this mapping as approximate. */
  approximate: boolean;
  note?: string;
};

const C08: Record<AtlasAgeBand, string[]> = {
  age_below10: ["0-6", "7", "8", "9"],
  age_10_13: ["10", "11", "12", "13"],
  age_14_17: ["14", "15", "16", "17"],
  age_18_21: ["18", "19"],
  age_22_25: ["20-24"],
  age_26_29: ["25-29"],
  age_30_33: ["30-34"],
  age_34_plus: ["35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80+"],
};

const C09: Record<AtlasAgeBand, string[]> = {
  ...C08,
  age_34_plus: ["35-59", "60+"],
};

const C02: Record<AtlasAgeBand, string[]> = {
  age_below10: ["0-9"],
  age_10_13: ["10-14"],
  age_14_17: ["15-19"],
  age_18_21: ["20-24"],
  age_22_25: ["20-24"],
  age_26_29: ["25-29"],
  age_30_33: ["30-34"],
  age_34_plus: ["35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80+"],
};

const MARRIAGE: Record<AtlasAgeBand, string[]> = {
  age_below10: ["Less than 10", "less than 10"],
  age_10_13: ["10-11", "12-13"],
  age_14_17: ["14-15", "16-17"],
  age_18_21: ["18-19", "20-21"],
  age_22_25: ["22-23", "24-25"],
  age_26_29: ["26-27", "28-29"],
  age_30_33: ["30-31", "32-33"],
  age_34_plus: ["34+", "34 +"],
};

const C12: Record<AtlasAgeBand, string[]> = {
  age_below10: ["5", "6", "7", "8", "9"],
  age_10_13: ["10", "11", "12", "13"],
  age_14_17: ["14", "15", "16", "17"],
  age_18_21: ["18", "19"],
  age_22_25: [],
  age_26_29: [],
  age_30_33: [],
  age_34_plus: [],
};

const C02_APPROXIMATE = new Set<AtlasAgeBand>([
  "age_10_13",
  "age_14_17",
  "age_18_21",
  "age_22_25",
  "age_26_29",
  "age_30_33",
  "age_34_plus",
]);

const C08_APPROXIMATE = new Set<AtlasAgeBand>([
  "age_18_21",
  "age_22_25",
  "age_26_29",
  "age_30_33",
  "age_34_plus",
]);

function familyMaps(censusTable: string): {
  brackets: Record<AtlasAgeBand, string[]>;
  allAges: string[];
  approximate: Set<AtlasAgeBand>;
} {
  if (censusTable.startsWith("C-08")) {
    return { brackets: C08, allAges: ["All ages"], approximate: C08_APPROXIMATE };
  }
  if (censusTable.startsWith("C-09")) {
    return { brackets: C09, allAges: ["Total"], approximate: C08_APPROXIMATE };
  }
  if (censusTable.startsWith("C-02")) {
    return { brackets: C02, allAges: ["All ages"], approximate: C02_APPROXIMATE };
  }
  if (censusTable.startsWith("C-12")) {
    return { brackets: C12, allAges: ["5-19"], approximate: new Set(["age_below10", "age_18_21"]) };
  }
  if (
    censusTable.startsWith("C-04") ||
    censusTable.startsWith("C-05") ||
    censusTable.startsWith("C-06") ||
    censusTable.startsWith("C-07")
  ) {
    return { brackets: MARRIAGE, allAges: ["All ages"], approximate: new Set() };
  }
  return { brackets: C08, allAges: ["All ages"], approximate: new Set() };
}

export function isAtlasAgeBand(value: string): value is AtlasAgeBand {
  return (ATLAS_AGE_BANDS as readonly string[]).includes(value);
}

/**
 * Map a DSL ageBand to Census labels.
 * `all` → the table's aggregate row (All ages / Total / 5-19).
 * An atlas id like age_14_17 → the Python bracket's labels (may need summing).
 * Anything else is treated as a raw Census label (e.g. "15-19").
 */
export function resolveAgeLabels(censusTable: string, ageBand: string): AgeResolution {
  const { brackets, allAges, approximate } = familyMaps(censusTable);
  const raw = ageBand.trim();
  const key = raw.toLowerCase().replace(/[–—]/g, "-").replace(/\s+/g, "_");

  if (key === "all" || key === "all_ages" || key === "all-ages") {
    return { labels: allAges, approximate: false };
  }

  const aliases: Record<string, AtlasAgeBand> = {
    below10: "age_below10",
    "<10": "age_below10",
    "10-13": "age_10_13",
    "14-17": "age_14_17",
    "18-21": "age_18_21",
  };
  const atlas = isAtlasAgeBand(raw)
    ? raw
    : isAtlasAgeBand(`age_${key}` as AtlasAgeBand)
      ? (`age_${key}` as AtlasAgeBand)
      : aliases[raw] ?? aliases[key];

  if (atlas) {
    const labels = brackets[atlas];
    if (!labels || labels.length === 0) {
      return {
        labels: [],
        approximate: true,
        note: `${atlas} is not available on ${censusTable}`,
      };
    }
    return {
      labels,
      approximate: approximate.has(atlas),
      note: approximate.has(atlas)
        ? `${atlas} on ${censusTable} is an approximate mapping (see Python AGE_BRACKET notes)`
        : undefined,
    };
  }

  return { labels: [raw], approximate: false };
}
