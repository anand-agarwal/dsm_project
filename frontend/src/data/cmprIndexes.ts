import { CMPR_DATA_BY_YEAR, CMPR_INDEX_KEYS } from "@/data/cmprDataset";

export type Year = 2001 | 2011;
export type AgeBracket = "<10" | "10-13" | "14-17" | "18-21";
export type CmprIndexKey = (typeof CMPR_INDEX_KEYS)[number];

export const YEARS: Year[] = [2001, 2011];
export const AGE_BRACKETS: AgeBracket[] = ["<10", "10-13", "14-17", "18-21"];

export const INDEX_GROUPS = [
  { key: "total", label: "Total" },
  { key: "sc", label: "Scheduled Caste (SC)" },
  { key: "st", label: "Scheduled Tribe (ST)" },
  { key: "hindu", label: "Hindu" },
  { key: "muslim", label: "Muslim" },
  { key: "christian", label: "Christian" },
  { key: "sikh", label: "Sikh" },
  { key: "buddhist", label: "Buddhist" },
  { key: "jain", label: "Jain" },
  { key: "agri_labourers", label: "Agricultural labourers" },
  { key: "below_primary", label: "Below primary" },
  { key: "cultivators", label: "Cultivators" },
  { key: "household_industry", label: "Household industry" },
  { key: "illiterate", label: "Illiterate" },
  { key: "main_workers", label: "Main workers" },
  { key: "matric", label: "Matric" },
  { key: "middle", label: "Middle School" },
  { key: "non_workers", label: "Non-workers" },
  { key: "other_workers", label: "Other workers" },
  { key: "primary", label: "Primary School" },
] as const;

export type IndexGroupKey = (typeof INDEX_GROUPS)[number]["key"];
export type Gender = "female" | "male";
export const GENDERS: Gender[] = ["female", "male"];

export function buildIndexKey(group: IndexGroupKey, gender: Gender): CmprIndexKey {
  if (group === "sc") return `CMPR_SC_${gender}` as CmprIndexKey;
  if (group === "st") return `CMPR_ST_${gender}` as CmprIndexKey;
  return `CMPR_${group}_${gender}` as CmprIndexKey;
}

export function cmprValue(
  stateName: string,
  year: Year,
  age: AgeBracket,
  indexKey: CmprIndexKey,
): number | null {
  const yearData = CMPR_DATA_BY_YEAR[String(year) as keyof typeof CMPR_DATA_BY_YEAR];
  const stateData = yearData?.[stateName as keyof typeof yearData];
  const ageData = stateData?.[age as keyof typeof stateData];
  if (!ageData) return null;
  const value = ageData[indexKey as keyof typeof ageData];
  return typeof value === "number" ? value : null;
}

export function indexLabel(indexKey: CmprIndexKey): string {
  const short = indexKey.replace(/^CMPR_/, "");
  const suffix = short.endsWith("_female") ? "Female" : "Male";
  if (short.startsWith("SC_")) return `SC (${suffix})`;
  if (short.startsWith("ST_")) return `ST (${suffix})`;
  const base = short
    .replace(/_(female|male)$/, "")
    .split("_")
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
  return `${base} (${suffix})`;
}
