"""Compare six FROZEN best-checkpoint evaluations for identical CSP subjects.

Reads 3 baseline and 3 training-intensity-augmented validation CSV files.
Does not train, run inference, choose a threshold, or modify MRI/label files.
The 11 validation subjects have been reused during development: all results
are exploratory. Do not treat them as an external holdout or evaluate absent
CSP specificity from this reference-positive set.

Narval login-shell usage (no GPU required):
    python scripts/compare_csp25d_variants.py \
      --runs-root "$SCRATCH/csp25d_private/baseline_seed843/runs"
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean, pstdev


SEEDS = (843, 844, 845)
ARMS = ("baseline", "augmented")
FIELDS = (
    "reference_voxels", "predicted_voxels", "true_positive_voxels",
    "false_positive_voxels", "false_negative_voxels", "dice",
    "recall", "reference_volume_mm3", "predicted_volume_mm3",
    "signed_volume_error_mm3", "absolute_volume_error_mm3",
)


def read_cases(path: Path) -> dict[str, dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing evaluation metrics: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not set(FIELDS + ("subject_id",)).issubset(reader.fieldnames or []):
            raise ValueError(f"Missing expected per-case metric columns: {path}")
        cases = {}
        for row in reader:
            subject_id = row["subject_id"]
            if not subject_id or subject_id in cases:
                raise ValueError(f"Invalid or repeated subject ID in {path}: {subject_id!r}")
            cases[subject_id] = {field: float(row[field]) for field in FIELDS}
    if not cases:
        raise ValueError(f"Empty evaluation CSV: {path}")
    return cases


def metric_path(root: Path, seed: int, arm: str) -> Path:
    stem = f"baseline_20epoch_seed{seed}" if arm == "baseline" else f"baseline_20epoch_augint_seed{seed}"
    return root / f"{stem}_eval_best" / "per_case_metrics.csv"


def analyze(root: Path, n_expected: int = 11) -> list[dict]:
    runs = {(seed, arm): read_cases(metric_path(root, seed, arm))
            for seed in SEEDS for arm in ARMS}
    ids = sorted(runs[(843, "baseline")])
    if len(ids) != n_expected:
        raise ValueError(f"Expected {n_expected} cases; found {len(ids)}")
    for (seed, arm), cases in runs.items():
        if set(cases) != set(ids):
            raise ValueError(f"Subject mismatch for {seed}/{arm}: missing/extra vs frozen comparison")
    records = []
    for subject_id in ids:
        refs = [runs[key][subject_id]["reference_voxels"] for key in runs]
        if len(set(refs)) != 1:
            raise ValueError(f"Reference mask voxel count changed across runs: {subject_id}")
        rec = {"subject_id": subject_id, "reference_voxels": int(refs[0])}
        for arm in ARMS:
            for field in ("dice", "recall", "false_positive_voxels",
                          "false_negative_voxels", "absolute_volume_error_mm3"):
                vals = [runs[(seed, arm)][subject_id][field] for seed in SEEDS]
                rec[f"{arm}_{field}_mean"] = mean(vals)
            rec[f"{arm}_dice_range"] = (
                max(runs[(seed, arm)][subject_id]["dice"] for seed in SEEDS)
                - min(runs[(seed, arm)][subject_id]["dice"] for seed in SEEDS)
            )
        rec["delta_mean_dice_aug_minus_base"] = (
            rec["augmented_dice_mean"] - rec["baseline_dice_mean"]
        )
        records.append(rec)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", required=True, type=Path)
    parser.add_argument("--expected-subjects", type=int, default=11)
    args = parser.parse_args()
    data = analyze(args.runs_root, args.expected_subjects)

    print("=== SAME 11 SUBJECTS, THREE SEEDS EACH: AUGMENTATION VS BASELINE ===")
    print("Subject  RefVox  BaseDice  AugDice  ΔDice    BaseFP  AugFP  BaseFN  AugFN  BaseSeedRange  AugSeedRange")
    for r in sorted(data, key=lambda item: item["delta_mean_dice_aug_minus_base"]):
        print(
            f'{r["subject_id"]:7} {r["reference_voxels"]:6} '
            f'{r["baseline_dice_mean"]:8.3f} {r["augmented_dice_mean"]:8.3f} '
            f'{r["delta_mean_dice_aug_minus_base"]:+7.3f} '
            f'{r["baseline_false_positive_voxels_mean"]:7.1f} '
            f'{r["augmented_false_positive_voxels_mean"]:6.1f} '
            f'{r["baseline_false_negative_voxels_mean"]:7.1f} '
            f'{r["augmented_false_negative_voxels_mean"]:6.1f} '
            f'{r["baseline_dice_range"]:14.3f} '
            f'{r["augmented_dice_range"]:13.3f}'
        )
    deltas = [r["delta_mean_dice_aug_minus_base"] for r in data]
    improved = sum(d > 0 for d in deltas)
    print()
    print(f"Subjects with positive mean Dice change: {improved}/{len(data)}")
    print(f"Mean subject-level augmented - baseline Dice: {mean(deltas):+.6f}")
    print(f"Subjects with worse mean Dice: {sum(d < 0 for d in deltas)}/{len(data)}")
    print("All three baseline and augmented runs must use the exact same private R1 reference masks.")
    print("Development-val repeated model selection; NOT independent generalization evidence.")


if __name__ == "__main__":
    main()
