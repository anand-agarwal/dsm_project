"""
=============================================================================
build_ST.py  —  Builds df_ST (Scheduled Tribes population)
=============================================================================
Sources  : C-02_(ST)  (Marital status × Age × Sex)
           C-08_(ST)  (Education level × Age × Sex)
           C-12_(ST)  (School attendance × Economic activity, age 5-19)

Outputs  : df_ST_state.csv   — all columns (male + female + persons)
           df_ST_male.csv    — geo keys + male columns only
           df_ST_female.csv  — geo keys + female columns only

Format   : LONG — one row per (state × age_bracket)
           Age brackets: age_below10 | age_10_13 | age_14_17 | age_18_21

Note: The parsers and compute functions here are structurally identical to
      build_SC.py. The only difference is PREFIX = 'ST' and the dataset
      keys passed to _glob_files (C-02-ST, C-08-ST, C-12-ST).
=============================================================================
"""

import numpy as np
import pandas as pd

from utils import (
    AGE_BRACKETS, AGE_BRACKET_POPULATION,
    GEO_KEYS,
    _read_excel, _glob_files, _pad_df, _clean_name,
    _state_slice, _rows_for_bracket, _make_geo, _outer_merge,
    gender_split, save_outputs,
    safe_div,
)

PREFIX = 'ST'


# =============================================================================
# SECTION 1 — C-02_(ST)   (Marital status × Age × Sex)
# Columns: CMPR_ST_male, CMPR_ST_female, CMPR_ST_persons
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
    return raw.reset_index(drop=True)


def _compute_c02_for_bracket(df: pd.DataFrame, bracket: str) -> dict:
    """
    CMPR = currently married in bracket / total population in bracket × 100
    Produces _male, _female, _persons variants.
    """
    p       = PREFIX
    br_rows = _rows_for_bracket(df, 'age_group', bracket, AGE_BRACKET_POPULATION)

    return {
        f'CMPR_{p}_male'    : safe_div(br_rows['curr_married_m'].sum(),
                                       br_rows['total_m'].sum()),
        f'CMPR_{p}_female'  : safe_div(br_rows['curr_married_f'].sum(),
                                       br_rows['total_f'].sum()),
        f'CMPR_{p}_persons' : safe_div(br_rows['curr_married_p'].sum(),
                                       br_rows['total_p'].sum()),
    }


def build_c02_indexes(dataset_key: str = 'C-02-ST') -> pd.DataFrame:
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
# SECTION 2 — C-08_(ST)   (Education level × Age × Sex)
# Columns: Literacy_rate_ST_male/female, Illiteracy_rate_ST_female,
#          Below_primary_share_ST_female, Graduate_rate_ST_male/female
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


def _parse_c08(filepath: str) -> pd.DataFrame:
    raw = _pad_df(_read_excel(filepath), len(C08_COLS))
    raw.columns = C08_COLS
    for col in ['district_code', 'area_type', 'age_group', 'area_name', 'state_code']:
        raw[col] = raw[col].astype(str).str.strip()
    for c in C08_COLS[6:]:
        raw[c] = pd.to_numeric(raw[c], errors='coerce').fillna(0)
    return raw.reset_index(drop=True)


def _compute_c08_for_bracket(df: pd.DataFrame, bracket: str) -> dict:
    """
    Literacy and education indexes for the ST population in one age bracket.
    """
    p  = PREFIX
    br = _rows_for_bracket(df, 'age_group', bracket, AGE_BRACKET_POPULATION)

    tot_m   = br['total_m'].sum()
    tot_f   = br['total_f'].sum()
    lit_m   = br['literate_m'].sum()
    lit_f   = br['literate_f'].sum()
    illit_f = br['illiterate_f'].sum()
    bp_f    = br['below_primary_f'].sum()
    grad_m  = br['graduate_m'].sum()
    grad_f  = br['graduate_f'].sum()

    return {
        f'Literacy_rate_{p}_male'         : safe_div(lit_m, tot_m),
        f'Literacy_rate_{p}_female'       : safe_div(lit_f, tot_f),
        f'Illiteracy_rate_{p}_female'     : safe_div(illit_f, tot_f),
        f'Below_primary_share_{p}_female' : safe_div(bp_f, lit_f),
        f'Graduate_rate_{p}_male'         : safe_div(grad_m, tot_m),
        f'Graduate_rate_{p}_female'       : safe_div(grad_f, tot_f),
    }


def build_c08_indexes(dataset_key: str = 'C-08-ST') -> pd.DataFrame:
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
# SECTION 3 — C-12_(ST)   (School attendance × Economic activity, age 5-19)
# Columns: School_attendance_rate_ST_male/female, Dropout_rate_ST_male/female,
#          Child_labour_attending_ST_male/female,
#          Child_labour_dropout_ST_male/female,
#          Non_worker_dropout_ST_female
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


def _parse_c12(filepath: str) -> pd.DataFrame:
    raw = _pad_df(_read_excel(filepath), len(C12_COLS))
    raw.columns = C12_COLS
    for col in ['district_code', 'area_type', 'age_group', 'area_name', 'state_code']:
        raw[col] = raw[col].astype(str).str.strip()
    for c in C12_COLS[6:]:
        raw[c] = pd.to_numeric(raw[c], errors='coerce').fillna(0)
    return raw.reset_index(drop=True)


def _compute_c12_for_bracket(df: pd.DataFrame, bracket: str) -> dict:
    """
    School attendance, dropout, and child labour indexes for the ST population.
    """
    p  = PREFIX
    br = _rows_for_bracket(df, 'age_group', bracket, AGE_BRACKET_POPULATION)
    if br.empty:
        br = df   # fallback: use all rows

    tot_m = br['total_m'].sum()
    tot_f = br['total_f'].sum()

    # Attending school (workers + non-workers who attend)
    att_m = (br['att_main_m'] + br['att_marg36_m'] +
             br['att_marg3_m'] + br['att_nonw_m']).sum()
    att_f = (br['att_main_f'] + br['att_marg36_f'] +
             br['att_marg3_f'] + br['att_nonw_f']).sum()

    # Not attending school
    natt_m = (br['natt_main_m'] + br['natt_marg36_m'] +
              br['natt_marg3_m'] + br['natt_nonw_m']).sum()
    natt_f = (br['natt_main_f'] + br['natt_marg36_f'] +
              br['natt_marg3_f'] + br['natt_nonw_f']).sum()

    # Child labour (main + marginal workers) — attending school
    cl_att_m = (br['att_main_m'] + br['att_marg36_m'] + br['att_marg3_m']).sum()
    cl_att_f = (br['att_main_f'] + br['att_marg36_f'] + br['att_marg3_f']).sum()

    # Child labour (main + marginal workers) — not attending school
    cl_natt_m = (br['natt_main_m'] + br['natt_marg36_m'] + br['natt_marg3_m']).sum()
    cl_natt_f = (br['natt_main_f'] + br['natt_marg36_f'] + br['natt_marg3_f']).sum()

    # Non-worker and not attending (female only — key vulnerability indicator)
    nonw_natt_f = br['natt_nonw_f'].sum()

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


def build_c12_indexes(dataset_key: str = 'C-12-ST') -> pd.DataFrame:
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

def build_df_ST() -> pd.DataFrame:
    print("\n[df_ST] Building from C-02_(ST), C-08_(ST), C-12_(ST) ...")
    c02 = build_c02_indexes('C-02-ST')
    c08 = build_c08_indexes('C-08-ST')
    c12 = build_c12_indexes('C-12-ST')
    df  = _outer_merge(_outer_merge(c02, c08, on=GEO_KEYS), c12, on=GEO_KEYS)
    print(f"  df_ST assembled: {df.shape[0]} rows × {df.shape[1]} cols")
    return df


def main():
    df_ST = build_df_ST()

    print("\n--- Gender splits ---")
    df_ST_m, df_ST_f = gender_split(df_ST, 'df_ST')

    outputs = {
        'df_ST_state.csv'  : df_ST,
        'df_ST_male.csv'   : df_ST_m,
        'df_ST_female.csv' : df_ST_f,
    }
    save_outputs(outputs)
    print("\nDone — df_ST.")


if __name__ == '__main__':
    main()