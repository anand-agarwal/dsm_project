"""
=============================================================================
build_total.py  —  Builds df_total (General Population)
=============================================================================
Sources  : C-04  (Age at Marriage × Ever-married counts)
           C-06  (Education level × Age at Marriage)
           C-07  (Economic activity × Age at Marriage)
           C-08  (Education level × Age × Sex)          ← NEW
           C-12  (School attendance × Economic activity) ← NEW

Outputs  : df_total_state.csv   — all columns (male + female)
           df_total_male.csv    — geo keys + male columns only
           df_total_female.csv  — geo keys + female columns only

Format   : LONG — one row per (state × age_bracket)
           Age brackets: age_below10 | age_10_13 | age_14_17 | age_18_21

Coverage notes (NEW sources):
  C-08 : age_18_21 captures only ages 18-19 (20-21 inseparable from 20-24)
  C-12 : age_below10 starts at age 5; age_18_21 captures only 18-19
=============================================================================
"""

import numpy as np
import pandas as pd

from utils import (
    AGE_BRACKETS, AGE_BRACKET_MARRIAGE, ALL_AGES_LABEL, EXCLUDE_AGES,
    AGE_BRACKET_C08, AGE_BRACKET_C12,                  # NEW
    EDU_LEVEL_ALIASES, EDU_SHORT, ECON_KW,
    GEO_KEYS,
    _read_excel, _glob_files, _pad_df, _clean_name,
    _state_slice, _rows_for_bracket, _sum_bracket, _make_geo, _outer_merge,  # _sum_bracket NEW
    gender_split, save_outputs,
    safe_div,
)


# =============================================================================
# SECTION 1 — C-04   (General Age at Marriage)
# Columns: CMPR_total_male, CMPR_total_female
# =============================================================================

C04_COLS = [
    'table_name', 'state_code', 'district_code', 'tehsil_code', 'area_name', 'area_type',
    'age_at_marriage',
    'ever_married_m', 'ever_married_f',
    'curr_m_all', 'curr_f_all',
    'curr_m_0_4', 'curr_f_0_4',
    'curr_m_5_9', 'curr_f_5_9',
    'curr_m_10_19', 'curr_f_10_19',
    'curr_m_20_29', 'curr_f_20_29',
    'curr_m_30_39', 'curr_f_30_39',
    'curr_m_40plus', 'curr_f_40plus',
    'curr_m_dur_unk', 'curr_f_dur_unk',
]


def _parse_c04(filepath: str) -> pd.DataFrame:
    raw = _pad_df(_read_excel(filepath), len(C04_COLS))
    raw.columns = C04_COLS
    for col in ['district_code', 'area_type', 'age_at_marriage',
                'area_name', 'state_code']:
        raw[col] = raw[col].astype(str).str.strip()
    raw = raw[~raw['age_at_marriage'].isin(EXCLUDE_AGES)]
    for c in C04_COLS[7:]:
        raw[c] = pd.to_numeric(raw[c], errors='coerce').fillna(0)
    return raw.reset_index(drop=True)


def _compute_c04_for_bracket(df: pd.DataFrame, bracket: str) -> dict:
    """
    CMPR = (ever-married in bracket) / (total ever-married, all ages) × 100
    """
    br_rows = _rows_for_bracket(df, 'age_at_marriage', bracket, AGE_BRACKET_MARRIAGE)
    all_row = df[df['age_at_marriage'].str.lower() == ALL_AGES_LABEL.lower()]

    # Fallback: if no explicit 'All ages' row, sum all non-bracket rows
    if all_row.empty:
        all_row = df[~df['age_at_marriage'].str.lower().isin(
            {l for v in AGE_BRACKET_MARRIAGE.values() for l in v} |
            {a.lower() for a in EXCLUDE_AGES}
        )]

    return {
        'CMPR_total_male'  : safe_div(br_rows['ever_married_m'].sum(),
                                      all_row['ever_married_m'].sum()),
        'CMPR_total_female': safe_div(br_rows['ever_married_f'].sum(),
                                      all_row['ever_married_f'].sum()),
    }


def build_c04_indexes(dataset_key: str = 'C-04') -> pd.DataFrame:
    files = _glob_files(dataset_key)
    print(f"    {dataset_key}: {len(files)} files")
    rows = []
    for fp in files:
        try:
            df = _parse_c04(fp)
            if df.empty:
                continue
            sl = _state_slice(df)
            if sl.empty:
                continue
            state_code = sl['state_code'].iloc[0]
            state_name = _clean_name(sl['area_name'].iloc[0])
            for bracket in AGE_BRACKETS:
                idx = _compute_c04_for_bracket(sl, bracket)
                idx.update(_make_geo(state_code, state_name, bracket))
                rows.append(idx)
        except Exception as e:
            print(f"      [WARN] {fp}: {e}")
    return pd.DataFrame(rows)


# =============================================================================
# SECTION 2 — C-06   (Education × Age at Marriage)
# Columns: CMPR_{edu_level}_male, CMPR_{edu_level}_female
# edu levels: illiterate | below_primary | primary | middle | matric
# =============================================================================

C06_COLS = [
    'table_name', 'state_code', 'district_code', 'tehsil_code', 'area_name', 'area_type',
    'edu_level', 'age_at_marriage',
    'ever_married_m', 'ever_married_f',
    'curr_m_all', 'curr_f_all',
    'curr_m_0_4', 'curr_f_0_4',
    'curr_m_5_9', 'curr_f_5_9',
    'curr_m_10_19', 'curr_f_10_19',
    'curr_m_20_29', 'curr_f_20_29',
    'curr_m_30_39', 'curr_f_30_39',
    'curr_m_40plus', 'curr_f_40plus',
    'curr_m_dur_unk', 'curr_f_dur_unk',
]


def _parse_c06(filepath: str) -> pd.DataFrame:
    raw = _pad_df(_read_excel(filepath), len(C06_COLS))
    raw.columns = C06_COLS
    for col in ['district_code', 'area_type', 'age_at_marriage',
                'area_name', 'state_code']:
        raw[col] = raw[col].astype(str).str.strip()
    raw['edu_level'] = (raw['edu_level'].astype(str)
                                        .str.strip()
                                        .replace(EDU_LEVEL_ALIASES))
    raw = raw[~raw['age_at_marriage'].isin(EXCLUDE_AGES)]
    for c in C06_COLS[8:]:
        raw[c] = pd.to_numeric(raw[c], errors='coerce').fillna(0)
    return raw.reset_index(drop=True)


def _compute_c06_for_bracket(df: pd.DataFrame, bracket: str) -> dict:
    """
    For each education level, compute CMPR_male and CMPR_female.
    CMPR = (ever-married in bracket for that edu level) /
           (total ever-married for that edu level, all ages) × 100
    """
    row = {}
    for full_name, short_key in EDU_SHORT.items():
        sub = df[df['edu_level'] == full_name]
        if sub.empty:
            row[f'CMPR_{short_key}_male']   = np.nan
            row[f'CMPR_{short_key}_female'] = np.nan
            continue

        all_row = sub[sub['age_at_marriage'].str.lower() == ALL_AGES_LABEL.lower()]
        br_rows = _rows_for_bracket(sub, 'age_at_marriage', bracket, AGE_BRACKET_MARRIAGE)

        if all_row.empty:
            all_row = sub[~sub['age_at_marriage'].str.lower().isin(
                {l for v in AGE_BRACKET_MARRIAGE.values() for l in v} |
                {a.lower() for a in EXCLUDE_AGES}
            )]

        row[f'CMPR_{short_key}_male']   = safe_div(
            br_rows['ever_married_m'].sum(), all_row['ever_married_m'].sum())
        row[f'CMPR_{short_key}_female'] = safe_div(
            br_rows['ever_married_f'].sum(), all_row['ever_married_f'].sum())
    return row


def build_c06_indexes(dataset_key: str = 'C-06') -> pd.DataFrame:
    files = _glob_files(dataset_key)
    print(f"    {dataset_key}: {len(files)} files")
    rows = []
    for fp in files:
        try:
            df = _parse_c06(fp)
            if df.empty:
                continue
            sl = _state_slice(df)
            if sl.empty:
                continue
            state_code = sl['state_code'].iloc[0]
            state_name = _clean_name(sl['area_name'].iloc[0])
            for bracket in AGE_BRACKETS:
                idx = _compute_c06_for_bracket(sl, bracket)
                idx.update(_make_geo(state_code, state_name, bracket))
                rows.append(idx)
        except Exception as e:
            print(f"      [WARN] {fp}: {e}")
    return pd.DataFrame(rows)


# =============================================================================
# SECTION 3 — C-07   (Economic Activity × Age at Marriage)
# Columns: CMPR_{econ_category}_male, CMPR_{econ_category}_female
# Categories: main_workers | cultivators | agri_labourers |
#             household_industry | other_workers | non_workers
# =============================================================================

C07_COLS = [
    'table_name', 'state_code', 'district_code', 'tehsil_code', 'area_name', 'area_type',
    'econ_activity', 'age_at_marriage',
    'ever_married_m', 'ever_married_f',
    'curr_m_all', 'curr_f_all',
    'curr_m_0_4', 'curr_f_0_4',
    'curr_m_5_9', 'curr_f_5_9',
    'curr_m_10_19', 'curr_f_10_19',
    'curr_m_20_29', 'curr_f_20_29',
    'curr_m_30_39', 'curr_f_30_39',
    'curr_m_40plus', 'curr_f_40plus',
    'curr_m_dur_unk', 'curr_f_dur_unk',
]


def _parse_c07(filepath: str) -> pd.DataFrame:
    raw = _pad_df(_read_excel(filepath), len(C07_COLS))
    raw.columns = C07_COLS
    for col in ['district_code', 'area_type', 'econ_activity',
                'age_at_marriage', 'area_name', 'state_code']:
        raw[col] = raw[col].astype(str).str.strip()
    raw = raw[~raw['age_at_marriage'].isin(EXCLUDE_AGES)]
    for c in C07_COLS[8:]:
        raw[c] = pd.to_numeric(raw[c], errors='coerce').fillna(0)
    return raw.reset_index(drop=True)


def _compute_c07_for_bracket(df: pd.DataFrame, bracket: str) -> dict:
    """
    For each economic activity category, compute CMPR_male and CMPR_female.
    """
    row = {}
    for short, keyword in ECON_KW.items():
        sub = df[df['econ_activity'].str.lower().str.contains(keyword, na=False)]
        if sub.empty:
            row[f'CMPR_{short}_male']   = np.nan
            row[f'CMPR_{short}_female'] = np.nan
            continue

        all_row = sub[sub['age_at_marriage'].str.lower() == ALL_AGES_LABEL.lower()]
        br_rows = _rows_for_bracket(sub, 'age_at_marriage', bracket, AGE_BRACKET_MARRIAGE)

        if all_row.empty:
            all_row = sub[~sub['age_at_marriage'].str.lower().isin(
                {l for v in AGE_BRACKET_MARRIAGE.values() for l in v} |
                {a.lower() for a in EXCLUDE_AGES}
            )]

        row[f'CMPR_{short}_male']   = safe_div(
            br_rows['ever_married_m'].sum(), all_row['ever_married_m'].sum())
        row[f'CMPR_{short}_female'] = safe_div(
            br_rows['ever_married_f'].sum(), all_row['ever_married_f'].sum())
    return row


def build_c07_indexes(dataset_key: str = 'C-07') -> pd.DataFrame:
    files = _glob_files(dataset_key)
    print(f"    {dataset_key}: {len(files)} files")
    rows = []
    for fp in files:
        try:
            df = _parse_c07(fp)
            if df.empty:
                continue
            sl = _state_slice(df)
            if sl.empty:
                continue
            state_code = sl['state_code'].iloc[0]
            state_name = _clean_name(sl['area_name'].iloc[0])
            for bracket in AGE_BRACKETS:
                idx = _compute_c07_for_bracket(sl, bracket)
                idx.update(_make_geo(state_code, state_name, bracket))
                rows.append(idx)
        except Exception as e:
            print(f"      [WARN] {fp}: {e}")
    return pd.DataFrame(rows)


# =============================================================================
# SECTION 4 — C-08   (Education level × Age × Sex)              ← NEW
# Columns: Literacy_rate_total_male/female,
#          Illiteracy_rate_total_male/female,
#          Below_primary_share_total_male/female
#
# NOTE: age_18_21 captures only ages 18-19.
#       Ages 20-21 cannot be separated from the '20-24' grouped band.
# =============================================================================

C08_COLS = [
    'table_name', 'state_code', 'district_code', 'tehsil_code', 'area_name', 'area_type',
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

C08_VALUE_COLS = C08_COLS[7:]


def _parse_c08(filepath: str) -> pd.DataFrame:
    raw = _pad_df(_read_excel(filepath), len(C08_COLS))
    raw.columns = C08_COLS
    for col in ['district_code', 'area_type', 'age_group', 'area_name', 'state_code']:
        raw[col] = raw[col].astype(str).str.strip()
    for c in C08_VALUE_COLS:
        raw[c] = pd.to_numeric(raw[c], errors='coerce').fillna(0)
    raw = raw[~raw['age_group'].str.strip().str.lower().isin(
        {ALL_AGES_LABEL.lower()} | {e.lower() for e in EXCLUDE_AGES}
    )]
    return raw.reset_index(drop=True)


def _compute_c08_for_bracket(df: pd.DataFrame, bracket: str) -> dict:
    """
    Literacy and education indexes for the general population in one age bracket.
    Uses AGE_BRACKET_C08 — individual-year rows are summed via _sum_bracket.
    """
    p   = 'total'
    agg = _sum_bracket(df, 'age_group', C08_VALUE_COLS, bracket, AGE_BRACKET_C08)

    tot_m     = agg['total_m']
    tot_f     = agg['total_f']
    lit_m     = agg['literate_m']
    lit_f     = agg['literate_f']
    illit_m   = agg['illiterate_m']
    illit_f   = agg['illiterate_f']
    bp_m      = agg['below_primary_m']
    bp_f      = agg['below_primary_f']

    return {
        f'Literacy_rate_{p}_male'         : safe_div(lit_m,   tot_m),
        f'Literacy_rate_{p}_female'       : safe_div(lit_f,   tot_f),
        f'Illiteracy_rate_{p}_male'       : safe_div(illit_m, tot_m),
        f'Illiteracy_rate_{p}_female'     : safe_div(illit_f, tot_f),
        f'Below_primary_share_{p}_male'   : safe_div(bp_m,    lit_m),
        f'Below_primary_share_{p}_female' : safe_div(bp_f,    lit_f),
    }


def build_c08_indexes(dataset_key: str = 'C-08') -> pd.DataFrame:
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
# SECTION 5 — C-12   (School attendance × Economic activity, age 5-19) ← NEW
# Columns: School_attendance_rate_total_male/female,
#          Dropout_rate_total_male/female,
#          Child_labour_attending_total_male/female,
#          Child_labour_dropout_total_male/female,
#          Non_worker_dropout_total_female
#
# NOTE: age_below10 covers only ages 5-9 (no data for 0-4 in C-12).
#       age_18_21 covers only ages 18-19 (dataset ends at 19).
# =============================================================================

C12_COLS = [
    'table_name', 'state_code', 'district_code', 'tehsil_code', 'area_name', 'area_type',
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

C12_VALUE_COLS = C12_COLS[7:]


def _parse_c12(filepath: str) -> pd.DataFrame:
    raw = _pad_df(_read_excel(filepath), len(C12_COLS))
    raw.columns = C12_COLS
    for col in ['district_code', 'area_type', 'age_group', 'area_name', 'state_code']:
        raw[col] = raw[col].astype(str).str.strip()
    for c in C12_VALUE_COLS:
        raw[c] = pd.to_numeric(raw[c], errors='coerce').fillna(0)
    # Drop the '5-19' aggregate row; filter defensively for any excluded labels.
    raw = raw[~raw['age_group'].str.strip().str.lower().isin(
        {'5-19', ALL_AGES_LABEL.lower()} | {e.lower() for e in EXCLUDE_AGES}
    )]
    return raw.reset_index(drop=True)


def _compute_c12_for_bracket(df: pd.DataFrame, bracket: str) -> dict:
    """
    School attendance, dropout, and child labour indexes for the general
    population.  Uses AGE_BRACKET_C12 — individual-year rows summed via
    _sum_bracket.  Returns NaN for any bracket with no matching rows.
    """
    p   = 'total'
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
        f'School_attendance_rate_{p}_male'   : safe_div(att_m,         tot_m),
        f'School_attendance_rate_{p}_female' : safe_div(att_f,         tot_f),
        f'Dropout_rate_{p}_male'             : safe_div(natt_m,        tot_m),
        f'Dropout_rate_{p}_female'           : safe_div(natt_f,        tot_f),
        f'Child_labour_attending_{p}_male'   : safe_div(cl_att_m,      tot_m),
        f'Child_labour_attending_{p}_female' : safe_div(cl_att_f,      tot_f),
        f'Child_labour_dropout_{p}_male'     : safe_div(cl_natt_m,     tot_m),
        f'Child_labour_dropout_{p}_female'   : safe_div(cl_natt_f,     tot_f),
        f'Non_worker_dropout_{p}_female'     : safe_div(nonw_natt_f,   tot_f),
    }


def build_c12_indexes(dataset_key: str = 'C-12') -> pd.DataFrame:
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

def build_df_total() -> pd.DataFrame:
    print("\n[df_total] Building from C-04, C-06, C-07, C-08, C-12 ...")
    c04 = build_c04_indexes('C-04')
    c06 = build_c06_indexes('C-06')
    c07 = build_c07_indexes('C-07')
    c08 = build_c08_indexes('C-08')     # NEW
    c12 = build_c12_indexes('C-12')     # NEW
    df  = _outer_merge(_outer_merge(c04, c06, on=GEO_KEYS), c07, on=GEO_KEYS)
    df  = _outer_merge(df, c08, on=GEO_KEYS)   # NEW
    df  = _outer_merge(df, c12, on=GEO_KEYS)   # NEW
    print(f"  df_total assembled: {df.shape[0]} rows × {df.shape[1]} cols")
    return df


def main():
    df_total = build_df_total()

    print("\n--- Gender splits ---")
    df_total_m, df_total_f = gender_split(df_total, 'df_total')

    outputs = {
        'df_total_state.csv'  : df_total,
        'df_total_male.csv'   : df_total_m,
        'df_total_female.csv' : df_total_f,
    }
    save_outputs(outputs)
    print("\nDone — df_total.")


if __name__ == '__main__':
    main()