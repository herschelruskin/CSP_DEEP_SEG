"""Evaluate frozen CSP 2.5D U-Net predictions against SAME-SCAN R1/R2 masks.

The 20 subjects are the repeat-annotation (R2) development cohort, some
potentially in the original 44-subject R1 training set. The script insists on
the checkpoint's frozen training-manifest SHA and labels each subject's R1
exposure as train, val or not_in_model_split. Results are NOT an independent
model generalization test. Never use results to choose a checkpoint/threshold.

Requires the stage exported by prepare_csp25d_r2_eval_inputs.py, checkpoint,
and original private training manifest. One inference per T2 scan, scored against
both references; R1/R2 are never supplied to the model for prediction.
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
    CoronalUNet25D, load_case, load_csp25d_checkpoint, predict_case, read_manifest,
)
from evaluate_csp25d_checkpoint import require_same_manifest
from prepare_csp25d_r2_eval_inputs import R2_IDS, R1_ABSENT, R2_ABSENT


def score(pred: np.ndarray, ref: np.ndarray, voxel_mm3: float) -> dict:
    """Compute spatial metrics with explicit undefined Dice for an empty ref."""
    p, r = np.asarray(pred, dtype=bool), np.asarray(ref, dtype=bool)
    if p.shape != r.shape or not np.isfinite(voxel_mm3) or voxel_mm3 <= 0:
        raise ValueError("Mask grid or physical voxel volume mismatch")
    tp = int(np.count_nonzero(p & r))
    fp = int(np.count_nonzero(p & ~r))
    fn = int(np.count_nonzero(~p & r))
    n_pred = tp + fp
    n_ref = tp + fn
    return {
        "reference_voxels": n_ref,
        "predicted_voxels": n_pred,
        "tp": tp, "fp": fp, "fn": fn,
        "dice": 2 * tp / (n_pred + n_ref) if n_ref else None,
        "recall": tp / n_ref if n_ref else None,
        "precision": tp / n_pred if n_pred else None,
        "predicted_present": bool(n_pred),
        "signed_volume_error_mm3": (n_pred - n_ref) * voxel_mm3,
        "absolute_volume_error_mm3": abs(n_pred - n_ref) * voxel_mm3,
        "false_positive_volume_mm3": fp * voxel_mm3,
    }


def read_stage(stage: Path) -> tuple[list[dict], str]:
    provenance = json.loads((stage / "READY.json").read_text(encoding="utf-8"))
    path = stage / "r2_eval_manifest.csv"
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if provenance.get("manifest_sha256") != sha or provenance.get("subjects") != 20:
        raise ValueError("Staged R2 manifest SHA256/subject count does not match frozen READY.json")
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        expected = {"subject_id", "crop_t2", "crop_json", "r1_presence", "r2_presence",
                    "r1_mask", "r2_mask", "r1_voxels", "r2_voxels"}
        if not expected.issubset(set(reader.fieldnames or [])):
            raise ValueError("R2 stage manifest lacks required columns")
        rows = list(reader)
    ids = [r["subject_id"] for r in rows]
    if len(ids) != 20 or len(set(ids)) != 20 or set(ids) != set(R2_IDS):
        raise ValueError("Unexpected or duplicate R2 comparison subjects")
    for row in rows:
        sid = row["subject_id"]
        for label in ("r1", "r2"):
            expected_presence = "absent" if sid in (R1_ABSENT if label == "r1" else R2_ABSENT) else "present"
            if row[label + "_presence"] != expected_presence:
                raise ValueError(f"{sid}: {label.upper()} presence differs from frozen audit")
            has_mask = bool(row[label + "_mask"])
            if has_mask != (expected_presence == "present"):
                raise ValueError(f"{sid}: {label.upper()} mask path/presence mismatch")
        for field in ("crop_t2", "crop_json", "r1_mask", "r2_mask"):
            relative = row[field]
            if not relative:
                continue
            # Enforce self-contained private staging; never access host paths.
            fpath = Path(relative)
            if fpath.is_absolute() or ".." in fpath.parts or not (stage / fpath).is_file():
                raise ValueError(f"{sid}: invalid staged {field} path")
    return rows, sha


def summarize(records: list[dict], checkpoint: dict, manifest_sha: str, stage_sha: str, threshold: float) -> dict:
    both = [r for r in records if r["r1_presence"] == "present" and r["r2_presence"] == "present"]
    r1_positive = [r for r in records if r["r1_presence"] == "present"]
    r2_positive = [r for r in records if r["r2_presence"] == "present"]
    def avg(rows, key):
        return float(np.mean([r[key] for r in rows])) if rows else None
    return {
        "interpretation": "R2 REPEAT-ANNOTATION DEVELOPMENT COHORT, some R1 TRAIN cases; NOT independent test",
        "checkpoint_epoch": checkpoint.get("epoch"),
        "model_seed": checkpoint["config"].get("seed"),
        "augmentation_used_in_training": bool(checkpoint["config"].get("intensity_augment", False)),
        "model_training_manifest_sha256": manifest_sha,
        "frozen_r2_stage_sha256": stage_sha,
        "threshold": threshold,
        "subjects": len(records),
        "exposure_counts": {e: sum(r["exposure"] == e for r in records)
                            for e in ("train", "val", "not_in_model_split")},
        "r1_positive_count": len(r1_positive),
        "r2_positive_count": len(r2_positive),
        "r1_and_r2_positive_count": len(both),
        "r1_and_r2_both_absent_count": sum(r["r1_presence"] == "absent" and r["r2_presence"] == "absent" for r in records),
        "r1_absent_r2_present_count": sum(r["r1_presence"] == "absent" and r["r2_presence"] == "present" for r in records),
        "mean_model_r1_dice_on_r1_positive": avg(r1_positive, "model_r1_dice"),
        "mean_model_r2_dice_on_r2_positive": avg(r2_positive, "model_r2_dice"),
        "paired_both_positive_mean_model_r1_dice": avg(both, "model_r1_dice"),
        "paired_both_positive_mean_model_r2_dice": avg(both, "model_r2_dice"),
        "paired_both_positive_mean_human_r1_r2_dice": avg(both, "r1_r2_dice"),
        "paired_both_positive_mean_model_dice_delta_r2_minus_r1": avg(both, "delta_model_dice_r2_minus_r1"),
        "model_detected_all_r2_positives": sum(bool(r["model_present"]) for r in r2_positive),
        "r1_absent_subjects_with_model_detection": [r["subject_id"] for r in records
                                                     if r["r1_presence"] == "absent" and r["model_present"]],
        "r2_absent_subjects_with_model_detection": [r["subject_id"] for r in records
                                                     if r["r2_presence"] == "absent" and r["model_present"]],
        "family_independence_verified": False,
    }


def evaluate(stage: Path, checkpoint_path: Path, original_manifest: Path,
             output: Path, threshold: float, require_cuda: bool = False) -> dict:
    if output.exists():
        raise FileExistsError("Do not overwrite prior R2 model scores")
    if not 0 < threshold < 1:
        raise ValueError("Threshold must be strictly inside (0,1)")
    stage_rows, stage_sha = read_stage(stage)
    checkpoint = load_csp25d_checkpoint(checkpoint_path, map_location="cpu")
    config = checkpoint.get("config")
    if not isinstance(config, dict):
        raise ValueError("Checkpoint lacks frozen model configuration")
    manifest_sha = require_same_manifest(original_manifest, config)
    train_rows = read_manifest(original_manifest)
    exposure = {r["subject_id"]: r["split"] for r in train_rows}
    if len(exposure) != len(train_rows):
        raise ValueError("Duplicate subjects in private frozen training manifest")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if require_cuda and device.type != "cuda":
        raise ValueError("R2 evaluation was configured to require GPU but CUDA unavailable")
    model = CoronalUNet25D(int(config["slices"]), int(config["width"])).to(device)
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    model.eval()
    records = []
    for row in stage_rows:
        sid = row["subject_id"]
        crop = stage / row["crop_t2"]
        sidecar = stage / row["crop_json"]
        prob, _, metadata = predict_case(
            model, {"subject_id": sid, "crop_t2": str(crop), "crop_json": str(sidecar)},
            device, int(config["slices"])
        )
        pred = prob >= threshold
        labels = {}
        for label in ("r1", "r2"):
            _, mask, _, _ = load_case(
                sid, str(crop), str(sidecar),
                str(stage / row[label + "_mask"]) if row[label + "_mask"] else "",
                row[label + "_presence"]
            )
            if int(np.count_nonzero(mask)) != int(row[label + "_voxels"]):
                raise ValueError(f"{sid}: staged {label.upper()} mask voxel count changed")
            labels[label] = mask.astype(bool)

        volume = abs(float(np.linalg.det(np.asarray(metadata["original_affine"], dtype=float)[:3, :3])))
        m1 = score(pred, labels["r1"], volume)
        m2 = score(pred, labels["r2"], volume)
        human = score(labels["r2"], labels["r1"], volume)
        both_positive = bool(np.any(labels["r1"]) and np.any(labels["r2"]))
        rec = {
            "subject_id": sid,
            "exposure": exposure.get(sid, "not_in_model_split"),
            "r1_presence": row["r1_presence"], "r2_presence": row["r2_presence"],
            "model_present": bool(np.any(pred)),
            "model_voxels": int(np.count_nonzero(pred)),
            "r1_voxels": int(np.count_nonzero(labels["r1"])),
            "r2_voxels": int(np.count_nonzero(labels["r2"])),
            "r1_r2_dice": human["dice"] if both_positive else None,
            "model_r1_dice": m1["dice"],
            "model_r2_dice": m2["dice"],
            "delta_model_dice_r2_minus_r1": (
                m2["dice"] - m1["dice"] if both_positive else None
            ),
        }
        for label, m in (("r1", m1), ("r2", m2)):
            for name in ("tp", "fp", "fn", "recall", "precision", "signed_volume_error_mm3",
                         "absolute_volume_error_mm3", "false_positive_volume_mm3"):
                rec[f"model_{label}_{name}"] = m[name]
        records.append(rec)
        print(f"[R2 EVAL] {sid} exposure={rec['exposure']} "
              f"R1={rec['r1_voxels']} R2={rec['r2_voxels']} model={rec['model_voxels']} "
              f"Dice(model,R1)={rec['model_r1_dice']} Dice(model,R2)={rec['model_r2_dice']}", flush=True)

    summary = summarize(records, checkpoint, manifest_sha, stage_sha, threshold)
    output.mkdir(parents=True, exist_ok=False)
    with (output / "per_case_r1_r2_model.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("[R2 EVAL COMPLETE]", json.dumps(summary, indent=2), flush=True)
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--original-manifest", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--require-cuda", action="store_true")
    args = p.parse_args()
    evaluate(args.stage, args.checkpoint, args.original_manifest, args.out,
             args.threshold, args.require_cuda)


if __name__ == "__main__":
    main()
