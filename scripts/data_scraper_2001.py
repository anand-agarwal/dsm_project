import os
import re
import time
import requests
import urllib3

# -----------------------------
# CONFIG
# -----------------------------
API_BASE_URL = "https://censusindia.gov.in/nada/index.php/api/"
SAVE_FOLDER  = "test_census_downloads_2001"
PAGE_LIMIT   = 50

CENSUS_YEARS = ["2001"]

# ─────────────────────────────────────────────
# TARGET DATASETS
# ─────────────────────────────────────────────
TARGET_DATASETS = [
    "C-07"
]

# ─────────────────────────────────────────────
# 🔴 NEW: DATASET ID MAP (MANUAL OVERRIDE)
# ─────────────────────────────────────────────
# Fill ONLY for problematic datasets
# Example values — replace with real IDs from discover()
DATASET_ID_MAP = {
    # "C-12": "12345",
    # "C-08 Appendix": "67890",
}

# ─────────────────────────────────────────────
# SEARCH KEYWORDS
# ─────────────────────────────────────────────
SEARCH_KEYWORDS = {
    "C-02": "C-02",
    "C-02 Appendix": "C-02 Appendix",
    "C-03": "C-03",
    "C-03 Appendix": "C-03 Appendix",
    "C-04": "C-04",
    "C-05": "C-05",
    "C-06": "C-06",
    "C-07": "C-07",
    "C-08": "C-08",
    "C-09": "C-09",
    "C-12": "C-12",
}

# -----------------------------
# DISABLE SSL WARNINGS
# -----------------------------
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# -----------------------------
# SESSION
# -----------------------------
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
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
    return name


def build_download_name(dataset_name, year, state, district, sc, st, original):
    ext = "." + original.split(".")[-1] if "." in original else ""

    location = safe_filename(state) if state else "National"
    if district:
        location += "_" + safe_filename(district)

    group = "_SC" if sc else "_ST" if st else ""

    return f"{safe_filename(dataset_name)}_{year}_{location}{group}{ext}"


# ─────────────────────────────────────────────
# 🔴 NEW: FETCH BY DATASET ID
# ─────────────────────────────────────────────
def fetch_table_by_id(dataset_id: str) -> dict:
    url = f"{API_BASE_URL}datasets/{dataset_id}"
    print(f"  🔎 Fetching by dataset_id={dataset_id}")

    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("dataset", {})
    except Exception as e:
        print(f"  ❌ Failed to fetch dataset_id {dataset_id}: {e}")
        return {}


# ─────────────────────────────────────────────
# FETCH VIA KEYWORD
# ─────────────────────────────────────────────
def build_api_url(keyword, offset):
    return f"{API_BASE_URL}tables/data/global/census_tables/{PAGE_LIMIT}/{offset}/?ft_query={keyword}&census_year=2001"


def fetch_tables_for_keyword(keyword):
    results = []
    offset = 0

    while True:
        url = build_api_url(keyword, offset)
        try:
            r = session.get(url)
            r.raise_for_status()
            data = r.json()
        except:
            break

        tables = data.get("data", [])
        results.extend(tables)

        if not tables:
            break

        offset += PAGE_LIMIT
        time.sleep(0.2)

    return results


def match_table(table, target):
    table_id = table.get("table_id", "").lower()
    title = table.get("title", "").lower()
    return target.lower() in table_id or target.lower() in title


# ─────────────────────────────────────────────
# LINK EXTRACTION
# ─────────────────────────────────────────────
def collect_links(table):
    results = []

    for link in table.get("links", []):
        results.append({
            "url": link["link"],
            "state": "All_India",
            "district": "",
            "sc": 0,
            "st": 0
        })

    for item in table.get("items", []):
        for link in item.get("links", []):
            results.append({
                "url": link["link"],
                "state": item.get("state_name", ""),
                "district": item.get("district_name", ""),
                "sc": int(item.get("sc", 0)),
                "st": int(item.get("st", 0)),
            })

    return results


# ─────────────────────────────────────────────
# DOWNLOAD
# ─────────────────────────────────────────────
def download(url, path):
    try:
        with session.get(url, stream=True) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
        return True
    except:
        return False


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    for dataset in TARGET_DATASETS:
        print(f"\n📂 {dataset}")

        # 🔴 STEP 1: TRY ID FIRST
        if dataset in DATASET_ID_MAP:
            table = fetch_table_by_id(DATASET_ID_MAP[dataset])
        else:
            # 🔁 FALLBACK TO KEYWORD SEARCH
            keyword = SEARCH_KEYWORDS[dataset]
            tables = fetch_tables_for_keyword(keyword)

            matched = [t for t in tables if match_table(t, dataset)]

            if not matched:
                print("  ❌ No match")
                continue

            table = matched[0]

        if not table:
            print("  ❌ Empty table")
            continue

        year = "2001"

        folder = os.path.join(SAVE_FOLDER, safe_filename(dataset))
        os.makedirs(folder, exist_ok=True)

        links = collect_links(table)
        print(f"  📁 {len(links)} files")

        for i, item in enumerate(links, 1):
            url = item["url"]
            filename = build_download_name(
                dataset,
                year,
                item["state"],
                item["district"],
                item["sc"],
                item["st"],
                url.split("/")[-1]
            )

            path = os.path.join(folder, filename)

            if os.path.exists(path):
                continue

            print(f"    ⬇️ {filename}")

            if not download(url, path):
                print("    ❌ Failed")

            time.sleep(0.1)

    print("\n🎉 Done")


if __name__ == "__main__":
    main()