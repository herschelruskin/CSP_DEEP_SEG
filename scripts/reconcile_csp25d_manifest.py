"""Join PRIVATE ROI calibration annotations to the verified finished batch inventory.

Only inventory PASS records enter the model manifest. Every missing/failed
subject is recorded separately in a PRIVATE exceptions CSV; presence/QC is
never changed to 'absent' to mask a failed or missing crop. Does not assign
train/val/test splits, infer family groups or copy any images.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path, PureWindowsPath


def filename(path):
    return PureWindowsPath(path).name if path else ""


def unique_by_id(rows, source):
    indexed = {}
    for row in rows:
        sid = row.get("subject_id", "").strip()
        if not (len(sid) == 6 and sid.isdecimal()):
            raise ValueError(f"{source}: invalid six-digit subject ID: {sid}")
        if sid in indexed:
            raise ValueError(f"{source}: duplicate subject ID {sid}")
        indexed[sid] = row
    return indexed


def reconcile(cohort_rows, inventory_rows):
    """Return (eligible-path model rows, explicitly rejected annotations)."""
    cohort = unique_by_id(cohort_rows, "cohort")
    inventory = unique_by_id(inventory_rows, "inventory")
    accepted, rejected = [], []
    for sid, row in cohort.items():
        audit = inventory.get(sid)
        if audit is None or audit.get("status") != "PASS":
            reason = "No inventory record" if audit is None else audit.get("error", "Crop audit did not pass")
            rejected.append(dict(subject_id=sid, reason=reason or "Crop audit did not pass"))
            continue
        crop = audit.get("crop_t2", "").strip()
        sidecar = audit.get("crop_json", "").strip()
        source = audit.get("original_t2", "").strip()
        if not crop or not sidecar or not source:
            rejected.append(dict(subject_id=sid, reason="PASS inventory row lacks crop, JSON or source path"))
            continue
        if filename(source) != filename(row.get("source_t2", "")):
            rejected.append(dict(subject_id=sid, reason="Original T2 filename differs between cohort and crop inventory"))
            continue
        if not crop.endswith("_3T_T2w_SPC1_proportional_reduced.nii.gz"):
            rejected.append(dict(subject_id=sid, reason="Unexpected verified crop filename"))
            continue
        split = row.get("split", "").strip().lower()
        if split not in ("train", "val", "test"):
            split = "unassigned"
        accepted.append(dict(
            subject_id=sid, split=split, family_group=row.get("family_group", "").strip(),
            crop_t2=crop, crop_json=sidecar, source_mask=row.get("mask_path", "").strip(),
            presence=row.get("presence", "").strip().lower(), qc=row.get("qc", "").strip().lower(),
            negative_confidence=row.get("negative_confidence", "").strip().lower(),
            original_t2=source))
    return accepted, rejected


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("Missing or empty CSV: " + str(path))
    return rows


def write_csv(path, rows, fields):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", required=True, help="PRIVATE 70-subject calibration manifest")
    parser.add_argument("--inventory", required=True, help="PRIVATE finished-crop inventory CSV")
    parser.add_argument("--output", required=True, help="PRIVATE model-ready manifest path")
    parser.add_argument("--exceptions", required=True, help="PRIVATE skipped-subjects report")
    args = parser.parse_args()
    accepted, rejected = reconcile(read_csv(args.cohort), read_csv(args.inventory))
    if accepted:
        fields = list(accepted[0])
        write_csv(args.output, accepted, fields)
    else:
        raise SystemExit("FAIL: no cohort subjects had PASS crop inventory; no model manifest written")
    write_csv(args.exceptions, rejected, ["subject_id", "reason"])
    print(f"[MANIFEST JOIN] crop-verified={len(accepted)}, skipped={len(rejected)}")
    print("Review the PRIVATE exception report:", args.exceptions)
    print("Manifest splits, family groups, mask QC and negative confidence still require verification:", args.output)


if __name__ == "__main__":
    main()
