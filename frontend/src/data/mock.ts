// Realistic-but-synthetic Census-style indicators for India (2001 & 2011).
// Numbers are anchored to commonly cited public statistics with small variation
// per state/age/gender so the dashboard "feels" right. NOT for analytical use.

import { STATES } from "./states";

export type Year = 2001 | 2011;
export type Gender = "female" | "male";
export type AgeGroup = "<10" | "10-13" | "14-17" | "18-21";
export type Category = "total" | "sc" | "st" | "hindu" | "muslim" | "christian" | "sikh" | "buddhist" | "jain";

export const YEARS: Year[] = [2001, 2011];
export const AGE_GROUPS: AgeGroup[] = ["<10", "10-13", "14-17", "18-21"];
export const GENDERS: Gender[] = ["female", "male"];
export const CATEGORIES: { key: Category; label: string }[] = [
  { key: "total", label: "Total population" },
  { key: "sc", label: "Scheduled Caste" },
  { key: "st", label: "Scheduled Tribe" },
  { key: "hindu", label: "Hindu" },
  { key: "muslim", label: "Muslim" },
  { key: "christian", label: "Christian" },
  { key: "sikh", label: "Sikh" },
  { key: "buddhist", label: "Buddhist" },
  { key: "jain", label: "Jain" },
];

// State "severity" anchors (CMPR base for females 14–17 in 2011, %).
// Loosely calibrated against publicly known relative ordering.
const BASE_CMPR_F_14_17_2011: Record<string, number> = {
  "Bihar": 22.4, "Rajasthan": 19.8, "Jharkhand": 21.1, "West Bengal": 20.7,
  "Madhya Pradesh": 18.6, "Uttar Pradesh": 16.2, "Andhra Pradesh": 14.6,
  "Telangana": 14.1, "Tripura": 16.8, "Assam": 17.4, "Chhattisgarh": 15.2,
  "Odisha": 13.3, "Gujarat": 11.6, "Maharashtra": 9.8, "Karnataka": 12.1,
  "Tamil Nadu": 6.9, "Kerala": 4.1, "Punjab": 5.4, "Haryana": 7.2,
  "Himachal Pradesh": 4.8, "Uttarakhand": 7.6, "Goa": 3.6,
  "Jammu & Kashmir": 6.3, "Delhi": 5.1, "Chandigarh": 4.4, "Puducherry": 5.6,
  "Sikkim": 5.9, "Manipur": 6.7, "Meghalaya": 9.4, "Mizoram": 6.2,
  "Nagaland": 6.1, "Arunachal Pradesh": 8.8,
  "Andaman & Nicobar": 5.2, "Ladakh": 7.0, "Lakshadweep": 4.0,
  "Dadra and Nagar Haveli and Daman and Diu": 8.5,
};

const BASE_LITERACY_F_2011: Record<string, number> = {
  "Kerala": 91.1, "Mizoram": 89.3, "Goa": 84.7, "Tripura": 82.7,
  "Tamil Nadu": 73.4, "Maharashtra": 75.5, "Himachal Pradesh": 76.6,
  "Punjab": 71.3, "Haryana": 66.8, "Karnataka": 68.1, "West Bengal": 71.2,
  "Gujarat": 70.7, "Delhi": 80.9, "Chandigarh": 81.4, "Andhra Pradesh": 59.7,
  "Telangana": 57.9, "Odisha": 64.0, "Madhya Pradesh": 60.0,
  "Chhattisgarh": 60.6, "Uttar Pradesh": 59.3, "Assam": 67.3,
  "Jharkhand": 56.2, "Rajasthan": 52.1, "Bihar": 53.3,
  "Arunachal Pradesh": 59.6, "Manipur": 73.2, "Meghalaya": 73.8,
  "Nagaland": 76.7, "Sikkim": 76.4, "Uttarakhand": 70.7,
  "Jammu & Kashmir": 56.4, "Puducherry": 81.2, "Andaman & Nicobar": 81.8,
  "Ladakh": 62.0, "Lakshadweep": 88.2,
  "Dadra and Nagar Haveli and Daman and Diu": 65.9,
};

// ---------- Deterministic seeded jitter so re-renders are stable ----------
function hash(s: string) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}
function rand(seed: string) {
  // 0..1
  return (hash(seed) % 10000) / 10000;
}
function jitter(seed: string, spread: number) {
  return (rand(seed) - 0.5) * 2 * spread;
}
const clamp = (n: number, lo = 0, hi = 100) => Math.max(lo, Math.min(hi, n));

// ---------- Core CMPR model ----------
function cmprBase(state: string): number {
  return BASE_CMPR_F_14_17_2011[state] ?? 9 + jitter(state + "cm", 4);
}

export function cmpr(opts: {
  state: string; year: Year; gender: Gender; age: AgeGroup; category: Category;
}): number {
  const { state, year, gender, age, category } = opts;
  let v = cmprBase(state);
  // age: <10 negligible, 10-13 modest, 14-17 base, 18-21 elevated
  const ageMul = age === "<10" ? 0.05 : age === "10-13" ? 0.32 : age === "14-17" ? 1 : 1.65;
  v *= ageMul;
  // gender: males consistently lower
  if (gender === "male") v *= 0.42 + 0.05 * rand(state + "g");
  // year: 2001 ~ 25–40% higher than 2011
  if (year === 2001) v *= 1.28 + 0.12 * rand(state + "y");
  // category modifiers
  const catMul: Record<Category, number> = {
    total: 1,
    sc: 1.18,
    st: 1.27,
    hindu: 1.02,
    muslim: 1.12,
    christian: 0.78,
    sikh: 0.74,
    buddhist: 0.92,
    jain: 0.46,
  };
  v *= catMul[category];
  v += jitter(`${state}-${year}-${gender}-${age}-${category}`, 0.6);
  return Math.round(clamp(v, 0, 95) * 10) / 10;
}

export function literacy(state: string, year: Year, gender: Gender = "female"): number {
  let v = BASE_LITERACY_F_2011[state] ?? 65 + jitter(state + "lit", 8);
  if (gender === "male") v += 11 + jitter(state + "litm", 3);
  if (year === 2001) v -= 9 + 4 * rand(state + "lity");
  return Math.round(clamp(v, 5, 99) * 10) / 10;
}

export function dropoutRate(state: string, year: Year, gender: Gender = "female"): number {
  const c = cmpr({ state, year, gender, age: "14-17", category: "total" });
  // Strong correlation with CMPR; negative with literacy
  let v = 8 + c * 0.55 - (literacy(state, year, gender) - 60) * 0.15;
  v += jitter(`${state}drop${gender}${year}`, 2);
  return Math.round(clamp(v, 1.5, 55) * 10) / 10;
}

export function childLabour(state: string, year: Year): number {
  const c = cmpr({ state, year, gender: "female", age: "10-13", category: "total" });
  let v = 1.2 + c * 0.35 + jitter(state + "cl" + year, 0.7);
  if (year === 2001) v *= 1.4;
  return Math.round(clamp(v, 0.2, 22) * 10) / 10;
}

// Education distribution for a state-year (sums ≈100). Female focus.
export function educationDist(state: string, year: Year) {
  const lit = literacy(state, year, "female");
  const illit = 100 - lit;
  // Split literate share into edu levels
  const belowPrimary = lit * (0.18 + 0.05 * rand(state + "bp"));
  const primary = lit * (0.22 + 0.04 * rand(state + "pr"));
  const middle = lit * (0.20 + 0.03 * rand(state + "mid"));
  const secondary = lit * (0.18 + 0.03 * rand(state + "sec"));
  const hsec = lit * (0.10 + 0.03 * rand(state + "hs"));
  const graduate = Math.max(1, lit - belowPrimary - primary - middle - secondary - hsec);
  const round = (n: number) => Math.round(n * 10) / 10;
  return {
    Illiterate: round(illit),
    "Below primary": round(belowPrimary),
    Primary: round(primary),
    Middle: round(middle),
    Secondary: round(secondary),
    "Higher secondary": round(hsec),
    Graduate: round(graduate),
  };
}

// CMPR by worker category — Section C.
export const WORKER_CATEGORIES = [
  "Cultivators",
  "Agricultural labourers",
  "Household industry",
  "Other workers",
  "Main workers",
  "Non-workers",
] as const;
export type WorkerCategory = typeof WORKER_CATEGORIES[number];

export function cmprByWorker(state: string, year: Year, gender: Gender = "female") {
  const base = cmpr({ state, year, gender, age: "14-17", category: "total" });
  const mults: Record<WorkerCategory, number> = {
    Cultivators: 1.05,
    "Agricultural labourers": 1.55,
    "Household industry": 1.28,
    "Other workers": 0.78,
    "Main workers": 0.95,
    "Non-workers": 1.18,
  };
  return WORKER_CATEGORIES.map((w) => ({
    worker: w,
    cmpr: Math.round(clamp(base * mults[w] + jitter(state + w + year, 0.8), 0, 95) * 10) / 10,
  }));
}

// School attendance vs not-attending vs working — Section E.
export function schoolingSplit(state: string, year: Year, gender: Gender = "female") {
  const drop = dropoutRate(state, year, gender);
  const cl = childLabour(state, year);
  const attending = clamp(100 - drop - cl, 30, 99);
  return [
    { bucket: "Attending school", value: Math.round(attending * 10) / 10 },
    { bucket: "Not attending (no work)", value: Math.round((drop * 0.7) * 10) / 10 },
    { bucket: "Child labour (working)", value: Math.round(cl * 10) / 10 },
    { bucket: "Married, out of school", value: Math.round((drop * 0.3) * 10) / 10 },
  ];
}

// ---------- Raw C-table generator (used by Raw Data Explorer) ----------
export const C_TABLES = [
  { id: "C-02", title: "Marital status by age, sex & SC/ST" },
  { id: "C-03", title: "Marital status by religion" },
  { id: "C-04", title: "Age at marriage & duration" },
  { id: "C-05", title: "Marriage by religion" },
  { id: "C-06", title: "Marriage by educational level" },
  { id: "C-07", title: "Marriage by economic activity" },
  { id: "C-08", title: "Education levels (SC/ST)" },
  { id: "C-09", title: "Education by religion" },
  { id: "C-12", title: "School attendance & child labour" },
] as const;

export function generateRawTable(opts: {
  table: string; year: Year; area: "Total" | "Rural" | "Urban";
  gender: Gender | "both"; ageFilter?: AgeGroup | "all";
}) {
  const { table, year, area, gender, ageFilter = "all" } = opts;
  const rows: Record<string, string | number>[] = [];
  for (const s of STATES) {
    const ages = ageFilter === "all" ? AGE_GROUPS : [ageFilter];
    const genders: Gender[] = gender === "both" ? GENDERS : [gender];
    for (const a of ages) {
      for (const g of genders) {
        const c = cmpr({ state: s.name, year, gender: g, age: a, category: "total" });
        const lit = literacy(s.name, year, g);
        const populationSeed = hash(`${s.name}${year}${a}${g}${area}`);
        const pop = 50000 + (populationSeed % 1500000);
        const married = Math.round(pop * (c / 100));
        rows.push({
          State: s.name,
          Area: area,
          Year: year,
          Sex: g === "female" ? "Female" : "Male",
          "Age group": a,
          "Population (15+)": pop,
          "Ever married": married,
          "CMPR (%)": c,
          "Literacy (%)": lit,
          Table: table,
        });
      }
    }
  }
  return rows;
}

// ---------- Convenience: nation aggregates ----------
export function nationalAverage(metric: "cmpr-f-14-17" | "literacy-f" | "dropout-f", year: Year) {
  const vals = STATES.map((s) =>
    metric === "cmpr-f-14-17" ? cmpr({ state: s.name, year, gender: "female", age: "14-17", category: "total" }) :
    metric === "literacy-f" ? literacy(s.name, year, "female") :
    dropoutRate(s.name, year, "female"),
  );
  return Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10;
}

// ---------- Per-state digest used by KPIs ----------
export function stateDigest(state: string, year: Year) {
  return {
    cmprF: cmpr({ state, year, gender: "female", age: "14-17", category: "total" }),
    cmprM: cmpr({ state, year, gender: "male", age: "14-17", category: "total" }),
    cmprFOlder: cmpr({ state, year, gender: "female", age: "18-21", category: "total" }),
    cmprSC: cmpr({ state, year, gender: "female", age: "14-17", category: "sc" }),
    cmprST: cmpr({ state, year, gender: "female", age: "14-17", category: "st" }),
    literacyF: literacy(state, year, "female"),
    literacyM: literacy(state, year, "male"),
    dropoutF: dropoutRate(state, year, "female"),
    childLabour: childLabour(state, year),
  };
}
