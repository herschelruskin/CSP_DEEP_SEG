"""Synthetic-only safeguards for R1/R2 staging and frozen checkpoint scoring."""
import csv
import importlib.util
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load(script_name):
    spec = importlib.util.spec_from_file_location(script_name, SCRIPTS / (script_name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_reference_absence_and_dice_not_falsely_perfect():
    evaluator = load("evaluate_csp25d_r2")
    a = np.zeros((5, 5, 5), dtype=bool)
    b = a.copy()
    b[2, 2, 2] = True
    assert evaluator.score(a, a, .343)["dice"] is None
    assert evaluator.score(b, a, .343)["dice"] is None
    assert evaluator.score(b, a, .343)["fp"] == 1
    assert evaluator.score(a, b, .343)["dice"] == 0
    assert evaluator.score(a, b, .343)["fn"] == 1
    assert evaluator.score(b, b, .343)["dice"] == 1


def test_crop_export_is_exact_and_rejects_r2_drift(tmp_path):
    prep = load("prepare_csp25d_r2_eval_inputs")
    full_affine = np.eye(4)
    full_affine[:3, :3] *= .7
    source = np.zeros((9, 12, 13), np.uint8)
    source[4, 6, 7] = 1
    mask = tmp_path / "100610_2.nii"
    nib.save(nib.Nifti1Image(source, full_affine), str(mask))
    start = np.array((2, 4, 5))
    end = np.array((7, 9, 10))
    crop_affine = full_affine.copy()
    crop_affine[:3, 3] = (full_affine @ np.r_[start, 1])[:3]
    crop = nib.Nifti1Image(np.ones((5, 5, 5), np.float32), crop_affine)
    meta = {
        "source_shape_kji": [13, 12, 9],
        "start_ijk": start.tolist(),
        "end_ijk": end.tolist(),
        "original_affine": full_affine.tolist(),
        "output_affine": crop_affine.tolist(),
    }
    result = tmp_path / "roi_mask.nii.gz"
    assert prep.extract_label("100610", mask, False, crop, meta, result, known_voxels=1) == 1
    saved = nib.load(str(result))
    assert np.count_nonzero(np.asarray(saved.dataobj)) == 1
    np.testing.assert_allclose(saved.affine, crop.affine, atol=1e-4)
    with pytest.raises(ValueError, match="voxel count changed"):
        prep.extract_label("100610", mask, False, crop, meta, tmp_path / "bad.nii.gz", known_voxels=2)
    with pytest.raises(ValueError, match="unexpectedly has a mask"):
        prep.extract_label("100610", mask, True, crop, meta, tmp_path / "never.nii.gz")


def test_stage_read_enforces_exact_queue_and_sha(tmp_path):
    prep = load("prepare_csp25d_r2_eval_inputs")
    evaluator = load("evaluate_csp25d_r2")
    rows = []
    for sid in prep.R2_IDS:
        row = {
            "subject_id": sid,
            "crop_t2": f"scans/{sid}.nii.gz",
            "crop_json": f"scans/{sid}.crop.json",
            "r1_presence": "absent" if sid in prep.R1_ABSENT else "present",
            "r2_presence": "absent" if sid in prep.R2_ABSENT else "present",
            "r1_mask": "" if sid in prep.R1_ABSENT else f"masks/{sid}_r1_crop.nii.gz",
            "r2_mask": "" if sid in prep.R2_ABSENT else f"masks/{sid}_r2_crop.nii.gz",
            "r1_voxels": 0 if sid in prep.R1_ABSENT else 1,
            "r2_voxels": 0 if sid in prep.R2_ABSENT else 1,
        }
        rows.append(row)
        for field in ("crop_t2", "crop_json", "r1_mask", "r2_mask"):
            if row[field]:
                dst = tmp_path / row[field]
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(b"fake for manifest gate")
    path = tmp_path / "r2_eval_manifest.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    import hashlib
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    (tmp_path / "READY.json").write_text(json.dumps({"subjects": 20, "manifest_sha256": sha}))
    parsed, read_sha = evaluator.read_stage(tmp_path)
    assert len(parsed) == 20 and read_sha == sha
    path.write_text(path.read_text().replace("100610", "999999"))
    with pytest.raises(ValueError, match="SHA256"):
        evaluator.read_stage(tmp_path)


def test_paired_summary_prevents_different_reference_denominators():
    evaluator = load("evaluate_csp25d_r2")
    rows = [
        {
            "subject_id": "a", "exposure": "train",
            "r1_presence": "present", "r2_presence": "present",
            "model_present": True, "model_r1_dice": .6,
            "model_r2_dice": .7, "r1_r2_dice": .8,
            "delta_model_dice_r2_minus_r1": .1,
        },
        {
            "subject_id": "b", "exposure": "not_in_model_split",
            "r1_presence": "absent", "r2_presence": "present",
            "model_present": True, "model_r1_dice": None,
            "model_r2_dice": .4, "r1_r2_dice": None,
            "delta_model_dice_r2_minus_r1": None,
        },
    ]
    checkpoint = {"epoch": 7, "config": {"seed": 843, "intensity_augment": False}}
    r = evaluator.summarize(rows, checkpoint, "abc", "def", .5)
    assert r["r1_positive_count"] == 1 and r["r2_positive_count"] == 2
    assert r["paired_both_positive_mean_model_r1_dice"] == .6
    assert r["paired_both_positive_mean_model_r2_dice"] == .7
    assert r["exposure_counts"]["train"] == 1
