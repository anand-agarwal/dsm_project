"""
Plot side-by-side comparisons of age-wise LASSO summaries for 2001 and 2011.

This script is designed for the summary CSVs produced by:
  - scripts/cmpr_lasso_analysis.py
  - scripts/cmpr_lasso_analysis_religion.py

It reads the 2001 and 2011 summary files, parses the signed coefficients from
the `selected_predictors` column, and creates:
  1. Side-by-side heatmaps of the strongest predictors by age bracket
  2. Side-by-side age-wise model metric plots (R2 CV, R2 train, predictors selected)

Default inputs match the files referenced in the project.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm


AGE_ORDER = [
    "age_below10",
    "age_10_13",
    "age_14_17",
    "age_18_21",
    "age_22_25",
    "age_26_29",
    "age_30_33",
    "age_34_plus",
]

AGE_LABELS = {
    "age_below10": "<10",
    "age_10_13": "10-13",
    "age_14_17": "14-17",
    "age_18_21": "18-21",
    "age_22_25": "22-25",
    "age_26_29": "26-29",
    "age_30_33": "30-33",
    "age_34_plus": "34+",
}

DEFAULT_FILES = {
    "religion_2001": "/Users/anandagarwal/dsm_project/regression_outputs_2001/religion_lasso_agewise/religion_lasso_agewise_summary_2001.csv",
    "religion_2011": "/Users/anandagarwal/dsm_project/regression_outputs_2011/religion_lasso_agewise/religion_lasso_agewise_2011_summary.csv",
    "caste_2001": "/Users/anandagarwal/dsm_project/regression_outputs_2001/lasso_agewise/lasso_agewise_2001.csv",
    "caste_2011": "/Users/anandagarwal/dsm_project/regression_outputs_2011/lasso_agewise/lasso_agewise_2011.csv",
}

COEF_PATTERN = re.compile(
    r"\s*(.*?)\s*\(([+-]?\d+(?:\.\d+)?)\)(?:\s*\|\s*|$)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare 2001 and 2011 LASSO age-wise summaries."
    )
    parser.add_argument("--religion-2001", default=DEFAULT_FILES["religion_2001"])
    parser.add_argument("--religion-2011", default=DEFAULT_FILES["religion_2011"])
    parser.add_argument("--caste-2001", default=DEFAULT_FILES["caste_2001"])
    parser.add_argument("--caste-2011", default=DEFAULT_FILES["caste_2011"])
    parser.add_argument(
        "--output-dir",
        default="analysis_outputs/lasso_2001_2011_comparison",
        help="Directory where plots will be written.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=8,
        help="How many major predictors to show in each heatmap.",
    )
    return parser.parse_args()


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def load_summary(path: str | Path, year: int, kind: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    key_col = "religion" if kind == "religion" else "dataset"
    df = df.rename(columns={key_col: "group"}).copy()
    df["year"] = year
    df["kind"] = kind
    df["group"] = df["group"].astype(str)
    df["gender"] = df["gender"].astype(str)
    df["age_bracket"] = pd.Categorical(df["age_bracket"], AGE_ORDER, ordered=True)
    return df


def parse_selected_predictors(text: object) -> list[tuple[str, float]]:
    if pd.isna(text):
        return []

    text = str(text).strip()
    if not text:
        return []

    matches = COEF_PATTERN.findall(text)
    parsed = []
    for predictor, coef in matches:
        predictor = predictor.strip()
        if predictor:
            parsed.append((predictor, float(coef)))
    return parsed


def explode_coefficients(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for record in df.to_dict("records"):
        parsed = parse_selected_predictors(record.get("selected_predictors"))
        for predictor, coefficient in parsed:
            rows.append(
                {
                    "kind": record["kind"],
                    "group": record["group"],
                    "gender": record["gender"],
                    "age_bracket": record["age_bracket"],
                    "year": record["year"],
                    "predictor": predictor,
                    "coefficient": coefficient,
                    "abs_coefficient": abs(coefficient),
                }
            )
    return pd.DataFrame(rows)


def choose_major_predictors(coeff_df: pd.DataFrame, top_n: int) -> list[str]:
    if coeff_df.empty:
        return []

    ranked = (
        coeff_df.groupby("predictor", as_index=False)
        .agg(
            n_hits=("coefficient", "size"),
            years_present=("year", "nunique"),
            mean_abs=("abs_coefficient", "mean"),
            max_abs=("abs_coefficient", "max"),
        )
        .sort_values(
            by=["years_present", "n_hits", "mean_abs", "max_abs", "predictor"],
            ascending=[False, False, False, False, True],
        )
    )
    return ranked["predictor"].head(top_n).tolist()


def build_heatmap_matrix(
    coeff_df: pd.DataFrame, predictors: list[str], year: int
) -> pd.DataFrame:
    if not predictors:
        return pd.DataFrame(index=[], columns=AGE_ORDER)

    subset = coeff_df[
        (coeff_df["year"] == year) & (coeff_df["predictor"].isin(predictors))
    ].copy()

    pivot = subset.pivot_table(
        index="predictor",
        columns="age_bracket",
        values="coefficient",
        aggfunc="mean",
    )

    pivot = pivot.reindex(index=predictors, columns=AGE_ORDER)
    return pivot


def draw_heatmap(ax: plt.Axes, matrix: pd.DataFrame, title: str, vmax: float) -> None:
    if matrix.empty:
        ax.axis("off")
        ax.set_title(title, fontsize=12, weight="bold")
        ax.text(0.5, 0.5, "No selected predictors", ha="center", va="center")
        return

    data = matrix.values.astype(float)
    masked = np.ma.masked_invalid(data)
    cmap = plt.get_cmap("RdBu_r").copy()
    cmap.set_bad(color="#f3f3f3")
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax) if vmax > 0 else None

    im = ax.imshow(masked, aspect="auto", cmap=cmap, norm=norm)
    ax.set_title(title, fontsize=12, weight="bold")
    ax.set_xticks(np.arange(len(matrix.columns)))
    ax.set_xticklabels([AGE_LABELS.get(col, col) for col in matrix.columns], rotation=0)
    ax.set_yticks(np.arange(len(matrix.index)))
    ax.set_yticklabels(matrix.index)
    ax.set_xlabel("Age bracket")

    for row_idx in range(matrix.shape[0]):
        for col_idx in range(matrix.shape[1]):
            value = matrix.iat[row_idx, col_idx]
            if pd.notna(value):
                ax.text(
                    col_idx,
                    row_idx,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="black",
                )

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.set_xticks(np.arange(-0.5, len(matrix.columns), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(matrix.index), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1)
    ax.tick_params(which="minor", bottom=False, left=False)
    return im


def plot_heatmap_comparison(
    coeff_df: pd.DataFrame,
    kind: str,
    group: str,
    gender: str,
    output_dir: Path,
    top_n: int,
) -> Path | None:
    subset = coeff_df[
        (coeff_df["kind"] == kind)
        & (coeff_df["group"] == group)
        & (coeff_df["gender"] == gender)
    ].copy()

    major_predictors = choose_major_predictors(subset, top_n=top_n)
    if not major_predictors:
        return None

    matrix_2001 = build_heatmap_matrix(subset, major_predictors, year=2001)
    matrix_2011 = build_heatmap_matrix(subset, major_predictors, year=2011)
    vmax = np.nanmax(
        np.abs(
            np.concatenate(
                [
                    matrix_2001.to_numpy(dtype=float).ravel(),
                    matrix_2011.to_numpy(dtype=float).ravel(),
                ]
            )
        )
    )

    fig_height = max(4.5, 0.7 * len(major_predictors) + 2.5)
    fig, axes = plt.subplots(1, 2, figsize=(15, fig_height), constrained_layout=True)
    fig.patch.set_facecolor("white")

    im = draw_heatmap(axes[0], matrix_2001, "2001", vmax=vmax)
    draw_heatmap(axes[1], matrix_2011, "2011", vmax=vmax)
    axes[0].set_ylabel("Major predictors")

    if im is not None:
        cbar = fig.colorbar(im, ax=axes, shrink=0.8, pad=0.02)
        cbar.set_label("LASSO coefficient")

    title_prefix = "Religion" if kind == "religion" else "Caste / overall"
    fig.suptitle(
        f"{title_prefix}: {group} | {gender} | Major predictors by age",
        fontsize=14,
        weight="bold",
    )

    out_path = output_dir / kind / f"{slugify(group)}_{gender}_heatmap_2001_vs_2011.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_metrics_comparison(
    df: pd.DataFrame,
    kind: str,
    group: str,
    gender: str,
    output_dir: Path,
) -> Path | None:
    subset = df[
        (df["kind"] == kind)
        & (df["group"] == group)
        & (df["gender"] == gender)
        & (df["status"] == "ok")
    ].copy()

    if subset.empty:
        return None

    subset = subset.sort_values(["year", "age_bracket"])
    x = np.arange(len(AGE_ORDER))

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True, constrained_layout=True)
    fig.patch.set_facecolor("white")

    series_specs = [
        ("r2_cv", "Cross-validated R2", "#1f77b4"),
        ("r2_train", "Train R2", "#d62728"),
        ("n_selected", "Predictors selected", "#2ca02c"),
    ]

    for ax, (col, ylabel, color) in zip(axes, series_specs):
        for year, marker in [(2001, "o"), (2011, "s")]:
            year_data = (
                subset[subset["year"] == year]
                .set_index("age_bracket")
                .reindex(AGE_ORDER)
            )
            ax.plot(
                x,
                year_data[col].astype(float),
                marker=marker,
                linewidth=2,
                color=color if year == 2001 else "#444444",
                label=str(year),
            )
        ax.set_ylabel(ylabel)
        ax.axhline(0, color="#bdbdbd", linewidth=1, linestyle="--")
        ax.grid(axis="y", alpha=0.25)
        ax.legend(frameon=False)

    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels([AGE_LABELS[a] for a in AGE_ORDER])
    axes[-1].set_xlabel("Age bracket")

    title_prefix = "Religion" if kind == "religion" else "Caste / overall"
    fig.suptitle(
        f"{title_prefix}: {group} | {gender} | Model comparison",
        fontsize=14,
        weight="bold",
    )

    out_path = output_dir / kind / f"{slugify(group)}_{gender}_metrics_2001_vs_2011.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return out_path


def write_group_manifest(
    df: pd.DataFrame,
    coeff_df: pd.DataFrame,
    output_dir: Path,
    top_n: int,
) -> Path:
    rows = []
    for (kind, group, gender), subset in coeff_df.groupby(["kind", "group", "gender"]):
        major_predictors = choose_major_predictors(subset, top_n=top_n)
        rows.append(
            {
                "kind": kind,
                "group": group,
                "gender": gender,
                "major_predictors": " | ".join(major_predictors),
            }
        )

    manifest = pd.DataFrame(rows).sort_values(["kind", "group", "gender"])
    out_path = output_dir / "major_predictors_manifest.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(out_path, index=False)
    return out_path


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)

    frames = [
        load_summary(args.religion_2001, year=2001, kind="religion"),
        load_summary(args.religion_2011, year=2011, kind="religion"),
        load_summary(args.caste_2001, year=2001, kind="caste"),
        load_summary(args.caste_2011, year=2011, kind="caste"),
    ]
    summary_df = pd.concat(frames, ignore_index=True)
    coeff_df = explode_coefficients(summary_df)

    heatmap_paths = []
    metric_paths = []

    for kind, group_df in summary_df.groupby("kind"):
        for group, gender in (
            group_df[["group", "gender"]]
            .drop_duplicates()
            .sort_values(["group", "gender"])
            .itertuples(index=False, name=None)
        ):
            heatmap_path = plot_heatmap_comparison(
                coeff_df=coeff_df,
                kind=kind,
                group=group,
                gender=gender,
                output_dir=output_dir,
                top_n=args.top_n,
            )
            metric_path = plot_metrics_comparison(
                df=summary_df,
                kind=kind,
                group=group,
                gender=gender,
                output_dir=output_dir,
            )
            if heatmap_path is not None:
                heatmap_paths.append(str(heatmap_path))
            if metric_path is not None:
                metric_paths.append(str(metric_path))

    manifest_path = write_group_manifest(
        df=summary_df,
        coeff_df=coeff_df,
        output_dir=output_dir,
        top_n=args.top_n,
    )

    print(f"Wrote {len(heatmap_paths)} heatmaps")
    print(f"Wrote {len(metric_paths)} metrics plots")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
