"""
=============================================================================
run_all.py  —  Master runner: builds all four DataFrames in sequence
=============================================================================
Imports the four build_*.py modules and calls each one's build function,
then writes every CSV to OUTPUT_DIR (configured in utils.py).

Usage:
    python run_all.py                # build all four
    python run_all.py total          # build only df_total
    python run_all.py SC ST          # build df_SC and df_ST only
    python run_all.py total SC ST religion   # explicit ordering

Valid targets: total | SC | ST | religion
=============================================================================
"""

import sys
import os

# Ensure utils.py / build_*.py on the path when run from any directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import save_outputs, gender_split, OUTPUT_DIR, AGE_BRACKETS

from build_total    import build_df_total
from build_SC       import build_df_SC
from build_ST       import build_df_ST
from build_religion import build_df_religion


# ---------------------------------------------------------------------------
# TARGET REGISTRY
# Maps CLI name → (build_function, base_filename_stem)
# ---------------------------------------------------------------------------
TARGETS = {
    'total'    : (build_df_total,    'total'),
    'SC'       : (build_df_SC,       'SC'),
    'ST'       : (build_df_ST,       'ST'),
    'religion' : (build_df_religion, 'religion'),
}

DEFAULT_ORDER = ['total', 'SC', 'ST', 'religion']


def _run_target(name: str) -> dict:
    """
    Build one DataFrame, split by gender, return {filename: df} dict
    ready for save_outputs().
    """
    build_fn, stem = TARGETS[name]
    df = build_fn()

    print(f"\n--- Gender split: {name} ---")
    df_m, df_f = gender_split(df, f'df_{stem}')

    return {
        f'df_{stem}_state.csv'  : df,
        f'df_{stem}_male.csv'   : df_m,
        f'df_{stem}_female.csv' : df_f,
    }


def main(targets: list = None) -> None:
    if targets is None:
        targets = DEFAULT_ORDER

    # Validate
    invalid = [t for t in targets if t not in TARGETS]
    if invalid:
        print(f"[ERROR] Unknown target(s): {invalid}")
        print(f"        Valid targets: {list(TARGETS.keys())}")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_outputs: dict = {}
    for name in targets:
        print(f"\n{'='*70}")
        print(f"  Building: {name}")
        print(f"{'='*70}")
        all_outputs.update(_run_target(name))

    # Save everything in one call for a unified summary table
    save_outputs(all_outputs)

    print(f"\n  Age brackets : {AGE_BRACKETS}")
    print(f"  Format       : LONG — one row per (state × age_bracket)")
    print("\nAll done.")


if __name__ == '__main__':
    # Parse optional CLI arguments
    cli_targets = sys.argv[1:] if len(sys.argv) > 1 else None
    main(cli_targets)