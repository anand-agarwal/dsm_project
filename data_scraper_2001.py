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
PAGE_LIMIT   = 50  # results per API page

# Census year filter — pick one or more: "2011", "2001", "1991"
CENSUS_YEARS = ["2001"]

# All target datasets
TARGET_DATASETS = [
    "C-02",
    "C-02 (SC)",
    "C-02 (ST)",
    "C-02 Appendix",
    "C-02 Appendix (SC)",
    "C-02 Appendix (ST)",
    "C-03 Appendix",
    "C-03",
    "C-04",
    "C-04 (SC)",
    "C-04 (ST)",
    "C-05",
    "C-06",
    "C-07",
    "C-08",
    "C-08 (SC)",
    "C-08 (ST)",
    "C-08 Appendix (Total)",
    "C-08 Appendix (SC)",
    "C-08 Appendix (ST)",
    "C-09",
]

# -----------------------------
# FIX 1: Complete SEARCH_KEYWORDS mapping for ALL datasets.
# The keyword is what we send to the API (broad search).
# Local filtering (match_table) then picks the exact dataset.
# Datasets that share a prefix share a keyword → one API call, cached.
# -----------------------------
SEARCH_KEYWORDS = {
    "C-02":                  "C-02",
    "C-02 (SC)":             "C-02",
    "C-02 (ST)":             "C-02",
    "C-02 Appendix":         "C-02 Appendix",
    "C-02 Appendix (SC)":    "C-02 Appendix",
    "C-02 Appendix (ST)":    "C-02 Appendix",
    "C-03":                  "C-03",
    "C-03 Appendix":         "C-03 Appendix",
    "C-04":                  "C-04",
    "C-04 (SC)":             "C-04",
    "C-04 (ST)":             "C-04",
    "C-05":                  "C-05",
    "C-06":                  "C-06",
    "C-07":                  "C-07",
    "C-08":                  "C-08",
    "C-08 (SC)":             "C-08",
    "C-08 (ST)":             "C-08",
    "C-08 Appendix (Total)": "C-08 Appendix",
    "C-08 Appendix (SC)":    "C-08 Appendix",
    "C-08 Appendix (ST)":    "C-08 Appendix",
    "C-09":                  "C-09",
}

# Validate at startup that every target has a keyword mapping
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
    """Strip/replace characters that are invalid in filenames."""
    name = name.strip()
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = re.sub(r'\s+', "_", name)
    name = re.sub(r'_+', "_", name)
    return name


def build_download_name(dataset_name: str, year: str, state_name: str,
                         district_name: str, original_filename: str) -> str:
    ext = ""
    if "." in original_filename:
        ext = "." + original_filename.rsplit(".", 1)[-1]

    location = safe_filename(state_name) if state_name else "National"
    if district_name and district_name.strip():
        location += "_" + safe_filename(district_name)

    base      = safe_filename(dataset_name)
    year_part = f"_{year}" if year else ""
    return f"{base}{year_part}_{location}{ext}"


# -----------------------------
# FIX 2: Smarter match_table — avoids "C-08" matching "C-08 Appendix".
# Strategy: table_id must equal target exactly (case-insensitive),
# OR the title must contain the full target string bounded by
# word/punctuation boundaries, not just anywhere as a substring.
# -----------------------------
def match_table(table: dict, target: str) -> bool:
    table_id = table.get("table_id", "").strip()
    title    = table.get("title",    "").strip()

    # Exact match on table_id (most reliable)
    if table_id.lower() == target.lower():
        return True

    # Exact match on table_id after stripping leading "Table " prefix
    bare_id = re.sub(r'^table\s+', '', table_id, flags=re.IGNORECASE).strip()
    if bare_id.lower() == target.lower():
        return True

    # Title must contain the target as a whole "word group":
    # escape special regex chars in target, then require word boundaries
    # (or start/end of string / punctuation) around it.
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
        years_param = ",".join(CENSUS_YEARS)
        base += f"&census_year={years_param}"
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

        print(f"     page offset={offset} → {len(tables)} tables  (total found by API: {found})")

        if offset + PAGE_LIMIT >= found or not tables:
            break
        offset += PAGE_LIMIT
        time.sleep(0.3)

    return all_tables


def get_table_year(table: dict) -> str:
    for series in table.get("series", []):
        title = series.get("series_title", "")
        match = re.search(r'\b(19|20)\d{2}\b', title)
        if match:
            return match.group(0)
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
            })

    for item in table.get("items", []):
        for link in item.get("links", []):
            if link.get("format", "").lower() in EXCEL_FMTS:
                results.append({
                    "url":           link["link"],
                    "state_name":    item.get("state_name", "").strip(),
                    "district_name": item.get("district_name", "").strip(),
                })

    return results


# -----------------------------
# FIX 3: Retry logic on download failures.
# -----------------------------
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
                time.sleep(2 ** attempt)  # exponential back-off: 2s, 4s
    # Clean up partial file if it exists
    if os.path.exists(dest_path):
        os.remove(dest_path)
    print(f"    ❌ Download failed after {retries} attempts.")
    return False


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"  Census Table Scraper")
    if CENSUS_YEARS:
        print(f"  Year filter : {', '.join(CENSUS_YEARS)}")
    else:
        print(f"  Year filter : None (all years)")
    print(f"  Save folder : {SAVE_FOLDER}")
    print(f"{'='*60}\n")

    api_cache: dict = {}

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

        tables = api_cache[keyword]

        # FIX 4: Warn when multiple tables match; pick the best (shortest title = least ambiguous).
        matched = [t for t in tables if match_table(t, dataset_name)]

        if not matched:
            print(f"  ❌ No match found for '{dataset_name}'")
            continue

        if len(matched) > 1:
            print(f"  ⚠️  {len(matched)} tables matched '{dataset_name}' — picking shortest title:")
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

            original_filename = url.split("/")[-1].split("?")[0]
            new_filename = build_download_name(
                dataset_name, table_year, state_name, district_name, original_filename
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


if __name__ == "__main__":
    main()