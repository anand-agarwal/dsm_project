import { createClient } from "https://esm.sh/@supabase/supabase-js@2.57.4";
import { z } from "https://esm.sh/zod@3.25.76";

const RequestSchema = z.object({
  question: z.string().trim().min(5).max(400),
  year: z.union([z.literal(2001), z.literal(2011)]).optional(),
  area: z.enum(["Total", "Rural", "Urban"]).optional(),
  table_hint: z.string().trim().optional(),
});

const TABLE_ALLOWLIST = new Set([
  "raw_c_02",
  "raw_c_03",
  "raw_c_04",
  "raw_c_05",
  "raw_c_06",
  "raw_c_07",
  "raw_c_08",
  "raw_c_09",
  "raw_c_12",
]);

type ParsedRequest = z.infer<typeof RequestSchema>;
type MetricHint =
  | "female"
  | "male"
  | "persons"
  | "illiterate"
  | "literate"
  | "married_female"
  | "married_male"
  | "married_persons";

const STATE_NAMES = [
  "Andhra Pradesh",
  "Arunachal Pradesh",
  "Assam",
  "Bihar",
  "Chhattisgarh",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jammu & Kashmir",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Madhya Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Mizoram",
  "Nagaland",
  "Odisha",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil Nadu",
  "Telangana",
  "Tripura",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal",
  "Delhi",
  "Chandigarh",
  "Puducherry",
  "Andaman & Nicobar",
  "Ladakh",
  "Lakshadweep",
  "Dadra and Nagar Haveli and Daman and Diu",
] as const;

function detectIntent(question: string) {
  const q = question.toLowerCase();
  if (q.includes("compare") || q.includes("vs") || q.includes("2001") || q.includes("2011")) return "compare_years";
  if (q.includes("rural") || q.includes("urban")) return "rural_urban_gap";
  if (/\b(female|females|male|males|gender)\b/i.test(question)) return "gender_gap";
  if (q.includes("top") || q.includes("highest") || q.includes("largest")) return "top_changes";
  return "single_slice";
}

function inferTable(question: string, tableHint?: string) {
  const hint = tableHint?.toLowerCase();
  const byHint: Record<string, string> = {
    "c-02": "raw_c_02",
    "c-03": "raw_c_03",
    "c-04": "raw_c_04",
    "c-05": "raw_c_05",
    "c-06": "raw_c_06",
    "c-07": "raw_c_07",
    "c-08": "raw_c_08",
    "c-09": "raw_c_09",
    "c-12": "raw_c_12",
  };
  if (hint && byHint[hint] && TABLE_ALLOWLIST.has(byHint[hint])) return byHint[hint];

  const q = question.toLowerCase();
  if (q.includes("school") || q.includes("attendance") || q.includes("child labour")) return "raw_c_12";
  if (q.includes("education") || q.includes("literacy") || q.includes("illiterate")) return "raw_c_08";
  if (q.includes("religion")) return "raw_c_03";
  return "raw_c_02";
}

function inferMetric(question: string): MetricHint {
  const q = question.toLowerCase();
  const wantsMarried = /\b(ever married|currently married|married)\b/i.test(question);
  const hasFemale = /\b(female|females|women|girls)\b/i.test(question);
  const hasMale = /\b(male|males|men|boys)\b/i.test(question);

  if (wantsMarried && hasFemale) return "married_female";
  if (wantsMarried && hasMale) return "married_male";
  if (wantsMarried) return "married_persons";
  if (q.includes("illiterate")) return "illiterate";
  if (q.includes("literate") || q.includes("literacy")) return "literate";
  if (hasFemale) return "female";
  if (hasMale) return "male";
  if (q.includes("person") || q.includes("population") || q.includes("total")) return "persons";
  return "female";
}

function extractState(question: string): string | null {
  const q = question.toLowerCase();
  const found = STATE_NAMES.find((state) => q.includes(state.toLowerCase()));
  return found ?? null;
}

function pickMetricColumn(columns: string[], hint: MetricHint) {
  const preferred: Record<MetricHint, string[]> = {
    married_female: ["females_10", "females_7", "females_13", "females_16", "females_4"],
    married_male: ["males_9", "males_6", "males_12", "males_15", "males_3"],
    married_persons: ["married_persons_8", "currently_married_persons_8", "total_persons_2"],
    female: ["females_4", "females_10", "females_7"],
    male: ["males_3", "males_9", "males_6"],
    persons: ["total_persons_2", "total_population_persons_2"],
    illiterate: ["illiterate_persons_5"],
    literate: ["literate_persons_8"],
  };

  const exact = preferred[hint].find((col) => columns.includes(col));
  if (exact) return exact;

  const patterns: Record<MetricHint, RegExp[]> = {
    married_female: [/married.*female/i, /female.*married/i, /^females_\d+$/i],
    married_male: [/married.*male/i, /male.*married/i, /^males_\d+$/i],
    married_persons: [/married.*persons/i, /currently_married.*persons/i, /persons/i],
    female: [/female/i],
    male: [/\bmale\b/i],
    persons: [/persons/i, /population/i, /total_persons/i],
    illiterate: [/illiterate/i],
    literate: [/(^|_)literate/i],
  };

  const selected = columns.find((col) => patterns[hint].some((re) => re.test(col)));
  if (selected) return selected;
  return columns.find((col) => /(females|males|persons|literate|illiterate)/i.test(col)) ?? "id";
}

function toNum(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value !== "string") return null;
  const parsed = Number(value.replace(/,/g, "").trim());
  return Number.isFinite(parsed) ? parsed : null;
}

function average(rows: Record<string, unknown>[], column: string) {
  const vals = rows.map((row) => toNum(row[column])).filter((v): v is number => typeof v === "number");
  if (!vals.length) return 0;
  return vals.reduce((acc, v) => acc + v, 0) / vals.length;
}

function sum(rows: Record<string, unknown>[], column: string) {
  const vals = rows.map((row) => toNum(row[column])).filter((v): v is number => typeof v === "number");
  if (!vals.length) return 0;
  return vals.reduce((acc, v) => acc + v, 0);
}

function possibleReasons(intent: string, pctChange: number) {
  const shared = [
    "Administrative reporting quality and data completeness may differ between slices.",
    "These are possible reasons based on known patterns, not causal proof from this table alone.",
  ];
  if (intent === "rural_urban_gap") {
    return [
      `Rural and urban differences in access to schools and services can shape this gap (${pctChange.toFixed(1)}%).`,
      "Differences in household income stability and labor demand can affect continuation in education.",
      ...shared,
    ];
  }
  if (intent === "gender_gap") {
    return [
      `Gender-linked social expectations can contribute to observed divergence (${pctChange.toFixed(1)}%).`,
      "Variation in care burden and schooling continuation can influence outcomes by sex.",
      ...shared,
    ];
  }
  return [
    `Policy implementation and socio-economic shifts can contribute to this change (${pctChange.toFixed(1)}%).`,
    ...shared,
  ];
}

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
    },
  });
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return json({ ok: true });
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  const started = Date.now();
  const requestId = crypto.randomUUID();

  try {
    const payload = RequestSchema.parse(await req.json()) as ParsedRequest;
    const intent = detectIntent(payload.question);
    const table = inferTable(payload.question, payload.table_hint);
    const years = intent === "compare_years" ? [2001, 2011] : [payload.year ?? 2011];
    const area = payload.area ?? "Total";
    const metricHint = inferMetric(payload.question);
    const state = extractState(payload.question);

    const supabaseUrl = Deno.env.get("SUPABASE_URL");
    const supabaseServiceRole = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!supabaseUrl || !supabaseServiceRole) {
      return json({ error: "Missing Supabase service credentials in function environment." }, 500);
    }

    const client = createClient(supabaseUrl, supabaseServiceRole);
    const evidence = [];
    const points: Array<{ label: string; value: number; rows: number }> = [];
    let metricColumn = "unknown_metric";

    for (const year of years) {
      const { data, error } = await client
        .from(table)
        .select("*")
        .eq("year", year)
        .eq("total_rural_urban", area)
        .ilike("area_name", state ? `%${state}%` : "%")
        .limit(800);

      if (error) return json({ error: error.message }, 500);
      const rows = (data ?? []) as Record<string, unknown>[];
      const cols = rows[0] ? Object.keys(rows[0]) : [];
      metricColumn = pickMetricColumn(cols, metricHint);
      const avg = average(rows, metricColumn);
      const total = sum(rows, metricColumn);

      points.push({ label: String(year), value: avg, rows: rows.length });
      evidence.push({
        table,
        filters: { year, total_rural_urban: area, ...(state ? { area_name: state } : {}) },
        rows_considered: rows.length,
        metric_column: metricColumn,
        values: [
          { label: `${year}_average`, value: Number(avg.toFixed(2)) },
          { label: `${year}_total`, value: Number(total.toFixed(2)) },
        ],
      });
    }

    const rowsConsidered = points.reduce((acc, p) => acc + p.rows, 0);
    const confidence = rowsConsidered >= 500 ? "high" : rowsConsidered >= 100 ? "medium" : "low";
    const base = points[0]?.value ?? 0;
    const compare = points[1]?.value ?? points[0]?.value ?? 0;
    const delta = compare - base;
    const pctChange = base === 0 ? 0 : (delta / base) * 100;
    const trend = delta > 0 ? "increased" : delta < 0 ? "decreased" : "remained stable";
    const whereText = state ? ` for ${state}` : "";

    const response = {
      answer:
        intent === "compare_years"
          ? `In ${table}${whereText}, metric ${metricColumn} ${trend} from ${points[0]?.label ?? "baseline"} to ${points[1]?.label ?? points[0]?.label ?? "slice"} (${pctChange.toFixed(2)}%).`
          : `In ${table}${whereText}, metric ${metricColumn} average is ${base.toFixed(2)} across ${points[0]?.rows ?? 0} rows for ${area}.`,
      data_evidence: evidence,
      computed_findings: [
        { key: "average_value", label: `Average (${points[0]?.label ?? "slice"})`, value: Number(base.toFixed(2)), unit: "count" },
        ...(intent === "compare_years"
          ? [
              {
                key: "percent_change",
                label: "Percent change",
                value: Number(pctChange.toFixed(2)),
                unit: "percent" as const,
              },
            ]
          : []),
      ],
      possible_reasons: [
        "Returned values come directly from filtered Supabase rows and selected metric columns.",
        "If the metric column is not the one you expected, specify table and metric explicitly (for example: C-02 females_10 in Odisha).",
      ],
      confidence,
      follow_up_questions: [
        "Would you like this split by rural vs urban?",
        "Should I compare the same metric across 2001 and 2011?",
        "Should I switch to a different table (C-02 to C-12)?",
      ],
      metadata: {
        request_id: requestId,
        intent,
        table,
        latency_ms: Date.now() - started,
      },
    };

    return json(response);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown function error.";
    return json({ error: message, request_id: requestId }, 400);
  }
});
