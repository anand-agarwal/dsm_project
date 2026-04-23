"""
=============================================================================
build_total.py  —  Builds df_total (General Population)
=============================================================================
Sources  : C-04  (Age at Marriage × Ever-married counts)
           C-06  (Education level × Age at Marriage)
           C-07  (Economic activity × Age at Marriage)

Outputs  : df_total_state.csv   — all columns (male + female)
           df_total_male.csv    — geo keys + male columns only
           df_total_female.csv  — geo keys + female columns only

Format   : LONG — one row per (state × age_bracket)
           Age brackets: age_below10 | age_10_13 | age_14_17 | age_18_21
=============================================================================
"""

import numpy as np
import pandas as pd

from utils import (
    AGE_BRACKETS, AGE_BRACKET_MARRIAGE, ALL_AGES_LABEL, EXCLUDE_AGES,
    EDU_LEVEL_ALIASES, EDU_SHORT, ECON_KW,
    GEO_KEYS,
    _read_excel, _glob_files, _pad_df, _clean_name,
    _state_slice, _rows_for_bracket, _make_geo, _outer_merge,
    gender_split, save_outputs,
    safe_div,
)


# =============================================================================
# SECTION 1 — C-04   (General Age at Marriage)
# Columns: CMPR_total_male, CMPR_total_female
# =============================================================================

C04_COLS = [
    'table_name', 'state_code', 'district_code', 'area_name', 'area_type',
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
    for c in C04_COLS[6:]:
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
    'table_name', 'state_code', 'district_code', 'area_name', 'area_type',
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
    for c in C06_COLS[7:]:
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
    'table_name', 'state_code', 'district_code', 'area_name', 'area_type',
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
    for c in C07_COLS[7:]:
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
# ASSEMBLE + SPLIT + SAVE
# =============================================================================

def build_df_total() -> pd.DataFrame:
    print("\n[df_total] Building from C-04, C-06, C-07 ...")
    c04 = build_c04_indexes('C-04')
    c06 = build_c06_indexes('C-06')
    c07 = build_c07_indexes('C-07')
    df  = _outer_merge(_outer_merge(c04, c06, on=GEO_KEYS), c07, on=GEO_KEYS)
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