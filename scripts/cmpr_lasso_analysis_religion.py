"""
Age-wise CMPR LASSO analysis for the 2011 religion dataset.

What this script does
---------------------
1. Loads the combined religion CSV from output_datasets_2011_new.
2. Builds separate LASSO models for each religion, gender, and age bracket.
3. Uses one CMPR target at a time:
   - CMPR_{religion}_female
   - CMPR_{religion}_male
4. Uses religion-linked education predictors for the same gender only.
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


DATA_PATH = "/Users/anandagarwal/dsm_project/output_datasets_2001_new/df_religion_state.csv"
OUT_DIR = "regression_outputs_2001/religion_lasso_agewise"

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
RELIGIONS = ["buddhist", "christian", "hindu", "jain", "muslim", "sikh"]
GENDERS = ["female", "male"]

COLORS = {
    "positive": "#d55a3a",
    "negative": "#2b6ea6",
    "neutral": "#d7d7d7",
}

MIN_ROWS = 10
MIN_NON_MISSING = 10


def prettify_predictor_name(col):
    label = col
    label = label.replace("Literacy_rate_", "Literacy | ")
    label = label.replace("Illiteracy_rate_", "Illiteracy | ")
    label = label.replace("Below_primary_share_", "Below primary | ")
    label = label.replace("Middle_school_share_", "Middle school | ")
    label = label.replace("_female", " | F")
    label = label.replace("_male", " | M")
    parts = label.split(" | ")
    if len(parts) >= 2:
        parts[1] = parts[1].title()
    return " | ".join(parts)


def target_column(religion, gender):
    return f"CMPR_{religion}_{gender}"


def infer_predictor_columns(df, religion, gender):
    predictors = []
    for col in df.columns:
        if col in GEO_COLS or col.startswith("CMPR_"):
            continue
        if f"_{religion}_" not in col:
            continue
        if not col.endswith(f"_{gender}"):
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


def run_lasso_for_bracket(df, religion, gender, bracket, min_rows=MIN_ROWS):
    target_col = target_column(religion, gender)
    predictor_candidates = infer_predictor_columns(df, religion, gender)

    df_bracket = (
        df[(df["age_bracket"] == bracket) & (df["state_name"] != "INDIA")]
        .copy()
        .reset_index(drop=True)
    )

    if df_bracket.empty:
        return {
            "religion": religion,
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
            "religion": religion,
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
            "religion": religion,
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
        "religion": religion,
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


def run_agewise_models(df, religion, gender):
    results = {}
    print(f"\n{'=' * 72}")
    print(f"{religion.title()} | {gender}")
    print(f"{'=' * 72}")

    for bracket in AGE_BRACKETS:
        result = run_lasso_for_bracket(df, religion, gender, bracket)
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
                f"{prettify_predictor_name(col)} [{reason}]"
                for col, reason in result["skipped_predictors"]
            )
            print(f"    skipped: {skipped_names}")

        if result["selected"].empty:
            print("    selected predictors: none")
        else:
            selected_names = ", ".join(
                f"{prettify_predictor_name(col)} ({coef:+.3f})"
                for col, coef in result["selected"].items()
            )
            print(f"    selected predictors: {selected_names}")

    return results


def plot_coefficients_by_bracket(results, religion, gender):
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
        labels = [prettify_predictor_name(col) for col in coefs.index]
        colors = [
            COLORS["positive"] if val > 0 else COLORS["negative"] if val < 0 else COLORS["neutral"]
            for val in coefs.values
        ]

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
        f"Age-wise LASSO coefficients | {religion.title()} | {gender}\n"
        f"Target: {valid[0]['target']}",
        fontsize=13,
        fontweight="bold",
    )
    plt.tight_layout()
    path = os.path.join(OUT_DIR, f"{religion}_{gender}_coefficients_by_age.png")
    plt.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  -> Saved {path}")
    return path


def plot_agewise_heatmap(results, religion, gender):
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

    mat.index = [prettify_predictor_name(idx) for idx in mat.index]
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
        f"Age-wise coefficient heatmap | {religion.title()} | {gender}",
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
    path = os.path.join(OUT_DIR, f"{religion}_{gender}_heatmap_by_age.png")
    plt.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  -> Saved {path}")
    return path


def plot_model_performance(results, religion, gender):
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
        f"Age-wise model performance | {religion.title()} | {gender}",
        fontsize=12,
        fontweight="bold",
    )
    plt.tight_layout()
    path = os.path.join(OUT_DIR, f"{religion}_{gender}_model_performance.png")
    plt.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  -> Saved {path}")
    return path


def build_summary_table(all_results):
    rows = []
    for religion, gender_dict in all_results.items():
        for gender, results in gender_dict.items():
            for bracket in AGE_BRACKETS:
                result = results[bracket]
                base = {
                    "religion": religion,
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
                            f"{prettify_predictor_name(col)} [{reason}]"
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
                            prettify_predictor_name(col) for col in result["used_predictors"]
                        ),
                        "selected_predictors": " | ".join(
                            f"{prettify_predictor_name(col)} ({coef:+.3f})"
                            for col, coef in result["selected"].items()
                        ),
                        "skipped_predictors": " | ".join(
                            f"{prettify_predictor_name(col)} [{reason}]"
                            for col, reason in result["skipped_predictors"]
                        ),
                    })
                rows.append(base)
    return pd.DataFrame(rows)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("\n" + "=" * 72)
    print("AGE-WISE CMPR LASSO ANALYSIS | RELIGION DATASET")
    print("=" * 72)

    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Missing input file: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    all_results = {}

    for religion in RELIGIONS:
        all_results[religion] = {}
        for gender in GENDERS:
            all_results[religion][gender] = run_agewise_models(df, religion, gender)
            plot_coefficients_by_bracket(all_results[religion][gender], religion, gender)
            plot_agewise_heatmap(all_results[religion][gender], religion, gender)
            plot_model_performance(all_results[religion][gender], religion, gender)

    summary = build_summary_table(all_results)
    summary_path = os.path.join(OUT_DIR, "religion_lasso_agewise_summary.csv")
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
        f"religion_lasso_agewise_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
    )

    with open(log_path, "w") as handle:
        original_stdout = sys.stdout
        sys.stdout = handle
        try:
            main()
        finally:
            sys.stdout = original_stdout

    print(f"Log saved to: {log_path}")
