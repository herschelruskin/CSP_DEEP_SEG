"""Fail-visible native-grid crop audit before any CSP 2.5D GPU training.

This runs on a machine with nibabel and access to the PRIVATE manifest/data.
With --verify-original it also proves that the saved Slicer crop contains
exactly the native source T2 voxel values (no resampling or intensity change).
Reports are PRIVATE and must never be committed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from csp25d_baseline import load_case, read_manifest, usable_for_supervision
from native_nifti_orientation import extract_original_native_crop


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_case(row, rule_json=None, verify_original=False):
    import nibabel as nib

    sid = row["subject_id"]
    crop_path = Path(row["crop_t2"])
    json_path = Path(row["crop_json"])
    for p in (crop_path, json_path):
        if not p.is_file():
            raise FileNotFoundError(p)
    meta = json.loads(json_path.read_text(encoding="utf-8"))
    if meta.get("mode") != "proportional":
        raise ValueError("Expected the frozen proportional crop, not another mode")
    if "rule" not in meta:
        raise ValueError("Crop provenance lacks fitted rule")
    if rule_json:
        calibrated = json.loads(Path(rule_json).read_text(encoding="utf-8"))
        if meta["rule"] != calibrated["rules"]["proportional"]:
            raise ValueError("Crop was made with a different proportional rule")
    original_name = str(meta.get("source_file") or "").replace("\\", "/").split("/")[-1]
    if sid not in original_name or "_3T_T2w_SPC1" not in original_name:
        raise ValueError("Crop source filename/subject mismatch (expected original SPC1): " + sid)

    presence = row["presence"].strip().lower()
    if presence not in ("present", "absent"):
        raise ValueError("Unknown operational presence label")
    # The training loader itself checks crop native affine, voxel dimensions,
    # exact mask alignment, binarity and complete reference-CSP containment.
    image, mask, affine, _ = load_case(
        sid, str(crop_path), str(json_path),
        row["source_mask"] if presence == "present" else "", presence
    )
    if presence == "absent" and row["source_mask"].strip():
        # Never silently convert a real positive manual mask to zero-label.
        ref_path = Path(row["source_mask"])
        if not ref_path.is_file():
            raise FileNotFoundError(ref_path)
        source_mask = np.asanyarray(nib.load(str(ref_path)).dataobj)
        if np.any(source_mask > 0):
            raise ValueError("Operationally absent row has nonempty source mask; adjudicate")
    if verify_original:
        source = row.get("original_t2", "").strip()
        if not source:
            raise ValueError("Manifest lacks original_t2; rebuild with current build-manifest")
        original = nib.load(source)
        crop = nib.load(str(crop_path))
        # Slicer can reverse/reorder source NIfTI voxel axes on import.
        # Require an exact affine-consistent integer reindexing; never resample.
        # This also validates the source shape and saved crop indices.
        roi = extract_original_native_crop(original, meta)
        if not np.allclose(crop.affine, affine, atol=1e-3, rtol=0):
            raise ValueError("Crop reloaded affine differs from loader")
        stored = np.asarray(crop.dataobj)
        if roi.shape != stored.shape or not np.allclose(
            roi, stored, atol=1e-4, rtol=0, equal_nan=True
        ):
            raise ValueError("Native T2 crop voxel values differ from source: resampling/IO issue")
    return {
        "shape_ijk": "x".join(map(str, image.shape)),
        "mask_voxels": int(np.count_nonzero(mask)),
        "retained_fraction": float(np.prod(image.shape) / np.prod(meta["source_shape_kji"])),
        "crop_json_sha256": sha256(json_path),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", required=True, help="PRIVATE 2.5D model manifest")
    ap.add_argument("--report", required=True, help="PRIVATE local audit CSV")
    ap.add_argument("--rule-json", help="Exact corrected unshifted calibration JSON")
    ap.add_argument("--verify-original", action="store_true", help="Check source T2 voxel equality")
    ap.add_argument("--split", action="append", choices=["train", "val", "test", "unassigned"])
    ap.add_argument("--eligible-only", action="store_true", help="Audit only subjects eligible for hard supervision")
    ap.add_argument("--subject-id", action="append", help="Repeat to restrict a three-case smoke audit")
    args = ap.parse_args()

    all_rows = read_manifest(args.manifest)
    rows = [r for r in all_rows
            if (not args.split or r["split"] in args.split)
            and (not args.subject_id or r["subject_id"] in args.subject_id)]
    if args.eligible_only:
        before = len(rows)
        rows = [r for r in rows if usable_for_supervision(r)]
        print(f"Excluded {before - len(rows)} ineligible/unadjudicated rows from supervised preflight")
    if not rows:
        raise SystemExit("FAIL: no eligible manifest rows selected; no audit was performed")
    if args.rule_json and not Path(args.rule_json).is_file():
        raise SystemExit("FAIL: rule JSON not accessible")
    if args.rule_json:
        print("Frozen rule SHA256:", sha256(args.rule_json))

    records = []
    n_failed = 0
    for row in rows:
        record = {"subject_id": row["subject_id"], "split": row["split"],
                  "eligible": usable_for_supervision(row), "status": "PASS",
                  "message": "", "mask_voxels": "", "retained_fraction": "",
                  "shape_ijk": "", "crop_json_sha256": ""}
        try:
            result = audit_case(row, args.rule_json, args.verify_original)
            record.update(result)
        except Exception as exc:
            record["status"] = "FAIL"
            record["message"] = str(exc)
            n_failed += 1
        records.append(record)
        print(f"[{record['status']}] {row['subject_id']}: {record['message']}")
    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    print(f"Audited {len(rows)} selected subjects; failures={n_failed}; PRIVATE report: {out}")
    if n_failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
