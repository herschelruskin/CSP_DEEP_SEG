"""Rewrite PRIVATE CSP manifest paths after staging reduced images to Linux HPC.

No image files are copied by this tool. Preserve subject IDs, labels, splits,
family groups, QC and annotation confidence; never publish this manifest.
"""
import argparse
import csv
from pathlib import Path, PureWindowsPath


def basename(value):
    if not value:
        return ""
    return PureWindowsPath(value).name if "\\" in value else Path(value).name


def relocate(rows, crop_dir, mask_dir, original_dir=None):
    converted = []
    for row in rows:
        new = dict(row)
        for col in ("crop_t2", "crop_json"):
            if not row.get(col, "").strip():
                raise ValueError(f"{row.get('subject_id')}: missing {col}")
            new[col] = str(Path(crop_dir) / basename(row[col]))
        if row.get("source_mask", "").strip():
            new["source_mask"] = str(Path(mask_dir) / basename(row["source_mask"]))
        else:
            new["source_mask"] = ""
        new["original_t2"] = (str(Path(original_dir) / basename(row["original_t2"]))
                              if original_dir and row.get("original_t2", "").strip() else "")
        converted.append(new)
    return converted


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", required=True, help="PRIVATE local Windows manifest CSV")
    ap.add_argument("--output", required=True, help="PRIVATE Linux manifest CSV")
    ap.add_argument("--crop-dir", required=True, help="Absolute Linux crop directory")
    ap.add_argument("--mask-dir", required=True, help="Absolute Linux native-mask directory")
    ap.add_argument("--original-dir", help="Optional Linux original T2 directory")
    args = ap.parse_args()
    for arg in ("crop_dir", "mask_dir"):
        if not Path(getattr(args, arg)).is_absolute():
            raise SystemExit("FAIL: " + arg + " must be an absolute Linux path")
    with open(args.manifest, newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        if not fields:
            raise SystemExit("FAIL: manifest has no CSV header")
        rows = list(reader)
    if not rows:
        raise SystemExit("FAIL: manifest has no rows")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(relocate(rows, args.crop_dir, args.mask_dir, args.original_dir))
    print(f"Wrote PRIVATE Linux-path manifest ({len(rows)} rows): {output}")


if __name__ == "__main__":
    main()
