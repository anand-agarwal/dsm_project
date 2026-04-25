import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { SiteLayout } from "@/components/SiteLayout";
import { IndiaMap } from "@/components/IndiaMap";
import {
  AGE_BRACKETS,
  GENDERS,
  INDEX_GROUPS,
  YEARS,
  buildIndexKey,
  cmprValue,
  type AgeBracket,
  type Gender,
  type IndexGroupKey,
  type Year,
} from "@/data/cmprIndexes";
import geojson from "@/data/india-states.geojson.json";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Bharat.Census — A child-marriage atlas of India (2001 & 2011)" },
      { name: "description", content: "Explore child marriage prevalence, literacy and dropout across Indian states using Census 2001 & 2011 data." },
      { property: "og:title", content: "Bharat.Census — A child-marriage atlas of India" },
      { property: "og:description", content: "State-by-state CMPR, education and economic indicators from Census 2001 & 2011." },
    ],
  }),
  component: AtlasPage,
});

function AtlasPage() {
  const [year, setYear] = useState<Year>(2011);
  const [gender, setGender] = useState<Gender>("female");
  const [age, setAge] = useState<AgeBracket>("14-17");
  const [indexGroup, setIndexGroup] = useState<IndexGroupKey>("total");

  const selectedIndexKey = buildIndexKey(indexGroup, gender);
  const natCmpr = computeNationalAverage(year, "14-17", buildIndexKey("total", "female"));
  const natSelected = computeNationalAverage(year, age, selectedIndexKey);

  return (
    <SiteLayout>
      {/* Hero */}
      <section className="border-b border-rule">
        <div className="max-w-[1280px] mx-auto px-6 pt-12 pb-10 grid lg:grid-cols-12 gap-8">
          <div className="lg:col-span-7">
            <div className="eyebrow mb-3">Census of India · 2001 & 2011</div>
            <h1 className="font-display text-5xl md:text-6xl leading-[1.02] tracking-tight">
              When childhood ends
              <span className="block text-cmpr-700 italic">before it began.</span>
            </h1>
            <p className="dropcap mt-6 text-lg leading-relaxed max-w-[58ch] text-foreground/85">
              India's last two decennial censuses recorded millions of girls married before adulthood.
              This atlas maps that prevalence across states, alongside the literacy, schooling and
              labour patterns that travel with it. Hover any state for a quick read; click to open its
              full dossier.
            </p>
          </div>
          <aside className="lg:col-span-5 lg:border-l lg:border-rule lg:pl-8 flex flex-col justify-end gap-6">
            <Stat label={`National avg CMPR · F · 14–17 · ${year}`} value={`${natCmpr}%`} accent />
            <Stat label={`National avg selected index · ${year}`} value={`${natSelected}%`} />
            <p className="text-xs text-subtle leading-relaxed">
              CMPR = Child Marriage Prevalence Rate. The share of the age-group reported as "ever married"
              in the relevant Census C-series tables. All map values come from your processed 2001/2011 CSVs.
            </p>
          </aside>
        </div>
      </section>

      {/* Controls + Map */}
      <section className="max-w-[1280px] mx-auto px-6 py-10 grid lg:grid-cols-12 gap-8">
        <div className="lg:col-span-3 space-y-6">
          <ControlGroup label="Census year">
            <Toggle options={YEARS.map(String)} value={String(year)} onChange={(v) => setYear(Number(v) as Year)} />
          </ControlGroup>
          <ControlGroup label="Gender">
            <Toggle
              options={GENDERS.map((g) => g[0].toUpperCase() + g.slice(1))}
              value={gender[0].toUpperCase() + gender.slice(1)}
              onChange={(v) => setGender(v.toLowerCase() as Gender)}
            />
          </ControlGroup>
          <ControlGroup label="Age group">
            <Toggle options={AGE_BRACKETS as unknown as string[]} value={age} onChange={(v) => setAge(v as AgeBracket)} />
          </ControlGroup>
          <ControlGroup label="Index">
            <select
              value={indexGroup}
              onChange={(e) => setIndexGroup(e.target.value as IndexGroupKey)}
              className="w-full text-sm bg-transparent border border-rule rounded px-2 py-2 focus:outline-none focus:border-foreground"
            >
              {INDEX_GROUPS.map((idx) => (
                <option key={idx.key} value={idx.key}>{idx.label}</option>
              ))}
            </select>
          </ControlGroup>
          <p className="text-xs text-subtle leading-relaxed pt-2 border-t border-rule">
            Tip: pick any index + gender + age to compare 2001 and 2011 directly from the state CSV output.
          </p>
        </div>
        <div className="lg:col-span-9">
          <div className="rounded-md border border-rule bg-card p-2 md:p-4">
            <IndiaMap year={year} age={age} indexKey={selectedIndexKey} />
          </div>
        </div>
      </section>
    </SiteLayout>
  );
}

function computeNationalAverage(year: Year, age: AgeBracket, indexKey: ReturnType<typeof buildIndexKey>): number {
  const fc = geojson as unknown as { features: Array<{ properties: { NAME_1: string } }> };
  const values = fc.features
    .map((f) => cmprValue(f.properties.NAME_1, year, age, indexKey))
    .filter((v): v is number => v != null);
  if (!values.length) return 0;
  return Math.round((values.reduce((acc, cur) => acc + cur, 0) / values.length) * 10) / 10;
}

function Stat({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <div className="eyebrow mb-1">{label}</div>
      <div className={`font-display num leading-none ${accent ? "text-5xl text-cmpr-700" : "text-4xl"}`}>{value}</div>
    </div>
  );
}

function ControlGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="eyebrow mb-2">{label}</div>
      {children}
    </div>
  );
}

function Toggle({ options, value, onChange }: { options: string[]; value: string; onChange: (v: string) => void }) {
  return (
    <div className="inline-flex border border-rule rounded overflow-hidden">
      {options.map((o) => (
        <button
          key={o}
          type="button"
          onClick={() => onChange(o)}
          className={`px-3 py-1.5 text-xs num transition-colors ${
            o === value ? "bg-ink text-paper" : "hover:bg-muted"
          }`}
        >
          {o}
        </button>
      ))}
    </div>
  );
}
