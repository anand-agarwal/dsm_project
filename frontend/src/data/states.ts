// Canonical list of Indian states/UTs aligned with our GeoJSON `name` field.
export const STATES: { name: string; code: string; region: "North" | "South" | "East" | "West" | "Northeast" | "Central" | "UT" }[] = [
  { name: "Andhra Pradesh", code: "AP", region: "South" },
  { name: "Arunachal Pradesh", code: "AR", region: "Northeast" },
  { name: "Assam", code: "AS", region: "Northeast" },
  { name: "Bihar", code: "BR", region: "East" },
  { name: "Chhattisgarh", code: "CG", region: "Central" },
  { name: "Goa", code: "GA", region: "West" },
  { name: "Gujarat", code: "GJ", region: "West" },
  { name: "Haryana", code: "HR", region: "North" },
  { name: "Himachal Pradesh", code: "HP", region: "North" },
  { name: "Jammu & Kashmir", code: "JK", region: "North" },
  { name: "Jharkhand", code: "JH", region: "East" },
  { name: "Karnataka", code: "KA", region: "South" },
  { name: "Kerala", code: "KL", region: "South" },
  { name: "Madhya Pradesh", code: "MP", region: "Central" },
  { name: "Maharashtra", code: "MH", region: "West" },
  { name: "Manipur", code: "MN", region: "Northeast" },
  { name: "Meghalaya", code: "ML", region: "Northeast" },
  { name: "Mizoram", code: "MZ", region: "Northeast" },
  { name: "Nagaland", code: "NL", region: "Northeast" },
  { name: "Odisha", code: "OD", region: "East" },
  { name: "Punjab", code: "PB", region: "North" },
  { name: "Rajasthan", code: "RJ", region: "North" },
  { name: "Sikkim", code: "SK", region: "Northeast" },
  { name: "Tamil Nadu", code: "TN", region: "South" },
  { name: "Telangana", code: "TG", region: "South" },
  { name: "Tripura", code: "TR", region: "Northeast" },
  { name: "Uttar Pradesh", code: "UP", region: "North" },
  { name: "Uttarakhand", code: "UK", region: "North" },
  { name: "West Bengal", code: "WB", region: "East" },
  { name: "Delhi", code: "DL", region: "UT" },
  { name: "Chandigarh", code: "CH", region: "UT" },
  { name: "Puducherry", code: "PY", region: "UT" },
  { name: "Andaman & Nicobar", code: "AN", region: "UT" },
  { name: "Ladakh", code: "LA", region: "UT" },
  { name: "Lakshadweep", code: "LD", region: "UT" },
  { name: "Dadra and Nagar Haveli and Daman and Diu", code: "DN", region: "UT" },
];

export const STATE_BY_NAME = new Map(STATES.map((s) => [s.name, s]));
export const stateSlug = (name: string) =>
  name.toLowerCase().replace(/&/g, "and").replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
export const stateFromSlug = (slug: string) =>
  STATES.find((s) => stateSlug(s.name) === slug);
