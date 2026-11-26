"""Export lossless 0/1 CSP masks onto the frozen native 1% T2 crop grid.

Input: PRIVATE, previously audited cohort/model manifest containing full
Slicer-native reference labelmaps. Output: compressed ROI masks and a PRIVATE
copy of the manifest with only selected source_mask paths rewritten.

No interpolation, intensity normalization, relabeling, resampling, or editing
of the original MRI/segmentation files. Every positive voxel must be retained.
Requires that the source cohort have already passed the --verify-original
preflight for the frozen proportional crop (the exporter checks containment).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import nibabel as nib
import numpy as np

from csp25d_baseline import crop_native_mask, read_manifest, usable_for_supervision


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def export_one(row, out_dir):
    """Check full native mask, extract its ROI, and save a uint8 .nii.gz mask.

    Returns path to compressed ROI labelmap; refuses unproven mask containment,
    wrong Slicer native shape, wrong affine, or nonbinary labels.
    """
    if row["presence"].strip().lower() != "present":
        raise ValueError("ROI exporter requires CSP-positive reference masks")
    sid = row["subject_id"]
    original_mask_path = Path(row["source_mask"])
    crop_path = Path(row["crop_t2"])
    json_path = Path(row["crop_json"])
    for path in (original_mask_path, crop_path, json_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    metadata = json.loads(json_path.read_text(encoding="utf-8"))
    if metadata.get("mode") != "proportional":
        raise ValueError("Not a frozen proportional ROI: " + sid)
    if "rule" not in metadata:
        raise ValueError("Missing frozen ROI rule provenance: " + sid)
    orig = nib.load(str(original_mask_path))
    crop = nib.load(str(crop_path))
    values = np.asarray(orig.dataobj)
    if values.ndim != 3 or not np.isin(np.unique(values), [0, 1]).all():
        raise ValueError("Reference mask is not 3D binary 0/1: " + sid)
    native = crop_native_mask(
        values, metadata, orig.affine, crop.shape, crop.affine
    )
    source_n = int(np.count_nonzero(values))
    crop_n = int(np.count_nonzero(native))
    if not source_n or crop_n != source_n:
        raise ValueError(f"Full CSP containment not verified for {sid}: source={source_n} crop={crop_n}")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    destination = out_dir / f"{sid}_csp_roi_mask.nii.gz"
    compact = nib.Nifti1Image(native.astype(np.uint8), crop.affine)
    compact.set_qform(crop.affine, code=1)
    compact.set_sform(crop.affine, code=1)

    if destination.exists():
        existing = nib.load(str(destination))
        if (existing.shape != crop.shape
                or not np.allclose(existing.affine, crop.affine, atol=1e-3, rtol=0)
                or not np.array_equal(np.asarray(existing.dataobj), native)):
            raise FileExistsError("Existing ROI mask differs: " + str(destination))
    else:
        nib.save(compact, str(destination))
    saved = nib.load(str(destination))
    if (saved.shape != crop.shape
            or not np.allclose(saved.affine, crop.affine, atol=1e-3, rtol=0)
            or not np.array_equal(np.asarray(saved.dataobj), native)):
        raise IOError("Lossless ROI mask NIfTI roundtrip failed for " + sid)

    proof = dict(
        subject_id=sid,
        mask_voxels=source_n,
        source_mask=str(original_mask_path),
        source_mask_sha256=file_sha256(original_mask_path),
        crop_json_sha256=file_sha256(json_path),
        crop_t2=str(crop_path),
        cropped_mask=str(destination),
        cropped_mask_sha256=file_sha256(destination),
        cropped_shape_ijk=list(crop.shape),
        cropped_affine=crop.affine.tolist(),
        method="exact native array slicing; no resampling; full source mask contained",
    )
    proof_path = destination.with_name(f"{sid}_csp_roi_mask.provenance.json")
    proof_path.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    print(f"[ROI MASK] {sid}: preserved {source_n} voxels; {destination.stat().st_size} bytes; {destination}")
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="PRIVATE original/full-native-mask manifest CSV")
    parser.add_argument("--out-dir", required=True, help="Directory for compressed ROI masks and private provenance")
    parser.add_argument("--output-manifest", required=True,
                        help="PRIVATE copy of manifest with exported source_mask paths rewritten")
    parser.add_argument("--subject-id", action="append", help="Restrict to subject(s), e.g. 100408")
    parser.add_argument("--eligible-only", action="store_true",
                        help="Export only hard-supervision-eligible QC positives")
    args = parser.parse_args()
    if Path(args.output_manifest).resolve() == Path(args.manifest).resolve():
        raise SystemExit("Refusing to overwrite the original input manifest")
    rows = read_manifest(args.manifest)
    selected_ids = set(args.subject_id) if args.subject_id else None
    if selected_ids and not selected_ids.issubset({row["subject_id"] for row in rows}):
        raise SystemExit("At least one --subject-id not found in manifest")
    selected = [
        row for row in rows if (selected_ids is None or row["subject_id"] in selected_ids)
        and row["presence"].strip().lower() == "present"
        and (not args.eligible_only or usable_for_supervision(row))
    ]
    if not selected:
        raise SystemExit("No CSP-positive rows selected")
    updates = {}
    for row in selected:
        updates[row["subject_id"]] = str(export_one(row, args.out_dir))
    out_rows = []
    for row in rows:
        copy = dict(row)
        if row["subject_id"] in updates:
            copy["source_mask"] = updates[row["subject_id"]]
        out_rows.append(copy)
    output = Path(args.output_manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"[ROI MASK BATCH] exported={len(selected)}; new PRIVATE manifest={output}")


if __name__ == "__main__":
    main()
