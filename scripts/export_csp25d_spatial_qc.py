"""Export private 3D CSP prediction overlays and connected-component QC.

Run on an allocated GPU node using the frozen best.pt and fixed 11-subject
validation manifest, never on the Narval login node. A single ZIP is produced
for 3D Slicer review at home. Outputs are PRIVATE MRI-derived data and must
never be pushed to public GitHub.

Per subject the ZIP includes:
  - Original byte-identical native-grid cropped T2 (not whole brain);
  - Binary manual and model masks, same affine and native 0.7-mm voxel grid;
  - Float32 P(CSP) map, no threshold adjustment;
  - Labelmap: 1=TP, 2=FP, 3=FN, 0=background;
  - Both 6-neighbor and 26-neighbor 3D connected-component measurements.

The original 2-epoch checkpoint and ground-truth masks are never modified.
All counts are checked against prior per-case metrics before ZIP creation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import nibabel as nib
import numpy as np
import torch

from csp25d_baseline import (
    CoronalUNet25D, load_case, load_csp25d_checkpoint,
    predict_case, read_manifest, usable_for_supervision,
)
from evaluate_csp25d_checkpoint import per_case_metrics, require_same_manifest


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def connected_components(mask, connectivity=26):
    """Return largest-first 3D 6- or 26-connected voxel clusters.

    No scipy or additional dependencies. Purely topological (native IJK):
    6-connectivity joins through faces; 26 also joins edges and corners.
    Deterministic tie handling allows a stable largest-component image.
    """
    if connectivity not in (6, 26):
        raise ValueError("Connectivity must be 6 or 26")
    mask = np.asarray(mask, dtype=bool)
    if mask.ndim != 3:
        raise ValueError("Connected-component mask must be 3D")
    neighbors = [
        (i, j, k)
        for i in (-1, 0, 1)
        for j in (-1, 0, 1)
        for k in (-1, 0, 1)
        if (i or j or k) and (connectivity == 26 or abs(i) + abs(j) + abs(k) == 1)
    ]
    remaining = set(map(tuple, np.argwhere(mask)))
    clusters = []
    while remaining:
        start = min(remaining)
        remaining.remove(start)
        component = [start]
        index = 0
        while index < len(component):
            x, y, z = component[index]
            index += 1
            for dx, dy, dz in neighbors:
                other = (x + dx, y + dy, z + dz)
                if other in remaining:
                    remaining.remove(other)
                    component.append(other)
        clusters.append(component)
    clusters.sort(key=lambda group: (-len(group), min(group)))
    return clusters


def spatial_qc(pred, ref):
    """Connected prediction & FP-only topology, with attached vs isolated FP."""
    pred = np.asarray(pred, dtype=bool)
    ref = np.asarray(ref, dtype=bool)
    if pred.shape != ref.shape or pred.ndim != 3:
        raise ValueError("Expected matching 3D prediction/reference masks")
    fp = pred & ~ref
    result = {}
    for conn in (6, 26):
        pred_components = connected_components(pred, conn)
        fp_components = connected_components(fp, conn)
        prefix = f"c{conn}_"
        result[prefix + "pred_components"] = len(pred_components)
        result[prefix + "largest_pred_voxels"] = len(pred_components[0]) if pred_components else 0
        result[prefix + "largest_pred_fraction"] = (
            len(pred_components[0]) / int(pred.sum()) if pred_components else 0.0
        )
        result[prefix + "fp_only_components"] = len(fp_components)
        result[prefix + "largest_fp_only_voxels"] = len(fp_components[0]) if fp_components else 0
        if pred_components:
            # Largest predicted object may be mostly correct OR entirely spurious.
            coords = np.asarray(pred_components[0], dtype=int)
            main_tp = int(ref[coords[:, 0], coords[:, 1], coords[:, 2]].sum())
            main_fp = len(pred_components[0]) - main_tp
        else:
            main_tp, main_fp = 0, 0
        result[prefix + "largest_pred_tp_voxels"] = main_tp
        result[prefix + "largest_pred_fp_voxels"] = main_fp
        result[prefix + "fp_voxels_outside_largest_pred"] = int(fp.sum()) - main_fp
        result[prefix + "extra_pred_components"] = max(0, len(pred_components) - 1)
        result[prefix + "extra_pred_voxels"] = int(pred.sum()) - result[prefix + "largest_pred_voxels"]
    return result


def error_labelmap(pred, ref):
    """Nonoverlapping 0/1/2/3 codes to distinguish overlap and both error types."""
    pred = np.asarray(pred, dtype=bool)
    ref = np.asarray(ref, dtype=bool)
    if pred.shape != ref.shape:
        raise ValueError("Prediction and reference have unequal shapes")
    result = np.zeros(ref.shape, dtype=np.uint8)
    result[pred & ref] = 1  # green TP
    result[pred & ~ref] = 2  # red FP
    result[~pred & ref] = 3  # blue FN
    return result


def _load_expected_metrics(path, subject_ids):
    if not path:
        return None
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        expected = list(csv.DictReader(handle))
    lookup = {row["subject_id"]: row for row in expected}
    if len(lookup) != len(expected) or set(lookup) != set(subject_ids):
        raise ValueError("Prior per-case metrics do not match exactly the selected validation subjects")
    return lookup


def verify_prior_metrics(subject_id, metrics, previous):
    """Never silently export predictions inconsistent with earlier reported Dice."""
    if previous is None:
        return
    before = previous[subject_id]
    for key in ("reference_voxels", "predicted_voxels", "true_positive_voxels",
                "false_positive_voxels", "false_negative_voxels"):
        if int(before[key]) != metrics[key]:
            raise ValueError(f"{subject_id}: reproducibility mismatch for {key}")
    if not np.isclose(float(before["dice"]), metrics["dice"], atol=1e-12, rtol=0):
        raise ValueError(f"{subject_id}: Dice differs from prior frozen evaluation")


def _write_nifti(array, affine, path, description):
    nii = nib.Nifti1Image(np.ascontiguousarray(array), affine)
    nii.header["descrip"] = description.encode("ascii")[:79]
    nib.save(nii, str(path))
    reopened = nib.load(str(path))
    if tuple(reopened.shape) != tuple(array.shape) or not np.allclose(reopened.affine, affine, atol=1e-5):
        raise ValueError("Saved NIfTI changed grid/affine: " + str(path))


def export_case_files(out_dir, subject_id, original_crop, prob, affine, ref, threshold):
    """Write a self-contained Slicer-ready case, preserving cropped T2 bytes."""
    out_dir.mkdir(parents=True, exist_ok=False)
    original_crop = Path(original_crop)
    shutil.copy2(original_crop, out_dir / "T2_crop.nii.gz")
    pred = prob >= threshold
    labels = error_labelmap(pred, ref)
    _write_nifti(ref.astype(np.uint8), affine, out_dir / "manual_CSP.nii.gz",
                 "Manual CSP, native cropped T2 grid, 1=positive")
    _write_nifti(pred.astype(np.uint8), affine, out_dir / "predicted_CSP.nii.gz",
                 "Frozen 2.5D U-Net prediction at threshold 0.5")
    _write_nifti(prob.astype(np.float32), affine, out_dir / "probability_CSP.nii.gz",
                 "Frozen 2.5D U-Net per-voxel CSP probability")
    _write_nifti(labels, affine, out_dir / "error_TP1_FP2_FN3.nii.gz",
                 "Labelmap 1=TP 2=FP 3=FN; background=0")

    t2 = nib.load(str(out_dir / "T2_crop.nii.gz"))
    if tuple(t2.shape) != tuple(ref.shape) or not np.allclose(t2.affine, affine, atol=1e-4, rtol=0):
        raise ValueError(f"{subject_id}: bundled T2 grid does not match QC labelmaps")
    return pred


def build_zip(output_dir, archive_path):
    """Archive only this private output dir; preserve SHA256 of every file."""
    output_dir = Path(output_dir)
    archive_path = Path(archive_path)
    if archive_path.exists():
        raise FileExistsError("Refusing overwrite of existing QC ZIP: " + str(archive_path))
    files = sorted(path for path in output_dir.rglob("*") if path.is_file())
    with zipfile.ZipFile(archive_path, mode="x", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as z:
        for path in files:
            z.write(path, arcname=str(Path(output_dir.name) / path.relative_to(output_dir)))
    with zipfile.ZipFile(archive_path, "r") as z:
        invalid = z.testzip()
        if invalid is not None:
            archive_path.unlink()
            raise IOError("ZIP CRC failure in: " + invalid)
    return archive_path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", required=True, help="Private fixed 44/11 subject split")
    p.add_argument("--checkpoint", required=True, help="Original pilot best.pt")
    p.add_argument("--prior-metrics", required=True,
                   help="Prior frozen 11-subject per_case_metrics.csv; required consistency guard")
    p.add_argument("--out", required=True, help="New private QC directory (must NOT exist)")
    p.add_argument("--expected-subjects", type=int, default=11)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--require-cuda", action="store_true")
    args = p.parse_args()

    output_dir = Path(args.out)
    archive = output_dir.with_suffix(".zip")
    if output_dir.exists() or archive.exists():
        raise SystemExit("Refusing to overwrite existing QC output or ZIP")
    if not 0 < args.threshold < 1:
        raise ValueError("Threshold must lie strictly between zero and one")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if args.require_cuda and device.type != "cuda":
        raise RuntimeError("GPU allocation required; do not run training inference on login node")
    checkpoint = load_csp25d_checkpoint(args.checkpoint, map_location="cpu")
    config = checkpoint["config"]
    manifest_hash = require_same_manifest(args.manifest, config)
    if checkpoint.get("epoch") != 1:
        raise ValueError("Expected frozen best.pt from epoch 1, not another checkpoint")
    rows = [r for r in read_manifest(args.manifest)
            if r["split"] == "val" and usable_for_supervision(r)]
    if len(rows) != args.expected_subjects or any(row["presence"] != "present" for row in rows):
        raise ValueError(f"Expected precisely {args.expected_subjects} positive validation subjects")
    prior = _load_expected_metrics(args.prior_metrics, [row["subject_id"] for row in rows])

    model = CoronalUNet25D(slices=int(config["slices"]), width=int(config["width"]))
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    model.to(device).eval()

    # No output artifact until all expected rows/paths are validated.
    for row in rows:
        for col in ("crop_t2", "crop_json", "source_mask"):
            if not Path(row[col]).is_file():
                raise FileNotFoundError(row[col])
    output_dir.mkdir(parents=True, exist_ok=False)
    cases_dir = output_dir / "cases"
    cases_dir.mkdir()

    output_rows = []
    for row in rows:
        subject_id = row["subject_id"]
        print(f"[SPATIAL QC] {subject_id}", flush=True)
        prob, predicted_affine, meta = predict_case(model, row, device, int(config["slices"]))
        _, ref, manual_affine, _ = load_case(
            subject_id, row["crop_t2"], row["crop_json"], row["source_mask"], row["presence"])
        if prob.shape != ref.shape or not np.allclose(predicted_affine, manual_affine, atol=1e-5, rtol=0):
            raise ValueError(f"Predicted/manual geometry mismatch: {subject_id}")
        if not np.isfinite(prob).all() or (prob < 0).any() or (prob > 1).any():
            raise ValueError(f"Invalid probability values: {subject_id}")
        voxel_size = float(abs(np.linalg.det(np.asarray(meta["original_affine"])[:3, :3])))
        pred = prob >= args.threshold
        measures = per_case_metrics(pred, ref, voxel_size)
        verify_prior_metrics(subject_id, measures, prior)
        topology = spatial_qc(pred, ref)
        export_case_files(cases_dir / subject_id, subject_id, row["crop_t2"],
                          prob, manual_affine, ref, args.threshold)
        output_rows.append({"subject_id": subject_id, **measures, **topology})
        print(f"[SPATIAL QC] {subject_id}: Dice={measures['dice']:.4f}, "
              f"predicted_26_components={topology['c26_pred_components']}, "
              f"largest_26_fraction={topology['c26_largest_pred_fraction']:.3f}, "
              f"outside_main_26_fp={topology['c26_fp_voxels_outside_largest_pred']}", flush=True)

    report = output_dir / "component_report.csv"
    with report.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    report_summary = {
        "experiment": "2.5D CSP frozen epoch-1 positive-only validation QC",
        "threshold": args.threshold,
        "checkpoint_epoch": checkpoint["epoch"],
        "checkpoint_sha256": sha256(args.checkpoint),
        "manifest_sha256": manifest_hash,
        "prior_metrics_sha256": sha256(args.prior_metrics),
        "subjects": len(output_rows),
        "all_positive_reference": True,
        "family_independence_verified": False,
        "mean_case_dice": float(np.mean([r["dice"] for r in output_rows])),
        "total_predicted_components_26": sum(r["c26_pred_components"] for r in output_rows),
        "subjects_with_multiple_predicted_components_26": sum(
            r["c26_pred_components"] > 1 for r in output_rows),
        "subjects_with_multiple_predicted_components_6": sum(
            r["c6_pred_components"] > 1 for r in output_rows),
        "total_fp_voxels": sum(r["false_positive_voxels"] for r in output_rows),
        "total_fp_outside_largest_predicted_26": sum(
            r["c26_fp_voxels_outside_largest_pred"] for r in output_rows),
        "error_map_codes": {"0": "Background", "1": "True positive", "2": "False positive", "3": "False negative"},
    }
    (output_dir / "summary.json").write_text(json.dumps(report_summary, indent=2) + "\n",
                                             encoding="utf-8")

    local_script = Path(__file__).with_name("slicer_csp25d_qc_loader.py")
    if not local_script.is_file():
        raise FileNotFoundError("Slicer helper is missing from feature branch: " + str(local_script))
    shutil.copy2(local_script, output_dir / local_script.name)
    guide = [
        "CSP_DEEP_SEG: PRIVATE manual spatial QC export",
        "11 positive reference cases; exploratory subject-level validation only.",
        "HCP family IDs unavailable and crop rule calibrated on development data.",
        "",
        "Each cases/<subject_id>/ folder contains:",
        "- T2_crop.nii.gz -- exact T2 ROI used by model; no resampling.",
        "- manual_CSP.nii.gz -- manual binary mask (0/1).",
        "- predicted_CSP.nii.gz -- 0/1 predicted at frozen P>=0.5.",
        "- probability_CSP.nii.gz -- per voxel sigmoid probability (0-1).",
        "- error_TP1_FP2_FN3.nii.gz -- 0 background, 1 TP, 2 FP, 3 FN.",
        "",
        "In 3D Slicer, open Python Console (View > Python Interactor).",
        "Paste ONE line with the actual extracted Windows path:",
        "exec(open(r'D:\\CSP_DEEP_SEG\\derived\\csp25d_spatial_qc\\slicer_csp25d_qc_loader.py', encoding='utf-8').read()); load_csp25d_qc()",
        "Choose an extracted cases/<subject_id> directory in the file dialog.",
        "Green = correct overlap, red = extra prediction, blue = missed CSP.",
        "Reference and Predicted segmentations are also loaded, initially hidden.",
        "Use Segmentations module to toggle them; start with coronal, inspect all 3 planes.",
        "",
        "Read component_report.csv for 6-neighbor and 26-neighbor component counts.",
        "A FP-only component can touch the main predicted CSP and is NOT necessarily",
        "a disconnected prediction. Compare largest predicted cluster and FP outside it.",
        "Never publish the ZIP, images, private per-subject CSV or HCP subject metadata.",
    ]
    (output_dir / "README_QC.txt").write_text("\n".join(guide) + "\n", encoding="utf-8")

    # Hash every file to prove the ZIP can be restored exactly at home.
    contents = sorted(x for x in output_dir.rglob("*") if x.is_file())
    with (output_dir / "file_sha256.csv").open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=["path", "sha256", "bytes"])
        writer.writeheader()
        for item in contents:
            writer.writerow({"path": str(item.relative_to(output_dir)).replace("\\", "/"),
                             "sha256": sha256(item), "bytes": item.stat().st_size})
    build_zip(output_dir, archive)
    print(f"[SPATIAL QC COMPLETE] cases={len(rows)} "
          f"mean_dice={report_summary['mean_case_dice']:.8f} "
          f"multi_component_26={report_summary['subjects_with_multiple_predicted_components_26']} "
          f"FP_outside_main_26={report_summary['total_fp_outside_largest_predicted_26']}",
          flush=True)
    print(f"PRIVATE archive: {archive}; SHA256={sha256(archive)}; bytes={archive.stat().st_size}",
          flush=True)


if __name__ == "__main__":
    main()
