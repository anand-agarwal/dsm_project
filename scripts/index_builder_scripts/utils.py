"""
=============================================================================
utils.py  —  Shared constants, configuration, and helper functions
             for the Census 2011 Child Marriage Index Builder
=============================================================================
Import this module in every build_*.py script.
=============================================================================
"""

import os
import glob
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# CONFIGURATION  (edit here; all build scripts inherit these values)
# ---------------------------------------------------------------------------
DATA_ROOT  = "/Users/anandagarwal/dsm_project/census_2001_sorted"
OUTPUT_DIR = "/Users/anandagarwal/dsm_project/output_datasets_2001"

# ---------------------------------------------------------------------------
# FOLDER MAP
# ---------------------------------------------------------------------------
FOLDER = {
    'C-02-SC' : 'C-02_(SC)',
    'C-02-ST' : 'C-02_(ST)',
    'C-04'    : 'C-04',
    'C-05'    : 'C-05',
    'C-06'    : 'C-06',
    'C-07'    : 'C-07',
    'C-08-SC' : 'C-08_(SC)',
    'C-08-ST' : 'C-08_(ST)',
    'C-09'    : 'C-09',
    'C-12-SC' : 'C-12_(SC)',
    'C-12-ST' : 'C-12_(ST)',
}

# ---------------------------------------------------------------------------
# AGE BRACKET DEFINITIONS
# ---------------------------------------------------------------------------
# Four canonical brackets used across all datasets.
# See NOTE blocks below for known boundary limitations per dataset.
AGE_BRACKETS = ['age_below10', 'age_10_13', 'age_14_17', 'age_18_21']

# ---------------------------------------------------------------------------
# C-02 / C-02-SC / C-02-ST  — CURRENT population age (5-year bands)
# ---------------------------------------------------------------------------
# NOTE: C-02 uses 5-year bands so boundaries only approximate our 4-year
#       canonical brackets.  Specifically:
#         • '10-14' maps to age_10_13  → includes one extra year (14)
#         • '15-19' maps to age_14_17  → misses one year (14) captured above
#         • '20-24' maps to age_18_21  → includes three extra years (22-24)
#       This mismatch is structural and unavoidable.  Downstream scripts
#       should note C-02 figures as "approximate" for these brackets.
#
# Additional aggregate labels present in C-02:
#   'Less than 18'  — useful as a direct child-marriage numerator proxy
#   'Less than 21'  — useful as a young-marriage numerator proxy
#   'All ages'      — population total denominator
#   'Age not stated'— excluded from bracket sums (see EXCLUDE_AGES)
AGE_BRACKET_C02 = {
    'age_below10' : {'0-9'},
    'age_10_13'   : {'10-14'},          # ~approximate: includes age 14
    'age_14_17'   : {'15-19'},          # ~approximate: misses age 14
    'age_18_21'   : {'20-24'},          # ~approximate: includes ages 22-24
}

# Convenience sets for the aggregate labels in C-02
C02_AGGREGATE_LABELS = {
    'lt18'     : {'less than 18'},
    'lt21'     : {'less than 21'},
    'all_ages' : {'all ages'},
}

# Full individual age-group labels present in C-02 (for reference / validation)
# 0-9, 10-14, 15-19, 20-24, 25-29, 30-34, 35-39, 40-44, 45-49, 50-54,
# 55-59, 60-64, 65-69, 70-74, 75-79, 80+, Age not stated,
# Less than 18, Less than 21

# ---------------------------------------------------------------------------
# C-03  — No age column. No bracket mapping required.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# C-04  — AGE AT MARRIAGE (2-year bands, complete coverage to 34+)
# ---------------------------------------------------------------------------
# All canonical brackets map cleanly to 2-year sub-bands.
# 'Not stated' is treated the same as 'Age not stated' (excluded).
# Labels present: All ages, Less than 10, 10-11, 12-13, 14-15, 16-17,
#   18-19, 20-21, 22-23, 24-25, 26-27, 28-29, 30-31, 32-33, 34+, Not stated
AGE_BRACKET_MARRIAGE_C04 = {
    'age_below10' : {'less than 10'},
    'age_10_13'   : {'10-11', '12-13'},
    'age_14_17'   : {'14-15', '16-17'},
    'age_18_21'   : {'18-19', '20-21'}
}

# ---------------------------------------------------------------------------
# C-05  — AGE AT MARRIAGE (2-year bands, same structure as C-04)
# ---------------------------------------------------------------------------
# No 'Not stated' row in C-05 (unlike C-04).
# Labels present: All ages, Less than 10, 10-11, 12-13, 14-15, 16-17,
#   18-19, 20-21, 22-23, 24-25, 26-27, 28-29, 30-31, 32-33, 34+
AGE_BRACKET_MARRIAGE_C05 = {
    'age_below10' : {'less than 10'},
    'age_10_13'   : {'10-11', '12-13'},
    'age_14_17'   : {'14-15', '16-17'},
    'age_18_21'   : {'18-19', '20-21'},

}

# ---------------------------------------------------------------------------
# C-06  — AGE AT MARRIAGE × EDUCATION LEVEL (same age bands as C-05)
# ---------------------------------------------------------------------------
# Has 'Age Not stated' row (note different capitalisation from C-04's
# 'Not stated' — normalise to lowercase before matching).
# Labels present: All ages, Less than 10, 10-11, 12-13, 14-15, 16-17,
#   18-19, 20-21, 22-23, 24-25, 26-27, 28-29, 30-31, 32-33, 34+,
#   Age Not stated
AGE_BRACKET_MARRIAGE_C06 = {
    'age_below10' : {'less than 10'},
    'age_10_13'   : {'10-11', '12-13'},
    'age_14_17'   : {'14-15', '16-17'},
    'age_18_21'   : {'18-19', '20-21'},
}

# ---------------------------------------------------------------------------
# C-07  — AGE AT MARRIAGE × ECONOMIC ACTIVITY (same age bands as C-05)
# ---------------------------------------------------------------------------
# No 'Not stated' row. 34+ (not '34 +' with space — normalise when matching).
# Labels present: All ages, Less than 10, 10-11, 12-13, 14-15, 16-17,
#   18-19, 20-21, 22-23, 24-25, 26-27, 28-29, 30-31, 32-33, 34+
AGE_BRACKET_MARRIAGE_C07 = {
    'age_below10' : {'less than 10'},
    'age_10_13'   : {'10-11', '12-13'},
    'age_14_17'   : {'14-15', '16-17'},
    'age_18_21'   : {'18-19', '20-21'},
}

# Convenience alias: single dict used by build scripts that process
# C-04/05/06/07 identically for the four core brackets.
AGE_BRACKET_MARRIAGE = {
    'age_below10' : {'less than 10'},
    'age_10_13'   : {'10-11', '12-13'},
    'age_14_17'   : {'14-15', '16-17'},
    'age_18_21'   : {'18-19', '20-21'},
}

# ---------------------------------------------------------------------------
# C-08 / C-08-SC / C-08-ST  — CURRENT population age (individual years 7–19,
#                               then 5-year bands from 20 onward)
# ---------------------------------------------------------------------------
# Individual-year rows must be SUMMED to build brackets.
# NOTE for age_18_21: C-08 provides age 18 and age 19 individually, then
#   jumps to '20-24'.  Ages 20 and 21 cannot be separated from 22-24.
#   The age_18_21 bracket here captures 18 + 19 only; the build script
#   must document that 20-21 are unavailable for C-08.
#
# Labels present: All ages, 0-6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
#   18, 19, 20-24, 25-29, 30-34, 35-39, 40-44, 45-49, 50-54, 55-59, 60-64,
#   65-69, 70-74, 75-79, 80+, Age not stated
AGE_BRACKET_C08 = {
    'age_below10' : {'0-6', '7', '8', '9'},
    'age_10_13'   : {'10', '11', '12', '13'},
    'age_14_17'   : {'14', '15', '16', '17'},
    'age_18_21'   : {'18', '19'},           # NOTE: 20-21 not separable; partial
}

# ---------------------------------------------------------------------------
# C-09  — CURRENT population age × RELIGION (individual years 7–19,
#          then grouped bands; slightly different upper grouping from C-08)
# ---------------------------------------------------------------------------
# NOTE for age_18_21: same limitation as C-08 — 20-24 cannot be split.
#   Additionally C-09 collapses 35–59 into one band and 60+ into one band,
#   making those ranges unusable for our brackets (not relevant for <22).
#
# Labels present: Total, 0-6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
#   18, 19, 20-24, 25-29, 30-34, 35-59, 60+
# ('Total' plays the role of 'All ages' in this dataset)
AGE_BRACKET_C09 = {
    'age_below10' : {'0-6', '7', '8', '9'},
    'age_10_13'   : {'10', '11', '12', '13'},
    'age_14_17'   : {'14', '15', '16', '17'},
    'age_18_21'   : {'18', '19'},           # NOTE: 20-21 not separable; partial
}

# ---------------------------------------------------------------------------
# C-12 / C-12-SC / C-12-ST  — School ENROLMENT (ages 5–19 only)
# ---------------------------------------------------------------------------
# C-12 covers ages 5–19 as individual single years, plus an aggregate
# '5-19' row.  The dataset does NOT extend beyond age 19, so age_18_21
# is only partially covered (18 and 19 are present; 20-21 are absent).
# There is no 'Age not stated' row.
#
# NOTE for age_below10: C-12 starts at age 5, not 0.  Ages 0-4 are absent.
#   The bracket captures only 5, 6, 7, 8, 9.
#
# Labels present: 5-19 (aggregate), 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
#   15, 16, 17, 18, 19
AGE_BRACKET_C12 = {
    'age_below10' : {'5', '6', '7', '8', '9'},   # NOTE: ages 0-4 absent
    'age_10_13'   : {'10', '11', '12', '13'},
    'age_14_17'   : {'14', '15', '16', '17'},
    'age_18_21'   : {'18', '19'},                  # NOTE: 20-21 absent; partial
}

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
ALL_AGES_LABEL  = 'All ages'
ALL_AGES_C09    = 'Total'          # C-09 uses 'Total' instead of 'All ages'
EXCLUDE_AGES    = {'Age Not stated', 'Age not stated', 'Not stated',
                   'age not stated', 'not stated'}

# Education level aliases used by C-06 normalisation
EDU_LEVEL_ALIASES = {
    'Literate but below primary '         : 'Literate but below primary',
    'Below Primary'                       : 'Literate but below primary',
    'Primary'                             : 'Primary but below middle',
    'Middle'                              : 'Middle but below matric or secondary',
    'Matric/Secondary'                    : 'Matric or secondary but below graduate',
    'Matric or Secondary'                 : 'Matric or secondary but below graduate',
    'Graduate & above'                    : 'Graduate and above',
    'Graduate and Above'                  : 'Graduate and above',
}

# Full education level name → short key used in column names
EDU_SHORT = {
    'Illiterate'                             : 'illiterate',
    'Literate but below primary'             : 'below_primary',
    'Primary but below middle'               : 'primary',
    'Middle but below matric or secondary'   : 'middle',
    'Matric or secondary but below graduate' : 'matric',
}

# Economic activity keywords for C-07 matching
ECON_KW = {
    'main_workers'       : 'total main workers',
    'cultivators'        : 'cultivator',
    'agri_labourers'     : 'agricultural labour',
    'household_industry' : 'household industry',
    'other_workers'      : 'other workers',
    'non_workers'        : 'non worker',
}

# Religion constants for C-05 / C-09
SKIP_RELIGIONS   = {'All religious communities', 'nan', '', 'Total'}
SKIP_REL_C09     = {'Total', 'All religious communities', 'nan', ''}
TARGET_RELIGIONS = ['hindu', 'muslim', 'christian', 'sikh', 'buddhist', 'jain']

# Columns that identify a row uniquely in the long-format output
GEO_KEYS = ['state_code', 'state_name', 'age_bracket']

# ---------------------------------------------------------------------------
# BRACKET MAP REGISTRY
# ---------------------------------------------------------------------------
# Centralised lookup: pass a dataset key → get the right bracket dict.
# Build scripts can call: bracket_map = BRACKET_MAP_FOR[dataset_key]
BRACKET_MAP_FOR = {
    'C-02'    : AGE_BRACKET_C02,
    'C-02-SC' : AGE_BRACKET_C02,
    'C-02-ST' : AGE_BRACKET_C02,
    'C-04'    : AGE_BRACKET_MARRIAGE_C04,
    'C-05'    : AGE_BRACKET_MARRIAGE_C05,
    'C-06'    : AGE_BRACKET_MARRIAGE_C06,
    'C-07'    : AGE_BRACKET_MARRIAGE_C07,
    'C-08'    : AGE_BRACKET_C08,
    'C-08-SC' : AGE_BRACKET_C08,
    'C-08-ST' : AGE_BRACKET_C08,
    'C-09'    : AGE_BRACKET_C09,
    'C-12'    : AGE_BRACKET_C12,
    'C-12-SC' : AGE_BRACKET_C12,
    'C-12-ST' : AGE_BRACKET_C12,
}

# Which datasets have partial age_18_21 coverage (20-21 not separable)
PARTIAL_18_21 = {'C-08', 'C-08-SC', 'C-08-ST', 'C-09', 'C-12', 'C-12-SC', 'C-12-ST'}

# Which datasets use approximate 5-year bands for core brackets
APPROXIMATE_BRACKETS = {'C-02', 'C-02-SC', 'C-02-ST'}


# ---------------------------------------------------------------------------
# FILE I/O UTILITIES
# ---------------------------------------------------------------------------

def _detect_engine(filepath: str) -> str:
    """Detect whether the Excel file is .xlsx (openpyxl) or .xls (xlrd)."""
    with open(filepath, 'rb') as f:
        magic = f.read(4)
    if magic[:2] == b'PK':
        return 'openpyxl'
    elif magic[:4] == b'\xd0\xcf\x11\xe0':
        return 'xlrd'
    raise IOError(f"Unrecognised file format: {filepath}")


def _read_excel(filepath: str, skiprows: int = 7) -> pd.DataFrame:
    """Read a Census Excel file, skipping the standard 7-row header block."""
    engine = _detect_engine(filepath)
    raw = pd.read_excel(filepath, engine=engine, header=None,
                        skiprows=skiprows, dtype=str)
    return raw.dropna(how='all').reset_index(drop=True)


def _glob_files(dataset_key: str) -> list:
    """Return sorted list of Excel files for a given dataset key."""
    folder = FOLDER[dataset_key]
    base   = os.path.join(DATA_ROOT, folder)
    exts   = ['*.XLSX', '*.xlsx', '*.XLS', '*.xls']
    files  = []
    for ext in exts:
        files += glob.glob(os.path.join(base, ext))
    if not files:                                       # try recursive search
        for ext in exts:
            files += glob.glob(os.path.join(base, '**', ext), recursive=True)
    if not files:
        print(f"  [WARN] No files found in: {base}")
    return sorted(set(files))


# ---------------------------------------------------------------------------
# NUMERIC / RATIO HELPERS
# ---------------------------------------------------------------------------

def safe_div(num, den, scale: float = 100) -> float:
    """Return num/den * scale, rounded to 4 dp. Returns np.nan on error/zero."""
    try:
        n, d = float(num), float(den)
        if d != 0 and not np.isnan(d):
            return round(n / d * scale, 4)
    except (TypeError, ValueError):
        pass
    return np.nan


def _pad_df(raw: pd.DataFrame, n: int) -> pd.DataFrame:
    """Ensure DataFrame has exactly n columns (pad with NaN or truncate)."""
    while raw.shape[1] < n:
        raw[raw.shape[1]] = np.nan
    return raw.iloc[:, :n].copy()


# ---------------------------------------------------------------------------
# CANONICAL STATE / UT NAME TABLE  (Census 2011)
# ---------------------------------------------------------------------------
# This is the single source of truth for state names across all datasets.
# Every raw name that comes out of any Census Excel file gets mapped here.

CANONICAL_STATES = [
    # 28 States
    'Andhra Pradesh',
    'Arunachal Pradesh',
    'Assam',
    'Bihar',
    'Chhattisgarh',
    'Goa',
    'Gujarat',
    'Haryana',
    'Himachal Pradesh',
    'Jammu & Kashmir',
    'Jharkhand',
    'Karnataka',
    'Kerala',
    'Madhya Pradesh',
    'Maharashtra',
    'Manipur',
    'Meghalaya',
    'Mizoram',
    'Nagaland',
    'Odisha',
    'Punjab',
    'Rajasthan',
    'Sikkim',
    'Tamil Nadu',
    'Tripura',
    'Uttar Pradesh',
    'Uttarakhand',
    'West Bengal',
    # 7 Union Territories
    'Andaman & Nicobar Islands',
    'Chandigarh',
    'Dadra & Nagar Haveli',
    'Daman & Diu',
    'Lakshadweep',
    'NCT of Delhi',
    'Puducherry',
]

# Pre-computed lowercase versions for fast matching
_CANONICAL_LOWER = [c.lower() for c in CANONICAL_STATES]

# Additional aliases that the raw Census data uses but don't substring-match
# naturally.  Maps lowercase raw token → canonical name.
_ALIAS_MAP: dict[str, str] = {
    # Odisha was officially renamed from Orissa in 2011; some files still use it
    'orissa'                      : 'Odisha',
    # "NCT of Delhi" often appears as just "Delhi" or "Delhi (Nct)"
    'delhi'                       : 'NCT of Delhi',
    'nct of delhi'                : 'NCT of Delhi',
    'delhi (nct)'                 : 'NCT of Delhi',
    # Pondicherry → Puducherry
    'pondicherry'                 : 'Puducherry',
    # Andaman variations
    'andaman and nicobar islands' : 'Andaman & Nicobar Islands',
    'andaman & nicobar'           : 'Andaman & Nicobar Islands',
    'andaman and nicobar'         : 'Andaman & Nicobar Islands',
    # Dadra & Nagar Haveli
    'dadra and nagar haveli'      : 'Dadra & Nagar Haveli',
    # Daman & Diu
    'daman and diu'               : 'Daman & Diu',
    # Jammu variations
    'jammu and kashmir'           : 'Jammu & Kashmir',
    'jammu & kashmir'             : 'Jammu & Kashmir',
    # Uttarakhand / Uttaranchal (old name still found in some files)
    'uttaranchal'                 : 'Uttarakhand',
    # Chhattisgarh spelling variants
    'chattisgarh'                 : 'Chhattisgarh',
    'chhatisgarh'                 : 'Chhattisgarh',
}


def _normalise_raw(s: str) -> str:
    """
    Strip Census boilerplate from a raw area_name string and return a
    cleaned, lowercased token suitable for matching.

    Removes:
      - leading/trailing whitespace
      - prefixes:  'State - ', 'State- ', 'State-'
      - trailing numeric codes in parentheses, e.g. '(01)', '(29)'
      - the word 'state' itself if it appears standalone
    """
    import re
    s = str(s).strip()
    # Remove "State - " / "State- " prefixes (case-insensitive)
    s = re.sub(r'(?i)^state\s*[-–]\s*', '', s).strip()
    # Remove trailing parenthetical codes like "(01)" or "(India)"
    s = re.sub(r'\s*\(\s*\d+\s*\)\s*$', '', s).strip()
    # Remove trailing parenthetical words that aren't part of the name
    # e.g. "Andaman & Nicobar Islands (UT)" — keep "Islands"
    s = re.sub(r'\s*\(\s*ut\s*\)\s*$', '', s, flags=re.IGNORECASE).strip()
    return s.lower()


def resolve_state_name(raw: str) -> str:
    """
    Map any raw Census area_name to the canonical state/UT name.

    Resolution order
    ----------------
    1. Direct alias match  (fastest; catches known spelling variants)
    2. Exact lowercase match against canonical list
    3. Canonical name is a substring of the raw token
       e.g. 'jammu & kashmir' in 'state - jammu & kashmir (01)'  ✓
    4. Raw token is a substring of the canonical name
       e.g. 'maharashtra' in 'Maharashtra'  ✓  (handles truncated names)
    5. Fall back: return the cleaned raw string with original casing
       and emit a warning so the caller knows it was unresolved.

    Parameters
    ----------
    raw : str
        The area_name value as it appears in the Census Excel file.

    Returns
    -------
    str
        Canonical state/UT name, or cleaned raw name if unresolved.
    """
    token = _normalise_raw(raw)

    # 1. Explicit alias
    if token in _ALIAS_MAP:
        return _ALIAS_MAP[token]

    # 2. Exact match
    for idx, canon_lower in enumerate(_CANONICAL_LOWER):
        if token == canon_lower:
            return CANONICAL_STATES[idx]

    # 3. Canonical is a substring of the raw token
    #    (raw is the "bigger" string, e.g. 'state - jammu & kashmir (01)')
    for idx, canon_lower in enumerate(_CANONICAL_LOWER):
        if canon_lower in token:
            return CANONICAL_STATES[idx]

    # 4. Raw token is a substring of the canonical name
    #    (raw is the "smaller" string, e.g. 'maharashtra' vs 'Maharashtra')
    if token:                              # guard against empty string
        for idx, canon_lower in enumerate(_CANONICAL_LOWER):
            if token in canon_lower:
                return CANONICAL_STATES[idx]

    # 5. Unresolved — warn and return cleaned original
    cleaned = str(raw).strip()
    print(f"  [NAME WARN] Could not resolve state name: {repr(raw)!s} "
          f"(token={repr(token)}) — keeping as-is")
    return cleaned


def _clean_name(s: str) -> str:
    """
    Public entry point used by all build_*.py scripts.
    Delegates to resolve_state_name() so every caller automatically gets
    canonical, uniform state names.
    """
    return resolve_state_name(s)


def _make_geo(state_code, state_name, bracket) -> dict:
    """Return the standard geo-key dictionary for one row."""
    return {
        'state_code'  : state_code,
        'state_name'  : state_name,
        'age_bracket' : bracket,
    }


# ---------------------------------------------------------------------------
# FILTERING HELPERS
# ---------------------------------------------------------------------------

def _state_slice(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return only state-level Total rows.
    2011: district_code == '000'
    2001: district_code == '00' (2-digit) + tehsil_code == '0000'
    Handles both automatically.
    """
    area_total = df['area_type'] == 'Total'

    if 'tehsil_code' in df.columns:
        # 2001 format: state-level rows have district='00', tehsil='0000'
        return df[
            area_total &
            (df['district_code'] == '00') &
            (df['tehsil_code']   == '0000')
        ]
    else:
        # 2011 format: state-level rows have district='000'
        return df[
            area_total &
            (df['district_code'] == '000')
        ]

def _normalise_age_label(raw_label: str) -> str:
    """
    Normalise a raw age label string for robust bracket matching.
    Handles:
      - mixed capitalisation  ('Age Not stated' → 'age not stated')
      - extra whitespace      ('34 +' → '34+')
      - 'less than' variants  ('Less Than 10' → 'less than 10')
    """
    s = str(raw_label).strip().lower()
    s = s.replace(' +', '+')          # '34 +' → '34+'
    return s


def _rows_for_bracket(df: pd.DataFrame, age_col: str,
                      bracket: str, bracket_map: dict) -> pd.DataFrame:
    """
    Return rows whose age_col value (lowercased + stripped) is in the
    label set defined for `bracket` in `bracket_map`.

    Uses _normalise_age_label() so '34 +' and '34+' both match,
    and capitalisation differences are ignored.
    """
    labels = {_normalise_age_label(l) for l in bracket_map[bracket]}
    mask   = df[age_col].map(_normalise_age_label).isin(labels)
    return df[mask]


def _sum_bracket(df: pd.DataFrame, age_col: str,
                 value_cols: list, bracket: str,
                 bracket_map: dict) -> pd.Series:
    """
    For datasets with individual-year rows (C-08, C-09, C-12), sum all
    value_cols across the rows belonging to `bracket` and return a Series.

    Returns a Series of NaN when no matching rows are found (e.g. age_18_21
    in C-12 for ages 20-21 which are absent).
    """
    sub = _rows_for_bracket(df, age_col, bracket, bracket_map)
    if sub.empty:
        return pd.Series({c: np.nan for c in value_cols})
    return sub[value_cols].apply(pd.to_numeric, errors='coerce').sum()


# ---------------------------------------------------------------------------
# DATAFRAME MERGE HELPER
# ---------------------------------------------------------------------------

def _outer_merge(left: pd.DataFrame,
                 right: pd.DataFrame,
                 on: list) -> pd.DataFrame:
    """Outer-merge two DataFrames; handles empty inputs gracefully."""
    if left.empty:
        return right
    if right.empty:
        return left
    return left.merge(right, on=on, how='outer')


# ---------------------------------------------------------------------------
# GENDER SPLIT
# ---------------------------------------------------------------------------

def gender_split(df: pd.DataFrame, df_name: str) -> tuple:
    """
    Split a wide DataFrame into male-only and female-only versions.

    Rules
    -----
    - Columns containing '_male'   → df_male   only
    - Columns containing '_female' → df_female only
    - GEO_KEYS                     → both
    - Truly gender-neutral cols
      (e.g. CMPR_SC_persons)       → both
    """
    geo_cols     = [c for c in GEO_KEYS if c in df.columns]
    male_cols    = [c for c in df.columns if '_male'   in c and c not in geo_cols]
    female_cols  = [c for c in df.columns if '_female' in c and c not in geo_cols]
    neutral_cols = [c for c in df.columns
                    if c not in geo_cols
                    and '_male'   not in c
                    and '_female' not in c]

    df_male   = df[geo_cols + neutral_cols + male_cols].copy()
    df_female = df[geo_cols + neutral_cols + female_cols].copy()

    print(f"  {df_name} → male: {len(df_male.columns)} cols, "
          f"female: {len(df_female.columns)} cols")
    return df_male, df_female


# ---------------------------------------------------------------------------
# CSV SAVE HELPER
# ---------------------------------------------------------------------------

def _reorder_geo_first(df):
    """
    Return a copy of df with geo columns promoted to the front in the order:
        state_name | age_bracket | state_code | <all other cols, alphabetical>

    state_name and age_bracket are the primary tracking columns so they come
    first. state_code follows immediately. All remaining metric columns are
    sorted alphabetically so the output is easy to scan.
    """
    front = [c for c in ['state_name', 'age_bracket', 'state_code']
             if c in df.columns]
    rest  = sorted([c for c in df.columns if c not in front])
    return df[front + rest]


def save_outputs(outputs: dict) -> None:
    """
    Save each DataFrame in `outputs` dict to OUTPUT_DIR as a CSV.

    Column order in every output file:
        state_name | age_bracket | state_code | <metric cols, alphabetical>

    Skips empty DataFrames with a warning.

    Parameters
    ----------
    outputs : {filename: DataFrame}
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\n--- Saving CSVs ---")
    for fname, df in outputs.items():
        if df is None or df.empty:
            print(f"  SKIPPED (empty): {fname}")
            continue
        df = _reorder_geo_first(df)
        path = os.path.join(OUTPUT_DIR, fname)
        df.to_csv(path, index=False)
        print(f"  Saved : {fname}  ({len(df)} rows × {len(df.columns)} cols)")

    # Summary table
    print(f"\n{'='*70}")
    print(f"  {'File':<38} {'Rows':>6}  {'Cols':>5}")
    print(f"  {'-'*52}")
    for fname, df in outputs.items():
        if df is not None and not df.empty:
            print(f"  {fname:<38} {len(df):>6}  {len(df.columns):>5}")
    print(f"\n  Age brackets : {AGE_BRACKETS}")
    print(f"  Format       : LONG — one row per (state × age_bracket)")
    print(f"\n  Coverage notes:")
    print(f"    C-02/SC/ST : 5-year bands — brackets are APPROXIMATE")
    print(f"    C-08/09    : age_18_21 captures only ages 18-19 (20-21 inseparable from 20-24)")
    print(f"    C-12/SC/ST : age_below10 starts at age 5; age_18_21 captures only 18-19")
    print(f"{'='*70}")