"""
=============================================================================
build_SC.py  —  Builds df_SC (Scheduled Castes population)
=============================================================================
Sources  : C-02_(SC)  (Marital status × Age × Sex)
           C-08_(SC)  (Education level × Age × Sex)
           C-12_(SC)  (School attendance × Economic activity, age 5-19)

Outputs  : df_SC_state.csv   — all columns (male + female + persons)
           df_SC_male.csv    — geo keys + male columns only
           df_SC_female.csv  — geo keys + female columns only

Format   : LONG — one row per (state × age_bracket)
           Age brackets: age_below10 | age_10_13 | age_14_17 | age_18_21

Bracket map notes (see utils.py for full detail):
  C-02-SC : uses AGE_BRACKET_C02  — 5-year bands; brackets are APPROXIMATE
             ('10-14' → age_10_13, '15-19' → age_14_17, '20-24' → age_18_21)
  C-08-SC : uses AGE_BRACKET_C08  — individual years 7-19, then 5-year bands;
             age_18_21 captures only ages 18-19 (20-21 inseparable from 20-24)
  C-12-SC : uses AGE_BRACKET_C12  — individual years 5-19 only;
             age_below10 starts at age 5; age_18_21 captures only 18-19
=============================================================================
"""

import numpy as np
import pandas as pd

from utils import (
    AGE_BRACKETS,
    AGE_BRACKET_C02,
    AGE_BRACKET_C08,
    AGE_BRACKET_C12,
    ALL_AGES_LABEL, EXCLUDE_AGES,
    GEO_KEYS,
    _read_excel, _glob_files, _pad_df, _clean_name,
    _state_slice, _rows_for_bracket, _sum_bracket, _make_geo, _outer_merge,
    gender_split, save_outputs,
    safe_div,
)

PREFIX = 'SC'   # used in every column name produced by this script


# =============================================================================
# SECTION 1 — C-02_(SC)   (Marital status × Age × Sex)
# Bracket map : AGE_BRACKET_C02  (5-year bands; approximate)
# Columns     : CMPR_SC_male, CMPR_SC_female, CMPR_SC_persons
# =============================================================================

C02_COLS = [
    'table_name', 'state_code', 'district_code', 'area_name', 'area_type',
    'age_group',
    'total_p', 'total_m', 'total_f',
    'never_married_p', 'never_married_m', 'never_married_f',
    'curr_married_p', 'curr_married_m', 'curr_married_f',
    'widowed_p', 'widowed_m', 'widowed_f',
    'separated_p', 'separated_m', 'separated_f',
    'divorced_p', 'divorced_m', 'divorced_f',
    'unspecified_p', 'unspecified_m', 'unspecified_f',
]


def _parse_c02(filepath: str) -> pd.DataFrame:
    raw = _pad_df(_read_excel(filepath), len(C02_COLS))
    raw.columns = C02_COLS
    for col in ['district_code', 'area_type', 'age_group', 'area_name', 'state_code']:
        raw[col] = raw[col].astype(str).str.strip()
    for c in C02_COLS[6:]:
        raw[c] = pd.to_numeric(raw[c], errors='coerce').fillna(0)
    # Drop 'All ages' total row and 'Age not stated' rows — these must not
    # be summed into bracket numerators or denominators.
    raw = raw[~raw['age_group'].str.strip().str.lower().isin(
        {ALL_AGES_LABEL.lower()} | {e.lower() for e in EXCLUDE_AGES}
    )]
    return raw.reset_index(drop=True)


def _compute_c02_for_bracket(df: pd.DataFrame, bracket: str) -> dict:
    """
    CMPR = currently married in bracket / total population in bracket × 100.
    Uses AGE_BRACKET_C02 (5-year bands).  C-02 has a single matching row per
    bracket so _rows_for_bracket is sufficient (no summing of individual years).
    Produces _male, _female, _persons variants.
    """
    p       = PREFIX
    br_rows = _rows_for_bracket(df, 'age_group', bracket, AGE_BRACKET_C02)

    return {
        f'CMPR_{p}_male'    : safe_div(br_rows['curr_married_m'].sum(),
                                       br_rows['total_m'].sum()),
        f'CMPR_{p}_female'  : safe_div(br_rows['curr_married_f'].sum(),
                                       br_rows['total_f'].sum()),
        f'CMPR_{p}_persons' : safe_div(br_rows['curr_married_p'].sum(),
                                       br_rows['total_p'].sum()),
    }


def build_c02_indexes(dataset_key: str = 'C-02-SC') -> pd.DataFrame:
    files = _glob_files(dataset_key)
    print(f"    {dataset_key}: {len(files)} files")
    rows = []
    for fp in files:
        try:
            df = _parse_c02(fp)
            if df.empty:
                continue
            sl = _state_slice(df)
            if sl.empty:
                continue
            state_code = sl['state_code'].iloc[0]
            state_name = _clean_name(sl['area_name'].iloc[0])
            for bracket in AGE_BRACKETS:
                idx = _compute_c02_for_bracket(sl, bracket)
                idx.update(_make_geo(state_code, state_name, bracket))
                rows.append(idx)
        except Exception as e:
            print(f"      [WARN] {fp}: {e}")
    return pd.DataFrame(rows)


# =============================================================================
# SECTION 2 — C-08_(SC)   (Education level × Age × Sex)
# Bracket map : AGE_BRACKET_C08  (individual years 7-19, sums required)
# Columns     : Literacy_rate_SC_male/female, Illiteracy_rate_SC_female,
#               Below_primary_share_SC_female, Graduate_rate_SC_male/female
#
# NOTE: age_18_21 sums only ages 18 and 19.  Ages 20-21 cannot be separated
#       from the '20-24' grouped band and are therefore excluded.
# =============================================================================

C08_COLS = [
    'table_name', 'state_code', 'district_code', 'area_name', 'area_type',
    'age_group',
    'total_p', 'total_m', 'total_f',
    'illiterate_p', 'illiterate_m', 'illiterate_f',
    'literate_p', 'literate_m', 'literate_f',
    'lit_no_edu_p', 'lit_no_edu_m', 'lit_no_edu_f',
    'below_primary_p', 'below_primary_m', 'below_primary_f',
    'primary_p', 'primary_m', 'primary_f',
    'middle_p', 'middle_m', 'middle_f',
    'matric_p', 'matric_m', 'matric_f',
    'higher_sec_p', 'higher_sec_m', 'higher_sec_f',
    'non_tech_dip_p', 'non_tech_dip_m', 'non_tech_dip_f',
    'tech_dip_p', 'tech_dip_m', 'tech_dip_f',
    'graduate_p', 'graduate_m', 'graduate_f',
    'unclassified_p', 'unclassified_m', 'unclassified_f',
]

# Numeric columns that _sum_bracket will aggregate across individual-year rows
C08_VALUE_COLS = C08_COLS[6:]


def _parse_c08(filepath: str) -> pd.DataFrame:
    raw = _pad_df(_read_excel(filepath), len(C08_COLS))
    raw.columns = C08_COLS
    for col in ['district_code', 'area_type', 'age_group', 'area_name', 'state_code']:
        raw[col] = raw[col].astype(str).str.strip()
    for c in C08_VALUE_COLS:
        raw[c] = pd.to_numeric(raw[c], errors='coerce').fillna(0)
    # Drop the 'All ages' total row and 'Age not stated' rows before any
    # summing — including the '0-6' grouped band which is outside our brackets.
    raw = raw[~raw['age_group'].str.strip().str.lower().isin(
        {ALL_AGES_LABEL.lower()} | {e.lower() for e in EXCLUDE_AGES}
    )]
    return raw.reset_index(drop=True)


def _compute_c08_for_bracket(df: pd.DataFrame, bracket: str) -> dict:
    """
    Literacy and education indexes for the SC population in one age bracket.
    Uses AGE_BRACKET_C08 — individual-year rows are summed via _sum_bracket.
    """
    p   = PREFIX
    agg = _sum_bracket(df, 'age_group', C08_VALUE_COLS, bracket, AGE_BRACKET_C08)

    tot_m   = agg['total_m']
    tot_f   = agg['total_f']
    lit_m   = agg['literate_m']
    lit_f   = agg['literate_f']
    illit_m = agg['illiterate_m']
    illit_f = agg['illiterate_f']
    bp_m    = agg['below_primary_m']
    bp_f    = agg['below_primary_f']
    return {
        f'Literacy_rate_{p}_male'         : safe_div(lit_m,   tot_m),
        f'Literacy_rate_{p}_female'       : safe_div(lit_f,   tot_f),
        f'Illiteracy_rate_{p}_male'       : safe_div(illit_m, tot_m),
        f'Illiteracy_rate_{p}_female'     : safe_div(illit_f, tot_f),
        f'Below_primary_share_{p}_male'   : safe_div(bp_m,    lit_m),
        f'Below_primary_share_{p}_female' : safe_div(bp_f,    lit_f),
    }


def build_c08_indexes(dataset_key: str = 'C-08-SC') -> pd.DataFrame:
    files = _glob_files(dataset_key)
    print(f"    {dataset_key}: {len(files)} files")
    rows = []
    for fp in files:
        try:
            df = _parse_c08(fp)
            if df.empty:
                continue
            sl = _state_slice(df)
            if sl.empty:
                continue
            state_code = sl['state_code'].iloc[0]
            state_name = _clean_name(sl['area_name'].iloc[0])
            for bracket in AGE_BRACKETS:
                idx = _compute_c08_for_bracket(sl, bracket)
                idx.update(_make_geo(state_code, state_name, bracket))
                rows.append(idx)
        except Exception as e:
            print(f"      [WARN] {fp}: {e}")
    return pd.DataFrame(rows)


# =============================================================================
# SECTION 3 — C-12_(SC)   (School attendance × Economic activity, age 5-19)
# Bracket map : AGE_BRACKET_C12  (individual years 5-19; sums required)
# Columns     : School_attendance_rate_SC_male/female,
#               Dropout_rate_SC_male/female,
#               Child_labour_attending_SC_male/female,
#               Child_labour_dropout_SC_male/female,
#               Non_worker_dropout_SC_female
#
# NOTE: age_below10 covers only ages 5-9 (no data for 0-4 in C-12).
#       age_18_21 covers only ages 18-19 (dataset ends at 19).
#       When _sum_bracket returns NaN for a bracket, the index is also NaN.
# =============================================================================

C12_COLS = [
    'table_name', 'state_code', 'district_code', 'area_name', 'area_type',
    'age_group',
    'total_p', 'total_m', 'total_f',
    'att_main_p',   'att_main_m',   'att_main_f',
    'att_marg36_p', 'att_marg36_m', 'att_marg36_f',
    'att_marg3_p',  'att_marg3_m',  'att_marg3_f',
    'att_nonw_p',   'att_nonw_m',   'att_nonw_f',
    'natt_main_p',   'natt_main_m',   'natt_main_f',
    'natt_marg36_p', 'natt_marg36_m', 'natt_marg36_f',
    'natt_marg3_p',  'natt_marg3_m',  'natt_marg3_f',
    'natt_nonw_p',   'natt_nonw_m',   'natt_nonw_f',
]

C12_VALUE_COLS = C12_COLS[6:]


def _parse_c12(filepath: str) -> pd.DataFrame:
    raw = _pad_df(_read_excel(filepath), len(C12_COLS))
    raw.columns = C12_COLS
    for col in ['district_code', 'area_type', 'age_group', 'area_name', 'state_code']:
        raw[col] = raw[col].astype(str).str.strip()
    for c in C12_VALUE_COLS:
        raw[c] = pd.to_numeric(raw[c], errors='coerce').fillna(0)
    # Drop the '5-19' aggregate row — individual-year rows are summed instead.
    # C-12 has no 'Age not stated' row but we filter defensively anyway.
    raw = raw[~raw['age_group'].str.strip().str.lower().isin(
        {'5-19', ALL_AGES_LABEL.lower()} | {e.lower() for e in EXCLUDE_AGES}
    )]
    return raw.reset_index(drop=True)


def _compute_c12_for_bracket(df: pd.DataFrame, bracket: str) -> dict:
    """
    School attendance, dropout, and child labour indexes for the SC population.
    Uses AGE_BRACKET_C12 — individual-year rows are summed via _sum_bracket.
    Returns NaN for any index where the bracket has no rows (e.g. age_18_21
    beyond age 19, or age_below10 if 0-4 are needed but absent).
    """
    p   = PREFIX
    agg = _sum_bracket(df, 'age_group', C12_VALUE_COLS, bracket, AGE_BRACKET_C12)

    tot_m = agg['total_m']
    tot_f = agg['total_f']

    # Attending school: workers + non-workers who attend
    att_m = agg['att_main_m'] + agg['att_marg36_m'] + agg['att_marg3_m'] + agg['att_nonw_m']
    att_f = agg['att_main_f'] + agg['att_marg36_f'] + agg['att_marg3_f'] + agg['att_nonw_f']

    # Not attending school
    natt_m = agg['natt_main_m'] + agg['natt_marg36_m'] + agg['natt_marg3_m'] + agg['natt_nonw_m']
    natt_f = agg['natt_main_f'] + agg['natt_marg36_f'] + agg['natt_marg3_f'] + agg['natt_nonw_f']

    # Child labour (main + marginal workers) — attending school
    cl_att_m = agg['att_main_m'] + agg['att_marg36_m'] + agg['att_marg3_m']
    cl_att_f = agg['att_main_f'] + agg['att_marg36_f'] + agg['att_marg3_f']

    # Child labour (main + marginal workers) — not attending school
    cl_natt_m = agg['natt_main_m'] + agg['natt_marg36_m'] + agg['natt_marg3_m']
    cl_natt_f = agg['natt_main_f'] + agg['natt_marg36_f'] + agg['natt_marg3_f']

    # Non-worker and not attending (female only — key vulnerability indicator)
    nonw_natt_f = agg['natt_nonw_f']

    return {
        f'School_attendance_rate_{p}_male'   : safe_div(att_m,       tot_m),
        f'School_attendance_rate_{p}_female' : safe_div(att_f,       tot_f),
        f'Dropout_rate_{p}_male'             : safe_div(natt_m,      tot_m),
        f'Dropout_rate_{p}_female'           : safe_div(natt_f,      tot_f),
        f'Child_labour_attending_{p}_male'   : safe_div(cl_att_m,    tot_m),
        f'Child_labour_attending_{p}_female' : safe_div(cl_att_f,    tot_f),
        f'Child_labour_dropout_{p}_male'     : safe_div(cl_natt_m,   tot_m),
        f'Child_labour_dropout_{p}_female'   : safe_div(cl_natt_f,   tot_f),
        f'Non_worker_dropout_{p}_female'     : safe_div(nonw_natt_f, tot_f),
    }


def build_c12_indexes(dataset_key: str = 'C-12-SC') -> pd.DataFrame:
    files = _glob_files(dataset_key)
    print(f"    {dataset_key}: {len(files)} files")
    rows = []
    for fp in files:
        try:
            df = _parse_c12(fp)
            if df.empty:
                continue
            sl = _state_slice(df)
            if sl.empty:
                continue
            state_code = sl['state_code'].iloc[0]
            state_name = _clean_name(sl['area_name'].iloc[0])
            for bracket in AGE_BRACKETS:
                idx = _compute_c12_for_bracket(sl, bracket)
                idx.update(_make_geo(state_code, state_name, bracket))
                rows.append(idx)
        except Exception as e:
            print(f"      [WARN] {fp}: {e}")
    return pd.DataFrame(rows)


# =============================================================================
# ASSEMBLE + SPLIT + SAVE
# =============================================================================

def build_df_SC() -> pd.DataFrame:
    print("\n[df_SC] Building from C-02_(SC), C-08_(SC), C-12_(SC) ...")
    c02 = build_c02_indexes('C-02-SC')
    c08 = build_c08_indexes('C-08-SC')
    c12 = build_c12_indexes('C-12-SC')
    df  = _outer_merge(_outer_merge(c02, c08, on=GEO_KEYS), c12, on=GEO_KEYS)
    print(f"  df_SC assembled: {df.shape[0]} rows × {df.shape[1]} cols")
    return df


def main():
    df_SC = build_df_SC()

    print("\n--- Gender splits ---")
    df_SC_m, df_SC_f = gender_split(df_SC, 'df_SC')

    outputs = {
        'df_SC_state.csv'  : df_SC,
        'df_SC_male.csv'   : df_SC_m,
        'df_SC_female.csv' : df_SC_f,
    }
    save_outputs(outputs)
    print("\nDone — df_SC.")


if __name__ == '__main__':
    main()