"""Report whole-ROI 3D per-subject CSP metrics from a frozen 2.5D checkpoint.

This is a *diagnostic* for the held-out subject split, not a final generalization
study. HCP family IDs are unavailable, so subject-disjoint validation may have
twin/sibling leakage; the ROI was tuned on the development cohort. Results and
subject IDs are PRIVATE. Never commit the CSVs, masks, or MRI data.

Run this script ON A GPU COMPUTE NODE rather than the Narval login node.
Use the best checkpoint from an already finished training job; never retrain on
validation cases or select thresholds on these 11 validation subjects.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from csp25d_baseline import (
    CoronalUNet25D, load_case, predict_case, read_manifest, usable_for_supervision,
)


def per_case_metrics(pred, ref, voxel_volume_mm3):
    """Voxel overlap, classification and signed/absolute volume error in native space.

    Reference-positive Dice is defined for all cases in this initial pilot.
    Return null precision for no predicted CSP; recall remains 0 on a missed
    positive reference. Never silently treat empty references as Dice=1.
    """
    pred = np.asarray(pred, dtype=bool)
    ref = np.asarray(ref, dtype=bool)
    if pred.shape != ref.shape:
        raise ValueError("Predicted/reference masks have different shapes")
    if not np.isfinite(voxel_volume_mm3) or voxel_volume_mm3 <= 0:
        raise ValueError("Invalid physical voxel volume")
    tp = int(np.count_nonzero(pred & ref))
    fp = int(np.count_nonzero(pred & ~ref))
    fn = int(np.count_nonzero(~pred & ref))
    n_ref = tp + fn
    n_pred = tp + fp
    if not n_ref:
        raise ValueError("Pilot diagnostic expects a reference-positive CSP subject")
    denominator = 2 * tp + fp + fn
    return {
        "reference_voxels": n_ref,
        "predicted_voxels": n_pred,
        "true_positive_voxels": tp,
        "false_positive_voxels": fp,
        "false_negative_voxels": fn,
        "dice": 2.0 * tp / denominator if denominator else None,
        "iou": tp / (tp + fp + fn) if (tp + fp + fn) else None,
        "precision": tp / n_pred if n_pred else None,
        "recall": tp / n_ref,
        "reference_volume_mm3": n_ref * voxel_volume_mm3,
        "predicted_volume_mm3": n_pred * voxel_volume_mm3,
        "signed_volume_error_mm3": (n_pred - n_ref) * voxel_volume_mm3,
        "absolute_volume_error_mm3": abs(n_pred - n_ref) * voxel_volume_mm3,
    }


def require_same_manifest(manifest, config):
    """Prevent accidentally evaluating a checkpoint on a different split."""
    expected = config.get("manifest_sha256")
    if not expected:
        raise ValueError("Checkpoint lacks training-manifest hash")
    actual = hashlib.sha256(Path(manifest).read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError("Checkpoint manifest SHA256 differs from supplied manifest")
    return actual


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", required=True, help="PRIVATE 44/11 Linux-path manifest")
    p.add_argument("--checkpoint", required=True, help="Model best.pt from two-epoch pilot")
    p.add_argument("--out", required=True, help="PRIVATE, separate evaluation output directory")
    p.add_argument("--split", choices=["train", "val"], default="val")
    p.add_argument("--expected-subjects", type=int, default=11)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--require-cuda", action="store_true")
    args = p.parse_args()

    if not (0 < args.threshold < 1):
        raise SystemExit("Threshold must be strictly between 0 and 1")
    if args.expected_subjects <= 0:
        raise SystemExit("Expected subject count must be positive")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if args.require_cuda and device.type != "cuda":
        raise SystemExit("CUDA required; refusing to evaluate on login-node CPU")

    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    config = checkpoint.get("config")
    if not isinstance(config, dict):
        raise ValueError("Checkpoint lacks 2.5D config")
    manifest_sha = require_same_manifest(args.manifest, config)
    rows = [row for row in read_manifest(args.manifest)
            if row["split"] == args.split and usable_for_supervision(row)]
    if len(rows) != args.expected_subjects:
        raise ValueError(f"Expected {args.expected_subjects} eligible {args.split} cases, found {len(rows)}")
    if any(row["presence"] != "present" for row in rows):
        raise ValueError("This pilot report is intentionally restricted to reference-positive subjects")

    model = CoronalUNet25D(slices=int(config["slices"]), width=int(config["width"]))
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    model.to(device).eval()

    results = []
    print(f"[EVAL] checkpoint_epoch={checkpoint.get('epoch')} split={args.split} "
          f"subjects={len(rows)} threshold={args.threshold} device={device}", flush=True)
    for row in rows:
        prob, _, meta = predict_case(model, row, device, int(config["slices"]))
        _, reference, _, _ = load_case(
            row["subject_id"], row["crop_t2"], row["crop_json"],
            row["source_mask"], row["presence"]
        )
        voxel_volume = float(abs(np.linalg.det(np.asarray(meta["original_affine"])[:3, :3])))
        measurements = per_case_metrics(prob >= args.threshold, reference, voxel_volume)
        record = {"subject_id": row["subject_id"], "split": row["split"], **measurements}
        results.append(record)
        print(f"[EVAL] {record['subject_id']}: Dice={measurements['dice']:.4f} "
              f"reference={measurements['reference_voxels']} predicted={measurements['predicted_voxels']} "
              f"TP={measurements['true_positive_voxels']} FP={measurements['false_positive_voxels']} "
              f"FN={measurements['false_negative_voxels']}", flush=True)

    dices = np.asarray([r["dice"] for r in results], dtype=float)
    summary = {
        "source": "TRAIN-HELD-OUT SUBJECTS, exploratory (family groups unknown)",
        "checkpoint_epoch": checkpoint.get("epoch"),
        "manifest_sha256": manifest_sha,
        "checkpoint": str(Path(args.checkpoint).resolve()),
        "git_head": config.get("git_head"),
        "split": args.split,
        "subjects": len(results),
        "threshold": args.threshold,
        "mean_case_dice": float(np.mean(dices)),
        "median_case_dice": float(np.median(dices)),
        "min_case_dice": float(np.min(dices)),
        "max_case_dice": float(np.max(dices)),
        "cases_with_no_predicted_voxels": int(sum(not r["predicted_voxels"] for r in results)),
        "mean_case_recall": float(np.mean([r["recall"] for r in results])),
        "mean_abs_volume_error_mm3": float(np.mean([r["absolute_volume_error_mm3"] for r in results])),
        "family_disjoint_verified": False,
        "negative_cases_evaluated": 0,
        "validation_seed": config.get("seed"),
    }

    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    per_case_file = output / "per_case_metrics.csv"
    summary_file = output / "summary.json"
    if per_case_file.exists() or summary_file.exists():
        raise FileExistsError("Refusing to overwrite preexisting evaluation results")
    with per_case_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    summary_file.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"[EVAL COMPLETE] mean_Dice={summary['mean_case_dice']:.4f}, "
          f"median={summary['median_case_dice']:.4f}, min={summary['min_case_dice']:.4f}, "
          f"max={summary['max_case_dice']:.4f}, no_prediction={summary['cases_with_no_predicted_voxels']}", flush=True)
    print("PRIVATE per-case:", per_case_file, flush=True)
    print("PRIVATE summary:", summary_file, flush=True)


if __name__ == "__main__":
    main()
