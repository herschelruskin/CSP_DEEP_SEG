"""Create a single private transfer ZIP for the 55 audited HCP CSP 2.5D cases.

Input: immutable Windows split manifest and matching post-export PASS audit.
Output: one portable ZIP with only train/val native T2 crops, compact 0/1 CSP
masks, crop JSON metadata, ROI-mask provenance, frozen ROI rule and a manifest
rewritten for the requested Narval scratch directory. A SHA256 file inventory
allows exact byte verification after transfer. Original files are never edited.

IMPORTANT: No HCP family IDs available; the split is exploratory and only
subject-disjoint, NOT proven family-disjoint. Do not publish archive, manifests,
or subject-specific metadata to a public repository.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile


def _csv_bytes(rows, fieldnames):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _sha_bytes(content):
    return hashlib.sha256(content).hexdigest()


def _read_csv(filename):
    with Path(filename).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV missing header: " + str(filename))
        return reader.fieldnames, list(reader)


def make_package(manifest, audit_file, rule_json, output_zip, linux_root,
                 expected_train=44, expected_val=11):
    """Build and return an auditable lossless package; fail before writing if invalid."""
    manifest, audit_file, rule_json, output_zip = map(Path, (manifest, audit_file, rule_json, output_zip))
    if not str(linux_root).startswith("/") or ".." in PurePosixPath(linux_root).parts:
        raise ValueError("Linux destination must be an absolute path without ..")
    if output_zip.resolve() in {manifest.resolve(), audit_file.resolve(), rule_json.resolve()}:
        raise ValueError("Refusing to overwrite source inputs")
    if output_zip.exists():
        raise FileExistsError("Refusing to overwrite existing package: " + str(output_zip))

    fields, all_rows = _read_csv(manifest)
    if not {"subject_id", "split", "crop_t2", "crop_json", "source_mask",
            "presence", "qc", "original_t2"}.issubset(fields):
        raise ValueError("Split manifest missing required columns")
    ids = [row["subject_id"].strip() for row in all_rows]
    if len(ids) != len(set(ids)) or not all(ids):
        raise ValueError("Duplicate/empty subject IDs")
    selected = [row for row in all_rows if row["split"] in ("train", "val")]
    if any(row["split"] not in ("train", "val", "unassigned") for row in all_rows):
        raise ValueError("Unknown split in input manifest")
    train = sum(row["split"] == "train" for row in selected)
    val = sum(row["split"] == "val" for row in selected)
    if (train, val) != (expected_train, expected_val):
        raise ValueError(f"Unexpected train/val count: {train}/{val}; expected {expected_train}/{expected_val}")
    if any(row["presence"] != "present" or row["qc"] not in ("pass", "provisional")
           or (row.get("family_group") or "").strip() for row in selected):
        raise ValueError("Pilot requires eligible positive subjects with unknown family-group status")
    _, audit_rows = _read_csv(audit_file)
    audited = {row["subject_id"]: row for row in audit_rows}
    if len(audited) != len(audit_rows) or set(audited) != {row["subject_id"] for row in selected}:
        raise ValueError("Audit does not match exactly the selected 55 train/val subjects")
    if any(row.get("status") != "PASS" or int(row.get("mask_voxels") or 0) <= 0
           for row in audit_rows):
        raise ValueError("Audit contains failed or empty CSP reference case")
    if not rule_json.is_file():
        raise FileNotFoundError(rule_json)

    base = PurePosixPath(linux_root)
    content_paths = {}
    copied = []
    per_subject = []
    for row in selected:
        sid = row["subject_id"]
        images = (
            ("crop_t2", "crops", row["crop_t2"]),
            ("crop_json", "crops", row["crop_json"]),
            ("source_mask", "masks", row["source_mask"]),
        )
        new = dict(row)
        for field, folder, filename in images:
            path = Path(filename)
            if not path.is_file():
                raise FileNotFoundError(path)
            if not path.name.startswith(sid):
                raise ValueError(f"Unexpected {field} filename for {sid}: {path.name}")
            if field == "source_mask" and path.name != f"{sid}_csp_roi_mask.nii.gz":
                raise ValueError("Expected compressed compact CSP mask, not full-brain source: " + sid)
            rel = str(PurePosixPath(folder) / path.name)
            if rel in content_paths:
                raise ValueError("Archive collision at " + rel)
            content_paths[rel] = path
            new[field] = str(base / rel)
        provenance = Path(row["source_mask"]).with_name(sid + "_csp_roi_mask.provenance.json")
        if not provenance.is_file():
            raise FileNotFoundError("Missing private ROI export provenance: " + str(provenance))
        with provenance.open(encoding="utf-8") as handle:
            attestation = json.load(handle)
        if attestation.get("subject_id") != sid or int(attestation.get("mask_voxels") or 0) != int(audited[sid]["mask_voxels"]):
            raise ValueError("ROI mask provenance count/subject mismatch: " + sid)
        if _sha256(row["source_mask"]) != attestation.get("cropped_mask_sha256"):
            raise ValueError("ROI mask SHA256 differs from private provenance: " + sid)
        if _sha256(row["crop_json"]) != attestation.get("crop_json_sha256"):
            raise ValueError("ROI JSON SHA256 differs from private provenance: " + sid)
        content_paths["provenance/" + provenance.name] = provenance
        new["original_t2"] = ""  # Never stage whole-brain T2 with compact ROI package.
        copied.append(new)
        per_subject.append(sid)

    linux_manifest = _csv_bytes(copied, fields)
    rule_bytes = rule_json.read_bytes()
    meta = json.dumps({
        "experiment": "CSP 2.5D supervised pilot",
        "scope": "exploratory subject-disjoint; family relationships unknown",
        "expected_train": train, "expected_val": val,
        "subjects": len(copied), "linux_root": str(base),
        "source_split_manifest_sha256": _sha256(manifest),
        "source_compact_mask_audit_sha256": _sha256(audit_file),
        "frozen_rules_sha256": _sha_bytes(rule_bytes),
        "no_original_full_brain_T2_or_masks": True,
    }, indent=2).encode("utf-8") + b"\n"
    generated = {
        "manifests/model_25d_trainval_seed843_linux.csv": linux_manifest,
        "manifests/calibrated_rules.json": rule_bytes,
        "manifests/package_metadata.json": meta,
    }
    records = []
    for rel, source in sorted(content_paths.items()):
        records.append(dict(path=rel, sha256=_sha256(source), bytes=source.stat().st_size))
    for rel, data in sorted(generated.items()):
        records.append(dict(path=rel, sha256=_sha_bytes(data), bytes=len(data)))
    checksums = _csv_bytes(records, ["path", "sha256", "bytes"])

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(output_zip, "x", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as archive:
            for rel, source in sorted(content_paths.items()):
                archive.write(source, arcname=rel)
            for rel, data in sorted(generated.items()):
                archive.writestr(rel, data)
            archive.writestr("manifests/file_sha256.csv", checksums)
        with zipfile.ZipFile(output_zip, "r") as check:
            if check.testzip() is not None:
                raise IOError("ZIP CRC verification failed")
    except BaseException:
        output_zip.unlink(missing_ok=True)
        raise
    size = output_zip.stat().st_size
    print(f"[STAGING PACKAGE] train={train} val={val} total={len(copied)} "
          f"source_files={len(content_paths)} zip_bytes={size}")
    print("WARNING: Family-disjoint status UNKNOWN; exploratory train/val only")
    print("PRIVATE ZIP:", output_zip)
    print("Archive SHA256:", _sha256(output_zip))
    return output_zip


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", required=True, help="PRIVATE assigned 44/11 compact-mask split CSV")
    p.add_argument("--audit", required=True, help="PRIVATE PASS compact-mask audit CSV")
    p.add_argument("--rule-json", required=True, help="Frozen proportional ROI calibration JSON")
    p.add_argument("--output-zip", required=True, help="PRIVATE output ZIP; must not exist already")
    p.add_argument("--linux-root", required=True, help="Narval scratch destination")
    p.add_argument("--expected-train", type=int, default=44)
    p.add_argument("--expected-val", type=int, default=11)
    a = p.parse_args()
    make_package(a.manifest, a.audit, a.rule_json, a.output_zip,
                 a.linux_root, a.expected_train, a.expected_val)


if __name__ == "__main__":
    main()
