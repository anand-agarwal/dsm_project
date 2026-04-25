import { useMemo, useState } from "react";
import { geoMercator, geoPath } from "d3-geo";
import { useNavigate } from "@tanstack/react-router";
import geojson from "@/data/india-states.geojson.json";
import { cmprValue, indexLabel, type Year, type AgeBracket, type CmprIndexKey } from "@/data/cmprIndexes";
import { cmprColor, CMPR_BREAKS } from "@/lib/scales";
import { stateSlug } from "@/data/states";

type Feature = {
  type: "Feature";
  properties: { NAME_1: string };
  geometry: GeoJSON.Geometry;
};

const WIDTH = 760;
const HEIGHT = 820;

export function IndiaMap({
  year,
  age,
  indexKey,
}: {
  year: Year;
  age: AgeBracket;
  indexKey: CmprIndexKey;
}) {
  const navigate = useNavigate();
  const [hover, setHover] = useState<{ name: string; x: number; y: number } | null>(null);

  const { features, pathFn } = useMemo(() => {
    const fc = geojson as unknown as { features: Feature[] };
    const projection = geoMercator().fitSize([WIDTH, HEIGHT], fc as unknown as GeoJSON.FeatureCollection);
    const pathFn = geoPath(projection);
    return { features: fc.features, pathFn };
  }, []);

  const hoverData = hover
    ? {
        cmpr: cmprValue(hover.name, year, age, indexKey),
      }
    : null;

  return (
    <div className="relative w-full">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full h-auto select-none">
        <g>
          {features.map((f) => {
            const d = pathFn(f as unknown as GeoJSON.Feature) ?? "";
            const stateName = f.properties.NAME_1;
            const v = cmprValue(stateName, year, age, indexKey);
            const fill = cmprColor(v);
            const isHover = hover?.name === stateName;
            return (
              <path
                key={stateName}
                d={d}
                fill={fill}
                stroke={isHover ? "var(--color-ink)" : "var(--color-paper)"}
                strokeWidth={isHover ? 1.4 : 0.6}
                style={{ cursor: "pointer", transition: "stroke 120ms, opacity 120ms" }}
                onMouseEnter={(e) =>
                  setHover({
                    name: stateName,
                    x: e.clientX,
                    y: e.clientY,
                  })
                }
                onMouseMove={(e) =>
                  setHover((h) => (h ? { ...h, x: e.clientX, y: e.clientY } : h))
                }
                onMouseLeave={() => setHover(null)}
                onClick={() =>
                  navigate({ to: "/state/$slug", params: { slug: stateSlug(stateName) } })
                }
              >
                <title>{stateName}</title>
              </path>
            );
          })}
        </g>
      </svg>

      {hover && hoverData && (
        <div
          className="fixed z-50 pointer-events-none rounded border border-rule bg-card shadow-lg px-3 py-2 text-xs"
          style={{ left: hover.x + 14, top: hover.y + 14, minWidth: 180 }}
        >
          <div className="font-display text-sm font-semibold leading-tight">{hover.name}</div>
          <div className="mt-1.5 flex justify-between gap-4 num">
            <span className="text-subtle">{indexLabel(indexKey)}</span>
            <span className="font-medium">{hoverData.cmpr == null ? "NA" : `${hoverData.cmpr}%`}</span>
          </div>
          <div className="mt-1.5 text-[10px] text-subtle uppercase tracking-wider">Click to open</div>
        </div>
      )}

      <Legend metricLabel={indexLabel(indexKey)} />
    </div>
  );
}

function Legend({ metricLabel }: { metricLabel: string }) {
  return (
    <div className="absolute left-2 bottom-2 bg-card/90 backdrop-blur-sm border border-rule rounded p-3 text-xs">
      <div className="eyebrow mb-2">{metricLabel}</div>
      <div className="flex items-center gap-1">
        {CMPR_BREAKS.map((b) => (
          <div key={b.label} className="flex flex-col items-center gap-1">
            <div className="w-7 h-3" style={{ backgroundColor: b.color }} />
            <span className="text-[10px] text-subtle num">{b.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
