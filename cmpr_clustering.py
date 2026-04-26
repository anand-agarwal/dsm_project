"""
CMPR Hierarchical Clustering — State Groupings by Child Marriage Drivers
=========================================================================
Complements the LASSO analysis by answering:
  "Which states share the same structural pattern of child marriage drivers?"

Approach:
  - Uses ONLY the predictors LASSO selected as meaningful (not all predictors)
  - Runs separately for 2001 and 2011 to detect if state groupings shifted
  - Ward linkage hierarchical clustering (handles correlated predictors well)
  - Three output types per dataset × year:
      1. Dendrogram — full state tree, colour-coded by cluster
      2. Heatmap — states × predictors, rows ordered by cluster
      3. Cluster profile table — mean predictor values per cluster
  - Final plot: CMPR_total cross-group clustering (SC/ST/Hindu/Muslim/Christian
    CMPR simultaneously) to show inter-group disparity patterns by state

HOW TO RUN:
  python3 cmpr_clustering.py

  Outputs saved to: regression_outputs/clustering/
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from scipy.spatial.distance import pdist
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# ── Paths — must match cmpr_lasso_analysis.py ─────────────────────────────────
SC_PATH_2001      = 'output_datasets_2001/df_SC_state_2001.csv'
ST_PATH_2001      = 'output_datasets_2001/df_ST_state_2001.csv'
REL_PATH_2001     = 'output_datasets_2001/df_religion_state_2001.csv'
TOTAL_PATH_2001   = 'output_datasets_2001/df_total_state_2001.csv'

SC_PATH_2011      = 'output_datasets_2011/df_SC_state_2011.csv'
ST_PATH_2011      = 'output_datasets_2011/df_ST_state_2011.csv'
REL_PATH_2011     = 'output_datasets_2011/df_religion_state_2011.csv'
TOTAL_PATH_2011   = 'output_datasets_2011/df_total_state_2011.csv'

RAW_2001_APPENDIX = 'raw_data/2001/C-03_Appendix_states.csv'

OUT_DIR = 'regression_outputs/clustering/'
os.makedirs(OUT_DIR, exist_ok=True)

BRACKET = 'age_14_17'

# ── LASSO-selected predictors per dataset (from your LASSO results) ────────────
# Only using predictors that LASSO selected in at least one year.
# This avoids clustering on noise variables.
CLUSTER_FEATURES = {
    'SC_female': {
        'path_2001': SC_PATH_2001,
        'path_2011': SC_PATH_2011,
        # Union of selected predictors across both years
        'predictors': [
            'Literacy_rate_SC_female', 'Literacy_rate_SC_male',
            'Below_primary_share_SC_female',
            'Child_labour_attending_SC_female',
            'Child_labour_dropout_SC_male',
            'Illiteracy_rate_SC_female',
        ],
        'target': 'CMPR_SC_female',
        'label': 'SC Female CMPR',
    },
    'SC_male': {
        'path_2001': SC_PATH_2001,
        'path_2011': SC_PATH_2011,
        'predictors': [
            'Literacy_rate_SC_female', 'Below_primary_share_SC_female',
            'Child_labour_attending_SC_female', 'Illiteracy_rate_SC_female',
            'Child_labour_dropout_SC_male', 'Dropout_rate_SC_male',
            'Non_worker_dropout_SC_female',
        ],
        'target': 'CMPR_SC_male',
        'label': 'SC Male CMPR',
    },
    'ST_female': {
        'path_2001': ST_PATH_2001,
        'path_2011': ST_PATH_2011,
        'predictors': [
            'Below_primary_share_ST_female',
            'Child_labour_attending_ST_female',
            'Literacy_rate_ST_female',
            'Dropout_rate_ST_male', 'Dropout_rate_ST_female',
            'Child_labour_attending_ST_male', 'Child_labour_dropout_ST_male',
            'Non_worker_dropout_ST_female',
        ],
        'target': 'CMPR_ST_female',
        'label': 'ST Female CMPR',
    },
    'ST_male': {
        'path_2001': ST_PATH_2001,
        'path_2011': ST_PATH_2011,
        'predictors': [
            'Literacy_rate_ST_female', 'Below_primary_share_ST_female',
            'Dropout_rate_ST_female', 'Child_labour_dropout_ST_female',
        ],
        'target': 'CMPR_ST_male',
        'label': 'ST Male CMPR',
    },
    'Hindu_female': {
        'path_2001': None,   # religion 2001 loaded separately (needs merge)
        'path_2011': REL_PATH_2011,
        'predictors': [
            'Literacy_rate_hindu_female',
            'Middle_school_share_hindu_female',
            'Illiteracy_rate_hindu_female',
        ],
        'target': 'CMPR_hindu_female',
        'label': 'Hindu Female CMPR',
    },
    'Muslim_female': {
        'path_2001': None,
        'path_2011': REL_PATH_2011,
        'predictors': [
            'Below_primary_share_muslim_female',
            'Literacy_rate_muslim_female',
            'Illiteracy_rate_muslim_female',
        ],
        'target': 'CMPR_muslim_female',
        'label': 'Muslim Female CMPR',
    },
    'Christian_female': {
        'path_2001': None,
        'path_2011': REL_PATH_2011,
        'predictors': [
            'Below_primary_share_christian_female',
            'Literacy_rate_christian_female',
            'Middle_school_share_christian_female',
            'Literacy_rate_christian_male',
            'Illiteracy_rate_christian_female',
            'Illiteracy_rate_christian_male',
        ],
        'target': 'CMPR_christian_female',
        'label': 'Christian Female CMPR',
    },
    'Total_female': {
        'path_2001': TOTAL_PATH_2001,
        'path_2011': TOTAL_PATH_2011,
        'predictors': [
            'Literacy_rate_total_female',
            'Illiteracy_rate_total_female',
        ],
        'target': 'CMPR_total_female',
        'label': 'Total Female CMPR',
    },
}

# Short display names for plot axes
SHORT_NAMES = {
    'Literacy_rate_SC_female':              'Literacy (SC F)',
    'Literacy_rate_SC_male':                'Literacy (SC M)',
    'Illiteracy_rate_SC_female':            'Illiteracy (SC F)',
    'Below_primary_share_SC_female':        'Below primary (SC F)',
    'Child_labour_attending_SC_female':     'CL attending (SC F)',
    'Child_labour_dropout_SC_male':         'CL dropout (SC M)',
    'Dropout_rate_SC_male':                 'Dropout (SC M)',
    'Non_worker_dropout_SC_female':         'Non-worker dropout (SC F)',
    'Literacy_rate_ST_female':              'Literacy (ST F)',
    'Below_primary_share_ST_female':        'Below primary (ST F)',
    'Child_labour_attending_ST_female':     'CL attending (ST F)',
    'Dropout_rate_ST_male':                 'Dropout (ST M)',
    'Dropout_rate_ST_female':               'Dropout (ST F)',
    'Child_labour_attending_ST_male':       'CL attending (ST M)',
    'Child_labour_dropout_ST_male':         'CL dropout (ST M)',
    'Child_labour_dropout_ST_female':       'CL dropout (ST F)',
    'Non_worker_dropout_ST_female':         'Non-worker dropout (ST F)',
    'Literacy_rate_hindu_female':           'Literacy (Hindu F)',
    'Middle_school_share_hindu_female':     'Middle school (Hindu F)',
    'Illiteracy_rate_hindu_female':         'Illiteracy (Hindu F)',
    'Below_primary_share_muslim_female':    'Below primary (Muslim F)',
    'Literacy_rate_muslim_female':          'Literacy (Muslim F)',
    'Illiteracy_rate_muslim_female':        'Illiteracy (Muslim F)',
    'Below_primary_share_christian_female': 'Below primary (Christian F)',
    'Literacy_rate_christian_female':       'Literacy (Christian F)',
    'Middle_school_share_christian_female': 'Middle school (Christian F)',
    'Literacy_rate_christian_male':         'Literacy (Christian M)',
    'Illiteracy_rate_christian_female':     'Illiteracy (Christian F)',
    'Illiteracy_rate_christian_male':       'Illiteracy (Christian M)',
    'Literacy_rate_total_female':           'Literacy (Total F)',
    'Illiteracy_rate_total_female':         'Illiteracy (Total F)',
}

# Cluster colours (up to 6 clusters)
CLUSTER_COLORS = ['#D05538', '#1D6A9E', '#2E9E6A', '#E8A020', '#7B52AB', '#888888']


# ── Religion 2001 helper (same as LASSO script) ───────────────────────────────

def load_religion_2001(raw_path, rel_path):
    """Load religion 2001 CSV and merge in CMPR columns from raw census."""
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
    cmpr_wide.columns = [f'CMPR_{rel}_{g.split("_")[1]}' for g, rel in cmpr_wide.columns]
    cmpr_wide = cmpr_wide.reset_index()
    return pd.read_csv(rel_path).merge(cmpr_wide, on='state_code', how='left')


# ── Data preparation ───────────────────────────────────────────────────────────

def prepare_cluster_data(df, predictors, target, bracket=BRACKET):
    """
    Filter to bracket, drop INDIA aggregate, keep only complete rows.
    Returns X (standardised), state names, and raw target values.
    """
    df = df[
        (df['age_bracket'] == bracket) &
        (df['state_name'] != 'INDIA')
    ][['state_name'] + predictors + [target]].dropna().reset_index(drop=True)

    states = df['state_name'].tolist()
    y = df[target].values
    X = StandardScaler().fit_transform(df[predictors].values)
    return X, states, y


# ── Core clustering ───────────────────────────────────────────────────────────

def run_clustering(X, states, n_clusters=3, method='ward'):
    """
    Ward linkage hierarchical clustering.
    Returns: linkage matrix Z, cluster labels (1-indexed), dendrogram order.
    """
    Z = linkage(X, method=method, metric='euclidean')
    labels = fcluster(Z, n_clusters, criterion='maxclust')
    return Z, labels


def choose_n_clusters(X, max_k=6):
    """
    Elbow method on within-cluster sum of squares to suggest n_clusters.
    Returns the suggested k and a list of (k, wcss) pairs.
    """
    wcss = []
    for k in range(2, max_k + 1):
        Z = linkage(X, method='ward')
        labels = fcluster(Z, k, criterion='maxclust')
        centers = np.array([X[labels == c].mean(axis=0) for c in np.unique(labels)])
        ss = sum(
            np.sum((X[labels == c] - centers[i]) ** 2)
            for i, c in enumerate(np.unique(labels))
        )
        wcss.append((k, ss))

    # Simple elbow: largest drop in WCSS
    drops = [(wcss[i][0] + 1, wcss[i][1] - wcss[i + 1][1])
             for i in range(len(wcss) - 1)]
    best_k = max(drops, key=lambda x: x[1])[0]
    return best_k, wcss


# ── Plots ─────────────────────────────────────────────────────────────────────

def plot_dendrogram(Z, states, labels, year, dataset_key, title, n_clusters):
    """Dendrogram with leaves colour-coded by cluster assignment."""
    fig, ax = plt.subplots(figsize=(max(10, len(states) * 0.35 + 2), 6))
    fig.patch.set_facecolor('white')

    # Map each leaf to its cluster colour
    cluster_colors_map = {
        state: CLUSTER_COLORS[(labels[i] - 1) % len(CLUSTER_COLORS)]
        for i, state in enumerate(states)
    }

    def leaf_color_func(leaf_id):
        state = states[leaf_id]
        return cluster_colors_map[state]

    dend = dendrogram(
        Z,
        labels=states,
        ax=ax,
        leaf_rotation=90,
        leaf_font_size=8,
        color_threshold=0,   # disable scipy auto-colouring
        link_color_func=lambda k: '#AAAAAA',
        above_threshold_color='#AAAAAA',
    )

    # Recolour leaf labels by cluster
    for lbl, state in zip(ax.get_xticklabels(), [states[i] for i in dend['leaves']]):
        lbl.set_color(cluster_colors_map[state])
        lbl.set_fontweight('bold')

    ax.set_title(
        f"State Clustering — {title} | {year}\n"
        f"Ward linkage on LASSO-selected predictors  |  {n_clusters} clusters",
        fontsize=11, fontweight='bold'
    )
    ax.set_ylabel('Distance', fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    legend_elements = [
        mpatches.Patch(color=CLUSTER_COLORS[i], label=f'Cluster {i + 1}')
        for i in range(n_clusters)
    ]
    ax.legend(handles=legend_elements, fontsize=8, frameon=False,
              loc='upper right')

    plt.tight_layout()
    fname = f'{OUT_DIR}dendro_{dataset_key}_{year}.png'
    plt.savefig(fname, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"    → Dendrogram saved: {fname}")
    return fname


def plot_cluster_heatmap(df_raw, predictors, states, labels, year,
                          dataset_key, title, target, y):
    """
    Heatmap of standardised predictor values, states ordered by cluster,
    with CMPR values annotated on the right.
    """
    short_preds = [SHORT_NAMES.get(p, p) for p in predictors]

    # Build display dataframe ordered by cluster then CMPR within cluster
    order_df = pd.DataFrame({
        'state': states,
        'cluster': labels,
        'cmpr': y,
    }).sort_values(['cluster', 'cmpr'], ascending=[True, False])

    ordered_states  = order_df['state'].tolist()
    ordered_labels  = order_df['cluster'].tolist()
    ordered_cmpr    = order_df['cmpr'].tolist()

    # Standardised feature matrix in same order
    scaler = StandardScaler()
    X_std = scaler.fit_transform(
        df_raw[predictors].values
    )
    state_to_row = {s: i for i, s in enumerate(states)}
    mat = np.array([X_std[state_to_row[s]] for s in ordered_states])

    n_states, n_feats = mat.shape
    fig, (ax_heat, ax_cmpr) = plt.subplots(
        1, 2,
        figsize=(max(10, n_feats * 1.1 + 3), max(6, n_states * 0.35 + 2)),
        gridspec_kw={'width_ratios': [n_feats, 1]}
    )
    fig.patch.set_facecolor('white')

    vmax = max(abs(mat.max()), abs(mat.min()), 1.0)
    im = ax_heat.imshow(mat, cmap='RdBu_r', aspect='auto',
                         vmin=-vmax, vmax=vmax)

    ax_heat.set_xticks(range(n_feats))
    ax_heat.set_xticklabels(short_preds, rotation=45, ha='right', fontsize=8)
    ax_heat.set_yticks(range(n_states))

    # Y-tick labels coloured by cluster
    yticklabels = ax_heat.set_yticklabels(ordered_states, fontsize=8)
    for lbl, cl in zip(yticklabels, ordered_labels):
        lbl.set_color(CLUSTER_COLORS[(cl - 1) % len(CLUSTER_COLORS)])
        lbl.set_fontweight('bold')

    # Cluster boundary lines
    prev = ordered_labels[0]
    for i, cl in enumerate(ordered_labels):
        if cl != prev:
            ax_heat.axhline(i - 0.5, color='black', linewidth=1.5)
            prev = cl

    cbar = fig.colorbar(im, ax=ax_heat, shrink=0.6, pad=0.01)
    cbar.set_label('Standardised value', fontsize=8)

    # CMPR bar chart on right
    cmpr_colors = [CLUSTER_COLORS[(cl - 1) % len(CLUSTER_COLORS)]
                   for cl in ordered_labels]
    ax_cmpr.barh(range(n_states), ordered_cmpr, color=cmpr_colors,
                  edgecolor='white', linewidth=0.4)
    ax_cmpr.set_yticks([])
    ax_cmpr.set_xlabel('CMPR', fontsize=8)
    ax_cmpr.invert_yaxis()
    ax_cmpr.spines['top'].set_visible(False)
    ax_cmpr.spines['right'].set_visible(False)
    ax_cmpr.tick_params(axis='x', labelsize=7)

    fig.suptitle(
        f"State profiles by cluster — {title} | {year}\n"
        f"Blue = below average  |  Red = above average  |  "
        f"States ordered by cluster then CMPR",
        fontsize=10, fontweight='bold'
    )

    plt.tight_layout()
    fname = f'{OUT_DIR}heatmap_{dataset_key}_{year}.png'
    plt.savefig(fname, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"    → Cluster heatmap saved: {fname}")
    return fname


def plot_elbow(wcss, best_k, dataset_key, year, title):
    """Elbow curve for choosing n_clusters."""
    ks   = [w[0] for w in wcss]
    vals = [w[1] for w in wcss]

    fig, ax = plt.subplots(figsize=(6, 4))
    fig.patch.set_facecolor('white')
    ax.plot(ks, vals, 'o-', color='#1D6A9E', linewidth=2, markersize=6)
    ax.axvline(best_k, color='#D05538', linewidth=1.5, linestyle='--',
               label=f'Suggested k = {best_k}')
    ax.set_xlabel('Number of clusters (k)', fontsize=9)
    ax.set_ylabel('Within-cluster sum of squares', fontsize=9)
    ax.set_title(f'Elbow curve — {title} | {year}', fontsize=10, fontweight='bold')
    ax.legend(fontsize=8, frameon=False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    fname = f'{OUT_DIR}elbow_{dataset_key}_{year}.png'
    plt.savefig(fname, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"    → Elbow curve saved: {fname}")


# ── Cluster profile summary ───────────────────────────────────────────────────

def build_cluster_profile(states, labels, y, df_raw, predictors, target):
    """
    Returns a DataFrame: cluster | n_states | mean_CMPR | mean of each predictor.
    Useful for interpreting what makes each cluster distinct.
    """
    short_preds = [SHORT_NAMES.get(p, p) for p in predictors]
    rows = []
    state_to_idx = {s: i for i, s in enumerate(states)}

    for cl in sorted(np.unique(labels)):
        cl_states = [s for s, l in zip(states, labels) if l == cl]
        cl_cmpr   = [y[i] for i, l in enumerate(labels) if l == cl]
        cl_rows   = df_raw.iloc[[state_to_idx[s] for s in cl_states]]

        row = {
            'Cluster': cl,
            'N_states': len(cl_states),
            'States': ', '.join(sorted(cl_states)),
            f'Mean_{target}': round(np.mean(cl_cmpr), 2),
        }
        for p, sp in zip(predictors, short_preds):
            row[sp] = round(cl_rows[p].mean(), 3)
        rows.append(row)

    return pd.DataFrame(rows)


# ── Cross-group CMPR clustering ───────────────────────────────────────────────

def run_cross_group_clustering(df_rel_2001, df_rel_2011,
                                df_sc_2001, df_sc_2011,
                                df_st_2001, df_st_2011,
                                df_total_2001, df_total_2011):
    """
    Clusters states by their CMPR values across all groups simultaneously:
    SC_female, ST_female, Hindu_female, Muslim_female, Christian_female, Total_female.

    This shows which states have uniform vs disparate child marriage across groups.
    """
    print("\n  [Cross-group] Clustering states by multi-group CMPR profile...")

    cmpr_cols = {
        'CMPR_SC_female':        df_sc_2011,
        'CMPR_ST_female':        df_st_2011,
        'CMPR_hindu_female':     df_rel_2011,
        'CMPR_muslim_female':    df_rel_2011,
        'CMPR_christian_female': df_rel_2011,
        'CMPR_total_female':     df_total_2011,
    }

    dfs = []
    for col, df in cmpr_cols.items():
        sub = df[
            (df['age_bracket'] == BRACKET) &
            (df['state_name'] != 'INDIA')
        ][['state_name', col]].dropna()
        dfs.append(sub.set_index('state_name'))

    merged = pd.concat(dfs, axis=1).dropna()
    states = merged.index.tolist()

    X = StandardScaler().fit_transform(merged.values)
    best_k, wcss = choose_n_clusters(X, max_k=5)
    best_k = max(3, min(best_k, 5))   # clamp between 3 and 5

    Z, labels = run_clustering(X, states, n_clusters=best_k)

    # Plot
    short_cols = {
        'CMPR_SC_female':        'SC F',
        'CMPR_ST_female':        'ST F',
        'CMPR_hindu_female':     'Hindu F',
        'CMPR_muslim_female':    'Muslim F',
        'CMPR_christian_female': 'Christian F',
        'CMPR_total_female':     'Total F',
    }
    merged.columns = [short_cols[c] for c in merged.columns]

    n_states, n_feats = merged.shape
    order_df = pd.DataFrame({
        'state': states, 'cluster': labels,
        'total_cmpr': merged['Total F'].values,
    }).sort_values(['cluster', 'total_cmpr'], ascending=[True, False])

    ordered_states = order_df['state'].tolist()
    ordered_labels = order_df['cluster'].tolist()

    mat = np.array([X[states.index(s)] for s in ordered_states])

    fig, ax = plt.subplots(
        figsize=(max(8, n_feats * 1.4 + 2), max(6, n_states * 0.38 + 2))
    )
    fig.patch.set_facecolor('white')

    vmax = max(abs(mat.max()), abs(mat.min()), 1.0)
    im = ax.imshow(mat, cmap='RdBu_r', aspect='auto', vmin=-vmax, vmax=vmax)

    ax.set_xticks(range(n_feats))
    ax.set_xticklabels(list(merged.columns), fontsize=9, fontweight='bold')
    ax.set_yticks(range(n_states))
    yticklabels = ax.set_yticklabels(ordered_states, fontsize=8)
    for lbl, cl in zip(yticklabels, ordered_labels):
        lbl.set_color(CLUSTER_COLORS[(cl - 1) % len(CLUSTER_COLORS)])
        lbl.set_fontweight('bold')

    # Cluster boundaries
    prev = ordered_labels[0]
    for i, cl in enumerate(ordered_labels):
        if cl != prev:
            ax.axhline(i - 0.5, color='black', linewidth=1.5)
            prev = cl

    # Annotate values
    for i in range(n_states):
        for j in range(n_feats):
            val = mat[i, j]
            tc = 'white' if abs(val) > vmax * 0.55 else '#333333'
            ax.text(j, i, f'{val:+.1f}', ha='center', va='center',
                    fontsize=7, color=tc)

    cbar = fig.colorbar(im, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label('Standardised CMPR', fontsize=8)

    legend_elements = [
        mpatches.Patch(color=CLUSTER_COLORS[i], label=f'Cluster {i+1}')
        for i in range(best_k)
    ]
    ax.legend(handles=legend_elements, fontsize=8, frameon=False,
              bbox_to_anchor=(1.18, 1), loc='upper left')

    ax.set_title(
        "State clusters by female CMPR across all groups — 2011\n"
        "Red = high CMPR  |  Blue = low CMPR  |  "
        "States ordered by cluster then total CMPR",
        fontsize=10, fontweight='bold', pad=12
    )

    plt.tight_layout()
    fname = f'{OUT_DIR}cross_group_cmpr_clusters_2011.png'
    plt.savefig(fname, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"    → Cross-group cluster heatmap saved: {fname}")

    # Print cluster membership
    print(f"\n    Cross-group clusters (k={best_k}):")
    for cl in sorted(np.unique(labels)):
        cl_states = sorted([s for s, l in zip(states, labels) if l == cl])
        print(f"      Cluster {cl}: {', '.join(cl_states)}")

    return labels, states


# ── Main runner ───────────────────────────────────────────────────────────────

def run_one_dataset(cfg_key, cfg, df_2001, df_2011):
    """Run full clustering pipeline for one dataset × both years."""
    print(f"\n  [{cfg_key}]  {cfg['label']}")

    all_profiles = []

    for year, df in [('2001', df_2001), ('2011', df_2011)]:
        # Religion datasets only available as 2001 merged or 2011 direct
        if df is None:
            print(f"    ⚠ {year}: no data available — skipping")
            continue

        predictors = cfg['predictors']
        target     = cfg['target']

        try:
            X, states, y = prepare_cluster_data(df, predictors, target)
        except KeyError as e:
            print(f"    ⚠ {year}: missing column {e} — skipping")
            continue

        if len(states) < 6:
            print(f"    ⚠ {year}: only {len(states)} states after dropna — skipping")
            continue

        # Choose k via elbow
        best_k, wcss = choose_n_clusters(X, max_k=min(6, len(states) - 1))
        best_k = max(2, min(best_k, 4))   # clamp: 2–4 is interpretable
        plot_elbow(wcss, best_k, cfg_key, year, cfg['label'])

        # Run clustering
        Z, labels = run_clustering(X, states, n_clusters=best_k)

        # Plots
        plot_dendrogram(Z, states, labels, year, cfg_key, cfg['label'], best_k)

        # Need raw (unstandardised) df for heatmap predictor means
        df_raw = df[
            (df['age_bracket'] == BRACKET) &
            (df['state_name'] != 'INDIA')
        ][['state_name'] + predictors + [target]].dropna().reset_index(drop=True)

        plot_cluster_heatmap(df_raw, predictors, states, labels,
                              year, cfg_key, cfg['label'], target, y)

        # Cluster profile table
        profile = build_cluster_profile(states, labels, y, df_raw, predictors, target)
        profile.insert(0, 'Year', year)
        profile.insert(0, 'Dataset', cfg_key)
        all_profiles.append(profile)

        # Print summary
        print(f"\n    {year} — k={best_k} clusters:")
        for cl in sorted(np.unique(labels)):
            cl_states = sorted([s for s, l in zip(states, labels) if l == cl])
            cl_cmpr   = np.mean([y[i] for i, l in enumerate(labels) if l == cl])
            print(f"      Cluster {cl} (mean CMPR={cl_cmpr:.1f}): "
                  f"{', '.join(cl_states)}")

    return pd.concat(all_profiles) if all_profiles else pd.DataFrame()


def main():
    print("\n" + "="*60)
    print("  CMPR HIERARCHICAL CLUSTERING — State Groupings")
    print("="*60)

    # ── Load all datasets ───────────────────────────────────────────────────
    df_sc_2001    = pd.read_csv(SC_PATH_2001)
    df_sc_2011    = pd.read_csv(SC_PATH_2011)
    df_st_2001    = pd.read_csv(ST_PATH_2001)
    df_st_2011    = pd.read_csv(ST_PATH_2011)
    df_total_2001 = pd.read_csv(TOTAL_PATH_2001)
    df_total_2011 = pd.read_csv(TOTAL_PATH_2011)
    df_rel_2011   = pd.read_csv(REL_PATH_2011)
    df_rel_2001   = load_religion_2001(RAW_2001_APPENDIX, REL_PATH_2001)

    # Map dataset keys to (df_2001, df_2011) — None means not available
    DATA_MAP = {
        'SC_female':        (df_sc_2001,    df_sc_2011),
        'SC_male':          (df_sc_2001,    df_sc_2011),
        'ST_female':        (df_st_2001,    df_st_2011),
        'ST_male':          (df_st_2001,    df_st_2011),
        'Hindu_female':     (df_rel_2001,   df_rel_2011),
        'Muslim_female':    (df_rel_2001,   df_rel_2011),
        'Christian_female': (df_rel_2001,   df_rel_2011),
        'Total_female':     (df_total_2001, df_total_2011),
    }

    all_profiles = []

    for cfg_key, cfg in CLUSTER_FEATURES.items():
        df_2001, df_2011 = DATA_MAP[cfg_key]
        profile = run_one_dataset(cfg_key, cfg, df_2001, df_2011)
        if not profile.empty:
            all_profiles.append(profile)

    # ── Cross-group CMPR clustering ─────────────────────────────────────────
    print("\n" + "="*60)
    print("  Cross-group CMPR clustering")
    print("="*60)
    run_cross_group_clustering(
        df_rel_2001, df_rel_2011,
        df_sc_2001,  df_sc_2011,
        df_st_2001,  df_st_2011,
        df_total_2001, df_total_2011,
    )

    # ── Save combined profile table ─────────────────────────────────────────
    if all_profiles:
        combined = pd.concat(all_profiles, ignore_index=True)
        profile_path = f'{OUT_DIR}cluster_profiles.csv'
        combined.to_csv(profile_path, index=False)
        print(f"\n  → Cluster profiles saved: {profile_path}")

    print("\n" + "="*60)
    print(f"  All outputs saved to {OUT_DIR}")
    print("="*60)


if __name__ == '__main__':
    main()