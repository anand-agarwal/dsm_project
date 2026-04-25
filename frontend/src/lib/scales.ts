// Map a CMPR percentage to a discrete red-scale token.
export function cmprColor(value: number | null): string {
  if (value == null) return "var(--color-muted)";
  if (value < 3) return "var(--color-cmpr-50)";
  if (value < 7) return "var(--color-cmpr-100)";
  if (value < 12) return "var(--color-cmpr-300)";
  if (value < 18) return "var(--color-cmpr-500)";
  if (value < 25) return "var(--color-cmpr-700)";
  return "var(--color-cmpr-900)";
}

export const CMPR_BREAKS = [
  { label: "<3%", color: "var(--color-cmpr-50)" },
  { label: "3–7%", color: "var(--color-cmpr-100)" },
  { label: "7–12%", color: "var(--color-cmpr-300)" },
  { label: "12–18%", color: "var(--color-cmpr-500)" },
  { label: "18–25%", color: "var(--color-cmpr-700)" },
  { label: "≥25%", color: "var(--color-cmpr-900)" },
];

export function eduColor(value: number): string {
  if (value < 40) return "var(--color-edu-100)";
  if (value < 55) return "var(--color-edu-300)";
  if (value < 70) return "var(--color-edu-500)";
  if (value < 85) return "var(--color-edu-700)";
  return "var(--color-edu-900)";
}
