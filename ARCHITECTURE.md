# Bachpan — Architecture

Bachpan is a child-marriage atlas of India built from Census of India C-series tables for **2001** and **2011**. The live product is a static React SPA. Almost all analytical work happens **offline** in Python. The only runtime backend is **Supabase Postgres + PostgREST**, used solely by the Raw tables page.

There is no application server, no GraphQL layer, and no remaining edge-function agent. The frontend does not compute CMPR from live census rows; it looks up a pre-baked nested object for the map, and a separate synthetic generator for the state dossier.

If you are new to web development, start with **§0**. It explains the ideas the rest of this file assumes: browsers, SPAs, React, bundlers, APIs, databases, and why Bachpan is split into a static site plus an offline Python pipeline.

---

## 0. How this kind of website works (primer)

### 0.1 What happens when you open a URL

A website is not one magic file. It is a conversation:

1. You type a URL (or click a link). The browser asks a **DNS** server “what IP address is this hostname?” then opens a **TCP** connection and, on the public internet, wraps it in **TLS** (HTTPS) so the traffic is encrypted.
2. It sends an **HTTP request**: “GET `/` please.”
3. A **server** (here: Vercel’s CDN) replies with an **HTTP response**: status `200`, headers, and a body. For Bachpan the first body is `index.html` — a small document that says “put an empty `<div id="app">` on the page, then run this JavaScript.”
4. The browser **parses HTML**, then fetches extra files the HTML/JS mention: JavaScript bundles, CSS, fonts, GeoJSON already compiled into JS, images for the blog.
5. JavaScript **runs in the browser**. It builds the actual UI (the map, the nav, the tables) by creating DOM nodes — the tree of HTML elements you can inspect in DevTools.

Important mental model: **the browser is the computer that runs the app** for almost every Bachpan page. Vercel does not “run React” per click. It only stores files and hands them out. Python does not run when a visitor opens the atlas.

```
You (browser)                         Internet                    Machines we control
─────────────                         ────────                    ───────────────────
1. GET https://…/          ────────►  Vercel CDN  ──►  index.html + JS + CSS
2. JS executes locally
3. (Explore only) GET rows ────────►  Supabase    ──►  Postgres tables
```

### 0.2 Pages vs a single-page app (SPA)

A **multi-page site** (classic blogs, Wikipedia) loads a new HTML document on every click. The server renders each page.

A **single-page app** loads **one** HTML shell, then JavaScript swaps the visible content when the URL changes. Bachpan is an SPA:

- `index.html` never changes.
- TanStack Router looks at `window.location` (`/`, `/explore`, `/state/bihar`, …) and chooses which React **component** to show.
- That is why `vercel.json` **rewrites** unknown paths to `index.html`. If someone opens `/about` directly, the CDN does not have a file named `about`. The rewrite says “give them the SPA shell anyway; JS will show About.”

Tradeoff: first load downloads more JS; after that, changing pages is fast and can happen without a full reload. SEO and social previews need extra `head` tags (Bachpan sets those in `__root.tsx` and per-route `head`).

### 0.3 HTML, CSS, JavaScript — three jobs

| Language | Job | In Bachpan |
|---|---|---|
| **HTML** | Structure: headings, links, a box for the app | `frontend/index.html`; React then *generates* more HTML |
| **CSS** | Appearance: type, color, layout | `styles.css` + Tailwind utility classes on components |
| **JavaScript / TypeScript** | Behavior: clicks, filters, fetching data, drawing SVG | Almost all of `frontend/src` |

**TypeScript** is JavaScript plus types (`Year = 2001 | 2011`). Types are erased at build time; the browser only sees JS. They exist to catch mistakes before you ship (`cmprValue` cannot be passed a year `1991` without a compile error).

### 0.4 The DOM, React, and “components”

The **DOM** is the browser’s live tree of elements. Updating it by hand (`document.createElement`) does not scale.

**React** is a library that lets you describe UI as **functions of data**:

```tsx
function Stat({ label, value }) {
  return <div>{label}: {value}</div>;
}
```

That XML-looking syntax is **JSX**. It is not HTML in the file; a compiler turns it into `React.createElement(...)`. You **compose** small functions into pages: `AtlasPage` renders `SiteLayout`, which renders children, which include `IndiaMap`.

Key React ideas used everywhere in this repo:

- **Props** — inputs from a parent (`IndiaMap` receives `year`, `age`, `indexKey`). The child does not own them; the parent does.
- **State** — data the component owns and can change (`useState(2011)` for the year toggle). Changing state **schedules a re-render**: React calls the function again, diffs the new tree against the old one, and updates only what changed. That is the “virtual DOM” idea: describe the whole UI; let the library patch the real DOM.
- **Hooks** — functions whose names start with `use` that tap into React’s engine. `useState` holds state. `useEffect` runs *after* paint (data fetching on Explore). `useMemo` caches an expensive calculation (map projection). `useNavigate` is from the router, not React core, but follows the same rule: only call hooks at the top of a component, not inside loops.
- **Keys** — when you `.map()` a list to elements, React needs a stable `key` so it can tell “this path is still Odisha” vs “this is a new state.”

A **re-render is not a page reload**. The URL can stay `/`. Only the function runs again. That is why toggling 2001/2011 on the map feels instant: no network, just `setYear` → `IndiaMap` reads a different slice of `CMPR_DATA_BY_YEAR`.

### 0.5 Modules, bundling, and Vite

Source is split into **modules** (`import { cmprValue } from "@/data/cmprIndexes"`). Browsers can load native modules, but a real app has thousands of files, TypeScript, JSX, and CSS. A **bundler** (Vite, using Rollup for production) walks the import graph starting at `main.tsx`, compiles TS/JSX, tree-shakes unused code, and emits a few hashed files in `dist/`.

- **Dev (`npm run dev`)** — Vite serves source quickly, injects a WebSocket for hot reload. You edit `IndiaMap.tsx`; the browser updates without a full refresh.
- **Prod (`npm run build`)** — minified bundles. `cmprDataset.ts` is huge, so it becomes a large JS chunk the atlas must download. That is a deliberate choice: **ship the data with the app** so the map works offline-ish and without a database.

`@/` is a **path alias** (see `vite.config.ts` / `tsconfig`) meaning `frontend/src/`. It is not a special language feature.

### 0.6 Client-side routing

The **URL** is just a string. The **router** is a library that:

1. Matches it against a table of routes (`/` vs `/state/$slug`).
2. `$slug` is a **param** — a variable piece (`bihar`, `kerala`).
3. Runs an optional **loader** *before* showing the page (state route looks up the slug; if unknown, 404).
4. Renders the matching component inside the root’s `<Outlet />` — a placeholder that means “child route goes here.”

History API (`pushState`) changes the URL without asking the server for new HTML. The back button still works because the browser stores history entries; the router listens to `popstate`.

### 0.7 Where data can live (the core theory of this project)

Any web app must answer: **who has the numbers, and when are they computed?**

| Pattern | When computed | Who stores it | Bachpan example |
|---|---|---|---|
| **Bundled static data** | Once, before deploy | Inside the JS bundle | Atlas map (`cmprDataset.ts`) |
| **Computed in the browser** | On every render | Nowhere (pure functions) | State dossier (`mock.ts`); national average of visible states |
| **Fetched at runtime** | On demand | Database in the cloud | Explore page (`raw_c_*`) |
| **Computed on a server per request** | On each HTTP call | Server + DB | *Not used* (the old agent function would have been this) |
| **Batch / ETL offline** | When a researcher runs a script | Files on disk, then maybe DB or bundle | Index builders, LASSO |

Bachpan is mostly **static + ETL**. Census Excel is messy and slow. Python turns it into indexes **once**. The website is a viewer. Explore is the exception: it asks Postgres for raw rows so you can browse tables that would be too large to ship in JS.

### 0.8 HTTP APIs, REST, and PostgREST

When Explore needs rows, the browser cannot talk SQL to Postgres (that would leak credentials and isn’t how browsers work). Instead:

1. `@supabase/supabase-js` builds an **HTTP** request, roughly `GET /rest/v1/raw_c_08?year=eq.2011&total_rural_urban=eq.Urban`.
2. **PostgREST** (part of Supabase) is a program that maps HTTP to SQL: that URL becomes `SELECT * FROM raw_c_08 WHERE year = 2011 AND total_rural_urban = 'Urban' LIMIT 10000`.
3. Postgres returns rows; PostgREST returns **JSON**; JS puts JSON into React state; React renders a `<table>`.

This style is **REST-ish**: nouns (tables) as URLs, HTTP verbs (`GET` read, `POST` insert — Bachpan only GETs). JSON is the lingua franca: nested objects/arrays that both Python and JS understand.

The **anon key** in `.env.local` is not a password for your laptop user. It is a public-ish JWT that PostgREST uses to apply **Row Level Security**. If RLS allows `SELECT` for role `anon`, anyone who can read the frontend env can read those tables. Never put the **service role** key in Vite `VITE_*` variables — those are compiled into the browser bundle and are visible to every visitor.

**CORS**: the browser blocks JS from reading responses from another origin unless the server sends `Access-Control-Allow-Origin`. Supabase allows the web app origin. This is why `createClient(url, key)` works from localhost and from Vercel.

### 0.9 SQL and “migrations”

A **database** stores tables (rows × columns) with types, indexes, and constraints (`year in (2001, 2011)`).

A **migration** is a versioned SQL file: “here is the next change to the schema.” Running migrations in order brings any empty Postgres up to the same shape. Bachpan’s `CREATE TABLE raw_c_02 (...)` is the contract Explore depends on. **Seed** data is a later migration (or a separate load) that `INSERT`s CSV contents.

Indexes (`raw_c_02_year_idx`) are B-trees that make `WHERE year = 2011` fast. They are not “CMPR indexes” — unfortunate overloaded word. In this project:

- **DB index** = query accelerator.
- **CMPR index** = a derived statistic (child marriage prevalence rate).

### 0.10 Environment variables

Code should not hardcode secrets or machine-specific URLs. `VITE_SUPABASE_URL` is injected at **build/dev** time. Vite only exposes variables prefixed with `VITE_` to the browser. Changing `.env.local` requires restarting the dev server. Production sets the same names in the Vercel dashboard so the production bundle points at the hosted project.

### 0.11 CSS theory (enough to read this codebase)

**Cascade + specificity**: later / more specific rules win. **Utility CSS** (Tailwind) inverts the old “write a class `.card` in a CSS file” model: you put small classes on the element (`flex`, `max-w-[1280px]`, `text-cmpr-700`). Tailwind’s Vite plugin scans source and emits only the CSS you used.

Bachpan also uses **CSS variables** (`--color-cmpr-700`) as a design palette. `cmprColor()` returns `var(--color-cmpr-500)` so the map and theme stay in sync. Layout is mostly **flexbox** and **CSS grid** (`grid lg:grid-cols-12`). `lg:` means “this utility applies from the large breakpoint up” — responsive design without a separate mobile site.

### 0.12 SVG, GeoJSON, and map projections (atlas)

The map is not Google Maps. It is an **SVG** (scalable vector graphic): `<path d="M ...">` for each state.

**GeoJSON** is JSON for geography: `Feature` = properties + `geometry` (lists of longitude/latitude). Those coordinates are on a sphere. A **projection** (here **Mercator**) flattens them onto a 760×820 pixel plane. `d3-geo`’s `geoPath` turns a projected polygon into an SVG `d` string.

Color is a **choropleth**: each region filled by a statistic. `cmprColor` is a **discrete classification** (bins), not a continuous gradient — easier to legend and to compare states.

Clicking a path does not “select a GIS feature on a server.” It runs `navigate` with a **slug** (a URL-safe id: `"Jammu & Kashmir"` → `jammu-and-kashmir`).

### 0.13 Charts (Recharts)

Recharts wraps SVG. You pass **arrays of objects** (`[{ age: "14-17", Female: 12.3, Male: 4.1 }, ...]`). The library maps keys to lines/bars. This is the same idea as React: **data in, graphics out**. If the array is synthetic (`mock.ts`) the chart looks real but is not census output.

### 0.14 Offline Python: ETL, not “the backend”

**ETL** = Extract, Transform, Load.

- **Extract** — scrapers download Excel from Census NADA (an **API**: a documented HTTP interface for machines).
- **Transform** — pandas reads tables, filters state-level Total rows, maps messy age labels into brackets, computes ratios (`safe_div`).
- **Load** — write CSVs, or generate SQL `INSERT`s, or (manually) paste numbers into `cmprDataset.ts`.

Researchers run this on a laptop when the data changes. Visitors never wait for pandas.

**LASSO** is a regression that sets many coefficients to zero so you see *which* education/work variables co-move with CMPR. **Hierarchical clustering** groups states with similar predictor profiles. Both are **exploratory statistics** for the blog, not for the live map.

### 0.15 Hosting and CDNs

**Vercel** (and any static host) copies `dist/` to a **CDN**: servers in many cities that cache files. A user in India should get JS from a nearby edge node. There is no Node process computing CMPR per request.

SPA caveat: the CDN must serve `index.html` for client routes (the rewrite rule). Files with extensions (`/blog.html`, `/figures/foo.png`) are served as themselves.

### 0.16 How to read the rest of this file

You now have the vocabulary. Next sections are **this repo’s** map: folders, routes, tables, and census-specific CMPR definitions. When something says “bundled nested object,” that is §0.7 pattern 1. When it says “PostgREST,” that is §0.8.

---

## 1. System overview

```
Census of India NADA API
        │
        ▼
Python scrapers  →  census_downloads_{2001,2011}/  (Excel)
        │
        ▼
Manual / unnamed conversion  →  raw_data/{2001,2011}/*.csv
        │
        ├──────────────────────────────┐
        ▼                              ▼
Index builders (pandas)         Migration generators
        │                              │
        ▼                              ▼
output_datasets_*/*.csv         supabase/migrations/*.sql
        │                              │
        ├─ LASSO / clustering          ▼
        │  analysis_outputs/     Supabase Postgres
        │  regression_outputs_*        │
        │                              │  PostgREST (anon key)
        ▼                              ▼
Hand-compiled                 frontend /explore
frontend/src/data/cmprDataset.ts
        │
        ▼
Vite SPA (atlas map, about, blog)
        │
        ▼
Vercel static hosting
```

**Two independent read paths at runtime**

| Path | Used by | Source of truth | Network |
|---|---|---|---|
| Bundled CMPR JSON | `/` atlas map, national averages | `cmprDataset.ts` | None |
| Synthetic mock model | `/state/$slug` dossier charts | `mock.ts` | None |
| Supabase tables | `/explore` raw C-tables | `raw_c_*` Postgres tables | HTTPS to Supabase |
| Static HTML | `/blog` | `frontend/public/blog.html` | None (iframe) |

The state dossier **does not** read `cmprDataset.ts`. Its KPIs and charts come from a deterministic seeded model in `mock.ts` that is explicitly marked as not for analytical use. The map **does** use processed census-derived CMPR.

---

## 2. Repository layout

```
dsm_project/
├── frontend/                      # Vite + React + TanStack Router SPA
├── scripts/                       # Scrapers, index builders, analysis, SQL generators
├── supabase/                      # Local/remote Postgres project (schema only in git)
├── raw_data/{2001,2011}/          # Flattened state-level CSVs (one file per C-table)
├── census_downloads_{2001,2011}/  # Gitignored Excel dumps from NADA
├── output_datasets_{2001,2011}/   # Older long-format index CSVs
├── output_datasets_{2001,2011}_new/  # Current index-builder outputs
├── analysis_outputs/              # Clustering / LASSO run artifacts
├── regression_outputs_{2001,2011}/
├── blog.html                      # Root copy of the essay (public copy lives in frontend/public)
├── vercel.json                    # SPA rewrite for Vercel
├── tests.ipynb                    # Ad-hoc notebook
└── ARCHITECTURE.md, FLOW.md
```

Gitignored (not part of the deployed app): `census_downloads_*`, `.venv`, `.vercel`, `.DS_Store`. `.vercelignore` additionally excludes `raw_data`, `output_datasets_*`, `supabase`, and `tests.ipynb` from Vercel uploads.

---

## 3. Runtime product (frontend)

### 3.1 Stack

| Concern | Choice |
|---|---|
| UI | React 19 |
| Bundler / dev server | Vite 7 (`frontend/vite.config.ts`) |
| Routing | TanStack Router file routes + generated `routeTree.gen.ts` |
| Styling | Tailwind CSS 4 (`@tailwindcss/vite`), Inter + Source Serif 4 + Noto Serif Devanagari |
| Charts | Recharts 3 |
| Map projection | `d3-geo` Mercator + GeoJSON |
| Data client | `@supabase/supabase-js` (Explore only) |
| Component kit | shadcn/ui (New York) under `src/components/ui/` — **not used by product routes** |
| Hosting | Vercel; `vercel.json` rewrites all non-file paths to `index.html` |

Entry HTML is `frontend/index.html` (`#app` + `/src/main.tsx`). `main.tsx` calls `getRouter()` and mounts `<RouterProvider>`.

**Why this stack, in one paragraph.** React is the UI language. Vite is the factory that turns TSX into browser JS. TanStack Router is the URL→screen table (file-based: a file named `about.tsx` becomes `/about` by convention, which is easier to grep than a central `routes = []` list). Tailwind avoids a large custom CSS architecture. d3-geo is used *only* for projection/path — not the whole d3 charting suite — because the atlas is a custom SVG, not a chart. Recharts is the opposite: a high-level chart kit so the dossier does not hand-draw axes. Supabase JS is a thin HTTP wrapper; it is not an ORM in the Django sense.

**shadcn/ui** is a common React pattern: copy-paste accessible primitives (built on Radix) into *your* repo so you own the source. Bachpan includes the kit but the atlas was designed with plain elements (`<button>`, `<select>`, `<table>`). Unused kit code still ships only if something imports it; Vite tree-shakes the rest.

### 3.2 Routing

TanStack Router auto-discovers `frontend/src/routes/*` and writes `routeTree.gen.ts`.

| File | URL | Role |
|---|---|---|
| `__root.tsx` | (layout) | Document head, global CSS, 404 shell, `<Outlet />` |
| `index.tsx` | `/` | Atlas: filters + choropleth + national averages |
| `explore.tsx` | `/explore` | Raw C-table browser against Supabase |
| `state.$slug.tsx` | `/state/:slug` | Per-state dossier (synthetic metrics) |
| `about.tsx` | `/about` | Methodology copy |
| `blog.tsx` | `/blog` | Full-viewport iframe of `/blog.html` |

`router.tsx` wraps the generated tree with scroll restoration and a default error screen (`DefaultErrorComponent`).

`SiteLayout` wraps Atlas, Explore, About, and the state dossier (not Blog). It is the only shared chrome: brand, nav links (Atlas / Raw tables / About / Blog), footer.

**Layout theory.** `__root` is a **layout route**: it always renders. Children render in `<Outlet />`. That is how you share fonts and 404 UI without repeating them. `SiteLayout` is a *second* layout, but it is a normal component you wrap by hand — not a pathless route. Blog skips it because the essay is a full-screen iframe (a nested document; see §0.1 — an iframe is a browsing context with its own HTML).

**File-route naming.** `state.$slug.tsx` uses `$` to mean “this path segment is a variable.” The generated types then know `params.slug` is a string, so `Link` and `navigate` are checked at compile time. That is the point of a typed router vs `react-router` string paths you can typo.

**Loaders vs render.** The state `loader` runs when you enter the route. It is the right place for “does this slug exist?” because you can `throw notFound()` before painting a broken page. Filter state (`year` on the dossier) stays in `useState` because it is UI, not identity.

### 3.3 Product components

**`SiteLayout`** — presentational. No data fetching.

**`IndiaMap`** (`frontend/src/components/IndiaMap.tsx`)

- Props: `year`, `age`, `indexKey`.
- Loads `india-states.geojson.json`.
- `mergeFeaturesByState` groups polygons by `canonicalStateName`.
- `combineGeometries` flattens Polygon / MultiPolygon into one geometry per state.
- Projects with `geoMercator().fitSize([760, 820], …)` and `geoPath`.
- Fill color: `cmprValue(state, year, age, indexKey)` → `cmprColor`.
- Click: `navigate({ to: "/state/$slug", params: { slug: stateSlug(name) } })`.
- Hover tooltip shows `indexLabel(indexKey)` and the percent (or `NA`).
- `Legend` renders `CMPR_BREAKS`.

**How `IndiaMap` works conceptually.** The component is a **pure view of props + hover state**. Changing year on the parent does not “ask the map to reload data”; the parent passes a new `year` prop, React re-renders `IndiaMap`, and each `<path>` looks up a different number. Projection is wrapped in `useMemo(..., [])` so rotating the year does not redo spherical math — the outlines never change, only `fill`. Hover is local state because it is ephemeral UI (tooltip position), not something you want in the URL.

`mergeFeaturesByState` exists because GeoJSON often has **one row per polygon**, while a state like Goa or islands may be several polygons. GIS would use a MultiPolygon; here we merge in JS so one click target = one political unit = one slug.

**Atlas page helpers** (local to `index.tsx`, not exported)

- `computeNationalAverage` — unique GeoJSON states → `canonicalStateName` → `cmprValue` → mean, one decimal.
- `Stat`, `ControlGroup`, `Toggle` — UI only.

**Explore page helpers** (local to `explore.tsx`)

- `detectColumn` — regex pick of sex / age columns for client-side filter.
- `downloadCsv` — Blob download of the **filtered** row set.
- `Field`, `Select` — UI only.

**State dossier sections** (local to `state.$slug.tsx`)

- `StatePage` — year toggle, KPI strip from `stateDigest`.
- `SectionA` — CMPR by age/gender (line) and 2001 vs 2011 female bars.
- `SectionB` — literacy vs CMPR scatter across all `STATES`; `EduDistChart`.
- `SectionC` — CMPR by worker category.
- `SectionD` — SC / ST / religion tabs.
- `SectionE` — schooling split + a **derived** attendance-by-worker stacked bar (not a census table; it reuses `cmprByWorker` as a proxy).
- `Kpi`, `SectionTitle`, `Card` — presentation.

### 3.4 Frontend data modules

#### `states.ts`

Canonical list of 36 names with region and 2-letter code. Helpers:

- `canonicalStateName` — aliases (Orissa→Odisha, Uttaranchal→Uttarakhand, Telangana/Telengana→**Andhra Pradesh**, Daman & Diu→merged UT, etc.).
- `stateSlug` / `stateFromSlug` — URL ids.

Telangana is folded into Andhra Pradesh because 2001/2011 census geography predates the 2014 split.

#### `cmprDataset.ts`

Generated-style TypeScript constants (very large file):

- `CMPR_INDEX_KEYS` — 42 keys (`CMPR_total_female`, `CMPR_SC_male`, religions, worker and education slices, …).
- `CMPR_DATA_BY_YEAR` — `{ "2001" | "2011" → state → age bracket → indexKey → number | null }`.

Age keys in this object are UI brackets: `"<10" | "10-13" | "14-17" | "18-21"` (not the Python `age_14_17` strings). This file is the **compiled atlas layer**. It is not generated by a checked-in script; it is a snapshot of index-builder CSVs.

#### `cmprIndexes.ts`

Typed façade over `cmprDataset.ts`:

- Types: `Year`, `AgeBracket`, `CmprIndexKey`, `IndexGroupKey`, `Gender`.
- `INDEX_GROUPS` — dropdown on the atlas.
- `buildIndexKey(group, gender)` — special-cases SC/ST naming (`CMPR_SC_female` not `CMPR_sc_female`).
- `cmprValue(state, year, age, indexKey)` — normalize name, walk the nested object, return `number | null`.
- `indexLabel` — human legend text.

#### `mock.ts`

Synthetic Census-style generator used by the **state dossier** (and leftover `C_TABLES` metadata used by Explore). Documented in-file as *not for analytical use*.

Anchors: `BASE_CMPR_F_14_17_2011`, `BASE_LITERACY_F_2011`. Deterministic FNV-style `hash` / `rand` / `jitter`.

Public API: `cmpr`, `literacy`, `dropoutRate`, `childLabour`, `educationDist`, `cmprByWorker`, `schoolingSplit`, `generateRawTable` (unused by Explore now), `nationalAverage` (unused by Atlas now), `stateDigest`.

Explore still imports `C_TABLES`, `AGE_GROUPS`, `GENDERS`, `YEARS` from this file for filter labels only.

**Why a nested object instead of CSV in the browser?** JS can `import` JSON/TS at build time; the values become a plain object in memory. Lookup is `O(1)` hash maps: year → state → age → key. No parsing, no async. The cost is **download size**. A database would stream only the requested slice; the atlas instead pays once and then filters for free. That is the classic static-site vs API tradeoff (§0.7).

**Why `mock.ts` uses a hash instead of `Math.random()`.** `Math.random()` is different every render, so charts would flicker. A **seeded** hash of `"Bihar-2011-female-14-17-total"` is stable: same inputs → same jitter forever. It *looks* like variation across states but is a design/demo layer. Treat dossier numbers as illustrations unless you replace `mock.ts` with `cmprDataset` lookups.

**Façade pattern (`cmprIndexes.ts`).** Pages should not poke `CMPR_DATA_BY_YEAR["2011"]["Bihar"]` directly. A small module owns naming (`buildIndexKey`) and missing-data (`null`). If you later load from an API, you change one function.

#### `india-states.geojson.json`

State polygons. Extra copies `india-states.geojson-1.json` and `india-states.geojson-backup.json` are unused by the map.

### 3.5 Libraries

| File | Role |
|---|---|
| `lib/supabase.ts` | Builds a browser client if `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` are valid HTTP URLs; else `supabase = null`. |
| `lib/scales.ts` | Discrete choropleth bins for CMPR; unused `eduColor` for literacy. |
| `lib/utils.ts` | `cn()` = `clsx` + `tailwind-merge` (shadcn). |
| `hooks/use-mobile.tsx` | `useIsMobile` — only consumed by unused `ui/sidebar.tsx`. |

Env: `frontend/.env.local` (Vite `VITE_*`). Not committed as a secret store for the pipeline.

`lib/supabase.ts` is a **null object** pattern: if env is missing, `supabase` is `null` and Explore shows an error instead of crashing on `createClient(undefined)`. `isValidHttpUrl` guards against empty strings that would throw inside the SDK.

`cn()` exists because Tailwind classes often conflict (`p-2` vs `p-4`). `tailwind-merge` keeps the last one. Product pages rarely need it; shadcn components do.

### 3.6 shadcn/ui kit

`frontend/src/components/ui/*` is a full Radix + shadcn dump (button, dialog, sidebar, chart wrapper, …). **Product routes do not import these.** They are available for future UI work. `components.json` configures aliases `@/components`, `@/lib`, `@/hooks`.

### 3.7 Static blog

`/blog` iframes `/blog.html` from `frontend/public/`. Figures live under `frontend/public/figures` and `frontend/public/lasso_2001_2011_comparison`. A duplicate `blog.html` exists at the repo root.

### 3.8 What the frontend does *not* do

- No TanStack Query usage despite the dependency.
- No `@tanstack/react-start` SSR usage despite the dependency (client-only Vite).
- No Cloudflare plugin usage despite `@cloudflare/vite-plugin`.
- No remaining `agent-query` function.
- No write path to Supabase (select-only).
- Atlas and dossier do not share a metric implementation.

---

## 4. Backend: Supabase

**What “backend” means here.** In tutorials, a backend is often Express/Django that returns JSON you designed. Bachpan’s backend is **Postgres + a generic REST translator**. You do not write `app.get('/c08')`. You create a table; PostgREST exposes it. That is faster for tabular census dumps and worse if you need custom business logic (joins, CMPR formulas, auth workflows). Custom logic lived briefly in an edge function; it was removed. Formula work stays in Python.

### 4.1 Project

`supabase/config.toml` — local stack (API 54321, DB 54322, Studio 54323, Postgres 17, Deno 2 edge runtime). `project_id = "dsm_project"`. Studio OpenAI key is a default template (`env(OPENAI_API_KEY)`), unused by the app.

`supabase/.gitignore` ignores `.branches`, `.temp`, dotenvx files.

### 4.2 Schema

Migrations:

| File | Status |
|---|---|
| `20260426111453_create_raw_census_tables.sql` | Empty placeholder |
| `20260426165000_create_raw_census_tables.sql` | Real schema, generated by `scripts/generate_raw_census_migration.py` |
| `20260426170000_seed_raw_census_data.sql` | Generator exists; the seed file itself is currently deleted in the working tree |

Each `raw_*` table:

- `id bigserial primary key`
- `year integer not null check (year in (2001, 2011))`
- Remaining census header columns as `text` (names sanitized from CSV headers)
- Index on `year`

Tables (24):

`raw_c_02`, `raw_c_02_appendix`, `raw_c_02_appendix_sc`, `raw_c_02_appendix_st`, `raw_c_02_sc`, `raw_c_02_st`, `raw_c_03`, `raw_c_03_appendix`, `raw_c_04`, `raw_c_04_sc`, `raw_c_04_st`, `raw_c_05`, `raw_c_06`, `raw_c_07`, `raw_c_08`, `raw_c_08_appendix_sc`, `raw_c_08_appendix_st`, `raw_c_08_sc`, `raw_c_08_st`, `raw_c_09`, `raw_c_12`, `raw_c_12_sc`, `raw_c_12_st`.

Explore’s `TABLE_MAP` only queries a subset:

```
C-02 → raw_c_02
C-03 → raw_c_03
C-04 → raw_c_04
C-05 → raw_c_05
C-06 → raw_c_06
C-07 → raw_c_07
C-08 → raw_c_08
C-09 → raw_c_09
C-12 → raw_c_12
```

SC/ST/appendix tables exist in Postgres but are not exposed in the UI.

There are **no RLS policies** in the committed migrations. Access control, if any, is whatever is configured on the hosted project (typically open `SELECT` for `anon` if Explore works with the anon key).

### 4.3 Query contract (Explore)

```
from(table)
  .select("*")
  .eq("year", year)
  .eq("total_rural_urban", area)   // "Total" | "Rural" | "Urban"
  .limit(10000)
```

Gender and age filters are applied **in the browser** after load, by guessing column names (`/^sex$/i`, `/gender/i`, `/^age/i`, …). Many C-tables store sex as separate male/female **columns**, not a `sex` row dimension, so those filters often no-op.

**Client-side vs server-side filter.** Fetching 10k rows then filtering in JS is simple and fine at this scale. A “real” app would add `.eq("sex", gender)` on the query so Postgres does the work and less data crosses the network. That requires a **normalized** schema (a `sex` column). Census extracts are **wide** (males_3, females_4, …), so the UI cannot filter sex with a single equality without knowing column roles. Regex `detectColumn` is a heuristic, not a data dictionary.

### 4.4 Seed pipeline

`scripts/generate_raw_census_seed_migration.py` walks `raw_data/{year}/*.csv`, maps files to `raw_*` tables, injects `year` from the parent folder name, and emits `INSERT` SQL. That is the intended load path. Runtime Explore data quality depends on that seed having been applied remotely.

---

## 5. Offline data pipeline

This is the real “backend” of Bachpan: batch Python, not HTTP.

**Theory: why not do this in the browser?** Census workbooks are wide, multi-header, and inconsistent across years. pandas is built for that. Browsers have RAM/CPU limits and you do not want every visitor to parse 30 Excel files. So the pipeline is a **batch job**: run when source data changes, commit or upload the products. The website is a **read replica** of those products (JSON bundle or Postgres).

**Scraping theory.** An HTML page is for humans; an **API** returns structured JSON. The scraper paginates (`offset`) because catalogs are long. It **caches** search results per keyword so C-02 and C-02 (SC) do not hit the network twice. `match_table` is careful because `"C-08"` is a substring of `"C-08 Appendix"` — a classic parsing bug. Downloads skip existing files (**idempotent** jobs: safe to re-run).

### 5.1 Layer 0 — Acquisition

| Script | Output | Notes |
|---|---|---|
| `scripts/data_scraper.py` | `census_downloads_2011/` | Census NADA API, year filter `2011` |
| `scripts/data_scraper_2001.py` | `census_downloads_2001/` | Same idea for 2001 |
| `scripts/2001_rename.py` | `census_downloads_2001_renamed/` | Re-folders files into `C-02_(SC)` style names the index builder expects |

NADA base: `https://censusindia.gov.in/nada/index.php/api/`. SSL verify is disabled. Downloads skip existing files.

`utils.FOLDER` maps dataset keys (`C-04`, `C-02-SC`, …) to those folder names.

### 5.2 Layer 1 — Flattened raw CSVs

`raw_data/2001/` and `raw_data/2011/` hold `*_states.csv` extracts (state-level rows). Conversion from Excel → these CSVs is **not** a first-class script in `scripts/` (aside from ad-hoc `data_check.py` / `tests.ipynb`). These CSVs are the schema source for Supabase.

### 5.3 Layer 2 — Index builder

`scripts/index_builder_scripts/`

| Module | Responsibility |
|---|---|
| `utils.py` | Paths, age-bracket maps, state name canon, Excel I/O, merge/save |
| `build_total.py` | General population: C-04, C-06, C-07, C-08, C-12 |
| `build_SC.py` | SC: C-02-SC, C-08-SC, C-12-SC |
| `build_ST.py` | ST: same shape as SC |
| `build_religion.py` | C-05, C-09 |
| `run_all.py` | CLI orchestrator |

**Config (edit in `utils.py`):**

- `DATA_ROOT` — currently pointed at `census_downloads_2001`
- `OUTPUT_DIR` — currently `output_datasets_2001_new`

Re-point these for a 2011 run. The `_new` vs non-`_new` output folders reflect successive builder versions.

**Grain of every output CSV:** one row per `(state_code, state_name, age_bracket)`.

**Tidy / long format.** Spreadsheets often have one column per age. Analytics prefers **long** data: repeated geo keys and one metric column set. Then “filter to age_14_17” is a row filter, not a column hunt. `gender_split` then produces wide-ish male/female files for LASSO (one target column per file).

**Rates vs counts.** `safe_div` implements the statistical idea of a **proportion × 100**. Denominator of 0 becomes NaN, not crash or `Inf`. Always ask of any CMPR: *percent of what?* Ever-married stock vs current-age population are different theories of “prevalence.”

Python age brackets (8):

`age_below10`, `age_10_13`, `age_14_17`, `age_18_21`, `age_22_25`, `age_26_29`, `age_30_33`, `age_34_plus`.

The atlas UI only exposes the first four, remapped to `<10`, `10-13`, `14-17`, `18-21`.

**CMPR definitions are table-specific** (important):

| Source | Formula (simplified) |
|---|---|
| C-04 / C-06 / C-07 (total) | ever-married in age-at-marriage bracket / ever-married all ages × 100 |
| C-02 SC/ST | currently married in current-age band / population in band × 100 |
| C-05 religion | currently married in bracket / ever-married all ages for that religion × 100 |
| 2001 religion patch (`2001_religion_cmpr.py`) | married under 18 / population under 18 × **1000** from C-03 Appendix |

C-02 uses 5-year age bands, so child brackets are **approximate**. C-04/05/06/07 use 2-year age-at-marriage bands (exact for the eight brackets). C-08/C-09/C-12 have partial coverage above ~19. See `BRACKET_COVERAGE_NOTES` in `utils.py`.

Each builder:

1. Glob Excel files for a dataset key.
2. Parse with a fixed column layout (`C0*_COLS`).
3. Keep state-level Total rows (`_state_slice`).
4. For each canonical age bracket, compute ratios via `safe_div`.
5. Outer-merge on `GEO_KEYS`.
6. `gender_split` → `df_*_state.csv`, `df_*_male.csv`, `df_*_female.csv`.

### 5.4 Layer 3 — 2001 religion patch

`scripts/2001_religion_cmpr.py` appends religion CMPR columns onto `df_religion_state.csv` because the original 2001 religion extract lacked them. It reads `raw_data/2001/C-03_Appendix_states.csv`. Clustering comments still refer to this as a prerequisite.

### 5.5 Layer 4 — Statistical analysis (not in the SPA)

| Script | Role | Typical I/O |
|---|---|---|
| `cmpr_lasso_analysis.py` | Age-wise LASSO (SC/ST/Total × gender) | `output_datasets_*_new` → `regression_outputs_*/lasso_agewise` |
| `cmpr_lasso_analysis_religion.py` | Same for religions | religion CSVs → plots + summary CSV |
| `plot_lasso_2001_2011_comparison.py` | Side-by-side heatmaps / R² plots | LASSO summaries → `frontend/public/lasso_2001_2011_comparison` (used by blog) |
| `cmpr_clustering.py` | Ward hierarchical clustering on LASSO-selected predictors | state CSVs → dendrograms, heatmaps, cluster profiles |

These scripts do not feed the map at runtime. Some figures are copied into `frontend/public` for the essay.

**LASSO in plain language.** Ordinary least squares fits `y ≈ a + b1 x1 + b2 x2 + …` and keeps every `b`. With ~30 states and many correlated predictors (literacy vs illiteracy), that overfits. LASSO adds a penalty that **shrinks many `b`s to exactly 0**, leaving a sparse story: “for this age band, dropout and below-primary share survive.” `StandardScaler` puts predictors on a common scale so the penalty is fair. Leave-one-out CV asks: if we hide one state, how well do we predict it? (`r2`). Age-wise models exist because child marriage **mechanisms can differ by age**; pooling 0–34 would mix them.

**Clustering in plain language.** After LASSO names the important axes, Ward clustering builds a tree of states: merge the pair that increases within-group variance the least. A **dendrogram** is that tree drawn. A **heatmap** shows the same numbers, rows sorted by cluster, so you see “this group is high-literacy / low-CMPR.” It is unsupervised: there is no “correct” k; `choose_n_clusters` is a heuristic (elbow).

### 5.6 Layer 5 — SQL generation

- `generate_raw_census_migration.py` — union of CSV headers per table group → `CREATE TABLE`.
- `generate_raw_census_seed_migration.py` — `INSERT` statements (can be huge).

---

## 6. Data layers (end-to-end)

Think of six layers. Only L4–L5 are in the browser.

| Layer | Name | Format | Who writes | Who reads |
|---|---|---|---|---|
| L0 | Official micro-tables | Excel on NADA | Census of India | Scrapers |
| L1 | Download cache | Excel on disk | Scrapers / rename | Index builders |
| L2 | Flattened raw | CSV in `raw_data/` | Offline conversion | SQL generators, 2001 religion patch |
| L3 | Derived indexes | Long CSV in `output_datasets_*` | Index builders | LASSO, clustering, (manual) compile into TS |
| L4a | Atlas bundle | Nested TS object | Manual compile | Map, national averages |
| L4b | Synthetic model | Functions in `mock.ts` | Authors | State dossier |
| L4c | Hosted raw | Postgres `raw_c_*` | Seed migration | Explore page |
| L5 | Presentation | SVG / Recharts / HTML table | React | User |

**Canonical state names are not unified across layers.** Python `CANONICAL_STATES` uses `NCT of Delhi`, `Andaman & Nicobar Islands`, separate Dadra and Daman. Frontend `STATES` uses `Delhi`, `Andaman & Nicobar`, merged Dadra+Daman UT. `canonicalStateName` on the frontend is the adapter between GeoJSON labels and `cmprDataset` keys.

**Why adapters exist.** Every system that talks about “Delhi” is a different **ontology** (naming scheme). GIS files, Census Excel, and UI copy disagree. The robust pattern is: pick one canonical list per layer, then write **pure functions** that map aliases. If you skip this, the map shows `NA` for perfectly good data because `"Orissa" !== "Odisha"`.

---

## 7. Census table catalog (what each C-series is for)

| Table | Topic | Index builder | Explore |
|---|---|---|---|
| C-02 | Marital status by age, sex | SC/ST only (`C-02-SC/ST`) | Yes (`raw_c_02`) |
| C-02 Appendix | Alternate marital-status layout | No | Schema only |
| C-03 / Appendix | Marital status by religion | 2001 religion patch uses Appendix | Yes (`raw_c_03`) |
| C-04 | Age at marriage (ever married) | `build_total` | Yes |
| C-05 | Age at marriage × religion | `build_religion` | Yes |
| C-06 | Age at marriage × education | `build_total` | Yes |
| C-07 | Age at marriage × economic activity | `build_total` | Yes |
| C-08 | Education × current age | total + SC + ST | Yes |
| C-09 | Education × religion × age | `build_religion` | Yes |
| C-12 | School attendance × work, ages 5–19 | total + SC + ST | Yes |

---

## 8. Deployment and environments

**Local frontend:** `cd frontend && npm run dev` (Vite). Needs `.env.local` only for Explore.

**Local Supabase:** `supabase start` using `config.toml`. Apply `20260426165000_…sql` (and seed if present).

**Production frontend:** Vercel. Root `vercel.json`:

- `buildCommand`: `npm run build`
- `outputDirectory`: `dist`
- SPA rewrite: `/((?!.*\\.).*)` → `/index.html`

Vercel project root is expected to be `frontend/` (where `package.json` lives). `.vercelignore` at repo root keeps census dumps off the upload.

**Production data:** hosted Supabase project referenced by `VITE_SUPABASE_URL`. Atlas works even if Supabase is down; Explore does not.

**Dev vs prod mental model.** Locally, Vite is a process on your machine serving unbundled TS. Production is **immutable files** from `npm run build`. Bugs that only happen in prod are often “I used a dev-only API” or “env var missing at build time” (Vite inlines `import.meta.env.VITE_*` when it builds — changing Vercel env without rebuilding does nothing).

**Why the atlas survives a DB outage.** Graph A never calls the network for metrics. That is **resilience by architecture**, not retries. Explore is the opposite: no cache layer, so a failed `fetch` is an empty table.

---

## 9. Tooling and miscellaneous

| Item | Role |
|---|---|
| `frontend/eslint.config.js`, Prettier | Lint/format |
| `frontend/vitest.config.ts` | Test runner (`npm test`) — no substantial product tests in-tree |
| `.vscode/extensions.json`, `settings.json` | Editor |
| `scripts/data_check.py` | One-off `read_excel` of a single C-08 SC file |
| `tests.ipynb` | Exploratory notebook |
| Empty `supabase/functions/` | Agent function removed; directory gone |

---

## 10. Invariants and known splits

1. **Map metrics ≠ dossier metrics.** Map = processed census CMPR. Dossier = synthetic `mock.ts`.
2. **CMPR is not one formula.** Total/education/work indexes are age-at-marriage shares of ever-married; SC/ST C-02 indexes are currently-married prevalence in a current-age band; 2001 religion patch is per-thousand under 18.
3. **Age bands leak.** C-02 `10-14` is mapped to `age_10_13`; `15-19` to `age_14_17`. Documented in `utils.py`.
4. **Telangana is Andhra Pradesh** in the frontend alias table.
5. **Explore gender/age filters** are best-effort and often ineffective on column-oriented C-tables.
6. **No write API.** The app is read-only.
7. **Index builder paths are hardcoded** to one year’s `DATA_ROOT` / `OUTPUT_DIR` at a time.

---

## 11. Component inventory (frontend product vs kit)

**Product (wired):** `main.tsx`, `router.tsx`, `routeTree.gen.ts`, all files under `routes/`, `SiteLayout`, `IndiaMap`, `data/{states,cmprIndexes,cmprDataset,mock,india-states.geojson.json}`, `lib/{supabase,scales,utils}`, `styles.css`.

**Scaffold only:** `hooks/use-mobile.tsx`, entire `components/ui/*`, unused GeoJSON backups, unused `generateRawTable` / `nationalAverage` / `eduColor`.

---

## 12. If you are learning web dev from this repo

Suggested order:

1. Open `frontend/index.html` and `main.tsx` — see the empty `#app` and React taking over.
2. Open `routes/about.tsx` — a component with no state (static JSX).
3. Open `routes/index.tsx` — `useState` + child `IndiaMap` (props). Toggle year in the browser and watch DevTools; no network on the atlas.
4. Open `routes/explore.tsx` — `useEffect` + `await` + `setAllRows` (async state). Network tab will show PostgREST.
5. Open `lib/supabase.ts` — env vars become a client or `null`.
6. Skim `cmprIndexes.ts` vs `mock.ts` — lookup vs generator.
7. Run `python scripts/index_builder_scripts/run_all.py` in your head using FLOW.md §10 — files in, CSVs out.

Five ideas that explain most of Bachpan:

1. The **browser runs the UI**.
2. **State changes → re-render**, not full page reload.
3. **Most numbers are precomputed**; the site is a viewer.
4. **Explore is the only live database read**.
5. **Names must be aliased** or the map and CSVs will miss each other.
