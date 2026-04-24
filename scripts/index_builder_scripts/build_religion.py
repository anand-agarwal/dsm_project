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

Indexes produced
----------------
C-05 (age at marriage):
  CMPR_{religion}_male/female
    = currently married in bracket / total ever-married for religion

C-09 (education × religion × current age):
  Literacy_rate_{religion}_male/female
  Illiteracy_rate_{religion}_male/female
  Below_primary_share_{religion}_female
  Middle_school_share_{religion}_female
  Graduate_rate_{religion}_male/female

Coverage notes:
  C-05 age_18_21 bracket   : sums 18-19 and 20-21 rows (exact match)
  C-09 age_18_21 bracket   : sums only ages 18-19; 20-21 inseparable
                              from '20-24' band (partial)
  C-09 age_below10 bracket : sums only ages 7-9 (no 0-6 individual rows)
=============================================================================
"""

import numpy as np
import pandas as pd

from utils import (
    AGE_BRACKETS,
    AGE_BRACKET_MARRIAGE_C05,   # C-05: 2-year bands, age at marriage
    AGE_BRACKET_C09,            # C-09: individual years 7-19, current age
    ALL_AGES_LABEL, ALL_AGES_C09, EXCLUDE_AGES,
    TARGET_RELIGIONS,
    GEO_KEYS,
    _read_excel, _glob_files, _pad_df, _clean_name,
    _rows_for_bracket, _sum_bracket, _make_geo, _outer_merge,
    gender_split, save_outputs,
    safe_div,
)

# Lowercase versions of skip sets — comparisons always happen after .lower()
_SKIP_C05 = {'all religious communities', 'nan', '', 'total'}
_SKIP_C09 = {'all religious communities', 'nan', '', 'total'}


# =============================================================================
# SECTION 1 — C-05   (Religion × Age at Marriage)
# ONE national file; rows cover all states via state_code groups.
#
# Column layout
# -------------
# ever_married_m/f  : total ever-married for this religion × age-at-marriage
#                     cell.  The 'All ages' row gives the religion total.
# curr_m/f_all      : currently married (all marriage durations combined).
#                     This is the numerator for CMPR.
#
# CMPR formula
# ------------
# CMPR_{religion}_{sex} =
#     sum(curr_{sex}_all  for rows in bracket)
#   / sum(ever_married_{sex} for 'All ages' row of same religion)
#   × 100
#
# Denominator is the 'All ages' ever-married total for the religion (not the
# bracket total) so that CMPR represents the fraction of all ever-married
# persons in this religion who are currently married AND were in the given
# age-at-marriage bracket.
# =============================================================================

# In build_religion.py

C05_COLS = [
    'table_name', 'state_code', 'district_code', 'area_type', 'area_name',  # FIXED: swapped area_type ↔ area_name
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

_C05_ALL_AGES = ALL_AGES_LABEL.lower()   # 'all ages'

# ── In build_religion.py ──────────────────────────────────────────────────


def _parse_c05(filepath: str) -> pd.DataFrame:
    raw = _pad_df(_read_excel(filepath), len(C05_COLS))
    raw.columns = C05_COLS
    for col in ['district_code', 'area_type', 'religion',
                'age_at_marriage', 'area_name', 'state_code']:
        raw[col] = raw[col].astype(str).str.strip()
    raw['religion']        = raw['religion'].str.lower()
    raw['age_at_marriage'] = raw['age_at_marriage'].str.lower()
    raw = raw[~raw['age_at_marriage'].isin({e.lower() for e in EXCLUDE_AGES})]
    for c in C05_COLS[7:]:
        raw[c] = pd.to_numeric(raw[c], errors='coerce').fillna(0)
    return raw.reset_index(drop=True)


def build_c05_indexes(dataset_key: str = 'C-05') -> pd.DataFrame:
    files = _glob_files(dataset_key)
    print(f"    {dataset_key}: {len(files)} files (expected 1 national file)")
    if not files:
        return pd.DataFrame()

    fp = files[0]
    try:
        df = _parse_c05(fp)
        # FIXED: filter on area_type (col3 = 'Total'/'Rural'/'Urban')
        df = df[df['area_type'].str.lower() == 'total']
        if df.empty:
            print(f"      [WARN] No rows matched area_type='Total'")
            return pd.DataFrame()
    except Exception as e:
        print(f"      [ERROR] C-05 parse failed: {e}")
        return pd.DataFrame()

    rows = []
    for state_code, state_df in df.groupby('state_code'):
        # FIXED: state name is in area_name (col4), strip 'State - ' prefix
        raw_label = str(state_df['area_name'].iloc[0])
        state_name = _clean_name(raw_label.replace('State - ', '').strip())

        religion_raw_map: dict[str, list] = {}
        for raw_rel in state_df['religion'].unique():
            if raw_rel in _SKIP_C05:
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
                all_row = sub[sub['age_at_marriage'] == _C05_ALL_AGES]
                br_rows = _rows_for_bracket(
                    sub, 'age_at_marriage', bracket, AGE_BRACKET_MARRIAGE_C05)

                if all_row.empty:
                    denom_m = sub['ever_married_m'].sum()
                    denom_f = sub['ever_married_f'].sum()
                else:
                    denom_m = all_row['ever_married_m'].sum()
                    denom_f = all_row['ever_married_f'].sum()

                row[f'CMPR_{target}_male']   = safe_div(
                    br_rows['curr_m_all'].sum(), denom_m)
                row[f'CMPR_{target}_female'] = safe_div(
                    br_rows['curr_f_all'].sum(), denom_f)

            rows.append(row)

    return pd.DataFrame(rows)

# =============================================================================
# SECTION 2 — C-09   (Education × Religion × Age 7+ × Sex)
# ONE national file; rows cover all states via state_code groups.
#
# C-09 stores ages as individual single-year rows (7, 8, 9, 10 … 19) then
# grouped bands (20-24, 25-29, 30-34, 35-59, 60+).  AGE_BRACKET_C09 defines
# which individual years belong to each canonical bracket; _sum_bracket sums
# them.  There is no district_code column — area_type == 'Total' is the
# state-level filter.
#
# age_18_21 NOTE: Only ages 18 and 19 are available as individual rows.
#   Ages 20-21 are embedded in the '20-24' grouped band and cannot be
#   separated.  The bracket is therefore partial for C-09.
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

C09_VALUE_COLS = C09_COLS[6:]

# C-09 uses 'Total' instead of 'All ages' as the age-group total row label
_C09_ALL_AGES = ALL_AGES_C09.lower()   # 'total'


def _nan_religion_c09(row: dict, target: str) -> None:
    """Fill all C-09 metrics for one religion with NaN in-place."""
    for metric in [
        f'Literacy_rate_{target}_male',
        f'Literacy_rate_{target}_female',
        f'Illiteracy_rate_{target}_male',
        f'Illiteracy_rate_{target}_female',
        f'Below_primary_share_{target}_female',
        f'Middle_school_share_{target}_female',
    ]:
        row[metric] = np.nan


def build_c09_indexes(dataset_key: str = 'C-09') -> pd.DataFrame:
    """
    Build per-state, per-bracket literacy / education indexes for each
    religion from C-09.
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
        # State-level rows: C-09 has no district_code; use area_type directly
        raw = raw[raw['area_type'] == 'Total']
        # Lowercase for consistent matching
        raw['religion']  = raw['religion'].str.lower()
        raw['age_group'] = raw['age_group'].str.lower()
        # Drop aggregate age rows before summing individual years
        # ('total'/'all ages' and 'age not stated' rows must not be summed)
        raw = raw[~raw['age_group'].isin(
            {_C09_ALL_AGES} | {e.lower() for e in EXCLUDE_AGES}
        )]
        for c in C09_VALUE_COLS:
            raw[c] = pd.to_numeric(raw[c], errors='coerce').fillna(0)
    except Exception as e:
        print(f"      [ERROR] C-09 parse failed: {e}")
        return pd.DataFrame()

    rows = []
    for state_code, state_df in raw.groupby('state_code'):
        state_name = _clean_name(state_df['area_name'].iloc[0])

        # Build religion label map — religion is already lowercased;
        # skip set is also lowercase to ensure correct exclusion.
        religion_raw_map: dict[str, list] = {}
        for raw_rel in state_df['religion'].unique():
            if raw_rel in _SKIP_C09:
                continue
            for target in TARGET_RELIGIONS:
                if target in raw_rel:
                    religion_raw_map.setdefault(target, []).append(raw_rel)

        for bracket in AGE_BRACKETS:
            row = _make_geo(state_code, state_name, bracket)

            for target in TARGET_RELIGIONS:
                raw_labels = religion_raw_map.get(target, [])
                if not raw_labels:
                    _nan_religion_c09(row, target)
                    continue

                # Filter to this religion, then sum individual-year rows for
                # the bracket using AGE_BRACKET_C09 via _sum_bracket.
                rel_df = state_df[state_df['religion'].isin(raw_labels)]
                agg = _sum_bracket(
                    rel_df, 'age_group', C09_VALUE_COLS, bracket, AGE_BRACKET_C09)

                tot_m   = agg['total_m']
                tot_f   = agg['total_f']
                lit_m   = agg['literate_m']
                lit_f   = agg['literate_f']
                illit_m = agg['illiterate_m']
                illit_f = agg['illiterate_f']
                bp_f    = agg['below_primary_f']
                mid_f   = agg['middle_f']

                row[f'Literacy_rate_{target}_male']         = safe_div(lit_m,   tot_m)
                row[f'Literacy_rate_{target}_female']       = safe_div(lit_f,   tot_f)
                row[f'Illiteracy_rate_{target}_male']       = safe_div(illit_m, tot_m)
                row[f'Illiteracy_rate_{target}_female']     = safe_div(illit_f, tot_f)
                row[f'Below_primary_share_{target}_female'] = safe_div(bp_f,    lit_f)
                row[f'Middle_school_share_{target}_female'] = safe_div(mid_f,   lit_f)
               

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