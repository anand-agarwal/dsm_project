"""
Append Religion-Specific CMPR to df_religion_state_2001.csv
=============================================================
The original df_religion_state_2001.csv has no CMPR columns.
This script computes them from C-03_Appendix_states.csv (raw 2001 census)
and saves an updated version of the file WITH the CMPR columns appended.

Formula:
    CMPR = (married females/males under 18) / (total females/males under 18) × 1000

Age group used: 'Less than 18' → maps to age_14_17 bracket in your pipeline.

HOW TO RUN:
    python3 append_religion_cmpr_2001.py

Output:
    output_datasets_2001/df_religion_state_2001.csv  ← updated IN PLACE
"""

import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────────
REL_PATH_2001     = '/Users/anandagarwal/dsm_project/output_datasets_2001_new/df_religion_state.csv'
RAW_2001_APPENDIX = '/Users/anandagarwal/dsm_project/raw_data/2001/C-03_Appendix_states.csv'


def compute_religion_cmpr_2001(raw_path):
    """
    Compute religion-specific CMPR per 1000 from C-03_Appendix_states.csv.
    Returns wide DataFrame: state_code + CMPR_{religion}_{female/male} columns.
    """
    df_raw = pd.read_csv(raw_path)

    religions = ['Hindu', 'Muslim', 'Christian', 'Sikh', 'Buddhist', 'Jain']

    df_f = df_raw[
        (df_raw['Total/ | Rural/ | Urban/'] == 'Total') &
        (df_raw['Age- | group | 1'] == 'Less than 18') &
        (df_raw['Religion'].isin(religions))
    ].copy()

    df_f['state_code'] = df_f['State | Code'].astype(int)
    df_f['CMPR_female'] = (df_f['Females | 10'] / df_f['Females | 4'] * 1000).round(4)
    df_f['CMPR_male']   = (df_f['Males | 9']    / df_f['Males | 3']   * 1000).round(4)
    df_f['rel'] = df_f['Religion'].str.lower()

    cmpr_wide = df_f.pivot_table(
        index='state_code', columns='rel',
        values=['CMPR_female', 'CMPR_male'], aggfunc='first'
    )
    cmpr_wide.columns = [
        f'CMPR_{rel}_{g.split("_")[1]}' for g, rel in cmpr_wide.columns
    ]
    return cmpr_wide.reset_index()


def main():
    print("\n" + "="*60)
    print("  Appending Religion CMPR to df_religion_state_2001.csv")
    print("="*60)

    # ── Load original file ──────────────────────────────────────────────────
    df_rel = pd.read_csv(REL_PATH_2001)
    print(f"\n  Original file: {REL_PATH_2001}")
    print(f"  Shape: {df_rel.shape}")
    print(f"  Columns ({len(df_rel.columns)}): {df_rel.columns.tolist()}")

    # ── Check for existing CMPR columns ────────────────────────────────────
    existing_cmpr = [c for c in df_rel.columns if c.startswith('CMPR_')]
    if existing_cmpr:
        print(f"\n  ⚠  File already has CMPR columns: {existing_cmpr}")
        print("  These will be replaced with freshly computed values.")
        df_rel = df_rel.drop(columns=existing_cmpr)

    # ── Compute CMPR ────────────────────────────────────────────────────────
    print(f"\n  Computing CMPR from: {RAW_2001_APPENDIX}")
    cmpr_wide = compute_religion_cmpr_2001(RAW_2001_APPENDIX)

    cmpr_cols = [c for c in cmpr_wide.columns if c != 'state_code']
    print(f"\n  CMPR columns computed ({len(cmpr_cols)}):")
    for c in sorted(cmpr_cols):
        print(f"    {c}")

    # ── Merge ───────────────────────────────────────────────────────────────
    df_updated = df_rel.merge(cmpr_wide, on='state_code', how='left')

    # Verify merge quality
    n_matched = df_updated[cmpr_cols[0]].notna().sum()
    n_total   = len(df_updated)
    print(f"\n  Merge result: {n_matched}/{n_total} rows matched on state_code")

    unmatched = df_updated[df_updated[cmpr_cols[0]].isna()]['state_name'].unique()
    if len(unmatched) > 0:
        print(f"  ⚠  Unmatched state_names (no CMPR computed): {list(unmatched)}")

    # ── Save updated file ───────────────────────────────────────────────────
    df_updated.to_csv(REL_PATH_2001, index=False)

    print(f"\n  ✓ Updated file saved: {REL_PATH_2001}")
    print(f"  New shape: {df_updated.shape}")
    print(f"  New columns ({len(df_updated.columns)}):")
    print(f"    {df_updated.columns.tolist()}")

    # ── Sanity check: show a few CMPR values ───────────────────────────────
    print("\n  Sample CMPR values (age_14_17, first 5 states):")
    sample = df_updated[
        df_updated['age_bracket'] == 'age_14_17'
    ][['state_name'] + sorted(cmpr_cols)].head(5)
    print(sample.to_string(index=False))

    print("\n" + "="*60)
    print("  Done. Updated file saved in place.")
    print("="*60)


if __name__ == '__main__':
    main()