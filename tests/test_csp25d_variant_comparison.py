"""Synthetic CSV checks for read-only six-run CSP comparison (no MRI data)."""
from pathlib import Path
import csv
import importlib.util

import pytest


def load_module():
    src = Path(__file__).parents[1] / "scripts" / "compare_csp25d_variants.py"
    spec = importlib.util.spec_from_file_location("compare_csp25d_variants", src)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_inputs(root, n=11):
    module = load_module()
    for seed in module.SEEDS:
        for arm in module.ARMS:
            out = module.metric_path(root, seed, arm)
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("w", newline="") as handle:
                w = csv.DictWriter(handle, fieldnames=["subject_id", *module.FIELDS])
                w.writeheader()
                for i in range(n):
                    tp = 7 + i
                    fn = 3
                    fp = 4 if arm == "baseline" else 2
                    ref = tp + fn
                    pred = tp + fp
                    vals = {
                        "subject_id": str(100001 + i),
                        "reference_voxels": ref,
                        "predicted_voxels": pred,
                        "true_positive_voxels": tp,
                        "false_positive_voxels": fp,
                        "false_negative_voxels": fn,
                        "dice": 2 * tp / (2 * tp + fp + fn),
                        "recall": tp / ref,
                        "reference_volume_mm3": 0.343 * ref,
                        "predicted_volume_mm3": 0.343 * pred,
                        "signed_volume_error_mm3": 0.343 * (pred - ref),
                        "absolute_volume_error_mm3": 0.343 * abs(pred - ref),
                    }
                    w.writerow(vals)
    return module


def test_same_subject_and_reference_checks(tmp_path):
    module = make_inputs(tmp_path)
    records = module.analyze(tmp_path)
    assert len(records) == 11
    assert all(x["delta_mean_dice_aug_minus_base"] > 0 for x in records)
    assert all(x["augmented_false_positive_voxels_mean"] == 2 for x in records)


def test_reject_missing_or_mismatched_frozen_subjects(tmp_path):
    module = make_inputs(tmp_path)
    path = module.metric_path(tmp_path, 845, "augmented")
    path.unlink()
    with pytest.raises(FileNotFoundError):
        module.analyze(tmp_path)
    module = make_inputs(tmp_path)
    text = path.read_text()
    path.write_text(text.replace("100001", "999999", 1))
    with pytest.raises(ValueError, match="Subject mismatch"):
        module.analyze(tmp_path)


def test_reject_different_reference_masks(tmp_path):
    module = make_inputs(tmp_path)
    path = module.metric_path(tmp_path, 844, "baseline")
    contents = path.read_text()
    path.write_text(contents.replace(",10,11,7,4,3,", ",11,11,7,4,3,", 1))
    with pytest.raises(ValueError, match="Reference mask voxel count"):
        module.analyze(tmp_path)
