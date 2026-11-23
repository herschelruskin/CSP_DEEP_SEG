"""Synthetic integration checks: NIfTI original -> Slicer-style native crop -> loader."""
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from csp25d_baseline import class_subject_balanced_weights, read_manifest
from audit_csp25d_manifest import audit_case


def test_subject_and_class_balancing():
    index = (
        [("tiny", 0, True)] +
        [("long", j, True) for j in range(10)] +
        [("tiny", j + 1, False) for j in range(4)] +
        [("empty", j, False) for j in range(5)]
    )
    weights = class_subject_balanced_weights(index).numpy()
    assert np.isclose(weights.sum(), 1.0)
    assert np.isclose(weights[[t[2] for t in index]].sum(), .5)
    for label in (False, True):
        distinct_subjects = {sid for sid, _, yes in index if yes == label}
        masses = [sum(w for w, t in zip(weights, index) if t[0] == sid and t[2] == label)
                  for sid in distinct_subjects]
        assert np.allclose(masses, .5 / len(distinct_subjects))


def make_case(tmp_path):
    sid = "111111"
    root = tmp_path / (sid + "_3T_T2w_SPC1.nii.gz")
    crop_path = tmp_path / (sid + "_3T_T2w_SPC1_proportional_reduced.nii.gz")
    json_path = tmp_path / (sid + "_3T_T2w_SPC1_proportional_reduced.crop.json")
    mask_path = tmp_path / (sid + ".nii.gz")
    rules_path = tmp_path / "calibrated_rules.json"
    original = 50 + np.arange(14 ** 3, dtype=np.float32).reshape((14, 14, 14))
    mask = np.zeros_like(original, dtype=np.uint8)
    mask[6, 7, 8] = 1
    affine = np.diag([.7, .7, .7, 1.])
    affine[:3, 3] = [15, -20, 40]
    start, end = [2, 3, 4], [11, 12, 13]
    shifted = affine.copy()
    shifted[:3, 3] = (affine @ np.r_[start, 1.])[:3]
    nib.save(nib.Nifti1Image(original, affine), root)
    nib.save(nib.Nifti1Image(original[2:11, 3:12, 4:13], shifted), crop_path)
    nib.save(nib.Nifti1Image(mask, affine), mask_path)
    rule = {"mode": "proportional", "margin_mm": 8.0, "lr_half_width": .1}
    rules_path.write_text(json.dumps({"rules": {"proportional": rule}}))
    json_path.write_text(json.dumps({
        "mode": "proportional", "rule": rule, "source_file": str(root),
        "source_shape_kji": [14, 14, 14], "start_ijk": start, "end_ijk": end,
        "original_affine": affine.tolist(), "output_affine": shifted.tolist()
    }))
    row = dict(subject_id=sid, split="train", family_group="F1",
               crop_t2=str(crop_path), crop_json=str(json_path),
               source_mask=str(mask_path), original_t2=str(root),
               presence="present", qc="pass", negative_confidence="")
    return row, rules_path, crop_path, shifted


def test_native_nifti_roundtrip_and_frozen_rule(tmp_path):
    row, rule_json, _, _ = make_case(tmp_path)
    result = audit_case(row, rule_json, verify_original=True)
    assert result["mask_voxels"] == 1
    assert result["shape_ijk"] == "9x9x9"


def test_detects_modified_crop_voxel(tmp_path):
    row, rule_json, crop_path, affine = make_case(tmp_path)
    image = np.asarray(nib.load(str(crop_path)).dataobj).copy()
    image[1, 1, 1] += 1
    nib.save(nib.Nifti1Image(image, affine), crop_path)
    with pytest.raises(ValueError, match="voxel values differ"):
        audit_case(row, rule_json, verify_original=True)


def test_detects_wrong_fitted_rule(tmp_path):
    row, rules_path, _, _ = make_case(tmp_path)
    rules_path.write_text(json.dumps({"rules": {"proportional": {"margin_mm": 1.0}}}))
    with pytest.raises(ValueError, match="different proportional rule"):
        audit_case(row, rules_path, verify_original=True)


def test_reject_duplicate_crop_reassigned_to_another_subject(tmp_path):
    row, _, _, _ = make_case(tmp_path)
    import csv
    path = tmp_path / "manifest.csv"
    other = dict(row, subject_id="222222")
    with path.open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=row.keys())
        writer.writeheader()
        writer.writerows([row, other])
    with pytest.raises(ValueError, match="same crop T2"):
        read_manifest(path)
