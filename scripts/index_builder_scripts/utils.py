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
DATA_ROOT  = "/Users/anandagarwal/dsm_project/census_downloads_2011"
OUTPUT_DIR = "/Users/anandagarwal/dsm_project/output_datasets"

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
AGE_BRACKETS = ['age_below10', 'age_10_13', 'age_14_17', 'age_18_21']

# For C-04 / C-05 / C-06 / C-07  (age AT MARRIAGE labels)
AGE_BRACKET_MARRIAGE = {
    'age_below10' : {'less than 10', 'below 10'},
    'age_10_13'   : {'10-11', '12-13'},
    'age_14_17'   : {'14-15', '16-17'},
    'age_18_21'   : {'18-19', '20-21'},
}

# For C-02 / C-08 / C-12  (current population age-group labels)
AGE_BRACKET_POPULATION = {
    'age_below10' : {'below 10', '0-4', '5-9'},
    'age_10_13'   : {'10-14'},
    'age_14_17'   : {'15-19'},
    'age_18_21'   : {'20-24'},
}

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
ALL_AGES_LABEL = 'All ages'
EXCLUDE_AGES   = {'Age Not stated', 'Age not stated'}

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
# STRING / NAME HELPERS
# ---------------------------------------------------------------------------

def _clean_name(s: str) -> str:
    """Strip Census state-name prefixes."""
    return str(s).replace('State - ', '').replace('State- ', '').strip()


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
    Criterion: district_code == '000'  AND  area_type == 'Total'.
    """
    return df[
        (df['district_code'] == '000') &
        (df['area_type']     == 'Total')
    ]


def _rows_for_bracket(df: pd.DataFrame, age_col: str,
                      bracket: str, bracket_map: dict) -> pd.DataFrame:
    """
    Return rows whose age_col value (lowercased + stripped) is in the
    label set defined for `bracket` in `bracket_map`.
    """
    labels = bracket_map[bracket]
    mask   = df[age_col].str.lower().str.strip().isin(labels)
    return df[mask]


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

def save_outputs(outputs: dict) -> None:
    """
    Save each DataFrame in `outputs` dict to OUTPUT_DIR as a CSV.
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
    print(f"{'='*70}")