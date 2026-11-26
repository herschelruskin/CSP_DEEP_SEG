"""Prepare PRIVATE R1/R2 reference pairs for frozen U-Net inference on Narval.

Run on Windows with nibabel/numpy and completed 1% proportional ROI crops.
Original full-resolution Slicer labelmaps are read but NEVER modified. Export
only 20 existing T2 ROI crops, .crop.json sidecars and 0/1 cropped labelmaps.
Refuse missing positive annotations, surprising absent masks, nonbinary voxels,
affine/grid mismatches, partial crop containment and duplicate crop paths.

The 20-subject R2 reliability queue is predefined; no automatic negative
classification from generic missing files. Outputs are private HCP data.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path

import nibabel as nib
import numpy as np

from csp25d_baseline import crop_native_mask
from inventory_csp25d_crops import CROP_SUFFIX, META_SUFFIX, collect_files

# Frozen R2 queue: 17 both-positive, two R1-absent/R2-positive, one both-absent.
R2_IDS = (
    "100610", "101006", "102513", "103010", "103111", "104416",
    "105014", "105115", "106016", "107018", "108121", "109325",
    "110007", "111514", "111716", "112516", "112920", "113215",
    "114116", "102614",
)
R1_ABSENT = frozenset(("102614", "107018", "109325"))
R2_ABSENT = frozenset(("102614",))
# R2 full-resolution voxel counts recorded in the blinded intra-rater audit.
R2_EXPECTED_COUNTS = {
    "100610": 28, "101006": 49, "102513": 116, "103010": 77,
    "103111": 55, "104416": 31, "105014": 54, "105115": 24,
    "106016": 39, "107018": 8, "108121": 74, "109325": 22,
    "110007": 38, "111514": 19, "111716": 153, "112516": 20,
    "112920": 53, "113215": 37, "114116": 25,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def extract_label(
    subject_id: str,
    source: Path,
    expected_absent: bool,
    crop_nii,
    meta: dict,
    out_path: Path,
    known_voxels: int | None = None,
) -> int:
    if expected_absent:
        if source.exists():
            raise ValueError(f"{subject_id}: frozen absent label unexpectedly has a mask: {source}")
        return 0
    if not source.is_file():
        raise FileNotFoundError(f"{subject_id}: expected POSITIVE mask missing: {source}")
    ref = nib.load(str(source))
    vox = np.asarray(ref.dataobj)
    if not np.isin(np.unique(vox), (0, 1)).all():
        raise ValueError(f"{subject_id}: R1/R2 mask contains nonbinary labels: {source}")
    total = int(np.count_nonzero(vox))
    if total <= 0:
        raise ValueError(f"{subject_id}: expected positive reference is empty: {source}")
    if known_voxels is not None and total != known_voxels:
        raise ValueError(f"{subject_id}: R2 voxel count changed since reliability audit: {total} != {known_voxels}")
    crop = crop_native_mask(vox, meta, ref.affine, crop_nii.shape, crop_nii.affine)
    if int(np.count_nonzero(crop)) != total:
        raise ValueError(f"{subject_id}: reference CSP not fully retained in reduced T2 ROI")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(crop.astype(np.uint8), crop_nii.affine), str(out_path))
    reloaded = nib.load(str(out_path))
    if reloaded.shape != crop_nii.shape or not np.allclose(reloaded.affine, crop_nii.affine, atol=1e-4, rtol=0):
        raise ValueError(f"{subject_id}: saved cropped reference geometry changed")
    if int(np.count_nonzero(np.asarray(reloaded.dataobj))) != total:
        raise ValueError(f"{subject_id}: saved reference voxel count changed")
    return total


def prepare(crop_root: Path, mask_root: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(f"Never overwrite a private R2 evaluation stage: {output}")
    if not mask_root.is_dir():
        raise FileNotFoundError(f"R1/R2 mask directory not found: {mask_root}")
    crops = collect_files(crop_root, CROP_SUFFIX)
    sidecars = collect_files(crop_root, META_SUFFIX)
    missing = set(R2_IDS) - (set(crops) & set(sidecars))
    if missing:
        raise ValueError(f"Frozen R2 subjects missing verified 1% crop/JSON: {sorted(missing)}")

    # Separate incomplete directory avoids mistaking an interrupted batch for
    # a valid, immutable stage; never delete it automatically.
    incomplete = output.with_name(output.name + ".INCOMPLETE")
    if incomplete.exists():
        raise FileExistsError(f"Previous incomplete stage needs manual inspection: {incomplete}")
    incomplete.mkdir(parents=True)
    (incomplete / "scans").mkdir()
    (incomplete / "masks").mkdir()

    rows = []
    for sid in R2_IDS:
        crop_nii = nib.load(str(crops[sid]))
        meta = json.loads(sidecars[sid].read_text(encoding="utf-8"))
        shape = np.asarray(crop_nii.shape)
        start = np.asarray(meta["start_ijk"], dtype=int)
        end = np.asarray(meta["end_ijk"], dtype=int)
        native = np.asarray(meta["original_affine"], dtype=float)
        expected_affine = native.copy()
        expected_affine[:3, 3] = (native @ np.r_[start, 1.0])[:3]
        if tuple(end - start) != tuple(shape) or not np.allclose(
            crop_nii.affine, expected_affine, rtol=0, atol=1e-3
        ):
            raise ValueError(f"{sid}: crop geometry does not agree with .crop.json")
        if meta.get("mode") != "proportional":
            raise ValueError(f"{sid}: expected completed proportional 1% crop")
        scan_rel = "scans/" + crops[sid].name
        meta_rel = "scans/" + sidecars[sid].name
        shutil.copyfile(crops[sid], incomplete / scan_rel)
        shutil.copyfile(sidecars[sid], incomplete / meta_rel)
        r1_rel = "masks/" + sid + "_r1_crop.nii.gz"
        r2_rel = "masks/" + sid + "_r2_crop.nii.gz"
        r1_count = extract_label(
            sid, mask_root / (sid + ".nii"), sid in R1_ABSENT,
            crop_nii, meta, incomplete / r1_rel,
        )
        r2_count = extract_label(
            sid, mask_root / (sid + "_2.nii"), sid in R2_ABSENT,
            crop_nii, meta, incomplete / r2_rel,
            R2_EXPECTED_COUNTS.get(sid),
        )
        rows.append({
            "subject_id": sid, "crop_t2": scan_rel, "crop_json": meta_rel,
            "r1_presence": "absent" if sid in R1_ABSENT else "present",
            "r2_presence": "absent" if sid in R2_ABSENT else "present",
            "r1_mask": "" if sid in R1_ABSENT else r1_rel,
            "r2_mask": "" if sid in R2_ABSENT else r2_rel,
            "r1_voxels": r1_count, "r2_voxels": r2_count,
        })
        print(f"[R2 STAGE] {sid}: R1={r1_count} vox R2={r2_count} vox", flush=True)

    with (incomplete / "r2_eval_manifest.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    manifest_hash = sha256_file(incomplete / "r2_eval_manifest.csv")
    provenance = {
        "subjects": len(rows), "manifest_sha256": manifest_hash,
        "r2_expected_counts_verified": True,
        "r2_presence_disagreements": ["107018", "109325"],
        "both_absent_subject_id": "102614",
        "data_type": "PRIVATE; no original full-volume T2 or full labelmap transferred",
        "source_crop_root": str(crop_root),
        "source_mask_root": str(mask_root),
    }
    (incomplete / "READY.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    incomplete.rename(output)
    print(f"[R2 STAGE COMPLETE] 20 paired cases: {output}", flush=True)
    print(f"Frozen stage manifest SHA256: {manifest_hash}", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--crop-root", type=Path, required=True, help="Windows finalized 1112-crop batch")
    p.add_argument("--mask-root", type=Path, required=True, help="Windows native R1 + _2.nii R2 masks")
    p.add_argument("--out", type=Path, required=True, help="New PRIVATE directory, never overwritten")
    args = p.parse_args()
    prepare(args.crop_root, args.mask_root, args.out)


if __name__ == "__main__":
    main()
