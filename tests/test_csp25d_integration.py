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


def test_volume_and_tiny_object_metrics():
    from csp25d_baseline import binary_case_metrics
    gt = np.zeros((3, 4, 5), dtype=np.uint8)
    prediction = np.zeros_like(gt)
    gt[1, 2, 3] = 1
    prediction[1, 2, 3] = 1
    prediction[1, 2, 2] = 1
    metrics = binary_case_metrics(prediction, gt, .343)
    assert np.isclose(metrics["dice"], 2 / 3)
    assert metrics["recall"] == 1
    assert np.isclose(metrics["reference_volume_mm3"], .343)
    assert np.isclose(metrics["volume_error_mm3"], .343)
    assert np.isclose(metrics["false_positive_volume_mm3"], .343)
    empty = binary_case_metrics(prediction, np.zeros_like(gt), .343)
    assert empty["dice"] is None and empty["recall"] is None
    assert np.isclose(empty["false_positive_volume_mm3"], 2 * .343)


def test_exact_native_reconstruction_roundtrip(tmp_path):
    from csp25d_baseline import reconstruct_native_grid, crop_native_mask
    row, _, _, _ = make_case(tmp_path)
    meta = json.loads(Path(row["crop_json"]).read_text())
    full = np.asanyarray(nib.load(row["source_mask"]).dataobj)
    affine = nib.load(row["source_mask"]).affine
    crop_nii = nib.load(row["crop_t2"])
    extracted = crop_native_mask(full, meta, affine, crop_nii.shape, crop_nii.affine)
    reconstructed = reconstruct_native_grid(extracted, meta)
    np.testing.assert_array_equal(reconstructed, full)
    with pytest.raises(ValueError, match="Predicted crop"):
        reconstruct_native_grid(np.zeros((1, 1, 1)), meta)


def test_synthetic_2d_unet_can_overfit_tiny_signal():
    """Fixed one-example optimizer diagnostic, NOT a real CSP Dice experiment."""
    import torch
    from csp25d_baseline import CoronalUNet25D, bce_dice_loss
    torch.manual_seed(843)
    x = torch.rand(1, 7, 32, 24) * .02
    x[:, :, 12:17, 10:15] += .9
    y = torch.zeros(1, 1, 32, 24)
    y[:, :, 12:17, 10:15] = 1
    net = CoronalUNet25D(slices=7, width=8)
    optim = torch.optim.AdamW(net.parameters(), lr=.004)
    losses = []
    for _ in range(12):
        optim.zero_grad()
        loss = bce_dice_loss(net(x), y)
        loss.backward()
        optim.step()
        losses.append(float(loss.detach()))
    assert losses[-1] < .85 * losses[0]


def test_finished_batch_inventory_exact_geometry_and_source_voxels(tmp_path):
    """All-crop preflight also works without manual CSP reference labels."""
    from inventory_csp25d_crops import audit_one, collect_files, CROP_SUFFIX
    row, rules_path, crop_path, _ = make_case(tmp_path)
    meta_path = Path(row["crop_json"])
    meta = json.loads(meta_path.read_text())
    meta["cropped_shape_kji"] = [9, 9, 9]
    meta["retained_voxel_fraction"] = 9 ** 3 / 14 ** 3
    meta_path.write_text(json.dumps(meta))
    rule = json.loads(rules_path.read_text())["rules"]["proportional"]
    fraction, shape = audit_one(row["subject_id"], crop_path, meta_path, rule,
                                original=Path(row["original_t2"]), verify_original=True)
    assert np.isclose(fraction, 9 ** 3 / 14 ** 3)
    assert shape == "9x9x9"
    assert collect_files(tmp_path, CROP_SUFFIX)[row["subject_id"]] == crop_path


def test_finished_batch_inventory_flags_wrong_origin_and_rule(tmp_path):
    from inventory_csp25d_crops import audit_one
    row, rules_path, crop_path, _ = make_case(tmp_path)
    meta_path = Path(row["crop_json"])
    meta = json.loads(meta_path.read_text())
    meta["cropped_shape_kji"] = [9, 9, 9]
    meta["retained_voxel_fraction"] = 9 ** 3 / 14 ** 3
    meta_path.write_text(json.dumps(meta))
    rule = json.loads(rules_path.read_text())["rules"]["proportional"]
    with pytest.raises(ValueError, match="frozen"):
        audit_one(row["subject_id"], crop_path, meta_path, {"mode": "proportional"})
    meta["start_ijk"] = [3, 3, 4]
    meta["end_ijk"] = [12, 12, 13]
    meta_path.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="affine"):
        audit_one(row["subject_id"], crop_path, meta_path, rule)


def test_inventory_ignores_incomplete_staging_and_detects_duplicates(tmp_path):
    from inventory_csp25d_crops import collect_files, CROP_SUFFIX
    filename = "111111" + CROP_SUFFIX
    (tmp_path / filename).touch()
    staging = tmp_path / ".roi_staging_resume"
    staging.mkdir()
    (staging / filename).touch()
    assert len(collect_files(tmp_path, CROP_SUFFIX)) == 1
    duplicate = tmp_path / "extra"
    duplicate.mkdir()
    (duplicate / filename).touch()
    with pytest.raises(ValueError, match="Duplicate"):
        collect_files(tmp_path, CROP_SUFFIX)


def test_real_mask_overfit_diagnostic_selects_maximum_positive_training_slice(tmp_path):
    from overfit_csp25d_real import prepare_examples, training_slice_scores
    from csp25d_baseline import CoronalUNet25D
    import torch
    row, _, _, _ = make_case(tmp_path)
    cases = prepare_examples([row], slices=7)
    assert len(cases) == 1
    x, y, sid, j, voxel_volume = cases[0]
    assert x.shape == (1, 7, 9, 9)
    assert y.shape == (1, 1, 9, 9)
    assert y.sum() == 1
    assert sid == row["subject_id"]
    assert j == 4 and np.isclose(voxel_volume, .7 ** 3)
    net = CoronalUNet25D(slices=7, width=8)
    scores = training_slice_scores(net, cases, torch.device("cpu"))
    assert len(scores) == 1
    assert 0 <= scores[0]["train_slice_dice"] <= 1


def test_overfit_diagnostic_refuses_validation_and_absent_subjects(tmp_path):
    from overfit_csp25d_real import prepare_examples
    row, _, _, _ = make_case(tmp_path)
    with pytest.raises(ValueError, match="TRAIN"):
        prepare_examples([dict(row, split="val")])
    with pytest.raises(ValueError, match="positive TRAIN"):
        prepare_examples([dict(row, presence="absent")])
