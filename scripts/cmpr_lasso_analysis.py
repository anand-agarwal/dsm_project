"""
Age-wise CMPR LASSO analysis for the new gender-wise 2011 datasets.

What this script does
---------------------
1. Loads the gender-specific CSV files from output_datasets_new_2011.
2. Builds separate LASSO models for each dataset, gender, and age bracket.
3. Uses only one target column per file:
   - SC female  -> CMPR_SC_female
   - SC male    -> CMPR_SC_male
   - ST female  -> CMPR_ST_female
   - ST male    -> CMPR_ST_male
   - Total female -> CMPR_total_female
   - Total male   -> CMPR_total_male
4. For each age bracket, automatically skips predictor columns that are:
   - entirely missing for that bracket
   - too sparse to be usable
   - constant after filtering
   - causing the usable sample to drop below the minimum row threshold
5. Saves age-wise coefficient plots, heatmaps, model-performance plots,
   and a summary CSV.
"""

import os
import sys
import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import Lasso, LassoCV
from sklearn.metrics import r2_score
from sklearn.model_selection import LeaveOneOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")


DATA_DIR = "/Users/anandagarwal/dsm_project/output_datasets_2011_new"
OUT_DIR = "regression_outputs_2001/lasso_agewise"

GEO_COLS = ["state_name", "age_bracket", "state_code"]
AGE_BRACKETS = [
    "age_below10",
    "age_10_13",
    "age_14_17",
    "age_18_21",
    "age_22_25",
    "age_26_29",
    "age_30_33",
    "age_34_plus",
]

DATASETS = {
    "SC": {
        "female": os.path.join(DATA_DIR, "df_SC_female.csv"),
        "male": os.path.join(DATA_DIR, "df_SC_male.csv"),
        "target_prefix": "CMPR_SC",
    },
    "ST": {
        "female": os.path.join(DATA_DIR, "df_ST_female.csv"),
        "male": os.path.join(DATA_DIR, "df_ST_male.csv"),
        "target_prefix": "CMPR_ST",
    },
    "Total": {
        "female": os.path.join(DATA_DIR, "df_total_female.csv"),
        "male": os.path.join(DATA_DIR, "df_total_male.csv"),
        "target_prefix": "CMPR_total",
    },
}

SHORT_NAMES = {
    "Literacy_rate_SC_female": "Literacy",
    "Illiteracy_rate_SC_female": "Illiteracy",
    "Dropout_rate_SC_female": "Dropout",
    "School_attendance_rate_SC_female": "Attendance",
    "Child_labour_dropout_SC_female": "CL dropout",
    "Child_labour_attending_SC_female": "CL attending",
    "Non_worker_dropout_SC_female": "Non-worker dropout",
    "Below_primary_share_SC_female": "Below primary",
    "Literacy_rate_SC_male": "Literacy",
    "Illiteracy_rate_SC_male": "Illiteracy",
    "Dropout_rate_SC_male": "Dropout",
    "School_attendance_rate_SC_male": "Attendance",
    "Child_labour_dropout_SC_male": "CL dropout",
    "Child_labour_attending_SC_male": "CL attending",
    "Below_primary_share_SC_male": "Below primary",
    "Literacy_rate_ST_female": "Literacy",
    "Illiteracy_rate_ST_female": "Illiteracy",
    "Dropout_rate_ST_female": "Dropout",
    "School_attendance_rate_ST_female": "Attendance",
    "Child_labour_dropout_ST_female": "CL dropout",
    "Child_labour_attending_ST_female": "CL attending",
    "Non_worker_dropout_ST_female": "Non-worker dropout",
    "Below_primary_share_ST_female": "Below primary",
    "Literacy_rate_ST_male": "Literacy",
    "Illiteracy_rate_ST_male": "Illiteracy",
    "Dropout_rate_ST_male": "Dropout",
    "School_attendance_rate_ST_male": "Attendance",
    "Child_labour_dropout_ST_male": "CL dropout",
    "Child_labour_attending_ST_male": "CL attending",
    "Below_primary_share_ST_male": "Below primary",
    "Below_primary_share_total_female": "Below primary share",
    "Illiteracy_rate_total_female": "Illiteracy",
    "Literacy_rate_total_female": "Literacy",
    "Below_primary_share_total_male": "Below primary share",
    "Illiteracy_rate_total_male": "Illiteracy",
    "Literacy_rate_total_male": "Literacy",
    "Graduate_share_SC_female": "Graduate share",
    "Graduate_share_SC_male": "Graduate share",
    "Graduate_share_ST_female": "Graduate share",       
    "Graduate_share_ST_male": "Graduate share",
    "Graduate_share_total_female": "Graduate share",
    "Graduate_share_total_male": "Graduate share"     
}

COLORS = {
    "positive": "#d55a3a",
    "negative": "#2b6ea6",
    "neutral": "#d7d7d7",
    "line": "#444444",
}

MIN_ROWS = 10
MIN_NON_MISSING = 10


def infer_target_column(df, dataset_name, gender):
    expected = f"{DATASETS[dataset_name]['target_prefix']}_{gender}"
    if expected in df.columns:
        return expected
    raise ValueError(f"Target column not found: {expected}")


def infer_predictor_columns(df, target_col):
    predictors = []
    for col in df.columns:
        if col in GEO_COLS or col == target_col:
            continue
        if col == "CMPR_SC_persons" or col == "CMPR_ST_persons":
            continue
        if target_col.startswith("CMPR_total_") and col.startswith("CMPR_"):
            continue
        predictors.append(col)
    return predictors


def filter_predictors_for_bracket(df_bracket, predictor_cols, target_col,
                                  min_rows=MIN_ROWS, min_non_missing=MIN_NON_MISSING):
    eligible = []
    skipped = []

    for col in predictor_cols:
        non_missing = int(df_bracket[col].notna().sum())
        if non_missing == 0:
            skipped.append((col, "all_missing"))
            continue
        if non_missing < min_non_missing:
            skipped.append((col, f"too_sparse_{non_missing}"))
            continue
        if df_bracket[col].dropna().nunique() <= 1:
            skipped.append((col, "constant"))
            continue
        eligible.append(col)

    kept = eligible.copy()
    while kept:
        df_model = df_bracket[[target_col] + kept].dropna()
        if len(df_model) >= min_rows:
            return kept, skipped, df_model

        missing_counts = {
            col: int(df_bracket[col].isna().sum())
            for col in kept
        }
        worst = max(kept, key=lambda c: (missing_counts[c], -df_bracket[c].notna().sum(), c))
        kept.remove(worst)
        skipped.append((worst, "dropped_to_preserve_rows"))

    df_model = df_bracket[[target_col]].dropna()
    return [], skipped, df_model


def run_lasso_for_bracket(df, dataset_name, gender, bracket, min_rows=MIN_ROWS):
    target_col = infer_target_column(df, dataset_name, gender)
    predictor_candidates = infer_predictor_columns(df, target_col)

    df_bracket = (
        df[(df["age_bracket"] == bracket) & (df["state_name"] != "INDIA")]
        .copy()
        .reset_index(drop=True)
    )

    if df_bracket.empty:
        return {
            "dataset": dataset_name,
            "gender": gender,
            "bracket": bracket,
            "target": target_col,
            "status": "skipped",
            "reason": "no_rows_for_bracket",
        }

    kept_predictors, skipped_predictors, df_model = filter_predictors_for_bracket(
        df_bracket=df_bracket,
        predictor_cols=predictor_candidates,
        target_col=target_col,
        min_rows=min_rows,
    )

    if len(kept_predictors) == 0:
        return {
            "dataset": dataset_name,
            "gender": gender,
            "bracket": bracket,
            "target": target_col,
            "status": "skipped",
            "reason": "no_predictors_left_after_filtering",
            "n_rows": int(len(df_model)),
            "skipped_predictors": skipped_predictors,
        }

    if len(df_model) < min_rows:
        return {
            "dataset": dataset_name,
            "gender": gender,
            "bracket": bracket,
            "target": target_col,
            "status": "skipped",
            "reason": f"too_few_rows_{len(df_model)}",
            "n_rows": int(len(df_model)),
            "used_predictors": kept_predictors,
            "skipped_predictors": skipped_predictors,
        }

    X = df_model[kept_predictors].values
    y = df_model[target_col].values
    n = len(df_model)

    loo = LeaveOneOut()
    alphas = np.logspace(-3, 2, 100)
    model = LassoCV(alphas=alphas, cv=loo, max_iter=20000, random_state=42)
    X_scaled = StandardScaler().fit_transform(X)
    model.fit(X_scaled, y)

    loo_preds = np.empty(n)
    for train_idx, test_idx in loo.split(X):
        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("lasso", Lasso(alpha=model.alpha_, max_iter=20000)),
        ])
        pipe.fit(X[train_idx], y[train_idx])
        loo_preds[test_idx] = pipe.predict(X[test_idx])

    coefs = pd.Series(model.coef_, index=kept_predictors)
    selected = coefs[coefs != 0].sort_values(key=np.abs, ascending=False)

    return {
        "dataset": dataset_name,
        "gender": gender,
        "bracket": bracket,
        "target": target_col,
        "status": "ok",
        "alpha": float(model.alpha_),
        "r2_train": float(model.score(X_scaled, y)),
        "r2_cv": float(r2_score(y, loo_preds)),
        "n_rows": int(n),
        "n_predictors_used": int(len(kept_predictors)),
        "n_selected": int((coefs != 0).sum()),
        "used_predictors": kept_predictors,
        "skipped_predictors": skipped_predictors,
        "coefs": coefs,
        "selected": selected,
    }


def run_agewise_models(df, dataset_name, gender):
    results = {}
    print(f"\n{'=' * 72}")
    print(f"{dataset_name} | {gender}")
    print(f"{'=' * 72}")

    for bracket in AGE_BRACKETS:
        result = run_lasso_for_bracket(df, dataset_name, gender, bracket)
        results[bracket] = result

        if result["status"] != "ok":
            print(f"  {bracket:12s} -> skipped ({result['reason']})")
            continue

        print(
            f"  {bracket:12s} -> n={result['n_rows']:2d}, "
            f"predictors={result['n_predictors_used']:2d}, "
            f"selected={result['n_selected']:2d}, "
            f"alpha={result['alpha']:.4f}, "
            f"R2_train={result['r2_train']:.3f}, R2_cv={result['r2_cv']:.3f}"
        )

        if result["skipped_predictors"]:
            skipped_names = ", ".join(
                f"{SHORT_NAMES.get(col, col)} [{reason}]"
                for col, reason in result["skipped_predictors"]
            )
            print(f"    skipped: {skipped_names}")

        if result["selected"].empty:
            print("    selected predictors: none")
        else:
            selected_names = ", ".join(
                f"{SHORT_NAMES.get(col, col)} ({coef:+.3f})"
                for col, coef in result["selected"].items()
            )
            print(f"    selected predictors: {selected_names}")

    return results


def plot_coefficients_by_bracket(results, dataset_name, gender):
    valid = [results[b] for b in AGE_BRACKETS if results[b]["status"] == "ok"]
    if not valid:
        return None

    n_panels = len(valid)
    ncols = 2
    nrows = int(np.ceil(n_panels / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, max(4 * nrows, 6)))
    axes = np.atleast_1d(axes).flatten()
    fig.patch.set_facecolor("white")

    for ax, result in zip(axes, valid):
        coefs = result["selected"] if not result["selected"].empty else result["coefs"]
        coefs = coefs.sort_values(key=np.abs, ascending=True)
        labels = [SHORT_NAMES.get(col, col) for col in coefs.index]
        colors = [COLORS["positive"] if val > 0 else COLORS["negative"] if val < 0 else COLORS["neutral"]
                  for val in coefs.values]

        ax.barh(np.arange(len(coefs)), coefs.values, color=colors, edgecolor="white")
        ax.axvline(0, color="#888888", linewidth=0.8, linestyle="--")
        ax.set_yticks(np.arange(len(coefs)))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_title(
            f"{result['bracket']} | n={result['n_rows']} | sel={result['n_selected']}",
            fontsize=10,
            fontweight="bold",
        )
        ax.tick_params(axis="x", labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    for ax in axes[n_panels:]:
        ax.axis("off")

    fig.suptitle(
        f"Age-wise LASSO coefficients | {dataset_name} | {gender}\n"
        f"Target: {valid[0]['target']}",
        fontsize=13,
        fontweight="bold",
    )
    plt.tight_layout()
    path = os.path.join(OUT_DIR, f"{dataset_name.lower()}_{gender}_coefficients_by_age.png")
    plt.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  -> Saved {path}")
    return path


def plot_agewise_heatmap(results, dataset_name, gender):
    valid = [results[b] for b in AGE_BRACKETS if results[b]["status"] == "ok"]
    if not valid:
        return None

    all_predictors = []
    for result in valid:
        all_predictors.extend(result["coefs"].index.tolist())
    all_predictors = list(dict.fromkeys(all_predictors))

    mat = pd.DataFrame(index=all_predictors, columns=[r["bracket"] for r in valid], dtype=float)
    for result in valid:
        for predictor, coef in result["coefs"].items():
            mat.loc[predictor, result["bracket"]] = coef

    mat = mat.fillna(0.0)
    mat = mat[(mat != 0).any(axis=1)]
    if mat.empty:
        return None

    mat.index = [SHORT_NAMES.get(idx, idx) for idx in mat.index]
    vmax = max(abs(mat.values.max()), abs(mat.values.min()), 0.5)

    fig, ax = plt.subplots(
        figsize=(max(8, 1.4 * len(mat.columns)), max(4, 0.45 * len(mat.index) + 2))
    )
    fig.patch.set_facecolor("white")
    im = ax.imshow(mat.values, cmap=plt.cm.RdBu_r, aspect="auto", vmin=-vmax, vmax=vmax)

    ax.set_xticks(np.arange(len(mat.columns)))
    ax.set_xticklabels(mat.columns, rotation=30, ha="right", fontsize=9)
    ax.set_yticks(np.arange(len(mat.index)))
    ax.set_yticklabels(mat.index, fontsize=9)
    ax.set_title(
        f"Age-wise coefficient heatmap | {dataset_name} | {gender}",
        fontsize=12,
        fontweight="bold",
    )

    for i in range(len(mat.index)):
        for j in range(len(mat.columns)):
            val = mat.iloc[i, j]
            if val != 0:
                color = "white" if abs(val) > vmax * 0.55 else "#333333"
                ax.text(j, i, f"{val:+.2f}", ha="center", va="center", fontsize=7.5, color=color)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label("Standardised coefficient", fontsize=9)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, f"{dataset_name.lower()}_{gender}_heatmap_by_age.png")
    plt.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  -> Saved {path}")
    return path


def plot_model_performance(results, dataset_name, gender):
    rows = []
    for bracket in AGE_BRACKETS:
        result = results[bracket]
        if result["status"] != "ok":
            continue
        rows.append({
            "bracket": bracket,
            "r2_train": result["r2_train"],
            "r2_cv": result["r2_cv"],
            "n_rows": result["n_rows"],
            "n_selected": result["n_selected"],
            "n_predictors_used": result["n_predictors_used"],
        })

    if not rows:
        return None

    perf = pd.DataFrame(rows)
    x = np.arange(len(perf))

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    fig.patch.set_facecolor("white")

    axes[0].plot(x, perf["r2_train"], marker="o", color="#cf5d3f", label="R2 train")
    axes[0].plot(x, perf["r2_cv"], marker="o", color="#2f6da3", label="R2 CV")
    axes[0].axhline(0, color="#999999", linewidth=0.8, linestyle="--")
    axes[0].set_ylabel("Model fit", fontsize=10)
    axes[0].legend(frameon=False, fontsize=9)
    axes[0].spines["top"].set_visible(False)
    axes[0].spines["right"].set_visible(False)

    width = 0.25
    axes[1].bar(x - width, perf["n_rows"], width=width, color="#4a7f52", label="Rows")
    axes[1].bar(x, perf["n_predictors_used"], width=width, color="#9b7d2f", label="Predictors used")
    axes[1].bar(x + width, perf["n_selected"], width=width, color="#7b5aa6", label="Selected")
    axes[1].set_ylabel("Counts", fontsize=10)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(perf["bracket"], rotation=30, ha="right", fontsize=9)
    axes[1].legend(frameon=False, fontsize=9)
    axes[1].spines["top"].set_visible(False)
    axes[1].spines["right"].set_visible(False)

    fig.suptitle(
        f"Age-wise model performance | {dataset_name} | {gender}",
        fontsize=12,
        fontweight="bold",
    )
    plt.tight_layout()
    path = os.path.join(OUT_DIR, f"{dataset_name.lower()}_{gender}_model_performance.png")
    plt.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  -> Saved {path}")
    return path


def build_summary_table(all_results):
    rows = []
    for dataset_name, gender_dict in all_results.items():
        for gender, results in gender_dict.items():
            for bracket in AGE_BRACKETS:
                result = results[bracket]
                base = {
                    "dataset": dataset_name,
                    "gender": gender,
                    "age_bracket": bracket,
                    "target": result.get("target"),
                    "status": result.get("status"),
                    "reason": result.get("reason", ""),
                    "n_rows": result.get("n_rows", np.nan),
                }
                if result["status"] != "ok":
                    base.update({
                        "alpha": np.nan,
                        "r2_train": np.nan,
                        "r2_cv": np.nan,
                        "n_predictors_used": np.nan,
                        "n_selected": np.nan,
                        "used_predictors": "",
                        "selected_predictors": "",
                        "skipped_predictors": " | ".join(
                            f"{SHORT_NAMES.get(col, col)} [{reason}]"
                            for col, reason in result.get("skipped_predictors", [])
                        ),
                    })
                else:
                    base.update({
                        "alpha": round(result["alpha"], 4),
                        "r2_train": round(result["r2_train"], 3),
                        "r2_cv": round(result["r2_cv"], 3),
                        "n_predictors_used": result["n_predictors_used"],
                        "n_selected": result["n_selected"],
                        "used_predictors": " | ".join(
                            SHORT_NAMES.get(col, col) for col in result["used_predictors"]
                        ),
                        "selected_predictors": " | ".join(
                            f"{SHORT_NAMES.get(col, col)} ({coef:+.3f})"
                            for col, coef in result["selected"].items()
                        ),
                        "skipped_predictors": " | ".join(
                            f"{SHORT_NAMES.get(col, col)} [{reason}]"
                            for col, reason in result["skipped_predictors"]
                        ),
                    })
                rows.append(base)
    return pd.DataFrame(rows)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("\n" + "=" * 72)
    print("AGE-WISE CMPR LASSO ANALYSIS | NEW GENDER-WISE DATASETS")
    print("=" * 72)

    all_results = {}

    for dataset_name, cfg in DATASETS.items():
        all_results[dataset_name] = {}
        for gender in ["female", "male"]:
            path = cfg[gender]
            if not os.path.exists(path):
                print(f"\nMissing file, skipping: {path}")
                continue

            df = pd.read_csv(path)
            all_results[dataset_name][gender] = run_agewise_models(df, dataset_name, gender)
            plot_coefficients_by_bracket(all_results[dataset_name][gender], dataset_name, gender)
            plot_agewise_heatmap(all_results[dataset_name][gender], dataset_name, gender)
            plot_model_performance(all_results[dataset_name][gender], dataset_name, gender)

    summary = build_summary_table(all_results)
    summary_path = os.path.join(OUT_DIR, "lasso_agewise_summary.csv")
    summary.to_csv(summary_path, index=False)

    print(f"\nSaved summary: {summary_path}")
    print("\n" + summary.to_string(index=False))
    print("\n" + "=" * 72)
    print(f"All outputs saved to {OUT_DIR}")
    print("=" * 72)


if __name__ == "__main__":
    os.makedirs("regression_outputs", exist_ok=True)

    log_path = os.path.join(
        "regression_outputs",
        f"lasso_agewise_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
    )

    with open(log_path, "w") as handle:
        original_stdout = sys.stdout
        sys.stdout = handle
        try:
            main()
        finally:
            sys.stdout = original_stdout

    print(f"Log saved to: {log_path}")
