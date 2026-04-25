import { useMemo, useState } from "react";
import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend as RcLegend, Line, LineChart,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from "recharts";
import { SiteLayout } from "@/components/SiteLayout";
import {
  AGE_GROUPS, GENDERS, WORKER_CATEGORIES, cmpr, cmprByWorker,
  educationDist, literacy, schoolingSplit, stateDigest,
  type Year,
} from "@/data/mock";
import { STATES, stateFromSlug } from "@/data/states";

export const Route = createFileRoute("/state/$slug")({
  head: ({ params }) => {
    const s = stateFromSlug(params.slug);
    const title = s ? `${s.name} — Census child-marriage dossier` : "State dossier";
    return {
      meta: [
        { title },
        { name: "description", content: s ? `Child marriage, literacy, dropout and worker-category indicators for ${s.name} from Census 2001 & 2011.` : "" },
        { property: "og:title", content: title },
      ],
    };
  },
  loader: ({ params }) => {
    const s = stateFromSlug(params.slug);
    if (!s) throw notFound();
    return { state: s };
  },
  component: StatePage,
  notFoundComponent: () => (
    <SiteLayout>
      <div className="max-w-[800px] mx-auto px-6 py-24 text-center">
        <h1 className="font-display text-4xl">State not found</h1>
        <p className="mt-3 text-subtle">Try one of the {STATES.length} states from the atlas.</p>
        <Link to="/" className="mt-6 inline-block underline">Back to atlas</Link>
      </div>
    </SiteLayout>
  ),
});

function StatePage() {
  const { state } = Route.useLoaderData();
  const [year, setYear] = useState<Year>(2011);
  const d = useMemo(() => stateDigest(state.name, year), [state.name, year]);

  return (
    <SiteLayout>
      {/* Header */}
      <section className="border-b border-rule">
        <div className="max-w-[1280px] mx-auto px-6 pt-10 pb-8">
          <Link to="/" className="eyebrow text-subtle hover:text-foreground">← Atlas</Link>
          <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
            <div>
              <div className="eyebrow">{state.region} India · {state.code}</div>
              <h1 className="font-display text-5xl md:text-6xl leading-none tracking-tight mt-1">{state.name}</h1>
            </div>
            <div className="inline-flex border border-rule rounded overflow-hidden">
              {[2001, 2011].map((y) => (
                <button
                  key={y}
                  onClick={() => setYear(y as Year)}
                  className={`px-4 py-2 text-sm num ${y === year ? "bg-ink text-paper" : "hover:bg-muted"}`}
                >
                  {y}
                </button>
              ))}
            </div>
          </div>

          {/* KPI strip */}
          <div className="mt-8 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-px bg-rule border border-rule rounded overflow-hidden">
            <Kpi label="CMPR · F · 14–17" value={`${d.cmprF}%`} tone="cmpr" />
            <Kpi label="CMPR · M · 14–17" value={`${d.cmprM}%`} />
            <Kpi label="Female literacy" value={`${d.literacyF}%`} tone="edu" />
            <Kpi label="Female dropout" value={`${d.dropoutF}%`} />
            <Kpi label="Child labour" value={`${d.childLabour}%`} />
            <Kpi label="SC/ST CMPR · F" value={`${d.cmprSC} / ${d.cmprST}%`} />
          </div>
        </div>
      </section>

      <div className="max-w-[1280px] mx-auto px-6 py-12 space-y-16">
        <SectionA stateName={state.name} year={year} />
        <SectionB stateName={state.name} year={year} />
        <SectionC stateName={state.name} year={year} />
        <SectionD stateName={state.name} year={year} />
        <SectionE stateName={state.name} year={year} />
      </div>
    </SiteLayout>
  );
}

function Kpi({ label, value, tone }: { label: string; value: string; tone?: "cmpr" | "edu" }) {
  const color = tone === "cmpr" ? "text-cmpr-700" : tone === "edu" ? "text-edu-700" : "text-foreground";
  return (
    <div className="bg-card px-4 py-4">
      <div className="eyebrow mb-2">{label}</div>
      <div className={`font-display text-3xl num leading-none ${color}`}>{value}</div>
    </div>
  );
}

function SectionTitle({ kicker, title, children }: { kicker: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="mb-6 flex items-end justify-between gap-6 flex-wrap">
      <div>
        <div className="eyebrow">{kicker}</div>
        <h2 className="font-display text-3xl md:text-4xl tracking-tight mt-1">{title}</h2>
      </div>
      {children}
    </div>
  );
}

const TOOLTIP_STYLE = {
  backgroundColor: "var(--color-card)",
  border: "1px solid var(--color-rule)",
  borderRadius: 4,
  fontSize: 12,
};

/* ---------- Section A: Child marriage insights ---------- */
function SectionA({ stateName, year }: { stateName: string; year: Year }) {
  const ageData = AGE_GROUPS.map((a) => ({
    age: a,
    Female: cmpr({ state: stateName, year, gender: "female", age: a, category: "total" }),
    Male: cmpr({ state: stateName, year, gender: "male", age: a, category: "total" }),
  }));
  const compare = AGE_GROUPS.map((a) => ({
    age: a,
    "2001": cmpr({ state: stateName, year: 2001, gender: "female", age: a, category: "total" }),
    "2011": cmpr({ state: stateName, year: 2011, gender: "female", age: a, category: "total" }),
  }));

  return (
    <section>
      <SectionTitle kicker="Section A" title="Child marriage by age & gender" />
      <div className="grid lg:grid-cols-2 gap-8">
        <Card title="CMPR across age groups">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={ageData} margin={{ left: -10, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--color-rule)" vertical={false} />
              <XAxis dataKey="age" tick={{ fontSize: 11 }} stroke="var(--color-subtle)" />
              <YAxis tick={{ fontSize: 11 }} stroke="var(--color-subtle)" unit="%" />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <RcLegend wrapperStyle={{ fontSize: 12 }} />
              <Line dataKey="Female" stroke="var(--color-cmpr-700)" strokeWidth={2.5} dot={{ r: 4 }} />
              <Line dataKey="Male" stroke="var(--color-edu-700)" strokeWidth={2.5} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
        <Card title="2001 vs 2011 — female cohort">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={compare} margin={{ left: -10, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--color-rule)" vertical={false} />
              <XAxis dataKey="age" tick={{ fontSize: 11 }} stroke="var(--color-subtle)" />
              <YAxis tick={{ fontSize: 11 }} stroke="var(--color-subtle)" unit="%" />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <RcLegend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="2001" fill="var(--color-cmpr-300)" />
              <Bar dataKey="2011" fill="var(--color-cmpr-700)" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
      <p className="text-xs text-subtle mt-3 max-w-prose">
        Year toggle controls the KPI strip and Section B–E. Section A always shows both years for context.
      </p>
    </section>
  );
}

/* ---------- Section B: Education vs CMPR ---------- */
function SectionB({ stateName, year }: { stateName: string; year: Year }) {
  const scatter = STATES.map((s) => ({
    x: literacy(s.name, year, "female"),
    y: cmpr({ state: s.name, year, gender: "female", age: "14-17", category: "total" }),
    name: s.name,
    z: s.name === stateName ? 280 : 60,
  }));

  return (
    <section>
      <SectionTitle kicker="Section B" title="Where literacy rises, marriage falls" />
      <div className="grid lg:grid-cols-3 gap-8">
        <Card title="Female literacy vs CMPR · all states" className="lg:col-span-2">
          <ResponsiveContainer width="100%" height={320}>
            <ScatterChart margin={{ left: 0, right: 12, top: 8, bottom: 8 }}>
              <CartesianGrid stroke="var(--color-rule)" />
              <XAxis type="number" dataKey="x" name="Female literacy" unit="%" tick={{ fontSize: 11 }} stroke="var(--color-subtle)" />
              <YAxis type="number" dataKey="y" name="CMPR" unit="%" tick={{ fontSize: 11 }} stroke="var(--color-subtle)" />
              <ZAxis dataKey="z" range={[40, 400]} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                cursor={{ strokeDasharray: "3 3" }}
                formatter={(v: number) => `${v}%`}
                labelFormatter={(_, p) => (p && p[0] ? String(p[0].payload.name) : "")}
              />
              <Scatter data={scatter}>
                {scatter.map((p) => (
                  <Cell key={p.name} fill={p.name === stateName ? "var(--color-cmpr-700)" : "var(--color-edu-300)"} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </Card>
        <Card title="Education distribution · female">
          <EduDistChart data={educationDist(stateName, year)} />
        </Card>
      </div>
    </section>
  );
}

function EduDistChart({ data }: { data: Record<string, number> }) {
  const arr = Object.entries(data).map(([name, value]) => ({ name, value }));
  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={arr} layout="vertical" margin={{ left: 60, right: 16, top: 8, bottom: 0 }}>
        <CartesianGrid stroke="var(--color-rule)" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--color-subtle)" unit="%" />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} stroke="var(--color-subtle)" width={110} />
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => `${v}%`} />
        <Bar dataKey="value" fill="var(--color-edu-500)" />
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ---------- Section C: Economic activity ---------- */
function SectionC({ stateName, year }: { stateName: string; year: Year }) {
  const data = cmprByWorker(stateName, year, "female");
  return (
    <section>
      <SectionTitle kicker="Section C" title="Marriage tracks the worker category" />
      <Card title="CMPR · female · 14–17 · by work participation">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} margin={{ left: -10, right: 16, top: 8, bottom: 0 }}>
            <CartesianGrid stroke="var(--color-rule)" vertical={false} />
            <XAxis dataKey="worker" tick={{ fontSize: 11 }} stroke="var(--color-subtle)" interval={0} angle={-12} textAnchor="end" height={60} />
            <YAxis tick={{ fontSize: 11 }} stroke="var(--color-subtle)" unit="%" />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => `${v}%`} />
            <Bar dataKey="cmpr">
              {data.map((d) => (
                <Cell
                  key={d.worker}
                  fill={
                    d.worker === "Agricultural labourers" ? "var(--color-cmpr-900)" :
                    d.worker === "Non-workers" ? "var(--color-cmpr-700)" :
                    d.worker === "Main workers" ? "var(--color-cmpr-500)" :
                    "var(--color-cmpr-300)"
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>
      <p className="text-xs text-subtle mt-3 max-w-prose">
        Source: Census C-07. Highlighted: agricultural labourers, non-workers, and main workers.
      </p>
    </section>
  );
}

/* ---------- Section D: Social group analysis (tabs) ---------- */
const SOCIAL_TABS = [
  { key: "sc", label: "Scheduled Caste" },
  { key: "st", label: "Scheduled Tribe" },
  { key: "religion", label: "By religion" },
] as const;
type SocialKey = typeof SOCIAL_TABS[number]["key"];

function SectionD({ stateName, year }: { stateName: string; year: Year }) {
  const [tab, setTab] = useState<SocialKey>("sc");

  const data =
    tab === "religion"
      ? (["hindu", "muslim", "christian", "sikh", "buddhist", "jain"] as const).map((c) => ({
          name: c[0].toUpperCase() + c.slice(1),
          CMPR: cmpr({ state: stateName, year, gender: "female", age: "14-17", category: c }),
        }))
      : AGE_GROUPS.map((a) => ({
          name: a,
          CMPR: cmpr({ state: stateName, year, gender: "female", age: a, category: tab }),
          "Total population": cmpr({ state: stateName, year, gender: "female", age: a, category: "total" }),
        }));

  return (
    <section>
      <SectionTitle kicker="Section D" title="Who carries the burden">
        <div className="inline-flex border border-rule rounded overflow-hidden">
          {SOCIAL_TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-3 py-1.5 text-xs ${tab === t.key ? "bg-ink text-paper" : "hover:bg-muted"}`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </SectionTitle>
      <Card title={tab === "religion" ? "CMPR · female · 14–17 · by religion" : `CMPR · ${tab.toUpperCase()} vs total · across age groups`}>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} margin={{ left: -10, right: 16, top: 8, bottom: 0 }}>
            <CartesianGrid stroke="var(--color-rule)" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} stroke="var(--color-subtle)" />
            <YAxis tick={{ fontSize: 11 }} stroke="var(--color-subtle)" unit="%" />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => `${v}%`} />
            <RcLegend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="CMPR" fill="var(--color-cmpr-700)" />
            {tab !== "religion" && <Bar dataKey="Total population" fill="var(--color-cmpr-300)" />}
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </section>
  );
}

/* ---------- Section E: Schooling & child labour ---------- */
function SectionE({ stateName, year }: { stateName: string; year: Year }) {
  const dataByGender = GENDERS.map((g) => {
    const rows = schoolingSplit(stateName, year, g);
    const obj: Record<string, string | number> = { Gender: g[0].toUpperCase() + g.slice(1) };
    for (const r of rows) obj[r.bucket] = r.value;
    return obj;
  });
  const buckets = schoolingSplit(stateName, year, "female").map((r) => r.bucket);
  const COLORS = ["var(--color-edu-700)", "var(--color-saffron)", "var(--color-cmpr-500)", "var(--color-cmpr-900)"];

  // Worker × attendance — small table-ish stacked bar
  const workerAttendance = WORKER_CATEGORIES.map((w) => {
    const att = 100 - (cmprByWorker(stateName, year, "female").find((x) => x.worker === w)?.cmpr ?? 0) - 5;
    return {
      worker: w,
      Attending: Math.round(Math.max(40, att) * 10) / 10,
      "Not attending": Math.round((100 - Math.max(40, att)) * 10) / 10,
    };
  });

  return (
    <section>
      <SectionTitle kicker="Section E" title="Schooling, work, and the gap between" />
      <div className="grid lg:grid-cols-2 gap-8">
        <Card title="Where the cohort actually is · by gender">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={dataByGender} margin={{ left: -10, right: 16, top: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--color-rule)" vertical={false} />
              <XAxis dataKey="Gender" tick={{ fontSize: 11 }} stroke="var(--color-subtle)" />
              <YAxis tick={{ fontSize: 11 }} stroke="var(--color-subtle)" unit="%" />
              <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => `${v}%`} />
              <RcLegend wrapperStyle={{ fontSize: 11 }} />
              {buckets.map((b, i) => (
                <Bar key={b} dataKey={b} stackId="s" fill={COLORS[i % COLORS.length]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card title="Attendance by worker category · female">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={workerAttendance} layout="vertical" margin={{ left: 50, right: 16, top: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--color-rule)" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--color-subtle)" unit="%" />
              <YAxis type="category" dataKey="worker" tick={{ fontSize: 11 }} stroke="var(--color-subtle)" width={140} />
              <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => `${v}%`} />
              <RcLegend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="Attending" stackId="a" fill="var(--color-edu-700)" />
              <Bar dataKey="Not attending" stackId="a" fill="var(--color-cmpr-700)" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </section>
  );
}

function Card({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`border border-rule rounded bg-card p-4 ${className}`}>
      <div className="eyebrow mb-3">{title}</div>
      {children}
    </div>
  );
}
