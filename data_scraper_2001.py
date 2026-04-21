import os
import re
import time
import requests
import urllib3

# -----------------------------
# CONFIG
# -----------------------------
API_BASE_URL = "https://censusindia.gov.in/nada/index.php/api/"
SAVE_FOLDER  = "census_downloads_2001"
PAGE_LIMIT   = 50

CENSUS_YEARS = ["2001"]

# ─────────────────────────────────────────────────────────────────────────────
# TARGET DATASETS
# ─────────────────────────────────────────────────────────────────────────────
# These are the ACTUAL table IDs confirmed from a live API run.
#
# Subject mapping to your 2011 scraper:
#
#  MARITAL STATUS
#   "C-02"           ≈ 2011 C-02        Marital status by age and sex (all)
#   "C-03"           ≈ 2011 C-02 (SC)   Marital status by religious community
#   "C-03 Appendix"  ≈ 2011 C-02 App.   Marital status by religion + age
#
#  EDUCATION
#   "C-08"           ≈ 2011 C-03        Educational level by age and sex
#   "C-08 Appendix"  ≈ 2011 C-03 App.   Education level graduate and above
#   "C-09"           (2001-only)         Education level by religious community
#   "C-10"           (2001-only)         Population attending educational institution
#   "C-11"           (2001-only)         Institution attendance by completed level
#   "C-12"           (2001-only)         Ages 5-19 attending by economic activity
#
#  AGE STRUCTURE
#   "C-13"           (2001-only)         Single year age returns
#   "C-13 Appendix"  (2001-only)         Single year age + literacy
#   "C-14"           (2001-only)         Five-year age groups
#
#  RELIGION × AGE
#   "C-15"           (2001-only)         Religious community by age group
#
# NOTE: (SC)/(ST) variants and worker tables (industrial category,
# occupation etc.) were not found under C-series in the 2001 NADA system.
# Use discover() at the bottom to search for them with keywords like
# "workers", "occupation", "B-" etc.
# ─────────────────────────────────────────────────────────────────────────────

TARGET_DATASETS = [
    # Marital status
    "C-02",
    "C-03",
    "C-03 Appendix",

    # Education
    "C-08",
    "C-08 Appendix",
    "C-09",
    "C-10",
    "C-11",
    "C-12",

    # Age structure
    "C-13",
    "C-13 Appendix",
    "C-14",

    # Religion × age
    "C-15",
]

# ─────────────────────────────────────────────────────────────────────────────
# SEARCH KEYWORDS
# ─────────────────────────────────────────────────────────────────────────────
SEARCH_KEYWORDS = {
    "C-02":          "C-02",
    "C-03":          "C-03",
    "C-03 Appendix": "C-03 Appendix",
    "C-08":          "C-08",
    "C-08 Appendix": "C-08 Appendix",
    "C-09":          "C-09",
    "C-10":          "C-10",
    "C-11":          "C-11",
    "C-12":          "C-12",
    "C-13":          "C-13",
    "C-13 Appendix": "C-13 Appendix",
    "C-14":          "C-14",
    "C-15":          "C-15",
}

_missing = [d for d in TARGET_DATASETS if d not in SEARCH_KEYWORDS]
if _missing:
    raise ValueError(f"Missing SEARCH_KEYWORDS entries for: {_missing}")

# -----------------------------
# DISABLE SSL WARNINGS
# -----------------------------
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# -----------------------------
# SESSION SETUP
# -----------------------------
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":     "application/json, text/plain, */*",
    "Referer":    "https://censusindia.gov.in/census.website/data/census-tables",
})
session.verify = False

os.makedirs(SAVE_FOLDER, exist_ok=True)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def safe_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = re.sub(r'\s+', "_", name)
    name = re.sub(r'_+', "_", name)
    return name


def build_download_name(dataset_name: str, year: str, state_name: str,
                         district_name: str, sc: int, st: int,
                         original_filename: str) -> str:
    ext = ""
    if "." in original_filename:
        ext = "." + original_filename.rsplit(".", 1)[-1]

    location = safe_filename(state_name) if state_name else "National"
    if district_name and district_name.strip():
        location += "_" + safe_filename(district_name)

    # Append population group suffix so SC/ST files don't collide with Total
    if sc:
        group = "_SC"
    elif st:
        group = "_ST"
    else:
        group = ""

    base      = safe_filename(dataset_name)
    year_part = f"_{year}" if year else ""
    return f"{base}{year_part}_{location}{group}{ext}"


def match_table(table: dict, target: str) -> bool:
    """
    Return True if *table* from the API corresponds to *target*.

    Rules (in priority order):
      1. Exact match on table_id (case-insensitive).
      2. Exact match after stripping a leading "Table " prefix.
      3. Title contains target as a whole token.

    City variants (table_id contains 'city') are ALWAYS excluded —
    we want national/all tables, not city sub-tables.
    """
    table_id = table.get("table_id", "").strip()
    title    = table.get("title",    "").strip()

    # Never match city-specific sub-tables
    if "city" in table_id.lower():
        return False

    # 1. Exact table_id
    if table_id.lower() == target.lower():
        return True

    # 2. Strip leading "Table " prefix
    bare_id = re.sub(r'^table\s+', '', table_id, flags=re.IGNORECASE).strip()
    if bare_id.lower() == target.lower():
        return True

    # 3. Word-boundary match in title
    escaped = re.escape(target)
    pattern = rf'(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])'
    if re.search(pattern, title, re.IGNORECASE):
        return True

    return False


def build_api_url(keyword: str, offset: int) -> str:
    base = (
        f"{API_BASE_URL}tables/data/global/census_tables/"
        f"{PAGE_LIMIT}/{offset}/?ft_query={requests.utils.quote(keyword)}"
    )
    if CENSUS_YEARS:
        base += f"&census_year={','.join(CENSUS_YEARS)}"
    return base


def fetch_tables_for_keyword(keyword: str) -> list:
    all_tables = []
    offset     = 0
    years_display = ", ".join(CENSUS_YEARS) if CENSUS_YEARS else "all years"
    print(f"  🔍 Querying API: keyword={keyword!r}  |  years={years_display}")

    while True:
        url = build_api_url(keyword, offset)
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  ⚠️  API error at offset {offset}: {e}")
            break

        tables = data.get("data", [])
        found  = data.get("found", 0)
        all_tables.extend(tables)
        print(f"     page offset={offset} → {len(tables)} tables  "
              f"(total found by API: {found})")

        if offset + PAGE_LIMIT >= found or not tables:
            break
        offset += PAGE_LIMIT
        time.sleep(0.3)

    return all_tables


def get_table_year(table: dict) -> str:
    for series in table.get("series", []):
        m = re.search(r'\b(19|20)\d{2}\b', series.get("series_title", ""))
        if m:
            return m.group(0)
    return ""


def collect_links_from_table(table: dict) -> list:
    results    = []
    EXCEL_FMTS = {"xls", "xlsx", "csv"}

    for link in table.get("links", []):
        if link.get("format", "").lower() in EXCEL_FMTS:
            results.append({
                "url":           link["link"],
                "state_name":    "All_India",
                "district_name": "",
                "sc":            0,
                "st":            0,
            })

    for item in table.get("items", []):
        for link in item.get("links", []):
            if link.get("format", "").lower() in EXCEL_FMTS:
                results.append({
                    "url":           link["link"],
                    "state_name":    item.get("state_name", "").strip(),
                    "district_name": item.get("district_name", "").strip(),
                    # The API sets sc=1 for Scheduled Castes rows,
                    # st=1 for Scheduled Tribes rows, both 0 for total.
                    "sc":            int(item.get("sc", 0) or 0),
                    "st":            int(item.get("st", 0) or 0),
                })

    return results


def download_file(url: str, dest_path: str, retries: int = 3) -> bool:
    for attempt in range(1, retries + 1):
        try:
            with session.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            return True
        except Exception as e:
            print(f"    ⚠️  Attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(2 ** attempt)
    if os.path.exists(dest_path):
        os.remove(dest_path)
    print(f"    ❌ Download failed after {retries} attempts.")
    return False


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"  Census Table Scraper — 2001")
    print(f"  Year filter : {', '.join(CENSUS_YEARS)}")
    print(f"  Save folder : {SAVE_FOLDER}")
    print(f"{'='*60}\n")

    api_cache: dict  = {}
    total_downloaded = 0
    total_skipped    = 0
    total_failed     = 0

    for dataset_name in TARGET_DATASETS:
        print(f"\n{'='*60}")
        print(f"📂 Dataset: {dataset_name}")
        print(f"{'='*60}")

        keyword = SEARCH_KEYWORDS[dataset_name]

        if keyword not in api_cache:
            api_cache[keyword] = fetch_tables_for_keyword(keyword)
        else:
            print(f"  ♻️  Using cached results for keyword={keyword!r}")

        tables  = api_cache[keyword]
        matched = [t for t in tables if match_table(t, dataset_name)]

        if not matched:
            print(f"  ❌ No match found for '{dataset_name}'")
            print(f"     Run discover('{keyword}') to inspect raw API results.")
            continue

        if len(matched) > 1:
            # Prefer exact table_id match first; fall back to shortest title
            exact = [
                t for t in matched
                if t.get("table_id", "").lower() == dataset_name.lower()
                or re.sub(r'^table\s+', '', t.get("table_id", ""),
                          flags=re.IGNORECASE).strip().lower()
                   == dataset_name.lower()
            ]
            if exact:
                matched = exact
            else:
                print(f"  ⚠️  {len(matched)} tables matched '{dataset_name}' "
                      f"— picking shortest title:")
                for m in matched:
                    print(f"       [{m.get('table_id')}] {m.get('title')}")
                matched = sorted(matched, key=lambda t: len(t.get("title", "")))

        table      = matched[0]
        table_year = get_table_year(table)

        print(f"  ✅ Matched : [{table.get('table_id')}] {table.get('title')}")
        print(f"  📅 Year    : {table_year if table_year else 'unknown'}")

        year_suffix    = f"_{table_year}" if table_year else ""
        dataset_folder = os.path.join(
            SAVE_FOLDER, safe_filename(dataset_name) + year_suffix
        )
        os.makedirs(dataset_folder, exist_ok=True)

        links = collect_links_from_table(table)
        print(f"  📁 Files   : {len(links)}")

        if not links:
            print("  ⚠️  No Excel/CSV links found for this table.")
            continue

        for i, item in enumerate(links, start=1):
            url           = item["url"]
            state_name    = item["state_name"]
            district_name = item["district_name"]
            sc            = item["sc"]
            st            = item["st"]

            original_filename = url.split("/")[-1].split("?")[0]
            new_filename = build_download_name(
                dataset_name, table_year,
                state_name, district_name, sc, st, original_filename
            )
            dest_path = os.path.join(dataset_folder, new_filename)

            if os.path.exists(dest_path):
                print(f"    ⏭️  [{i}/{len(links)}] Already exists: {new_filename}")
                total_skipped += 1
                continue

            print(f"    ⬇️  [{i}/{len(links)}] {new_filename}")
            success = download_file(url, dest_path)
            if success:
                total_downloaded += 1
            else:
                total_failed += 1

            time.sleep(0.2)

    print(f"\n{'='*60}")
    print(f"🎉 All done!")
    print(f"   ✅ Downloaded : {total_downloaded}")
    print(f"   ⏭️  Skipped   : {total_skipped}")
    print(f"   ❌ Failed     : {total_failed}")
    print(f"   📂 Saved to  : {SAVE_FOLDER}")
    print(f"{'='*60}\n")


# ─────────────────────────────────────────────
# DISCOVERY HELPER
# ─────────────────────────────────────────────
def discover(keyword: str):
    """
    Print every table the API returns for *keyword* in year 2001.
    Use this to find table IDs not yet in TARGET_DATASETS.

    Suggested searches for missing worker tables:
        discover("workers")
        discover("occupation")
        discover("marginal")
        discover("B-")
        discover("industrial")
    """
    tables = fetch_tables_for_keyword(keyword)
    print(f"\nAll API results for keyword={keyword!r}, year=2001:")
    print(f"  {'table_id':28s}  title")
    print("-" * 85)
    for t in tables:
        city_tag = "  [CITY]" if "city" in t.get("table_id", "").lower() else ""
        print(f"  {t.get('table_id',''):28s}  {t.get('title','')}{city_tag}")


if __name__ == "__main__":
    main()

    # ── Uncomment to search for missing worker/other tables ─────────────────
    # discover("workers")
    # discover("occupation")
    # discover("marginal")
    # discover("B-")