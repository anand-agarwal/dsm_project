"""
=============================================================================
CENSUS C-06 PARSER  —  2001 & 2011
Ever Married & Currently Married Population by Age at Marriage,
Duration of Marriage and Educational Level
=============================================================================

SHARED FILE STRUCTURE (identical in both census years)
-------------------------------------------------------
HEADER BLOCK (Rows 1–7, 0-indexed rows 0–6): SKIP ALL
  Row 0  : Title string in col 6, rest None
  Row 1  : Top-level column group labels (merged cells)
  Row 2  : Sub-labels (Rural/Urban, Age at marriage, etc.)
  Row 3  : Further sub-labels (All durations, 0-4, 5-9, etc.)
  Row 4  : Males/Females headers for each duration bucket
  Row 5  : Column numbers 1–19 (Census numbering)
  Row 6  : Blank separator row

DATA STARTS at Row 7 (0-indexed) / Row 8 (1-indexed).

COLUMN MAP (0-indexed, identical in 2001 and 2011):
  Col 0  : Table code         [e.g. 'C0106' (2001) / 'C1706' (2011)]
  Col 1  : State code
  Col 2  : District code      ['000' = state level, other = district]
  Col 3  : Area name
  Col 4  : Area type          ['Total', 'Rural', 'Urban']
  Col 5  : Educational level
  Col 6  : Age at marriage    (Census Col 1)
  Col 7  : Ever Married Males                              (Census Col 2)
  Col 8  : Ever Married Females                            (Census Col 3)
  Col 9  : Currently Married Males  — All durations        (Census Col 4)
  Col 10 : Currently Married Females — All durations       (Census Col 5)
  Col 11 : Currently Married Males  — Duration  0–4 yrs   (Census Col 6)
  Col 12 : Currently Married Females — Duration 0–4 yrs   (Census Col 7)
  Col 13 : Currently Married Males  — Duration  5–9 yrs   (Census Col 8)
  Col 14 : Currently Married Females — Duration 5–9 yrs   (Census Col 9)
  Col 15 : Currently Married Males  — Duration 10–19 yrs  (Census Col 10)
  Col 16 : Currently Married Females — Duration 10–19 yrs (Census Col 11)
  Col 17 : Currently Married Males  — Duration 20–29 yrs  (Census Col 12)
  Col 18 : Currently Married Females — Duration 20–29 yrs (Census Col 13)
  Col 19 : Currently Married Males  — Duration 30–39 yrs  (Census Col 14)
  Col 20 : Currently Married Females — Duration 30–39 yrs (Census Col 15)
  Col 21 : Currently Married Males  — Duration 40+ yrs    (Census Col 16)
  Col 22 : Currently Married Females — Duration 40+ yrs   (Census Col 17)
  Col 23 : Currently Married Males  — Duration Not Known  (Census Col 18)
  Col 24 : Currently Married Females — Duration Not Known (Census Col 19)

YEAR-SPECIFIC DIFFERENCES
--------------------------
1. Education level strings
     2011 (raw): 'Literate but below primary '   ← lowercase 'p', trailing space
     2001 (raw): 'Literate but below Primary'    ← uppercase 'P', no trailing space
   Fix: normalise to lowercase + strip before any comparison or grouping.

2. Area name prefix
     2011: 'State - Andaman & Nicobar Islands'   ← title case
     2001: 'STATE - ANDAMAN & NICOBAR ISLANDS'   ← ALL CAPS (common in older files)
   Fix: case-insensitive regex strip of the prefix.

3. Table code in Col 0
     2011: 'C1706', 'C1706SC'   (year-code 17)
     2001: 'C0106', 'C0106SC'   (year-code 01)
   Informational only — not used in parsing logic.

PARSING FILTERS (apply ALL simultaneously):
   district_code == '000'        → state level only
   area_type     == 'Total'      → combined, not Rural/Urban split
   age_group     != 'Age Not stated'
=============================================================================
"""

import re
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# COLUMN DEFINITIONS
# ---------------------------------------------------------------------------

COLUMN_NAMES = [
    'table_name',                  # Col 0
    'state_code',                  # Col 1
    'district_code',               # Col 2
    'area_name',                   # Col 3
    'area_type',                   # Col 4
    'edu_level',                   # Col 5
    'age_group',                   # Col 6  (Census Col 1)
    'ever_married_m',              # Col 7  (Census Col 2)
    'ever_married_f',              # Col 8  (Census Col 3)
    'curr_married_m_all',          # Col 9  (Census Col 4)
    'curr_married_f_all',          # Col 10 (Census Col 5)
    'curr_married_m_0_4',          # Col 11 (Census Col 6)
    'curr_married_f_0_4',          # Col 12 (Census Col 7)
    'curr_married_m_5_9',          # Col 13 (Census Col 8)
    'curr_married_f_5_9',          # Col 14 (Census Col 9)
    'curr_married_m_10_19',        # Col 15 (Census Col 10)
    'curr_married_f_10_19',        # Col 16 (Census Col 11)
    'curr_married_m_20_29',        # Col 17 (Census Col 12)
    'curr_married_f_20_29',        # Col 18 (Census Col 13)
    'curr_married_m_30_39',        # Col 19 (Census Col 14)
    'curr_married_f_30_39',        # Col 20 (Census Col 15)
    'curr_married_m_40plus',       # Col 21 (Census Col 16)
    'curr_married_f_40plus',       # Col 22 (Census Col 17)
    'curr_married_m_dur_unknown',  # Col 23 (Census Col 18)
    'curr_married_f_dur_unknown',  # Col 24 (Census Col 19)
]

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

# Age groups that constitute child marriage (married before age 18)
CHILD_MARRIAGE_AGES = frozenset({'Less than 10', '10-11', '12-13', '14-15', '16-17'})

ALL_AGES_ROW  = 'All ages'
EXCLUDE_AGES  = frozenset({'Age Not stated'})

# Canonical education level labels (normalised: lowercase, no trailing spaces).
# Used for ordering and as the join key after normalisation.
EDU_LEVEL_ORDER = [
    'illiterate',
    'literate but below primary',
    'primary but below middle',
    'middle but below matric or secondary',
    'matric or secondary but below graduate',
    'graduate and above',
]

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _detect_engine(filepath: str) -> str:
    """
    Return 'openpyxl' for true XLSX (ZIP magic) or 'xlrd' for legacy XLS
    (OLE2 magic).  Census files are frequently named .XLSX but are XLS.
    Raises IOError for unrecognised formats.
    """
    with open(filepath, 'rb') as f:
        magic = f.read(4)
    if magic[:2] == b'PK':
        return 'openpyxl'
    elif magic[:4] == b'\xd0\xcf\x11\xe0':
        return 'xlrd'
    else:
        raise IOError(
            f"Unrecognised file format for {filepath}. "
            "Expected XLSX (PK magic) or XLS (OLE2 magic)."
        )


def _normalise_edu(raw: pd.Series) -> pd.Series:
    """
    Normalise education level strings to lowercase with stripped whitespace.

    Handles both:
      2011: 'Literate but below primary '   → 'literate but below primary'
      2001: 'Literate but below Primary'    → 'literate but below primary'
    """
    return raw.str.strip().str.lower()


def _extract_state_name(area_name: pd.Series) -> pd.Series:
    """
    Strip the 'State - ' / 'STATE - ' prefix from the area name column.

    2011 example: 'State - Andaman & Nicobar Islands' → 'Andaman & Nicobar Islands'
    2001 example: 'STATE - ANDAMAN & NICOBAR ISLANDS' → 'Andaman & Nicobar Islands'
    """
    return (
        area_name
        .str.replace(r'(?i)^state\s*-\s*', '', regex=True)
        .str.strip()
        .str.title()          # normalise ALL CAPS to title case for both years
    )


# ---------------------------------------------------------------------------
# CORE PARSER
# ---------------------------------------------------------------------------

def parse_c06(filepath: str, state_only: bool = True) -> pd.DataFrame:
    """
    Parse a Census C-06 Excel file into a clean long-format DataFrame.
    Supports both 2001 and 2011 census files (auto-detects format).

    Parameters
    ----------
    filepath   : Path to the .XLSX or .XLS file
    state_only : If True (default), returns only state-level Total rows
                 (district_code == '000', area_type == 'Total').

    Returns
    -------
    pd.DataFrame with all COLUMN_NAMES columns, plus:
      'state_name'  : cleaned, title-cased state name
      'edu_level'   : normalised (lowercase, stripped) — use for joins/grouping
      'edu_level_raw': original string from file — preserved for inspection
      'edu_order'   : integer rank (0=Illiterate … 5=Graduate and above),
                      NaN if the level is 'Total' or unrecognised

    Notes
    -----
    Both 2001 and 2011 C-06 files share the same 7-row header, 25-column
    layout, district-code convention, and age-group labels.
    The only year-specific differences (education string casing, area-name
    capitalisation) are handled transparently inside this function.
    """
    engine = _detect_engine(filepath)

    raw = pd.read_excel(
        filepath,
        engine=engine,
        header=None,
        skiprows=7,
        dtype=str,
    )

    raw = raw.dropna(how='all').reset_index(drop=True)

    # Pad or trim to exactly 25 columns
    for i in range(raw.shape[1], 25):
        raw[i] = None
    raw = raw.iloc[:, :25]
    raw.columns = COLUMN_NAMES

    df = raw.copy()

    # ── Clean identifiers ────────────────────────────────────────────────────
    df['district_code'] = df['district_code'].astype(str).str.strip()
    df['area_type']     = df['area_type'].str.strip()
    df['age_group']     = df['age_group'].astype(str).str.strip()

    # ── Education level: keep raw + add normalised column ───────────────────
    df['edu_level_raw'] = df['edu_level'].copy()
    df['edu_level']     = _normalise_edu(df['edu_level'])

    # ── State name (handles both title-case and ALL-CAPS prefixes) ───────────
    df['state_name'] = _extract_state_name(df['area_name'])

    # ── Numeric columns ──────────────────────────────────────────────────────
    numeric_cols = COLUMN_NAMES[7:]   # cols 7–24 are all counts
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # ── Geography / area type filter ─────────────────────────────────────────
    if state_only:
        df = df[
            (df['district_code'] == '000') &
            (df['area_type']     == 'Total')
        ].copy()

    # ── Drop ambiguous age rows ───────────────────────────────────────────────
    df = df[~df['age_group'].isin(EXCLUDE_AGES)].copy()

    # ── Education order (works on normalised strings) ─────────────────────────
    edu_order_map = {lvl: i for i, lvl in enumerate(EDU_LEVEL_ORDER)}
    df['edu_order'] = df['edu_level'].map(edu_order_map)  # NaN for 'total'

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# INDEX CALCULATOR  (unchanged logic — works on normalised edu_level)
# ---------------------------------------------------------------------------

def compute_c06_indexes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute CMPR and education-based indexes from a parsed C-06 DataFrame.
    Returns one row per education level with all indexes as columns.

    Input : output of parse_c06()
    Output: DataFrame sorted low→high education, columns listed below.

    Columns produced
    ----------------
    edu_level                   : normalised label
    edu_level_raw               : original label from the file
    edu_order                   : integer rank (0–5)
    CMPR_male                   : % of ever-married males married before 18
    CMPR_female                 : % of ever-married females married before 18
    CMPR_curr_married_male      : same but based on currently-married stock
    CMPR_curr_married_female    : same but based on currently-married stock
    sex_disparity               : CMPR_female / CMPR_male
    early_duration_share_male   : of child-married males, % in 0-4 yr duration
    early_duration_share_female : of child-married females, % in 0-4 yr duration
    cm_ever_married_m/f         : raw child-married counts
    total_ever_married_m/f      : total ever-married counts
    edu_protection_index_male   : 1 − (CMPR / illiterate CMPR)
    edu_protection_index_female : same for females
    """
    results = []

    # Exclude the 'Total' aggregate row — process named education levels only
    edu_levels = [e for e in df['edu_level'].unique() if e != 'total']

    for edu in edu_levels:
        edu_df = df[df['edu_level'] == edu]

        # Denominators from the 'All ages' aggregate row
        all_ages = edu_df[edu_df['age_group'] == ALL_AGES_ROW]
        if all_ages.empty:
            continue

        total_ever_m = all_ages['ever_married_m'].values[0]
        total_ever_f = all_ages['ever_married_f'].values[0]
        total_curr_m = all_ages['curr_married_m_all'].values[0]
        total_curr_f = all_ages['curr_married_f_all'].values[0]

        # Numerators: rows for age-at-marriage < 18
        cm_rows     = edu_df[edu_df['age_group'].isin(CHILD_MARRIAGE_AGES)]
        cm_ever_m   = cm_rows['ever_married_m'].sum()
        cm_ever_f   = cm_rows['ever_married_f'].sum()
        cm_curr_m   = cm_rows['curr_married_m_all'].sum()
        cm_curr_f   = cm_rows['curr_married_f_all'].sum()
        cm_dur_0_4_m = cm_rows['curr_married_m_0_4'].sum()
        cm_dur_0_4_f = cm_rows['curr_married_f_0_4'].sum()

        def safe_rate(num, den):
            return round(num / den * 100, 4) if den > 0 else None

        # Recover the raw label for readability in output
        raw_label = edu_df['edu_level_raw'].iloc[0] if 'edu_level_raw' in edu_df else edu

        results.append({
            'edu_level'                     : edu,
            'edu_level_raw'                 : raw_label,
            'edu_order'                     : edu_df['edu_order'].iloc[0],

            'CMPR_male'                     : safe_rate(cm_ever_m,   total_ever_m),
            'CMPR_female'                   : safe_rate(cm_ever_f,   total_ever_f),
            'CMPR_curr_married_male'        : safe_rate(cm_curr_m,   total_curr_m),
            'CMPR_curr_married_female'      : safe_rate(cm_curr_f,   total_curr_f),

            'sex_disparity'                 : (
                safe_rate(cm_ever_f, total_ever_f) / safe_rate(cm_ever_m, total_ever_m)
                if safe_rate(cm_ever_m, total_ever_m) else None
            ),

            'early_duration_share_male'     : safe_rate(cm_dur_0_4_m, cm_curr_m),
            'early_duration_share_female'   : safe_rate(cm_dur_0_4_f, cm_curr_f),

            'cm_ever_married_m'             : int(cm_ever_m),
            'cm_ever_married_f'             : int(cm_ever_f),
            'total_ever_married_m'          : int(total_ever_m),
            'total_ever_married_f'          : int(total_ever_f),
        })

    indexes_df = pd.DataFrame(results).sort_values('edu_order').reset_index(drop=True)

    # Education protection index: reduction relative to illiterate baseline
    illiterate_m = indexes_df.loc[
        indexes_df['edu_level'] == 'illiterate', 'CMPR_male'
    ].values
    illiterate_f = indexes_df.loc[
        indexes_df['edu_level'] == 'illiterate', 'CMPR_female'
    ].values

    if len(illiterate_m) > 0 and illiterate_m[0]:
        indexes_df['edu_protection_index_male'] = indexes_df['CMPR_male'].apply(
            lambda x: round(1 - (x / illiterate_m[0]), 4) if x is not None else None
        )
    if len(illiterate_f) > 0 and illiterate_f[0]:
        indexes_df['edu_protection_index_female'] = indexes_df['CMPR_female'].apply(
            lambda x: round(1 - (x / illiterate_f[0]), 4) if x is not None else None
        )

    return indexes_df


# ---------------------------------------------------------------------------
# GENERALISATION NOTE FOR OTHER DATASETS
# ---------------------------------------------------------------------------
"""
HOW TO ADAPT THIS PARSER FOR OTHER C-SERIES FILES:

The following structural properties are CONSISTENT across C-04, C-05, C-06,
C-07 in BOTH 2001 and 2011:
  - 7 header rows to skip
  - Col 0: Table code
  - Col 1: State code
  - Col 2: District code  → filter '000' for state level
  - Col 3: Area name      → strip 'State - ' / 'STATE - ' prefix
  - Col 4: Total/Rural/Urban → filter 'Total'
  - Cols 7–8: Males/Females ever married (Census Cols 2–3)
  - Cols 9–24: Duration buckets (Census Cols 4–19)

What CHANGES per dataset is Col 5 and Col 6:
  C-04 (General):   Col 5 = Age at marriage (no group-by variable)
  C-05 (Religion):  Col 5 = Religion, Col 6 = Age at marriage
  C-06 (Education): Col 5 = Educational level, Col 6 = Age at marriage  ← this file
  C-07 (Econ):      Col 5 = Economic activity, Col 6 = Age at marriage

For C-02 / C-02 SC / C-02 ST (marital status by age/sex):
  DIFFERENT structure — 22 columns, no duration buckets
  Col 5 = Age group
  Cols 7–9   = Total (Persons/Males/Females)
  Cols 10–12 = Never Married
  Cols 13–15 = Currently Married
  Cols 16–18 = Widowed
  Cols 19–21 = Separated
  → Requires a separate parser

For C-12 (school attendance by economic activity, ages 5–19):
  28 columns — wider than C-06
  → Requires a separate parser

YEAR COMPATIBILITY NOTES:
  Education level strings differ in case between 2001 and 2011.
  Always use df['edu_level'] (normalised) for comparisons and grouping,
  not df['edu_level_raw'].
  State names in 2001 files are often ALL CAPS — _extract_state_name()
  applies .str.title() to normalise both years to the same format.
"""


# ---------------------------------------------------------------------------
# USAGE EXAMPLE
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import sys

    # Pass a file path as argument, or edit the defaults below
    FILE_2011 = "census_downloads_2011/C-06/C-06_Andaman_and_Nicobar_Islands.XLSX"
    FILE_2001 = "census_downloads_2001/C-06/C-06_Andaman_and_Nicobar_Islands.xls"

    target = sys.argv[1] if len(sys.argv) > 1 else FILE_2011

    print(f"=== Parsing: {target} ===")
    df = parse_c06(target)
    print(f"Parsed {len(df)} state-level rows")
    print(f"Education levels (raw) : {df['edu_level_raw'].unique().tolist()}")
    print(f"Education levels (norm): {df['edu_level'].unique().tolist()}")
    print(f"Age groups             : {df['age_group'].unique().tolist()}")
    print(f"State name             : {df['state_name'].iloc[0]}")
    print()

    print("=== Computing Indexes ===")
    indexes = compute_c06_indexes(df)
    print(indexes[[
        'edu_level', 'CMPR_male', 'CMPR_female',
        'sex_disparity', 'edu_protection_index_female'
    ]].to_string(index=False))