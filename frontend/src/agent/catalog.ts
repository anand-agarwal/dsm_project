import type { MetricRecipe, SexedColumns, SocialGroup, TableCard } from "./types";

const TOTAL: SexedColumns = {
  persons: "total_persons_2",
  males: "males_3",
  females: "females_4",
};

const LITERATE: SexedColumns = {
  persons: "literate_persons_8",
  males: "males_9",
  females: "females_10",
};

const ILLITERATE: SexedColumns = {
  persons: "illiterate_persons_5",
  males: "males_6",
  females: "females_7",
};

const CURRENTLY_MARRIED: SexedColumns = {
  persons: "currently_married_persons_8",
  males: "males_9",
  females: "females_10",
};

const NEVER_MARRIED: SexedColumns = {
  persons: "marital_status_persons_5",
  males: "never_married_males_6",
  females: "females_7",
};

function rate(
  id: MetricRecipe["id"],
  label: string,
  formula: string,
  numerator: SexedColumns,
  denominator: SexedColumns,
): MetricRecipe {
  return { id, label, formula, numerator, denominator };
}

function countMetric(
  id: MetricRecipe["id"],
  label: string,
  formula: string,
  columns: SexedColumns,
): MetricRecipe {
  return { id, label, formula, numerator: columns, denominator: null };
}

const LITERACY_METRICS: MetricRecipe[] = [
  rate(
    "literacy_rate",
    "Literacy rate",
    "literate / total population in the same sex column",
    LITERATE,
    TOTAL,
  ),
  rate(
    "illiteracy_rate",
    "Illiteracy rate",
    "illiterate / total population in the same sex column",
    ILLITERATE,
    TOTAL,
  ),
  countMetric("population", "Population count", "total persons / males / females", TOTAL),
];

const MARITAL_METRICS: MetricRecipe[] = [
  rate(
    "currently_married_share",
    "Currently married share",
    "currently married / total population in the same sex column (current age, not age at marriage)",
    CURRENTLY_MARRIED,
    TOTAL,
  ),
  rate(
    "never_married_share",
    "Never married share",
    "never married / total population in the same sex column",
    NEVER_MARRIED,
    TOTAL,
  ),
  countMetric("population", "Population count", "total persons / males / females", TOTAL),
];

const C08_FILTERS = {
  year: "year",
  state: "area_name",
  area: "total_rural_urban",
  age: "age_group_1",
};

const C02_FILTERS = {
  year: "year",
  state: "area_name",
  area: "total_rural_urban",
  age: "age_group_1",
};

function c08Card(socialGroup: SocialGroup): TableCard {
  const suffix = socialGroup === "total" ? "" : `_${socialGroup}`;
  const postgresTable = `raw_c_08${suffix}`;
  const groupLabel =
    socialGroup === "sc" ? "Scheduled Caste" : socialGroup === "st" ? "Scheduled Tribe" : "total population";
  return {
    id: `c08_${socialGroup}`,
    censusTable: "C-08",
    postgresTable,
    socialGroup,
    topic: `Education by current age (${groupLabel})`,
    purpose:
      "Literacy, illiteracy, and educational attainment by current age, sex, and rural/urban. This is the table for literacy rates.",
    grain: "One row = one geography × year × Total/Rural/Urban × current-age band",
    filterColumns: C08_FILTERS,
    metrics: LITERACY_METRICS,
    twins: {
      total: "raw_c_08",
      sc: "raw_c_08_sc",
      st: "raw_c_08_st",
    },
    years: [2001, 2011],
    caveats: [
      "There is no literacy column. Rate = literate count / total count (e.g. females_10 / females_4 for girls).",
      "Counts are stored as text; parse to numbers before dividing.",
      "area_name looks like 'State - ODISHA (21)', not 'Odisha'.",
      "State-level rows typically have distt_code 00.",
      "C-08 age 18–21 in the Python indexes only covers ages 18–19; 20–21 sit in a 20–24 band.",
    ],
    synonyms: [
      "c-08",
      "c08",
      "education",
      "educational level",
      "literacy",
      "literate",
      "illiteracy",
      "illiterate",
      "can read",
      "cannot read",
      "reading",
      "schooling",
      "primary",
      "matric",
      "graduate",
      ...(socialGroup === "sc" ? ["sc", "scheduled caste", "dalit"] : []),
      ...(socialGroup === "st" ? ["st", "scheduled tribe", "adivasi", "tribal"] : []),
      ...(socialGroup === "total" ? ["total population", "all social groups"] : []),
    ],
  };
}

function c02Card(socialGroup: SocialGroup): TableCard {
  const suffix = socialGroup === "total" ? "" : `_${socialGroup}`;
  const postgresTable = `raw_c_02${suffix}`;
  const groupLabel =
    socialGroup === "sc" ? "Scheduled Caste" : socialGroup === "st" ? "Scheduled Tribe" : "total population";
  return {
    id: `c02_${socialGroup}`,
    censusTable: "C-02",
    postgresTable,
    socialGroup,
    topic: `Marital status by current age (${groupLabel})`,
    purpose:
      "Never married / currently married / widowed / divorced by current age and sex. Used for currently-married prevalence (SC/ST CMPR in the Python pipeline uses this family).",
    grain: "One row = one geography × year × Total/Rural/Urban × current-age band",
    filterColumns: C02_FILTERS,
    metrics: MARITAL_METRICS,
    twins: {
      total: "raw_c_02",
      sc: "raw_c_02_sc",
      st: "raw_c_02_st",
    },
    years: [2001, 2011],
    caveats: [
      "This is marital status at the Census date, not age at marriage. Atlas CMPR for total/education/work uses C-04/C-06/C-07, not this table.",
      "Python SC/ST CMPR maps C-02 age 10-14 → age_10_13 and 15-19 → age_14_17.",
      "Prefer currently_married_persons_8 / males_9 / females_10 even when married_persons_8 is also present.",
    ],
    synonyms: [
      "c-02",
      "c02",
      "marital status",
      "currently married",
      "never married",
      "widowed",
      "divorced",
      "cmpr",
      "child marriage prevalence",
      "married girls",
      "married children",
      ...(socialGroup === "sc" ? ["sc", "scheduled caste", "dalit"] : []),
      ...(socialGroup === "st" ? ["st", "scheduled tribe", "adivasi", "tribal"] : []),
    ],
  };
}

function c12Card(socialGroup: SocialGroup): TableCard {
  const suffix = socialGroup === "total" ? "" : `_${socialGroup}`;
  const postgresTable = `raw_c_12${suffix}`;
  const groupLabel =
    socialGroup === "sc" ? "Scheduled Caste" : socialGroup === "st" ? "Scheduled Tribe" : "total population";
  const attendingNonWorkers: SexedColumns = {
    persons: "non_workers_persons_11",
    males: "males_12",
    females: "females_13",
  };
  const notAttendingMain: SexedColumns = {
    persons: "not_attending_educational_institution_main_workers_persons_14",
    males: "males_15",
    females: "females_16",
  };
  return {
    id: `c12_${socialGroup}`,
    censusTable: "C-12",
    postgresTable,
    socialGroup,
    topic: `School attendance and work, ages 5–19 (${groupLabel})`,
    purpose:
      "Whether children attend an educational institution, crossed with worker status. Use for school attendance and a child-labour proxy (not attending + working).",
    grain: "One row = one geography × year × Total/Rural/Urban × single year of age (5–19)",
    filterColumns: {
      year: "year",
      state: "area_name",
      area: "total_rural_urban",
      age: "age_1",
    },
    metrics: [
      rate(
        "school_attendance_share",
        "Share attending school (non-worker column as a starting point)",
        "Attending is split across main/marginal/non-worker columns; sum attending_* before dividing by total.",
        attendingNonWorkers,
        TOTAL,
      ),
      rate(
        "not_attending_worker_share",
        "Not attending and main worker (child-labour proxy)",
        "not-attending main workers / total in the same sex column. Add marginal workers for a broader proxy.",
        notAttendingMain,
        TOTAL,
      ),
      countMetric("population", "Population count ages 5–19", "total persons / males / females", TOTAL),
    ],
    twins: {
      total: "raw_c_12",
      sc: "raw_c_12_sc",
      st: "raw_c_12_st",
    },
    years: [2001, 2011],
    caveats: [
      "Attendance is three columns (main worker, marginal worker, non-worker). Do not treat non_workers_persons_11 as all students.",
      "Covers ages 5–19 only. age_18_21 in the Python indexes is only 18–19.",
    ],
    synonyms: [
      "c-12",
      "c12",
      "school attendance",
      "attending school",
      "not attending",
      "child labour",
      "child labor",
      "out of school",
      "workers",
      ...(socialGroup === "sc" ? ["sc", "scheduled caste", "dalit"] : []),
      ...(socialGroup === "st" ? ["st", "scheduled tribe", "adivasi", "tribal"] : []),
    ],
  };
}

export const TABLE_CARDS: TableCard[] = [
  c08Card("total"),
  c08Card("sc"),
  c08Card("st"),
  c02Card("total"),
  c02Card("sc"),
  c02Card("st"),
  c12Card("total"),
  c12Card("sc"),
  c12Card("st"),
  {
    id: "c09_religion",
    censusTable: "C-09",
    postgresTable: "raw_c_09",
    socialGroup: "religion",
    topic: "Education by religion and current age",
    purpose:
      "Literacy and educational attainment crossed with religion (Hindu, Muslim, Christian, Sikh, Buddhist, Jain, other).",
    grain: "One row = one geography × year × area × religion × current-age band",
    filterColumns: {
      year: "year",
      state: "area_name",
      area: "total_rural_urban",
      age: "age_group_1",
      extra: { religion: "religion" },
    },
    metrics: LITERACY_METRICS,
    twins: {},
    years: [2001, 2011],
    caveats: [
      "Filter religion in the religion column. Same literate/total column numbers as C-08 (females_10 / females_4 for female literacy).",
    ],
    synonyms: [
      "c-09",
      "c09",
      "religion",
      "hindu",
      "muslim",
      "christian",
      "sikh",
      "buddhist",
      "jain",
      "literacy",
      "education",
    ],
  },
  {
    id: "c03_religion",
    censusTable: "C-03",
    postgresTable: "raw_c_03",
    socialGroup: "religion",
    topic: "Marital status by religion (wide)",
    purpose: "Marital status counts split into religion columns on a wide row (not one religion per row).",
    grain: "One row = one geography × year × area × marital-status category",
    filterColumns: {
      year: "year",
      state: "area_name",
      area: "total_rural_urban",
      age: null,
      extra: { maritalStatus: "marital_status_1" },
    },
    metrics: [
      countMetric("population", "Population by religion (wide columns)", "Use the religion-specific persons/males/females columns", {
        persons: "religious_communities_hindu_persons_5",
        males: "males_6",
        females: "females_7",
      }),
    ],
    twins: {},
    years: [2001, 2011],
    caveats: [
      "Wide layout: Hindu/Muslim/… are columns, not rows. Prefer raw_c_03_appendix when you need religion × age × marital status in long form.",
    ],
    synonyms: ["c-03", "c03", "marital status", "religion", "hindu", "muslim"],
  },
  {
    id: "c03_appendix_religion",
    censusTable: "C-03 Appendix",
    postgresTable: "raw_c_03_appendix",
    socialGroup: "religion",
    topic: "Marital status by religion and age (long)",
    purpose: "Long-form marital status × religion × age. 2001 religion CMPR patch in Python uses this family.",
    grain: "One row = one geography × year × area × religion × age band",
    filterColumns: {
      year: "year",
      state: "area_name",
      area: "total_rural_urban",
      age: "age_group_1",
      extra: { religion: "religion" },
    },
    metrics: MARITAL_METRICS,
    twins: {},
    years: [2001, 2011],
    caveats: ["Prefer this over wide C-03 when the question names both a religion and an age band."],
    synonyms: [
      "c-03 appendix",
      "c03 appendix",
      "marital status",
      "religion",
      "currently married",
      "hindu",
      "muslim",
    ],
  },
  {
    id: "c04_total",
    censusTable: "C-04",
    postgresTable: "raw_c_04",
    socialGroup: "total",
    topic: "Age at marriage (ever married)",
    purpose:
      "Ever-married persons by age at marriage and duration of marriage. Atlas CMPR for the total population uses age-at-marriage shares from this family, not C-02 current marital status.",
    grain: "One row = one geography × year × area × age-at-marriage band",
    filterColumns: {
      year: "year",
      state: "area_name",
      area: "total_rural_urban",
      age: "age_at_marriage_1",
    },
    metrics: [
      countMetric("age_at_marriage_count", "Ever-married count by age at marriage", "number_of_ever_married_persons males_2 / females_3", {
        persons: "number_of_ever_married_persons_males_2",
        males: "number_of_ever_married_persons_males_2",
        females: "females_3",
      }),
    ],
    twins: { total: "raw_c_04", sc: "raw_c_04_sc", st: "raw_c_04_st" },
    years: [2001, 2011],
    caveats: [
      "Universe is ever-married persons, not all children. Do not treat females_3 / state population as CMPR without the Python formula.",
      "SC/ST twins: raw_c_04_sc, raw_c_04_st.",
    ],
    synonyms: [
      "c-04",
      "c04",
      "age at marriage",
      "ever married",
      "duration of marriage",
      "cmpr",
      "child marriage",
    ],
  },
  {
    id: "c05_religion",
    censusTable: "C-05",
    postgresTable: "raw_c_05",
    socialGroup: "religion",
    topic: "Age at marriage by religion",
    purpose: "Age at marriage crossed with religion. Used by the religion index builder.",
    grain: "One row = one geography × year × area × religion × age-at-marriage band",
    filterColumns: {
      year: "year",
      state: "area_name",
      area: "total_rural_urban",
      age: "age_at_marriage_1",
      extra: { religion: "religion" },
    },
    metrics: [
      countMetric("age_at_marriage_count", "Ever-married count by religion and age at marriage", "Use the sexed ever-married columns on this table", {
        persons: "number_of_ever_married_persons_males_2",
        males: "number_of_ever_married_persons_males_2",
        females: "females_3",
      }),
    ],
    twins: {},
    years: [2001, 2011],
    caveats: ["Confirm column names against a live row before computing rates; C-05 headers are wide."],
    synonyms: ["c-05", "c05", "age at marriage", "religion", "ever married", "hindu", "muslim"],
  },
  {
    id: "c06_total",
    censusTable: "C-06",
    postgresTable: "raw_c_06",
    socialGroup: "total",
    topic: "Age at marriage by educational level",
    purpose: "Age at marriage crossed with education. Feeds the education-split CMPR indexes.",
    grain: "One row = one geography × year × area × education × age-at-marriage band",
    filterColumns: {
      year: "year",
      state: "area_name",
      area: "total_rural_urban",
      age: "age_at_marriage_1",
    },
    metrics: [
      countMetric("age_at_marriage_count", "Ever-married count by education", "Use education × age-at-marriage counts; do not invent a literacy rate here", {
        persons: "number_of_ever_married_persons_males_2",
        males: "number_of_ever_married_persons_males_2",
        females: "females_3",
      }),
    ],
    twins: {},
    years: [2001, 2011],
    caveats: ["This is not C-08. Education here describes ever-married persons, not current-age literacy."],
    synonyms: ["c-06", "c06", "age at marriage", "education", "educational level", "cmpr"],
  },
  {
    id: "c07_total",
    censusTable: "C-07",
    postgresTable: "raw_c_07",
    socialGroup: "total",
    topic: "Age at marriage by economic activity",
    purpose: "Age at marriage crossed with worker status. Feeds work-split CMPR indexes.",
    grain: "One row = one geography × year × area × activity × age-at-marriage band",
    filterColumns: {
      year: "year",
      state: "area_name",
      area: "total_rural_urban",
      age: "age_at_marriage_1",
    },
    metrics: [
      countMetric("age_at_marriage_count", "Ever-married count by economic activity", "Use activity × age-at-marriage counts", {
        persons: "number_of_ever_married_persons_males_2",
        males: "number_of_ever_married_persons_males_2",
        females: "females_3",
      }),
    ],
    twins: {},
    years: [2001, 2011],
    caveats: ["Not a child-labour table. For attendance × work among children 5–19 use C-12."],
    synonyms: ["c-07", "c07", "age at marriage", "economic activity", "worker", "cmpr"],
  },
];

export const CARD_BY_ID = new Map(TABLE_CARDS.map((c) => [c.id, c]));
export const CARD_BY_POSTGRES = new Map(TABLE_CARDS.map((c) => [c.postgresTable, c]));
