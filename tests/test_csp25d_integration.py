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


def test_manifest_reconcile_uses_actual_nested_crop_paths_and_preserves_labels():
    from reconcile_csp25d_manifest import reconcile
    cohort = [
        dict(subject_id="111111", source_t2=r"D:\\T2w\\111111\\111111_3T_T2w_SPC1.nii.gz",
             mask_path=r"D:\\CSP_Seg\\111111.nii.gz", split="dev",
             presence="present", qc="pass"),
        dict(subject_id="222222", source_t2=r"D:\\T2w\\222222\\222222_3T_T2w_SPC1.nii.gz",
             mask_path="", split="dev", presence="absent", qc="pass"),
    ]
    inventory = [
        dict(subject_id="111111", status="PASS",
             crop_t2=r"D:\\roi_batch\\cohort\\nested\\111111_3T_T2w_SPC1_proportional_reduced.nii.gz",
             crop_json=r"D:\\roi_batch\\cohort\\nested\\111111_3T_T2w_SPC1_proportional_reduced.crop.json",
             original_t2=cohort[0]["source_t2"], error=""),
        dict(subject_id="222222", status="FAIL", error="Expected missing exception")
    ]
    accepted, rejected = reconcile(cohort, inventory)
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected[0]["subject_id"] == "222222"
    assert accepted[0]["crop_t2"] == inventory[0]["crop_t2"]
    assert accepted[0]["source_mask"] == cohort[0]["mask_path"]
    assert accepted[0]["presence"] == "present"
    assert accepted[0]["split"] == "unassigned"


def test_manifest_reconcile_refuses_duplicate_subjects_and_source_mismatch():
    from reconcile_csp25d_manifest import reconcile
    row = dict(subject_id="111111", source_t2="111111_3T_T2w_SPC1.nii.gz",
               split="train", presence="present", qc="pass")
    with pytest.raises(ValueError, match="duplicate"):
        reconcile([row, dict(row)], [])
    inventory = [dict(subject_id="111111", status="PASS", crop_t2="111111_3T_T2w_SPC1_proportional_reduced.nii.gz",
                      crop_json="111111_3T_T2w_SPC1_proportional_reduced.crop.json",
                      original_t2="222222_3T_T2w_SPC1.nii.gz")]
    accepted, rejected = reconcile([row], inventory)
    assert not accepted and rejected[0]["reason"].startswith("Original T2")


def make_reindexed_slicer_case(tmp_path, axes, flips):
    """Simulate Slicer's lossless native voxel reindexing of a raw NIfTI."""
    row, rules_path, crop_path, _ = make_case(tmp_path)
    source = nib.load(row["original_t2"])
    raw = np.asarray(source.dataobj)
    native_mask = np.asarray(nib.load(row["source_mask"]).dataobj)
    transform = np.eye(4)
    transform[:3, :3] = 0
    for target_axis, source_axis in enumerate(axes):
        transform[source_axis, target_axis] = -1 if flips[target_axis] else 1
        if flips[target_axis]:
            transform[source_axis, 3] = source.shape[source_axis] - 1
    slicer_affine = source.affine @ transform

    def transform_array(array):
        result = np.transpose(array, axes)
        for axis, flipped in enumerate(flips):
            if flipped:
                result = np.flip(result, axis=axis)
        return np.ascontiguousarray(result)

    raw_slicer = transform_array(raw)
    mask_slicer = transform_array(native_mask)
    meta_path = Path(row["crop_json"])
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    start, end = np.array(meta["start_ijk"]), np.array(meta["end_ijk"])
    crop_affine = slicer_affine.copy()
    crop_affine[:3, 3] = (slicer_affine @ np.r_[start, 1.0])[:3]
    cropped_slicer = raw_slicer[tuple(slice(lo, hi) for lo, hi in zip(start, end))]
    nib.save(nib.Nifti1Image(cropped_slicer, crop_affine), crop_path)
    nib.save(nib.Nifti1Image(mask_slicer, slicer_affine), row["source_mask"])
    meta["original_affine"] = slicer_affine.tolist()
    meta["output_affine"] = crop_affine.tolist()
    meta["source_shape_kji"] = list(raw_slicer.shape[::-1])
    meta["cropped_shape_kji"] = list(cropped_slicer.shape[::-1])
    meta["retained_voxel_fraction"] = cropped_slicer.size / raw.size
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    return row, rules_path, crop_path, meta_path


@pytest.mark.parametrize("axes,flips", [
    ((0, 1, 2), (False, False, True)),  # Observed Slicer reversal of K.
    ((0, 1, 2), (True, False, True)),   # Multiple sign reversals.
])
def test_slicer_native_axis_reindexing_retains_exact_original_voxels(tmp_path, axes, flips):
    from inventory_csp25d_crops import audit_one
    row, rule_path, crop_path, meta_path = make_reindexed_slicer_case(
        tmp_path, axes, flips
    )
    result = audit_case(row, rule_path, verify_original=True)
    assert result["mask_voxels"] == 1
    frozen_rule = json.loads(rule_path.read_text())["rules"]["proportional"]
    retained, shape = audit_one(row["subject_id"], crop_path, meta_path,
                                frozen_rule, original=Path(row["original_t2"]),
                                verify_original=True)
    assert np.isclose(retained, 9 ** 3 / 14 ** 3)
    assert shape == "9x9x9"


def test_slicer_axis_reindexed_crop_still_detects_modified_original_voxel(tmp_path):
    row, rules_path, crop_path, _ = make_reindexed_slicer_case(
        tmp_path, (0, 1, 2), (False, False, True)
    )
    image = nib.load(str(crop_path))
    modified = np.asarray(image.dataobj).copy()
    modified[2, 2, 2] += 1
    nib.save(nib.Nifti1Image(modified, image.affine), crop_path)
    with pytest.raises(ValueError, match="voxel values differ"):
        audit_case(row, rules_path, verify_original=True)


def test_slicer_axis_reindexing_rejects_unexplained_affine(tmp_path):
    from native_nifti_orientation import extract_original_native_crop
    row, _, _, meta_path = make_reindexed_slicer_case(
        tmp_path, (0, 1, 2), (False, False, True)
    )
    metadata = json.loads(meta_path.read_text())
    metadata["original_affine"][0][3] += 5
    with pytest.raises(ValueError, match="cannot be uniquely matched"):
        extract_original_native_crop(nib.load(row["original_t2"]), metadata)


def test_signed_permutation_voxel_proof_but_coronal_model_still_rejects_axis_swap(tmp_path):
    """The verifier supports permutations, but the frozen model forbids swapped MRI axes."""
    from native_nifti_orientation import extract_original_native_crop
    row, rules_path, crop_path, meta_path = make_reindexed_slicer_case(
        tmp_path, (2, 1, 0), (False, False, True)
    )
    metadata = json.loads(meta_path.read_text())
    expected = extract_original_native_crop(nib.load(row["original_t2"]), metadata)
    np.testing.assert_array_equal(expected, np.asarray(nib.load(str(crop_path)).dataobj))
    with pytest.raises(ValueError, match="Non-coronal native axis order"):
        audit_case(row, rules_path, verify_original=True)


def test_compact_csp_mask_export_preserves_every_label_and_loads(tmp_path):
    """An exported native 1% ROI labelmap can replace its full-brain source in TRAIN."""
    from prepare_csp25d_roi_masks import export_one
    from csp25d_baseline import load_case
    row, rules_path, crop_path, _ = make_case(tmp_path)
    target = export_one(row, tmp_path / "roi_masks")
    assert target.name == "111111_csp_roi_mask.nii.gz"
    original = nib.load(row["source_mask"])
    reference = nib.load(str(target))
    crop = nib.load(str(crop_path))
    assert reference.shape == crop.shape
    np.testing.assert_allclose(reference.affine, crop.affine, atol=1e-3)
    assert np.asarray(reference.dataobj).dtype == np.uint8
    assert np.count_nonzero(np.asarray(reference.dataobj)) == np.count_nonzero(np.asarray(original.dataobj))
    compact_row = dict(row, source_mask=str(target))
    image, mask, _, _ = load_case(row["subject_id"], row["crop_t2"], row["crop_json"], str(target), "present")
    assert mask.sum() == 1 and image.shape == mask.shape
    assert audit_case(compact_row, rules_path, verify_original=True)["mask_voxels"] == 1
    # Rerunning the exporter is idempotent, never changes matching data.
    assert export_one(row, tmp_path / "roi_masks") == target


def test_compact_mask_rejects_wrong_affine_and_nonbinary_values(tmp_path):
    from prepare_csp25d_roi_masks import export_one
    from csp25d_baseline import load_case
    row, _, crop_path, _ = make_case(tmp_path)
    target = export_one(row, tmp_path / "roi_masks")
    good = nib.load(str(target))
    data = np.asarray(good.dataobj)
    shifted = good.affine.copy()
    shifted[0, 3] += 4
    bad_path = tmp_path / "wrong_affine.nii.gz"
    nib.save(nib.Nifti1Image(data, shifted), bad_path)
    with pytest.raises(ValueError, match="Cropped CSP mask affine"):
        load_case(row["subject_id"], row["crop_t2"], row["crop_json"], str(bad_path), "present")
    corrupt = data.copy()
    corrupt[0, 0, 0] = 2
    bad_values = tmp_path / "nonbinary.nii.gz"
    nib.save(nib.Nifti1Image(corrupt, good.affine), bad_values)
    with pytest.raises(ValueError, match="Nonbinary mask"):
        load_case(row["subject_id"], row["crop_t2"], row["crop_json"], str(bad_values), "present")


def test_roi_mask_export_refuses_loss_of_any_reference_voxel(tmp_path):
    from prepare_csp25d_roi_masks import export_one
    row, _, _, _ = make_case(tmp_path)
    ref = nib.load(row["source_mask"])
    data = np.asarray(ref.dataobj).copy()
    data[0, 0, 0] = 1  # Outside the 2:11,3:12,4:13 crop
    nib.save(nib.Nifti1Image(data, ref.affine), row["source_mask"])
    with pytest.raises(ValueError, match="Full CSP containment"):
        export_one(row, tmp_path / "roi_masks")


def test_unknown_family_exploratory_split_volume_stratified_and_deterministic():
    """Subject-disjoint 55-case fallback keeps every reviewed-but-ineligible row unassigned."""
    from split_csp25d_exploratory import stratify_subjects
    rows = [
        dict(subject_id=str(200000 + i), split="unassigned", presence="present",
             qc="provisional", source_mask=f"{i}.nii.gz", family_group="")
        for i in range(55)
    ]
    rows += [
        dict(subject_id="999001", split="unassigned", presence="present",
             qc="needs_review", source_mask="review.nii.gz", family_group=""),
        dict(subject_id="999002", split="unassigned", presence="absent",
             qc="provisional", source_mask="", family_group=""),
    ]
    audit = [
        dict(subject_id=str(200000 + i), status="PASS", mask_voxels=str(i + 1))
        for i in range(55)
    ]
    result, bins = stratify_subjects(rows, audit, seed=843)
    repeat, repeat_bins = stratify_subjects(rows, audit, seed=843)
    assert (result, bins) == (repeat, repeat_bins)
    assert len(result) == 55
    assert sum(x == "val" for x in result.values()) == 11
    assert sum(x == "train" for x in result.values()) == 44
    assert "999001" not in result and "999002" not in result
    for index in (1, 2, 3):
        members = {sid for sid, b in bins.items() if b == index}
        assert any(result[sid] == "train" for sid in members)
        assert any(result[sid] == "val" for sid in members)
    assert [sum(bins[sid] == j and result[sid] == "val" for sid in result)
            for j in (1, 2, 3)] == [4, 4, 3]


def test_unknown_family_split_rejects_partial_audits_and_family_info():
    from split_csp25d_exploratory import stratify_subjects
    rows = [
        dict(subject_id=str(i), split="unassigned", presence="present",
             qc="provisional", source_mask="mask.nii.gz", family_group="")
        for i in range(12)
    ]
    audit = [dict(subject_id=str(i), status="PASS", mask_voxels=str(i + 1))
             for i in range(12)]
    with pytest.raises(ValueError, match="every eligible"):
        stratify_subjects(rows, audit[:-1])
    with pytest.raises(ValueError, match="nonpassing"):
        stratify_subjects(rows, [dict(row, status="FAIL") if row["subject_id"] == "1" else row for row in audit])
    with pytest.raises(ValueError, match="Family group"):
        stratify_subjects([dict(row, family_group="A") if row["subject_id"] == "1" else row for row in rows], audit)
    with pytest.raises(ValueError, match="assigned splits"):
        stratify_subjects([dict(row, split="train") if row["subject_id"] == "1" else row for row in rows], audit)


def test_staging_archive_preserves_44_11_split_and_private_sha256(tmp_path):
    """ZIP has exactly 55 compact native ROI cases and auditable manifest paths."""
    import csv
    import hashlib
    import zipfile
    from package_csp25d_pilot import make_package
    root = tmp_path / "private_windows"
    root.mkdir()
    columns = ["subject_id", "split", "family_group", "crop_t2", "crop_json",
               "source_mask", "presence", "qc", "negative_confidence", "original_t2"]
    rows, checks = [], []
    for i in range(55):
        sid = str(200000 + i)
        folder = root / sid
        folder.mkdir()
        t2 = folder / (sid + "_3T_T2w_SPC1_proportional_reduced.nii.gz")
        crop_json = folder / (sid + "_3T_T2w_SPC1_proportional_reduced.crop.json")
        mask = folder / (sid + "_csp_roi_mask.nii.gz")
        t2.write_bytes(b"csp t2 compressed " + sid.encode())
        crop_json.write_bytes(b'{"start_ijk":[1,2,3]}')
        mask.write_bytes(b"binary compact mask " + sid.encode())
        sidecar = folder / (sid + "_csp_roi_mask.provenance.json")
        sidecar.write_text(json.dumps({
            "subject_id": sid, "mask_voxels": i + 1,
            "cropped_mask_sha256": hashlib.sha256(mask.read_bytes()).hexdigest(),
            "crop_json_sha256": hashlib.sha256(crop_json.read_bytes()).hexdigest(),
        }))
        rows.append(dict(subject_id=sid, split="train" if i < 44 else "val",
                         family_group="", crop_t2=str(t2), crop_json=str(crop_json),
                         source_mask=str(mask), original_t2=str(folder / "wholebrain.nii.gz"),
                         presence="present", qc="provisional", negative_confidence=""))
        checks.append(dict(subject_id=sid, status="PASS", mask_voxels=str(i+1)))
    manifest = root / "split.csv"
    audit = root / "audit.csv"
    with manifest.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    with audit.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["subject_id", "status", "mask_voxels"])
        writer.writeheader()
        writer.writerows(checks)
    rule = root / "rules.json"
    rule.write_text('{"rules":{"proportional":{"mode":"proportional"}}}')
    archive = root / "pilot.zip"
    return_values = make_package(manifest, audit, rule, archive, "/scratch/user/csp25d/seed843")
    assert return_values == archive
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == 224  # 55 x 4 + 3 metadata + 1 SHA256 manifest
        with z.open("manifests/model_25d_trainval_seed843_linux.csv") as handle:
            linux = list(csv.DictReader(handle.read().decode("utf-8").splitlines()))
        assert len(linux) == 55 and sum(x["split"] == "val" for x in linux) == 11
        assert all(x["original_t2"] == "" and x["source_mask"].startswith("/scratch/user/csp25d/seed843/masks/")
                   for x in linux)
        for entry in csv.DictReader(z.read("manifests/file_sha256.csv").decode().splitlines()):
            assert hashlib.sha256(z.read(entry["path"])).hexdigest() == entry["sha256"]
            assert len(z.read(entry["path"])) == int(entry["bytes"])
    with pytest.raises(FileExistsError, match="existing package"):
        make_package(manifest, audit, rule, archive, "/scratch/user/csp25d/seed843")

    # The exporter sidecar is a hard integrity boundary, not decorative metadata.
    (root / "200000" / "200000_csp_roi_mask.nii.gz").write_bytes(b"tampered mask")
    with pytest.raises(ValueError, match="SHA256 differs"):
        make_package(manifest, audit, rule, root / "second.zip", "/scratch/user/csp25d/seed843")


def test_checkpoint_per_subject_metrics_native_voxel_volume_and_overlap():
    from evaluate_csp25d_checkpoint import per_case_metrics
    ref = np.zeros((2, 4, 3), dtype=np.uint8)
    pred = np.zeros_like(ref)
    ref[0, 1, 0] = 1
    ref[0, 2, 0] = 1
    ref[1, 2, 0] = 1
    pred[0, 1, 0] = 1
    pred[1, 2, 0] = 1
    pred[1, 3, 0] = 1
    met = per_case_metrics(pred, ref, 0.343)
    assert (met["true_positive_voxels"], met["false_positive_voxels"],
            met["false_negative_voxels"]) == (2, 1, 1)
    assert met["dice"] == pytest.approx(2 / 3)
    assert met["iou"] == pytest.approx(1 / 2)
    assert met["precision"] == pytest.approx(2 / 3)
    assert met["recall"] == pytest.approx(2 / 3)
    assert met["reference_volume_mm3"] == pytest.approx(1.029)
    assert met["predicted_volume_mm3"] == pytest.approx(1.029)
    assert met["absolute_volume_error_mm3"] == 0


def test_checkpoint_per_subject_metrics_empty_prediction_and_manifest_guard(tmp_path):
    import hashlib
    from evaluate_csp25d_checkpoint import per_case_metrics, require_same_manifest
    ref = np.ones((2, 2, 1), dtype=np.uint8)
    pred = np.zeros_like(ref)
    m = per_case_metrics(pred, ref, .343)
    assert m["dice"] == 0 and m["recall"] == 0 and m["precision"] is None
    assert m["false_negative_voxels"] == 4
    with pytest.raises(ValueError, match="reference-positive"):
        per_case_metrics(pred, pred, .343)
    with pytest.raises(ValueError, match="different shapes"):
        per_case_metrics(pred[:1], ref, .343)

    manifest = tmp_path / "private_manifest.csv"
    manifest.write_text("example,content\n", encoding="utf-8")
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert require_same_manifest(manifest, {"manifest_sha256": digest}) == digest
    with pytest.raises(ValueError, match="differs"):
        require_same_manifest(manifest, {"manifest_sha256": "invalid"})
    with pytest.raises(ValueError, match="lacks"):
        require_same_manifest(manifest, {})
