import { useEffect, useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { SiteLayout } from "@/components/SiteLayout";
import { hasSupabaseEnv, supabase } from "@/lib/supabase";
import {
  AGE_GROUPS,
  C_TABLES,
  GENDERS,
  YEARS,
  type AgeGroup,
  type Gender,
  type Year,
} from "@/data/mock";

export const Route = createFileRoute("/explore")({
  head: () => ({
    meta: [
      { title: "Raw Census tables — Bachpan" },
      {
        name: "description",
        content:
          "Browse C-02 to C-12 Census tables filtered by year, gender, age and area. Export as CSV.",
      },
    ],
  }),
  component: ExplorePage,
});

const PAGE_SIZE = 20;
const TABLE_MAP: Record<string, string> = {
  "C-02": "raw_c_02",
  "C-03": "raw_c_03",
  "C-04": "raw_c_04",
  "C-05": "raw_c_05",
  "C-06": "raw_c_06",
  "C-07": "raw_c_07",
  "C-08": "raw_c_08",
  "C-09": "raw_c_09",
  "C-12": "raw_c_12",
};

type RawRow = Record<string, string | number | null>;

function detectColumn(cols: string[], patterns: RegExp[]) {
  return cols.find((c) => patterns.some((p) => p.test(c)));
}

function ExplorePage() {
  const [tableId, setTableId] = useState<string>(C_TABLES[0].id);
  const [year, setYear] = useState<Year>(2011);
  const [area, setArea] = useState<"Total" | "Rural" | "Urban">("Total");
  const [gender, setGender] = useState<Gender | "both">("both");
  const [age, setAge] = useState<AgeGroup | "all">("all");
  const [page, setPage] = useState(0);
  const [allRows, setAllRows] = useState<RawRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoading(true);
      setError(null);
      setPage(0);
      const tableName = TABLE_MAP[tableId];
      if (!tableName) {
        setAllRows([]);
        setError(`No mapped Supabase table for ${tableId}`);
        setLoading(false);
        return;
      }
      if (!supabase || !hasSupabaseEnv) {
        setAllRows([]);
        setError(
          "Missing Supabase env. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in frontend/.env.local",
        );
        setLoading(false);
        return;
      }

      const { data, error: queryError } = await supabase
        .from(tableName)
        .select("*")
        .eq("year", year)
        .eq("total_rural_urban", area)
        .limit(10000);

      if (cancelled) return;

      if (queryError) {
        setAllRows([]);
        const details = [queryError.message, queryError.details, queryError.hint]
          .filter(Boolean)
          .join(" | ");
        setError(details || "Failed to load data from Supabase.");
      } else {
        setAllRows((data ?? []) as RawRow[]);
      }
      setLoading(false);
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [tableId, year, area]);

  const rows = useMemo(() => {
    const cols = allRows[0] ? Object.keys(allRows[0]) : [];
    const sexCol = detectColumn(cols, [/^sex$/i, /gender/i, /male/i, /female/i]);
    const ageCol = detectColumn(cols, [/^age/i, /age_group/i]);

    return allRows.filter((row) => {
      if (gender !== "both" && sexCol) {
        const value = String(row[sexCol] ?? "").toLowerCase();
        if (!value.includes(gender)) return false;
      }
      if (age !== "all" && ageCol) {
        const value = String(row[ageCol] ?? "");
        if (value !== age) return false;
      }
      return true;
    });
  }, [allRows, gender, age]);

  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const slice = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const cols = rows[0] ? Object.keys(rows[0]) : [];

  const downloadCsv = () => {
    const header = cols.join(",");
    const body = rows.map((r) => cols.map((c) => JSON.stringify(r[c] ?? "")).join(",")).join("\n");
    const blob = new Blob([header + "\n" + body], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${tableId}_${year}_${area}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <SiteLayout>
      <section className="border-b border-rule">
        <div className="max-w-[1280px] mx-auto px-6 py-10">
          <div className="eyebrow">Census of India · C-series</div>
          <h1 className="font-display text-5xl tracking-tight mt-1">Raw tables</h1>
          <p className="mt-3 text-subtle max-w-prose">
            The atlas is built on these underlying tables. Filter and export any slice.
          </p>
        </div>
      </section>

      <section className="max-w-[1280px] mx-auto px-6 py-8">

        <div className="grid md:grid-cols-6 gap-4 items-end mb-6">
          <Field label="Table">
            <select
              value={tableId}
              onChange={(e) => {
                setTableId(e.target.value);
                setPage(0);
              }}
              className="w-full border border-rule bg-transparent px-2 py-2 rounded text-sm"
            >
              {C_TABLES.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.id} · {t.title}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Year">
            <Select
              value={String(year)}
              options={YEARS.map(String)}
              onChange={(v) => {
                setYear(Number(v) as Year);
                setPage(0);
              }}
            />
          </Field>
          <Field label="Area">
            <Select
              value={area}
              options={["Total", "Rural", "Urban"]}
              onChange={(v) => {
                setArea(v as typeof area);
                setPage(0);
              }}
            />
          </Field>
          <Field label="Gender">
            <Select
              value={gender}
              options={["both", ...GENDERS]}
              onChange={(v) => {
                setGender(v as Gender | "both");
                setPage(0);
              }}
            />
          </Field>
          <Field label="Age group">
            <Select
              value={age}
              options={["all", ...AGE_GROUPS]}
              onChange={(v) => {
                setAge(v as AgeGroup | "all");
                setPage(0);
              }}
            />
          </Field>
          <button
            onClick={downloadCsv}
            className="bg-ink text-paper rounded px-4 py-2 text-sm hover:opacity-90"
          >
            Download CSV
          </button>
        </div>

        <div className="border border-rule rounded overflow-hidden bg-card">
          {loading && (
            <div className="px-3 py-2 text-sm text-subtle">Loading data from Supabase...</div>
          )}
          {error && <div className="px-3 py-2 text-sm text-red-600">{error}</div>}
          <div className="overflow-x-auto max-h-[560px]">
            <table className="w-full text-sm">
              <thead className="bg-muted sticky top-0">
                <tr>
                  {cols.map((c) => (
                    <th key={c} className="text-left px-3 py-2 eyebrow">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {slice.map((r, i) => (
                  <tr key={i} className="border-t border-rule hover:bg-muted/50">
                    {cols.map((c) => (
                      <td key={c} className="px-3 py-1.5 num">
                        {String(r[c])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="border-t border-rule px-3 py-2 flex items-center justify-between text-xs text-subtle">
            <span className="num">
              {rows.length.toLocaleString()} rows · page {page + 1} of {pages}
            </span>
            <div className="flex gap-2">
              <button
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
                className="px-2 py-1 border border-rule rounded disabled:opacity-40"
              >
                Prev
              </button>
              <button
                disabled={page >= pages - 1}
                onClick={() => setPage((p) => p + 1)}
                className="px-2 py-1 border border-rule rounded disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </section>
    </SiteLayout>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="eyebrow mb-1">{label}</div>
      {children}
    </label>
  );
}

function Select({
  value,
  options,
  onChange,
}: {
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full border border-rule bg-transparent px-2 py-2 rounded text-sm"
    >
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}
