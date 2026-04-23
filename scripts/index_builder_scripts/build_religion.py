"""
=============================================================================
build_religion.py  —  Builds df_religion (Religion-based analysis)
=============================================================================
Sources  : C-05  (Religion × Age at Marriage — one national file)
           C-09  (Education × Religion × Age 7+ × Sex — one national file)

Outputs  : df_religion_state.csv   — all columns (male + female)
           df_religion_male.csv    — geo keys + male columns only
           df_religion_female.csv  — geo keys + female columns only

Format   : LONG — one row per (state × age_bracket)
           Age brackets: age_below10 | age_10_13 | age_14_17 | age_18_21

Religions tracked: hindu | muslim | christian | sikh | buddhist | jain
=============================================================================
"""

import numpy as np
import pandas as pd

from utils import (
    AGE_BRACKETS, AGE_BRACKET_MARRIAGE, AGE_BRACKET_POPULATION,
    ALL_AGES_LABEL, EXCLUDE_AGES,
    TARGET_RELIGIONS, SKIP_RELIGIONS, SKIP_REL_C09,
    GEO_KEYS,
    _read_excel, _glob_files, _pad_df, _clean_name,
    _rows_for_bracket, _make_geo, _outer_merge,
    gender_split, save_outputs,
    safe_div,
)


# =============================================================================
# SECTION 1 — C-05   (Religion × Age at Marriage)
# ONE national file; iterate over state_code groups inside it.
# Columns per religion: CMPR_{religion}_male, CMPR_{religion}_female
# =============================================================================

C05_COLS = [
    'table_name', 'state_code', 'district_code', 'area_name', 'area_type',
    'religion', 'age_at_marriage',
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


def _parse_c05(filepath: str) -> pd.DataFrame:
    raw = _pad_df(_read_excel(filepath), len(C05_COLS))
    raw.columns = C05_COLS
    for col in ['district_code', 'area_type', 'religion', 'age_at_marriage',
                'area_name', 'state_code']:
        raw[col] = raw[col].astype(str).str.strip()
    raw = raw[~raw['age_at_marriage'].isin(EXCLUDE_AGES)]
    for c in C05_COLS[7:]:
        raw[c] = pd.to_numeric(raw[c], errors='coerce').fillna(0)
    return raw.reset_index(drop=True)


def build_c05_indexes(dataset_key: str = 'C-05') -> pd.DataFrame:
    """
    Parse the single national C-05 file and build per-state, per-bracket
    CMPR values for each religion.
    """
    files = _glob_files(dataset_key)
    print(f"    {dataset_key}: {len(files)} files (expected 1 national file)")
    if not files:
        return pd.DataFrame()

    fp = files[0]
    try:
        df = _parse_c05(fp)
        # Normalise for matching
        df['religion']       = df['religion'].str.lower().str.strip()
        df['age_at_marriage'] = df['age_at_marriage'].str.lower().str.strip()
        # Keep only Total area rows
        df = df[df['area_type'] == 'Total']
    except Exception as e:
        print(f"      [ERROR] C-05 parse failed: {e}")
        return pd.DataFrame()

    rows = []
    for state_code, state_df in df.groupby('state_code'):
        state_name = _clean_name(state_df['area_name'].iloc[0])

        # Build religion label map once per state to avoid repeated scanning
        religion_raw_map: dict[str, list] = {}
        for raw_rel in state_df['religion'].unique():
            if raw_rel in SKIP_RELIGIONS:
                continue
            for target in TARGET_RELIGIONS:
                if target in raw_rel:
                    religion_raw_map.setdefault(target, []).append(raw_rel)

        for bracket in AGE_BRACKETS:
            row = _make_geo(state_code, state_name, bracket)

            for target in TARGET_RELIGIONS:
                raw_labels = religion_raw_map.get(target, [])
                if not raw_labels:
                    row[f'CMPR_{target}_male']   = np.nan
                    row[f'CMPR_{target}_female'] = np.nan
                    continue

                sub = state_df[state_df['religion'].isin(raw_labels)]

                # 'All ages' row (normalised to lowercase in _parse_c05)
                all_row = sub[sub['age_at_marriage'] == ALL_AGES_LABEL.lower()]
                br_rows = _rows_for_bracket(
                    sub, 'age_at_marriage', bracket, AGE_BRACKET_MARRIAGE)

                # Fallback: if no explicit 'all ages' row, use the entire sub
                if all_row.empty:
                    all_row = sub

                row[f'CMPR_{target}_male']   = safe_div(
                    br_rows['ever_married_m'].sum(), all_row['ever_married_m'].sum())
                row[f'CMPR_{target}_female'] = safe_div(
                    br_rows['ever_married_f'].sum(), all_row['ever_married_f'].sum())

            rows.append(row)

    return pd.DataFrame(rows)


# =============================================================================
# SECTION 2 — C-09   (Education × Religion × Age 7+ × Sex)
# ONE national file; iterate over state_code groups inside it.
# Columns per religion:
#   Literacy_rate_{rel}_male/female
#   Illiteracy_rate_{rel}_female
#   Below_primary_share_{rel}_female
#   Middle_school_share_{rel}_female
#   Graduate_rate_{rel}_male/female
# =============================================================================

C09_COLS = [
    'table_name', 'state_code', 'area_type', 'area_name',
    'religion', 'age_group',
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
]

# Metrics to emit — listed explicitly so we can nan-fill missing religions
# consistently.
_C09_METRICS = [
    'Literacy_rate_{r}_male',
    'Literacy_rate_{r}_female',
    'Illiteracy_rate_{r}_female',
    'Below_primary_share_{r}_female',
    'Middle_school_share_{r}_female',
    'Graduate_rate_{r}_male',
    'Graduate_rate_{r}_female',
]


def _nan_religion(row: dict, target: str) -> None:
    """Fill all C-09 metrics for a religion with NaN in-place."""
    for tmpl in _C09_METRICS:
        row[tmpl.format(r=target)] = np.nan


def build_c09_indexes(dataset_key: str = 'C-09') -> pd.DataFrame:
    """
    Parse the single national C-09 file and build per-state, per-bracket
    literacy / education indexes for each religion.
    """
    files = _glob_files(dataset_key)
    print(f"    {dataset_key}: {len(files)} files (expected 1 national file)")
    if not files:
        return pd.DataFrame()

    fp = files[0]
    try:
        raw = _pad_df(_read_excel(fp), len(C09_COLS))
        raw.columns = C09_COLS
        for col in ['area_type', 'religion', 'age_group', 'state_code', 'area_name']:
            raw[col] = raw[col].astype(str).str.strip()
        raw = raw[raw['area_type'] == 'Total']
        for c in C09_COLS[6:]:
            raw[c] = pd.to_numeric(raw[c], errors='coerce').fillna(0)
    except Exception as e:
        print(f"      [ERROR] C-09 parse failed: {e}")
        return pd.DataFrame()

    rows = []
    for state_code, state_df in raw.groupby('state_code'):
        state_name = _clean_name(state_df['area_name'].iloc[0])

        # Build religion label map once per state
        religion_raw_map: dict[str, list] = {}
        for raw_rel in state_df['religion'].unique():
            if raw_rel in SKIP_REL_C09:
                continue
            key = raw_rel.lower().strip()
            for target in TARGET_RELIGIONS:
                if target in key:
                    religion_raw_map.setdefault(target, []).append(raw_rel)

        for bracket in AGE_BRACKETS:
            # Rows for this bracket in this state
            br = _rows_for_bracket(
                state_df, 'age_group', bracket, AGE_BRACKET_POPULATION)
            row = _make_geo(state_code, state_name, bracket)

            for target in TARGET_RELIGIONS:
                raw_labels = religion_raw_map.get(target, [])
                if not raw_labels:
                    _nan_religion(row, target)
                    continue

                rel_br = br[br['religion'].isin(raw_labels)]

                tot_m   = rel_br['total_m'].sum()
                tot_f   = rel_br['total_f'].sum()
                lit_m   = rel_br['literate_m'].sum()
                lit_f   = rel_br['literate_f'].sum()
                illit_f = rel_br['illiterate_f'].sum()
                bp_f    = rel_br['below_primary_f'].sum()
                mid_f   = rel_br['middle_f'].sum()
                grad_m  = rel_br['graduate_m'].sum()
                grad_f  = rel_br['graduate_f'].sum()

                row[f'Literacy_rate_{target}_male']         = safe_div(lit_m,   tot_m)
                row[f'Literacy_rate_{target}_female']       = safe_div(lit_f,   tot_f)
                row[f'Illiteracy_rate_{target}_female']     = safe_div(illit_f, tot_f)
                row[f'Below_primary_share_{target}_female'] = safe_div(bp_f,    lit_f)
                row[f'Middle_school_share_{target}_female'] = safe_div(mid_f,   lit_f)
                row[f'Graduate_rate_{target}_male']         = safe_div(grad_m,  tot_m)
                row[f'Graduate_rate_{target}_female']       = safe_div(grad_f,  tot_f)

            rows.append(row)

    return pd.DataFrame(rows)


# =============================================================================
# ASSEMBLE + SPLIT + SAVE
# =============================================================================

def build_df_religion() -> pd.DataFrame:
    print("\n[df_religion] Building from C-05, C-09 ...")
    c05 = build_c05_indexes('C-05')
    print(f"  C-05 shape: {c05.shape}")
    c09 = build_c09_indexes('C-09')
    print(f"  C-09 shape: {c09.shape}")
    df = _outer_merge(c05, c09, on=GEO_KEYS)
    print(f"  df_religion assembled: {df.shape[0]} rows × {df.shape[1]} cols")
    return df


def main():
    df_religion = build_df_religion()

    print("\n--- Gender splits ---")
    df_religion_m, df_religion_f = gender_split(df_religion, 'df_religion')

    outputs = {
        'df_religion_state.csv'  : df_religion,
        'df_religion_male.csv'   : df_religion_m,
        'df_religion_female.csv' : df_religion_f,
    }
    save_outputs(outputs)
    print("\nDone — df_religion.")


if __name__ == '__main__':
    main()