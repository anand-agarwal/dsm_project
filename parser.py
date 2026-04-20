"""
=============================================================================
CENSUS C-06 PARSING STRATEGY
Ever Married & Currently Married Population by Age at Marriage,
Duration of Marriage and Educational Level
=============================================================================

FILE STRUCTURE FINDINGS (from C-06_Andaman_and_Nicobar_Islands.XLSX)
----------------------------------------------------------------------

HEADER BLOCK (Rows 1–7, 0-indexed rows 0–6): SKIP ALL OF THESE
  Row 0  : Title string in col 6, rest None
  Row 1  : Top-level column group labels (merged cells)
  Row 2  : Sub-labels (Rural/Urban, Age at marriage, etc.)
  Row 3  : Further sub-labels (All durations, 0-4, 5-9, etc.)
  Row 4  : Males/Females headers for each duration bucket
  Row 5  : Column numbers 1–19 (as per Census numbering)
  Row 6  : Blank separator row

DATA STARTS at Row 7 (0-indexed), Row 8 (1-indexed).

COLUMN MAP (0-indexed, matching Census col numbers in parentheses):
  Col 0  : Table Name / Code         [e.g. 'C1706']
  Col 1  : State Code                [e.g. '35']
  Col 2  : District Code             [e.g. '000' = state level, '638' = district]
  Col 3  : Area Name                 [e.g. 'State - ANDAMAN & NICOBAR ISLANDS']
  Col 4  : Total/Rural/Urban         [values: 'Total', 'Rural', 'Urban']
  Col 5  : Educational Level         [see EDUCATION LEVELS below]
  Col 6  : Age at Marriage           (Census Col 1) [see AGE GROUPS below]
  Col 7  : Ever Married Males        (Census Col 2)
  Col 8  : Ever Married Females      (Census Col 3)
  Col 9  : Currently Married Males  - All durations     (Census Col 4)
  Col 10 : Currently Married Females - All durations    (Census Col 5)
  Col 11 : Currently Married Males  - Duration 0-4 yrs  (Census Col 6)
  Col 12 : Currently Married Females - Duration 0-4 yrs (Census Col 7)
  Col 13 : Currently Married Males  - Duration 5-9 yrs  (Census Col 8)
  Col 14 : Currently Married Females - Duration 5-9 yrs (Census Col 9)
  Col 15 : Currently Married Males  - Duration 10-19 yrs (Census Col 10)
  Col 16 : Currently Married Females - Duration 10-19 yrs (Census Col 11)
  Col 17 : Currently Married Males  - Duration 20-29 yrs (Census Col 12)
  Col 18 : Currently Married Females - Duration 20-29 yrs (Census Col 13)
  Col 19 : Currently Married Males  - Duration 30-39 yrs (Census Col 14)
  Col 20 : Currently Married Females - Duration 30-39 yrs (Census Col 15)
  Col 21 : Currently Married Males  - Duration 40+ yrs   (Census Col 16)
  Col 22 : Currently Married Females - Duration 40+ yrs  (Census Col 17)
  Col 23 : Currently Married Males  - Duration Not Known  (Census Col 18)
  Col 24 : Currently Married Females - Duration Not Known (Census Col 19)

EDUCATION LEVELS (Col 5 values):
  'Total'
  'Illiterate'
  'Literate'
  'Literate but below primary '          ← NOTE: trailing space in raw data
  'Primary but below middle'
  'Middle but below matric or secondary'
  'Matric or secondary but below graduate'
  'Graduate and above'

AGE GROUPS (Col 6 values):
  'All ages'       ← AGGREGATE ROW — use as denominator
  'Less than 10'   ← child marriage cohort
  '10-11'          ← child marriage cohort
  '12-13'          ← child marriage cohort
  '14-15'          ← child marriage cohort
  '16-17'          ← child marriage cohort
  '18-19'          ← adult (but partially overlaps child marriage threshold)
  '20-21', '22-23', '24-25', '26-27', '28-29', '30-31', '32-33', '34+'
  'Age Not stated' ← EXCLUDE from CMPR calculations

CHILD MARRIAGE AGE COHORTS (age at marriage < 18):
  Use: 'Less than 10', '10-11', '12-13', '14-15', '16-17'
  Exclude '18-19' (straddles the 18-year threshold)
  Exclude 'All ages' and 'Age Not stated'

DATA GEOGRAPHY STRUCTURE:
  District Code '000' → State-level aggregate  ← YOU ONLY WANT THIS
  District Code '638', '639', '640', etc. → Individual districts (skip)

  For each geography unit, data appears in 3 blocks:
    Total / Rural / Urban  (Col 4 = 'Total', 'Rural', 'Urban')
  
  You only need: Col 2 == '000' AND Col 4 == 'Total'

TOTAL ROWS IN FILE: 1418
STATE-LEVEL TOTAL ROWS: 128 (rows 8–135 in 1-indexed)
  = 8 education levels × 16 age groups each

=============================================================================
PARSING FILTERS (apply ALL three simultaneously):
  1. Col 2 == '000'       → state level only, not district
  2. Col 4 == 'Total'     → combined Total, not Rural/Urban split
  3. Col 6 != 'Age Not stated'  → exclude ambiguous age rows
=============================================================================
"""

import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# COLUMN DEFINITIONS
# ---------------------------------------------------------------------------

COLUMN_NAMES = [
    'table_name',       # Col 0
    'state_code',       # Col 1
    'district_code',    # Col 2
    'area_name',        # Col 3
    'area_type',        # Col 4: Total / Rural / Urban
    'edu_level',        # Col 5
    'age_group',        # Col 6 (Census Col 1)
    'ever_married_m',   # Col 7 (Census Col 2)
    'ever_married_f',   # Col 8 (Census Col 3)
    'curr_married_m_all',     # Col 9  (Census Col 4)
    'curr_married_f_all',     # Col 10 (Census Col 5)
    'curr_married_m_0_4',     # Col 11 (Census Col 6)
    'curr_married_f_0_4',     # Col 12 (Census Col 7)
    'curr_married_m_5_9',     # Col 13 (Census Col 8)
    'curr_married_f_5_9',     # Col 14 (Census Col 9)
    'curr_married_m_10_19',   # Col 15 (Census Col 10)
    'curr_married_f_10_19',   # Col 16 (Census Col 11)
    'curr_married_m_20_29',   # Col 17 (Census Col 12)
    'curr_married_f_20_29',   # Col 18 (Census Col 13)
    'curr_married_m_30_39',   # Col 19 (Census Col 14)
    'curr_married_f_30_39',   # Col 20 (Census Col 15)
    'curr_married_m_40plus',  # Col 21 (Census Col 16)
    'curr_married_f_40plus',  # Col 22 (Census Col 17)
    'curr_married_m_dur_unknown',  # Col 23 (Census Col 18)
    'curr_married_f_dur_unknown',  # Col 24 (Census Col 19)
]

# Age groups that constitute child marriage (married before age 18)
CHILD_MARRIAGE_AGES = {'Less than 10', '10-11', '12-13', '14-15', '16-17'}

# Age group used as the total denominator
ALL_AGES_ROW = 'All ages'

# Age group to always exclude
EXCLUDE_AGES = {'Age Not stated'}

# Education level ordering for gradient analysis (low → high)
EDU_LEVEL_ORDER = [
    'Illiterate',
    'Literate but below primary',           # stripped trailing space
    'Primary but below middle',
    'Middle but below matric or secondary',
    'Matric or secondary but below graduate',
    'Graduate and above',
]


# ---------------------------------------------------------------------------
# CORE PARSER
# ---------------------------------------------------------------------------

def _detect_engine(filepath: str) -> str:
    """
    Detect whether a file is a true XLSX (ZIP-based) or a legacy XLS binary.
    Census of India files are frequently named .XLSX but are actually .xls format.

    Returns 'openpyxl' for true XLSX, 'xlrd' for legacy XLS.
    Raises IOError if neither format is recognised.
    """
    with open(filepath, 'rb') as f:
        magic = f.read(4)

    if magic[:2] == b'PK':          # ZIP magic → true XLSX/XLSM
        return 'openpyxl'
    elif magic[:4] == b'\xd0\xcf\x11\xe0':  # OLE2 magic → legacy XLS
        return 'xlrd'
    else:
        raise IOError(
            f"Unrecognised file format for {filepath}. "
            "Expected XLSX (PK magic) or XLS (OLE2 magic). "
            "Try opening and re-saving the file in Excel or LibreOffice."
        )


def parse_c06(filepath: str, state_only: bool = True) -> pd.DataFrame:
    """
    Parse a Census C-06 Excel file into a clean long-format DataFrame.

    Parameters
    ----------
    filepath   : Path to the .XLSX or .XLS file (auto-detected)
    state_only : If True (default), returns only state-level Total rows
                 (District Code == '000', Area Type == 'Total').
                 Set to False to get all geographies and area types.

    Returns
    -------
    pd.DataFrame with columns as defined in COLUMN_NAMES, plus:
        - 'state_name' : cleaned state name (Area Name with 'State - ' stripped)
        - 'edu_level'  : trailing whitespace stripped

    Notes
    -----
    Census of India bulk downloads often ship .XLS files renamed as .XLSX.
    This function detects the true format from magic bytes and picks the
    correct engine automatically — no manual intervention needed.
    If you see "BadZipFile" or "xlrd" errors, this function handles it.
    """
    engine = _detect_engine(filepath)

    # Read raw — no header parsing, we handle headers manually
    raw = pd.read_excel(
        filepath,
        engine=engine,
        header=None,       # don't let pandas guess headers (they span 7 rows)
        skiprows=7,        # skip the 7 census header rows
        dtype=str,         # read everything as string first; cast numerics later
    )

    # Drop fully empty rows
    raw = raw.dropna(how='all').reset_index(drop=True)

    # Pad or trim to exactly 25 columns
    if raw.shape[1] < 25:
        for i in range(raw.shape[1], 25):
            raw[i] = None
    raw = raw.iloc[:, :25]

    raw.columns = COLUMN_NAMES
    df = raw.copy()

    # --- Clean up ---
    df['edu_level'] = df['edu_level'].str.strip()
    df['age_group'] = df['age_group'].astype(str).str.strip()
    df['area_type'] = df['area_type'].str.strip()
    df['district_code'] = df['district_code'].astype(str).str.strip()

    # Extract clean state name
    df['state_name'] = (
        df['area_name']
        .str.replace(r'^State\s*-\s*', '', regex=True)
        .str.strip()
    )

    # Convert numeric columns
    numeric_cols = COLUMN_NAMES[7:]  # cols 7–24 are all counts
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # --- Filter to state level only if requested ---
    if state_only:
        df = df[
            (df['district_code'] == '000') &
            (df['area_type'] == 'Total')
        ].copy()

    # --- Drop 'Age Not stated' rows ---
    df = df[~df['age_group'].isin(EXCLUDE_AGES)].copy()

    # Add education level ordering
    edu_order_map = {lvl: i for i, lvl in enumerate(EDU_LEVEL_ORDER)}
    df['edu_order'] = df['edu_level'].map(edu_order_map)

    df = df.reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# INDEX CALCULATOR
# ---------------------------------------------------------------------------

def compute_c06_indexes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all CMPR and education-based indexes from a parsed C-06 DataFrame.
    Returns one row per education level with all indexes as columns.

    Input: output of parse_c06()
    """
    results = []

    edu_levels = [e for e in df['edu_level'].unique() if e != 'Total']

    for edu in edu_levels:
        edu_df = df[df['edu_level'] == edu]

        # --- Denominators: 'All ages' row ---
        all_ages = edu_df[edu_df['age_group'] == ALL_AGES_ROW]
        if all_ages.empty:
            continue
        total_ever_m = all_ages['ever_married_m'].values[0]
        total_ever_f = all_ages['ever_married_f'].values[0]
        total_curr_m = all_ages['curr_married_m_all'].values[0]
        total_curr_f = all_ages['curr_married_f_all'].values[0]

        # --- Numerators: child marriage age rows ---
        cm_rows = edu_df[edu_df['age_group'].isin(CHILD_MARRIAGE_AGES)]
        cm_ever_m = cm_rows['ever_married_m'].sum()
        cm_ever_f = cm_rows['ever_married_f'].sum()
        cm_curr_m = cm_rows['curr_married_m_all'].sum()
        cm_curr_f = cm_rows['curr_married_f_all'].sum()
        cm_dur_0_4_m = cm_rows['curr_married_m_0_4'].sum()
        cm_dur_0_4_f = cm_rows['curr_married_f_0_4'].sum()

        def safe_rate(num, den):
            return round((num / den * 100), 4) if den > 0 else None

        row = {
            'edu_level'                     : edu,
            'edu_order'                     : edu_df['edu_order'].iloc[0],

            # Core CMPR — based on ever married (age at marriage)
            'CMPR_male'                     : safe_rate(cm_ever_m, total_ever_m),
            'CMPR_female'                   : safe_rate(cm_ever_f, total_ever_f),

            # CMPR based on currently married (stock measure)
            'CMPR_curr_married_male'        : safe_rate(cm_curr_m, total_curr_m),
            'CMPR_curr_married_female'      : safe_rate(cm_curr_f, total_curr_f),

            # Sex disparity within education level
            'sex_disparity'                 : (
                safe_rate(cm_ever_f, total_ever_f) / safe_rate(cm_ever_m, total_ever_m)
                if safe_rate(cm_ever_m, total_ever_m) else None
            ),

            # Early duration share: currently married <18 who married 0-4 yrs ago
            'early_duration_share_male'     : safe_rate(cm_dur_0_4_m, cm_curr_m),
            'early_duration_share_female'   : safe_rate(cm_dur_0_4_f, cm_curr_f),

            # Raw counts for reference
            'cm_ever_married_m'             : cm_ever_m,
            'cm_ever_married_f'             : cm_ever_f,
            'total_ever_married_m'          : total_ever_m,
            'total_ever_married_f'          : total_ever_f,
        }
        results.append(row)

    indexes_df = pd.DataFrame(results).sort_values('edu_order').reset_index(drop=True)

    # --- Education protection index: relative reduction from illiterate baseline ---
    illiterate_m = indexes_df.loc[
        indexes_df['edu_level'] == 'Illiterate', 'CMPR_male'
    ].values
    illiterate_f = indexes_df.loc[
        indexes_df['edu_level'] == 'Illiterate', 'CMPR_female'
    ].values

    if len(illiterate_m) > 0 and illiterate_m[0]:
        indexes_df['edu_protection_index_male'] = indexes_df['CMPR_male'].apply(
            lambda x: round(1 - (x / illiterate_m[0]), 4) if x else None
        )
    if len(illiterate_f) > 0 and illiterate_f[0]:
        indexes_df['edu_protection_index_female'] = indexes_df['CMPR_female'].apply(
            lambda x: round(1 - (x / illiterate_f[0]), 4) if x else None
        )

    return indexes_df


# ---------------------------------------------------------------------------
# GENERALISATION NOTE FOR OTHER DATASETS
# ---------------------------------------------------------------------------
"""
HOW TO ADAPT THIS PARSER FOR OTHER C-SERIES FILES:

The following structural properties are CONSISTENT across C-04, C-05, C-06, C-07:
  - 7 header rows to skip (min_row=8 in openpyxl)
  - Col 0: Table Name
  - Col 1: State Code
  - Col 2: District Code  → filter '000' for state level
  - Col 3: Area Name
  - Col 4: Total/Rural/Urban → filter 'Total'
  - Cols 7–8: Males/Females ever married (Census Cols 2–3)
  - Cols 9–24: Duration buckets (Census Cols 4–19)

What CHANGES per dataset is Col 5 and Col 6:
  C-04 (General):   Col 5 = Age at marriage (no group-by variable)
  C-05 (Religion):  Col 5 = Religion, Col 6 = Age at marriage
  C-06 (Education): Col 5 = Educational level, Col 6 = Age at marriage  ← THIS FILE
  C-07 (Econ):      Col 5 = Economic activity, Col 6 = Age at marriage

For C-02 SC/ST (Marital status by age/sex):
  DIFFERENT structure — 22 columns, no duration buckets
  Col 5 = Age group
  Cols 7–9   = Total (Persons/Males/Females)
  Cols 10–12 = Never Married
  Cols 13–15 = Currently Married
  Cols 16–18 = Widowed
  Cols 19–21 = Separated
  Cols 22–24 = Divorced  [adjust if fewer cols present]
  → You will need a separate parser for C-02 family

For C-12 SC/ST (School attendance by economic activity):
  28 columns total — wider than C-06
  Col 5 = Age group (5-19 only)
  Cols 7–9   = Total attending (Main Workers)
  Cols 10–12 = Attending (Marginal 3-6 months)
  Cols 13–15 = Attending (Marginal <3 months)
  Cols 16–18 = Attending (Non-workers)
  Cols 19–21 = Not attending (Main Workers)
  Cols 22–24 = Not attending (Marginal 3-6 months)
  Cols 25–27 = Not attending (Marginal <3 months)
  Cols 28–30 = Not attending (Non-workers)
  → You will need a separate parser for C-12 family

RECOMMENDED APPROACH:
  Build one base parser that handles the shared 7-row header skip and
  geography filter (Distt == '000', T/R/U == 'Total'), then subclass
  or pass a column_map dict for each dataset family.
"""


# ---------------------------------------------------------------------------
# USAGE EXAMPLE
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    FILE = "/Users/anandagarwal/dsm_project/census_downloads_2011/C-06/C-06_Andaman_and_Nicobar_Islands.XLSX"

    print("=== Parsing C-06 ===")
    df = parse_c06(FILE)
    print(f"Parsed {len(df)} state-level rows")
    print(f"Education levels: {df['edu_level'].unique().tolist()}")
    print(f"Age groups: {df['age_group'].unique().tolist()}")
    print()

    print("=== Computing Indexes ===")
    indexes = compute_c06_indexes(df)
    print(indexes[[
        'edu_level', 'CMPR_male', 'CMPR_female',
        'sex_disparity', 'edu_protection_index_female'
    ]].to_string(index=False))