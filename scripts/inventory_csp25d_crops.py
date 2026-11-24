"""Inventory the existing native-resolution HCP CSP ROI batch without recropping.

Run on the PRIVATE Windows workstation. Report and subject paths stay PRIVATE.
By default checks provenance, orientation, shapes, and affine translation for
every finished crop. --verify-original additionally reads full source volumes
and checks actual voxel equality (more I/O). No labels are read or modified.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

from native_nifti_orientation import extract_original_native_crop

ORIGINAL_SUFFIX = "_3T_T2w_SPC1.nii.gz"
CROP_SUFFIX = "_3T_T2w_SPC1_proportional_reduced.nii.gz"
META_SUFFIX = "_3T_T2w_SPC1_proportional_reduced.crop.json"


def is_staging(path):
    return any(part.startswith(".roi_staging") for part in path.parts)


def collect_files(directory, suffix):
    """Map exact six-digit HCP IDs to paths; reject ambiguous duplicates."""
    root = Path(directory)
    if not root.is_dir():
        raise FileNotFoundError(root)
    found = {}
    for path in root.rglob("*" + suffix):
        if is_staging(path.relative_to(root)):
            continue
        sid = path.name[:-len(suffix)]
        if len(sid) != 6 or not sid.isdecimal():
            raise ValueError("Unexpected subject filename: " + str(path))
        if sid in found:
            raise ValueError("Duplicate output for subject " + sid +
                             ": " + str(found[sid]) + " and " + str(path))
        found[sid] = path
    return found


def verify_geometry(meta, subject_id, crop_shape, crop_affine, frozen_rule):
    """Check Slicer crop provenance independently of mask availability."""
    source_name = str(meta.get("source_file") or "").replace(chr(92), "/").split("/")[-1]
    if source_name != subject_id + ORIGINAL_SUFFIX:
        raise ValueError("Incorrect source SPC1 filename")
    if meta.get("mode") != "proportional" or meta.get("rule") != frozen_rule:
        raise ValueError("Crop does not match the frozen unshifted proportional rule")
    orig = np.asarray(meta["source_shape_kji"][::-1], dtype=int)
    start = np.asarray(meta["start_ijk"], dtype=int)
    end = np.asarray(meta["end_ijk"], dtype=int)
    if orig.shape != (3,) or start.shape != (3,) or end.shape != (3,):
        raise ValueError("Invalid original/crop coordinate dimensions")
    if np.any(orig <= 0) or np.any(start < 0) or np.any(end <= start) or np.any(end > orig):
        raise ValueError("Invalid original/crop coordinate bounds")
    if tuple(end - start) != tuple(crop_shape):
        raise ValueError("Crop dimensions differ from metadata")
    if tuple(meta["cropped_shape_kji"][::-1]) != tuple(crop_shape):
        raise ValueError("Cropped KJI dimensions differ from saved NIfTI")
    original_affine = np.asarray(meta["original_affine"], dtype=float)
    recorded_affine = np.asarray(meta["output_affine"], dtype=float)
    actual_affine = np.asarray(crop_affine, dtype=float)
    if any(a.shape != (4, 4) or not np.isfinite(a).all()
           for a in (original_affine, recorded_affine, actual_affine)):
        raise ValueError("Invalid affine matrix")
    expected = original_affine.copy()
    expected[:3, 3] = (original_affine @ np.r_[start, 1.0])[:3]
    if not np.allclose(recorded_affine, expected, atol=1e-3, rtol=0):
        raise ValueError("Incorrect crop affine translation in metadata")
    if not np.allclose(actual_affine, expected, atol=1e-3, rtol=0):
        raise ValueError("Saved NIfTI affine differs from native crop origin")
    if np.argmax(np.abs(actual_affine[:3, :3]), axis=0).tolist() != [0, 1, 2]:
        raise ValueError("Native IJK axes are not dominant LR/AP/SI for coronal model")
    if min(crop_shape[0], crop_shape[2]) < 8:
        raise ValueError("Coronal image plane too small for 3 max-pooling levels")
    retained = float(np.prod(end - start) / np.prod(orig))
    if not (0 < retained < 1):
        raise ValueError("Input is not a reduced crop")
    if not np.isclose(retained, meta["retained_voxel_fraction"], rtol=0, atol=1e-5):
        raise ValueError("Recorded retained voxel fraction is inconsistent")
    return retained


def audit_one(sid, crop, metadata, frozen_rule, original=None, verify_original=False):
    import nibabel as nib

    meta = json.loads(metadata.read_text(encoding="utf-8"))
    image = nib.load(str(crop))
    fraction = verify_geometry(meta, sid, image.shape, image.affine, frozen_rule)
    if verify_original:
        if original is None:
            raise ValueError("Original source T2 unavailable for voxel equality")
        source = nib.load(str(original))
        # Slicer may store the native source grid with flipped/permuted axes.
        # Match the recorded RAS affine via exact index operations (no resampling).
        original_roi = extract_original_native_crop(source, meta)
        stored = np.asarray(image.dataobj)
        if original_roi.shape != stored.shape or not np.allclose(
            original_roi, stored, atol=1e-4, rtol=0, equal_nan=True
        ):
            raise ValueError("Source T2 voxel values differ from the saved crop")
    return fraction, "x".join(map(str, image.shape))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crop-dir", required=True, help="Existing FINAL batch ROI directory")
    parser.add_argument("--rule-json", required=True, help="Frozen corrected calibration")
    parser.add_argument("--report", required=True, help="PRIVATE subject-level audit CSV")
    parser.add_argument("--source-root", help="Original T2 root; enables detection of missing crops")
    parser.add_argument("--verify-original", action="store_true", help="Read original T2 and compare source voxels")
    parser.add_argument("--subject-id", action="append", help="Optionally restrict audit to selected IDs")
    args = parser.parse_args()
    if args.verify_original and not args.source_root:
        parser.error("--verify-original requires --source-root")
    rules = json.loads(Path(args.rule_json).read_text(encoding="utf-8"))
    frozen = rules["rules"]["proportional"]
    crops = collect_files(args.crop_dir, CROP_SUFFIX)
    metadata = collect_files(args.crop_dir, META_SUFFIX)
    originals = collect_files(args.source_root, ORIGINAL_SUFFIX) if args.source_root else {}
    expected = set(originals) if args.source_root else set(crops) | set(metadata)
    if args.subject_id:
        unknown = set(args.subject_id) - expected
        if unknown:
            parser.error("Subject IDs not found among expected scans: " + str(sorted(unknown)))
        expected &= set(args.subject_id)
    if not expected:
        raise SystemExit("FAIL: no subject files discovered")
    rows = []
    for sid in sorted(expected):
        crop, meta, source = crops.get(sid), metadata.get(sid), originals.get(sid)
        row = dict(subject_id=sid, status="PASS", error="", crop_t2=str(crop or ""),
                   crop_json=str(meta or ""), original_t2=str(source or ""),
                   retained_fraction="", shape_ijk="", source_voxels_checked=args.verify_original)
        try:
            if crop is None or meta is None:
                raise ValueError("Missing final crop NIfTI or matching .crop.json")
            fraction, shape = audit_one(
                sid, crop, meta, frozen, original=source,
                verify_original=args.verify_original)
            row.update(retained_fraction=f"{fraction:.8f}", shape_ijk=shape)
        except Exception as exc:
            row.update(status="FAIL", error=str(exc))
        rows.append(row)
        print(f"[{row['status']}] {sid}: {row['error']}")
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    counts = Counter(row["status"] for row in rows)
    extra = (set(crops) | set(metadata)) - set(originals) if args.source_root else set()
    print(f"[INVENTORY] expected={len(expected)} PASS={counts['PASS']} "
          f"FAIL={counts['FAIL']} extra_output_ids={len(extra)}; PRIVATE report: {report}")
    if extra:
        print("WARNING: completed output subject IDs not found in source root; inspect the private CSV/paths")
    if counts["FAIL"] or extra:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
