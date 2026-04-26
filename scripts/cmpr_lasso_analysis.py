"""
CMPR LASSO Analysis — 2001 vs 2011 Comparison Framework
=========================================================
This script runs LASSO regression separately on each year's data,
then produces a side-by-side comparison of which predictors changed.

Key notes:
  1. Religion CMPR for 2001 is pre-computed — run append_religion_cmpr_2001.py
     once to update df_religion_state_2001.csv before running this script.
  2. Religion CONFIGS use group-specific targets (CMPR_hindu_female etc.)
  3. R²_cv is computed via manual LOO to avoid sklearn NaN propagation.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from sklearn.linear_model import LassoCV, Lasso
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import r2_score
from sklearn.pipeline import Pipeline
import warnings
warnings.filterwarnings('ignore')
import sys
import os
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────────

# 2001 files
SC_PATH_2001      = 'output_datasets_2001/df_SC_state_2001.csv'
ST_PATH_2001      = 'output_datasets_2001/df_ST_state_2001.csv'
REL_PATH_2001     = 'output_datasets_2001/df_religion_state_2001.csv'

# 2011 files
SC_PATH_2011      = 'output_datasets_2011/df_SC_state_2011.csv'
ST_PATH_2011      = 'output_datasets_2011/df_ST_state_2011.csv'
REL_PATH_2011     = 'output_datasets_2011/df_religion_state_2011.csv'
TOTAL_PATH_2011   = 'output_datasets_2011/df_total_state_2011.csv'

# Total population files
TOTAL_PATH_2001   = 'output_datasets_2001/df_total_state_2001.csv'

OUT_DIR = 'regression_outputs/lasso/'

# ── Predictor / target config per dataset ─────────────────────────────────────
CONFIGS = {
    'SC': {
        'predictors': [
            'Literacy_rate_SC_female', 'Literacy_rate_SC_male',
            'Illiteracy_rate_SC_female', 'Illiteracy_rate_SC_male',
            'Dropout_rate_SC_female', 'Dropout_rate_SC_male',
            'School_attendance_rate_SC_female', 'School_attendance_rate_SC_male',
            'Child_labour_dropout_SC_female', 'Child_labour_dropout_SC_male',
            'Child_labour_attending_SC_female', 'Child_labour_attending_SC_male',
            'Non_worker_dropout_SC_female',
            'Below_primary_share_SC_female', 'Below_primary_share_SC_male',
        ],
        'targets': {'female': 'CMPR_SC_female', 'male': 'CMPR_SC_male'},
    },
    'ST': {
        'predictors': [
            'Literacy_rate_ST_female', 'Literacy_rate_ST_male',
            'Illiteracy_rate_ST_female', 'Illiteracy_rate_ST_male',
            'Dropout_rate_ST_female', 'Dropout_rate_ST_male',
            'School_attendance_rate_ST_female', 'School_attendance_rate_ST_male',
            'Child_labour_dropout_ST_female', 'Child_labour_dropout_ST_male',
            'Child_labour_attending_ST_female', 'Child_labour_attending_ST_male',
            'Non_worker_dropout_ST_female',
            'Below_primary_share_ST_female', 'Below_primary_share_ST_male',
        ],
        'targets': {'female': 'CMPR_ST_female', 'male': 'CMPR_ST_male'},
    },
    'Hindu': {
        'predictors': [
            'Literacy_rate_hindu_female', 'Literacy_rate_hindu_male',
            'Illiteracy_rate_hindu_female', 'Illiteracy_rate_hindu_male',
            'Below_primary_share_hindu_female', 'Middle_school_share_hindu_female',
        ],
        'targets': {'female': 'CMPR_hindu_female', 'male': 'CMPR_hindu_male'},
    },
    'Muslim': {
        'predictors': [
            'Literacy_rate_muslim_female', 'Literacy_rate_muslim_male',
            'Illiteracy_rate_muslim_female', 'Illiteracy_rate_muslim_male',
            'Below_primary_share_muslim_female', 'Middle_school_share_muslim_female',
        ],
        'targets': {'female': 'CMPR_muslim_female', 'male': 'CMPR_muslim_male'},
    },
    'Christian': {
        'predictors': [
            'Literacy_rate_christian_female', 'Literacy_rate_christian_male',
            'Illiteracy_rate_christian_female', 'Illiteracy_rate_christian_male',
            'Below_primary_share_christian_female', 'Middle_school_share_christian_female',
        ],
        'targets': {'female': 'CMPR_christian_female', 'male': 'CMPR_christian_male'},
    },
    'Total': {
        # Predictors restricted to columns present in BOTH 2001 and 2011.
        # 2011 is missing Child_labour_*, Dropout_rate_*, School_attendance_rate_*,
        # and Non_worker_dropout_* — so those are excluded here.
        'predictors': [
            'Literacy_rate_total_female', 'Literacy_rate_total_male',
            'Illiteracy_rate_total_female', 'Illiteracy_rate_total_male',
            'Below_primary_share_total_female', 'Below_primary_share_total_male',
        ],
        'targets': {'female': 'CMPR_total_female', 'male': 'CMPR_total_male'},
    },
}

# Short display names for predictors (used in plots)
SHORT_NAMES = {
    'Literacy_rate_SC_female':              'Literacy (SC F)',
    'Literacy_rate_SC_male':                'Literacy (SC M)',
    'Illiteracy_rate_SC_female':            'Illiteracy (SC F)',
    'Illiteracy_rate_SC_male':              'Illiteracy (SC M)',
    'Dropout_rate_SC_female':               'Dropout (SC F)',
    'Dropout_rate_SC_male':                 'Dropout (SC M)',
    'School_attendance_rate_SC_female':     'Attendance (SC F)',
    'School_attendance_rate_SC_male':       'Attendance (SC M)',
    'Child_labour_dropout_SC_female':       'CL dropout (SC F)',
    'Child_labour_dropout_SC_male':         'CL dropout (SC M)',
    'Child_labour_attending_SC_female':     'CL attending (SC F)',
    'Child_labour_attending_SC_male':       'CL attending (SC M)',
    'Non_worker_dropout_SC_female':         'Non-worker dropout (F)',
    'Below_primary_share_SC_female':        'Below primary (SC F)',
    'Below_primary_share_SC_male':          'Below primary (SC M)',
    'Literacy_rate_ST_female':              'Literacy (ST F)',
    'Literacy_rate_ST_male':                'Literacy (ST M)',
    'Illiteracy_rate_ST_female':            'Illiteracy (ST F)',
    'Illiteracy_rate_ST_male':              'Illiteracy (ST M)',
    'Dropout_rate_ST_female':               'Dropout (ST F)',
    'Dropout_rate_ST_male':                 'Dropout (ST M)',
    'School_attendance_rate_ST_female':     'Attendance (ST F)',
    'School_attendance_rate_ST_male':       'Attendance (ST M)',
    'Child_labour_dropout_ST_female':       'CL dropout (ST F)',
    'Child_labour_dropout_ST_male':         'CL dropout (ST M)',
    'Child_labour_attending_ST_female':     'CL attending (ST F)',
    'Child_labour_attending_ST_male':       'CL attending (ST M)',
    'Non_worker_dropout_ST_female':         'Non-worker dropout (F)',
    'Below_primary_share_ST_female':        'Below primary (ST F)',
    'Below_primary_share_ST_male':          'Below primary (ST M)',
    'Literacy_rate_hindu_female':           'Literacy (Hindu F)',
    'Literacy_rate_hindu_male':             'Literacy (Hindu M)',
    'Illiteracy_rate_hindu_female':         'Illiteracy (Hindu F)',
    'Illiteracy_rate_hindu_male':           'Illiteracy (Hindu M)',
    'Below_primary_share_hindu_female':     'Below primary (Hindu F)',
    'Middle_school_share_hindu_female':     'Middle school (Hindu F)',
    'Literacy_rate_muslim_female':          'Literacy (Muslim F)',
    'Literacy_rate_muslim_male':            'Literacy (Muslim M)',
    'Illiteracy_rate_muslim_female':        'Illiteracy (Muslim F)',
    'Illiteracy_rate_muslim_male':          'Illiteracy (Muslim M)',
    'Below_primary_share_muslim_female':    'Below primary (Muslim F)',
    'Middle_school_share_muslim_female':    'Middle school (Muslim F)',
    'Literacy_rate_christian_female':       'Literacy (Christian F)',
    'Literacy_rate_christian_male':         'Literacy (Christian M)',
    'Illiteracy_rate_christian_female':     'Illiteracy (Christian F)',
    'Illiteracy_rate_christian_male':       'Illiteracy (Christian M)',
    'Below_primary_share_christian_female': 'Below primary (Christian F)',
    'Middle_school_share_christian_female': 'Middle school (Christian F)',
    'Literacy_rate_total_female':           'Literacy (Total F)',
    'Literacy_rate_total_male':             'Literacy (Total M)',
    'Illiteracy_rate_total_female':         'Illiteracy (Total F)',
    'Illiteracy_rate_total_male':           'Illiteracy (Total M)',
    'Below_primary_share_total_female':     'Below primary (Total F)',
    'Below_primary_share_total_male':       'Below primary (Total M)',
}


# ── Core LASSO function ────────────────────────────────────────────────────────

def run_lasso(df_year, predictors, target, bracket='age_14_17',
              year_label='Year', cv_strategy='loo'):
    """
    Fit LassoCV on one year's data for a given target and bracket.

    Parameters
    ----------
    df_year      : DataFrame for one census year
    predictors   : list of predictor column names
    target       : target column name string
    bracket      : age bracket to filter on
    year_label   : string label for this year (e.g. '2001' or '2011')
    cv_strategy  : 'loo' for Leave-One-Out (best for n<40), or integer k for k-fold

    Returns
    -------
    dict with keys: alpha, r2_train, r2_cv, coefs (Series), n, year_label, target
    """
    df = df_year[
        (df_year['age_bracket'] == bracket) &
        (df_year['state_name'] != 'INDIA')
    ][predictors + [target]].dropna().reset_index(drop=True)

    if len(df) < 10:
        print(f"  ⚠ {year_label} {target}: only {len(df)} rows after dropna — skipping")
        return None

    X = df[predictors].values
    y = df[target].values
    n = len(df)

    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X)

    # LOO is best for small n; fall back to it if n < 40 regardless of setting
    cv = LeaveOneOut() if (cv_strategy == 'loo' or n < 40) else cv_strategy

    # Fit LassoCV
    alphas = np.logspace(-3, 2, 100)
    lasso = LassoCV(alphas=alphas, cv=cv, max_iter=20000, random_state=42)
    lasso.fit(X_sc, y)

    # CV R² — computed manually via LOO to avoid sklearn's NaN propagation.

    loo = LeaveOneOut()
    loo_preds = np.empty(n)
    for train_idx, test_idx in loo.split(X):
        pipe = Pipeline([
            ('scaler', StandardScaler()),
            ('lasso',  Lasso(alpha=lasso.alpha_, max_iter=20000))
        ])
        pipe.fit(X[train_idx], y[train_idx])
        loo_preds[test_idx] = pipe.predict(X[test_idx])
    # r2_score on the full vector is equivalent to LOO-R² and never NaNs
    r2_cv = float(r2_score(y, loo_preds))

    coefs = pd.Series(lasso.coef_, index=predictors)

    return {
        'year_label': year_label,
        'target':     target,
        'bracket':    bracket,
        'alpha':      lasso.alpha_,
        'r2_train':   lasso.score(X_sc, y),
        'r2_cv':      r2_cv,
        'coefs':      coefs,
        'n':          n,
        'n_selected': (coefs != 0).sum(),
        'selected':   coefs[coefs != 0].sort_values(key=abs, ascending=False),
    }


# ── Year comparison function ───────────────────────────────────────────────────

def run_year_comparison(df_2001, df_2011, dataset='SC', bracket='age_14_17'):
    """
    Run LASSO on both years and compare which predictors changed.
    """
    cfg = CONFIGS[dataset]
    predictors = cfg['predictors']
    results = {}

    print(f"\n{'='*60}")
    print(f"  LASSO — {dataset} dataset | bracket: {bracket}")
    print(f"{'='*60}")

    for gender, target in cfg['targets'].items():
        print(f"\n  Target: {target}")
        r01 = run_lasso(df_2001, predictors, target, bracket, year_label='2001')
        r11 = run_lasso(df_2011, predictors, target, bracket, year_label='2011')

        if r01 and r11:
            results[gender] = {'2001': r01, '2011': r11}
            _print_comparison(r01, r11)

    return results


def _print_comparison(r01, r11):
    """Print a text summary of what changed between years."""
    sel01 = set(r01['selected'].index)
    sel11 = set(r11['selected'].index)

    gained = sel11 - sel01
    lost   = sel01 - sel11
    kept   = sel01 & sel11

    print(f"\n    2001: α={r01['alpha']:.4f}, R²_train={r01['r2_train']:.3f}, "
          f"R²_cv={r01['r2_cv']:.3f}, n={r01['n']}, selected={r01['n_selected']}")
    print(f"    2011: α={r11['alpha']:.4f}, R²_train={r11['r2_train']:.3f}, "
          f"R²_cv={r11['r2_cv']:.3f}, n={r11['n']}, selected={r11['n_selected']}")

    # Flag null results — α at ceiling means LASSO zeroed everything out.
    # This indicates the predictors have no explanatory power for this
    # target in that year, not a code error.
    for label, r in [('2001', r01), ('2011', r11)]:
        if r['alpha'] >= 99.9 and r['n_selected'] == 0:
            print(f"    ⚠  {label}: α hit ceiling (100) — LASSO zeroed all predictors. "
                  f"No explanatory power detected for {r['target']} in {label}. "
                  f"Check target variance or consider dropping this group-year.")

    if kept:
        print(f"\n    ✓ Persistent drivers (both years):")
        for p in kept:
            c01, c11 = r01['coefs'][p], r11['coefs'][p]
            direction = '↑ stronger' if abs(c11) > abs(c01) else '↓ weaker'
            print(f"      {SHORT_NAMES.get(p,p):35s}  2001:{c01:+.3f}  2011:{c11:+.3f}  {direction}")

    if gained:
        print(f"\n    + Emerged in 2011 (new drivers):")
        for p in gained:
            print(f"      {SHORT_NAMES.get(p,p):35s}  2011:{r11['coefs'][p]:+.3f}")

    if lost:
        print(f"\n    - Dropped out in 2011 (no longer significant):")
        for p in lost:
            print(f"      {SHORT_NAMES.get(p,p):35s}  2001:{r01['coefs'][p]:+.3f}")


# ── Plotting ───────────────────────────────────────────────────────────────────

COLORS = {
    'pos_2001': '#D05538',
    'neg_2001': '#1D6A9E',
    'pos_2011': '#E8A020',
    'neg_2011': '#2E9E6A',
    'zeroed':   '#CCCCCC',
    'gained':   '#2E9E6A',
    'lost':     '#D05538',
    'kept':     '#5555AA',
}


def plot_coefficient_comparison(results_dict, dataset='SC', gender='female',
                                 title_suffix=''):
    """
    Side-by-side horizontal bar chart: 2001 coefficients vs 2011 coefficients.
    Blue = protective (negative), Red = risk factor (positive).
    Zeroed-out features shown as grey ticks.
    """
    if gender not in results_dict:
        print(f"No results for gender={gender}")
        return

    r01 = results_dict[gender]['2001']
    r11 = results_dict[gender]['2011']
    predictors = r01['coefs'].index.tolist()
    short = [SHORT_NAMES.get(p, p) for p in predictors]

    c01 = r01['coefs'].values
    c11 = r11['coefs'].values

    # Sort by absolute value in 2011 (most important at top)
    order = np.argsort(np.abs(c11))[::-1]
    c01_s = c01[order]
    c11_s = c11[order]
    labels = [short[i] for i in order]

    n = len(labels)
    fig, axes = plt.subplots(1, 2, figsize=(14, max(6, n * 0.45 + 1.5)),
                              sharey=True)
    fig.patch.set_facecolor('white')

    target_name = r01['target']
    fig.suptitle(
        f"LASSO coefficients — {target_name} ({r01['bracket']}){title_suffix}\n"
        f"Standardised predictors — bar width = effect size on CMPR",
        fontsize=12, fontweight='bold', y=1.01
    )

    y_pos = np.arange(n)

    for ax, coefs, year, r in zip(axes, [c01_s, c11_s], ['2001', '2011'], [r01, r11]):
        colors = [COLORS['neg_2001'] if (c < 0 and year == '2001') else
                  COLORS['pos_2001'] if (c > 0 and year == '2001') else
                  COLORS['neg_2011'] if (c < 0 and year == '2011') else
                  COLORS['pos_2011'] if (c > 0 and year == '2011') else
                  COLORS['zeroed']
                  for c in coefs]

        bars = ax.barh(y_pos, coefs, color=colors, edgecolor='white',
                       linewidth=0.5, height=0.65)

        for i, c in enumerate(coefs):
            if c == 0:
                ax.plot([0, 0.001], [i, i], color=COLORS['zeroed'],
                        linewidth=2, solid_capstyle='round')

        ax.axvline(0, color='#888888', linewidth=0.8, linestyle='--')
        ax.set_title(
            f"{year}\n"
            f"α = {r['alpha']:.4f}  |  R² train = {r['r2_train']:.2f}"
            f"  |  R² CV = {r['r2_cv']:.2f}  |  n = {r['n']}",
            fontsize=9, pad=8
        )
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel('Standardised coefficient', fontsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(axis='x', labelsize=8)

        for i, (bar, c) in enumerate(zip(bars, coefs)):
            if c != 0:
                ha = 'left' if c > 0 else 'right'
                offset = 0.03 if c > 0 else -0.03
                ax.text(c + offset, i, f'{c:+.2f}',
                        va='center', ha=ha, fontsize=7.5, color='#333333')

    axes[0].invert_xaxis()

    legend_elements = [
        mpatches.Patch(color=COLORS['neg_2001'], label='Protective (−)'),
        mpatches.Patch(color=COLORS['pos_2001'], label='Risk factor (+)'),
        mpatches.Patch(color=COLORS['zeroed'],   label='Zeroed by LASSO'),
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=3,
               fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.04))

    plt.tight_layout()
    fname = f'{OUT_DIR}lasso_{dataset}_{gender}_comparison.png'
    plt.savefig(fname, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  → Saved: {fname}")
    return fname


def plot_change_summary(results_dict, dataset='SC', gender='female'):
    """
    Single chart showing ONLY the changes between 2001 and 2011:
    - Green: gained significance in 2011
    - Red:   lost significance in 2011
    - Blue:  persistent but coefficient changed size
    """
    if gender not in results_dict:
        return

    r01 = results_dict[gender]['2001']
    r11 = results_dict[gender]['2011']
    c01 = r01['coefs']
    c11 = r11['coefs']

    change = c11 - c01
    status = []
    for p in c01.index:
        if c01[p] == 0 and c11[p] != 0:
            status.append('gained')
        elif c01[p] != 0 and c11[p] == 0:
            status.append('lost')
        elif c01[p] != 0 and c11[p] != 0:
            status.append('kept')
        else:
            status.append('zeroed_both')

    df_plot = pd.DataFrame({
        'predictor': [SHORT_NAMES.get(p, p) for p in c01.index],
        'coef_2001': c01.values,
        'coef_2011': c11.values,
        'change':    change.values,
        'status':    status,
    })
    df_plot = df_plot[df_plot['status'] != 'zeroed_both'].sort_values(
        'change', key=abs, ascending=True)

    if len(df_plot) == 0:
        print(f"  No changes to plot for {dataset} {gender}")
        return

    n = len(df_plot)
    fig, ax = plt.subplots(figsize=(10, max(4, n * 0.5 + 1.5)))
    fig.patch.set_facecolor('white')

    palette = {'gained': COLORS['gained'], 'lost': COLORS['lost'], 'kept': COLORS['kept']}
    bar_colors = [palette[s] for s in df_plot['status']]

    y_pos = np.arange(len(df_plot))
    bars = ax.barh(y_pos, df_plot['change'], color=bar_colors,
                   edgecolor='white', linewidth=0.5, height=0.65)

    ax.axvline(0, color='#888888', linewidth=0.8, linestyle='--')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(df_plot['predictor'], fontsize=9)
    ax.set_xlabel('Change in coefficient (2011 − 2001)', fontsize=9)
    ax.set_title(
        f"What changed between 2001 and 2011?\n"
        f"Target: {r01['target']} | bracket: {r01['bracket']}",
        fontsize=11, fontweight='bold'
    )
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    for i, (bar, row) in enumerate(zip(bars, df_plot.itertuples())):
        if row.status == 'gained':
            label = f'NEW  2011:{row.coef_2011:+.2f}'
        elif row.status == 'lost':
            label = f'DROPPED  2001:{row.coef_2001:+.2f}'
        else:
            label = f'2001:{row.coef_2001:+.2f} → 2011:{row.coef_2011:+.2f}'
        ha = 'left' if row.change >= 0 else 'right'
        offset = 0.03 if row.change >= 0 else -0.03
        ax.text(row.change + offset, i, label, va='center', ha=ha,
                fontsize=7.5, color='#333333')

    legend_elements = [
        mpatches.Patch(color=COLORS['gained'], label='New driver in 2011'),
        mpatches.Patch(color=COLORS['lost'],   label='Dropped out in 2011'),
        mpatches.Patch(color=COLORS['kept'],   label='Persistent (coefficient changed)'),
    ]
    ax.legend(handles=legend_elements, fontsize=8, frameon=False, loc='lower right')

    plt.tight_layout()
    fname = f'{OUT_DIR}lasso_{dataset}_{gender}_changes.png'
    plt.savefig(fname, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  → Saved: {fname}")
    return fname


def plot_all_datasets_heatmap(all_results, year='2011', gender='female',
                               bracket='age_14_17'):
    """
    Heatmap: rows = predictors, columns = datasets.
    Shows which predictors matter universally vs group-specifically.
    """
    datasets = list(all_results.keys())
    all_preds = []
    coef_matrix = {}

    for ds in datasets:
        if gender not in all_results[ds]:
            continue
        r = all_results[ds][gender][year]
        coef_matrix[ds] = r['coefs']
        all_preds.extend(r['coefs'].index.tolist())

    all_preds = list(dict.fromkeys(all_preds))
    if not all_preds or not coef_matrix:
        return

    mat = pd.DataFrame(index=all_preds, columns=list(coef_matrix.keys()))
    for ds, coefs in coef_matrix.items():
        for p in all_preds:
            mat.loc[p, ds] = coefs.get(p, 0.0)
    mat = mat.astype(float)
    mat = mat[(mat != 0).any(axis=1)]
    mat.index = [SHORT_NAMES.get(p, p) for p in mat.index]

    if mat.empty:
        print("  Heatmap: no non-zero coefficients across datasets")
        return

    fig, ax = plt.subplots(figsize=(max(8, len(mat.columns) * 1.6),
                                     max(5, len(mat) * 0.45 + 1.5)))
    fig.patch.set_facecolor('white')

    vmax = max(abs(mat.values.max()), abs(mat.values.min()), 0.5)
    cmap = plt.cm.RdBu_r
    im = ax.imshow(mat.values, cmap=cmap, aspect='auto', vmin=-vmax, vmax=vmax)

    ax.set_xticks(range(len(mat.columns)))
    ax.set_xticklabels(mat.columns, fontsize=10, fontweight='bold')
    ax.set_yticks(range(len(mat)))
    ax.set_yticklabels(mat.index, fontsize=9)

    for i in range(len(mat)):
        for j in range(len(mat.columns)):
            val = mat.iloc[i, j]
            if val != 0:
                text_color = 'white' if abs(val) > vmax * 0.6 else '#333333'
                ax.text(j, i, f'{val:+.2f}', ha='center', va='center',
                        fontsize=8, color=text_color, fontweight='500')

    cbar = fig.colorbar(im, ax=ax, shrink=0.7, pad=0.02)
    cbar.set_label('Standardised coefficient', fontsize=9)
    ax.set_title(
        f"LASSO coefficients across groups — {gender.upper()} CMPR ({bracket})\n"
        f"Year: {year}  |  Blue = protective  |  Red = risk factor  |  "
        f"White = zeroed by LASSO",
        fontsize=10, fontweight='bold', pad=12
    )
    for i in range(len(mat) + 1):
        ax.axhline(i - 0.5, color='white', linewidth=0.5)
    for j in range(len(mat.columns) + 1):
        ax.axvline(j - 0.5, color='white', linewidth=0.5)

    plt.tight_layout()
    fname = f'{OUT_DIR}lasso_heatmap_{year}_{gender}.png'
    plt.savefig(fname, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  → Saved: {fname}")
    return fname


def plot_alpha_path(df_year, predictors, target, bracket='age_14_17',
                    year_label='Year', dataset='SC'):
    """
    Regularisation path: shows how coefficients change as alpha increases.
    Predictors that survive high alpha are the most robust.
    """
    from sklearn.linear_model import lasso_path

    df = df_year[
        (df_year['age_bracket'] == bracket) &
        (df_year['state_name'] != 'INDIA')
    ][predictors + [target]].dropna()

    X = StandardScaler().fit_transform(df[predictors].values)
    y = df[target].values

    alphas, coefs, _ = lasso_path(X, y, alphas=np.logspace(-3, 2, 200),
                                   max_iter=20000)

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor('white')

    cmap_colors = plt.cm.tab20(np.linspace(0, 1, len(predictors)))
    for i, (pred, color) in enumerate(zip(predictors, cmap_colors)):
        if np.any(coefs[i] != 0):
            ax.plot(np.log10(alphas), coefs[i], label=SHORT_NAMES.get(pred, pred),
                    color=color, linewidth=1.5)

    ax.axvline(0, color='#888', linewidth=0.5, linestyle=':')
    ax.axhline(0, color='#888', linewidth=0.5)
    ax.set_xlabel('log₁₀(α)  — higher = more regularisation', fontsize=9)
    ax.set_ylabel('Standardised coefficient', fontsize=9)
    ax.set_title(
        f"Regularisation path — {target} ({bracket}) — {year_label}\n"
        "Predictors that survive high alpha are most robust",
        fontsize=10, fontweight='bold'
    )
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(fontsize=7.5, bbox_to_anchor=(1.01, 1), loc='upper left',
              frameon=False, ncol=1)

    plt.tight_layout()
    fname = f'{OUT_DIR}lasso_path_{dataset}_{year_label}.png'
    plt.savefig(fname, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  → Saved: {fname}")
    return fname


# ── Summary table ──────────────────────────────────────────────────────────────

def build_summary_table(all_results, bracket='age_14_17'):
    """
    DataFrame summarising model performance and selected predictors
    for each dataset × gender × year.
    """
    rows = []
    for dataset, gender_dict in all_results.items():
        for gender, year_dict in gender_dict.items():
            for year, r in year_dict.items():
                selected_names = [SHORT_NAMES.get(p, p) for p in r['selected'].index]
                rows.append({
                    'Dataset':             dataset,
                    'Gender':              gender,
                    'Year':                year,
                    'Target':              r['target'],
                    'Bracket':             r['bracket'],
                    'N':                   r['n'],
                    'Alpha':               round(r['alpha'], 4),
                    'R2_train':            round(r['r2_train'], 3),
                    'R2_cv':               round(r['r2_cv'], 3),
                    'N_selected':          r['n_selected'],
                    'Selected_predictors': ' | '.join(selected_names),
                })
    return pd.DataFrame(rows)


# ── MAIN ───────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*60)
    print("  CMPR LASSO ANALYSIS — 2001 vs 2011")
    print("="*60)

    # ── Load SC and ST ──────────────────────────────────────────────────────
    df_sc_2001    = pd.read_csv(SC_PATH_2001)
    df_sc_2011    = pd.read_csv(SC_PATH_2011)
    df_st_2001    = pd.read_csv(ST_PATH_2001)
    df_st_2011    = pd.read_csv(ST_PATH_2011)
    df_total_2001 = pd.read_csv(TOTAL_PATH_2001)
    df_total_2011 = pd.read_csv(TOTAL_PATH_2011)

    # ── Load religion files ─────────────────────────────────────────────────
    # Both files now have CMPR columns — 2001 was updated by
    # append_religion_cmpr_2001.py, 2011 had them originally.
    df_rel_2001 = pd.read_csv(REL_PATH_2001)
    df_rel_2011 = pd.read_csv(REL_PATH_2011)
    print(f"\n  Religion 2001 CMPR columns: "
          f"{[c for c in df_rel_2001.columns if c.startswith('CMPR_')]}")

    BRACKET = 'age_14_17'
    all_results = {}

    # ── SC ─────────────────────────────────────────────────────────────────
    print("\n[1/6] Running SC models...")
    all_results['SC'] = run_year_comparison(df_sc_2001, df_sc_2011,
                                             dataset='SC', bracket=BRACKET)
    plot_coefficient_comparison(all_results['SC'], dataset='SC', gender='female')
    plot_change_summary(all_results['SC'], dataset='SC', gender='female')
    plot_alpha_path(df_sc_2011, CONFIGS['SC']['predictors'],
                    'CMPR_SC_female', BRACKET, year_label='2011', dataset='SC')

    # ── ST ─────────────────────────────────────────────────────────────────
    print("\n[2/6] Running ST models...")
    all_results['ST'] = run_year_comparison(df_st_2001, df_st_2011,
                                             dataset='ST', bracket=BRACKET)
    plot_coefficient_comparison(all_results['ST'], dataset='ST', gender='female')
    plot_change_summary(all_results['ST'], dataset='ST', gender='female')

    # ── Hindu ──────────────────────────────────────────────────────────────
    print("\n[3/6] Running Hindu models...")
    all_results['Hindu'] = run_year_comparison(df_rel_2001, df_rel_2011,
                                                dataset='Hindu', bracket=BRACKET)
    plot_coefficient_comparison(all_results['Hindu'], dataset='Hindu', gender='female')
    plot_change_summary(all_results['Hindu'], dataset='Hindu', gender='female')

    # ── Muslim ─────────────────────────────────────────────────────────────
    print("\n[4/6] Running Muslim models...")
    all_results['Muslim'] = run_year_comparison(df_rel_2001, df_rel_2011,
                                                 dataset='Muslim', bracket=BRACKET)
    plot_coefficient_comparison(all_results['Muslim'], dataset='Muslim', gender='female')
    plot_change_summary(all_results['Muslim'], dataset='Muslim', gender='female')

    # ── Christian ──────────────────────────────────────────────────────────
    print("\n[5/6] Running Christian models...")
    all_results['Christian'] = run_year_comparison(df_rel_2001, df_rel_2011,
                                                    dataset='Christian', bracket=BRACKET)
    plot_coefficient_comparison(all_results['Christian'], dataset='Christian', gender='female')
    plot_change_summary(all_results['Christian'], dataset='Christian', gender='female')

    # ── Total ──────────────────────────────────────────────────────────────
    print("\n[6/6] Running Total population models...")
    all_results['Total'] = run_year_comparison(df_total_2001, df_total_2011,
                                                dataset='Total', bracket=BRACKET)
    plot_coefficient_comparison(all_results['Total'], dataset='Total', gender='female')
    plot_change_summary(all_results['Total'], dataset='Total', gender='female')
    plot_alpha_path(df_total_2011, CONFIGS['Total']['predictors'],
                    'CMPR_total_female', BRACKET, year_label='2011', dataset='Total')

    # ── Cross-dataset heatmap ───────────────────────────────────────────────
    print("\n[Heatmap] Building cross-dataset coefficient heatmap...")
    plot_all_datasets_heatmap(all_results, year='2011', gender='female',
                               bracket=BRACKET)

    # ── Summary table ───────────────────────────────────────────────────────
    print("\n[Summary table] Writing CSV...")
    summary = build_summary_table(all_results, bracket=BRACKET)
    summary_path = f'{OUT_DIR}lasso_summary_table.csv'
    summary.to_csv(summary_path, index=False)
    print(f"  → Saved: {summary_path}")
    print("\n" + summary.to_string(index=False))

    print("\n" + "="*60)
    print(f"  All outputs saved to {OUT_DIR}")
    print("="*60)


if __name__ == '__main__':
    os.makedirs('regression_outputs', exist_ok=True)

    log_path = f"regression_outputs/lasso_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    with open(log_path, "w") as f:
        original_stdout = sys.stdout
        sys.stdout = f  # redirect prints to file
        try:
            main()
        finally:
            sys.stdout = original_stdout  # restore stdout

    print(f"Log saved to: {log_path}")