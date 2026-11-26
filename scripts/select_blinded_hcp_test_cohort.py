"""Freeze a blind, unseen-subject HCP S1200 T2 CSP segmentation test queue.

Input is the already-audited 1,113-subject SPC1 ROI crop inventory plus the
70-subject manual/calibration cohort. Do NOT inspect model predictions or CSP
prevalence before selecting; subject IDs are sampled from a sorted PASS list.

This is a *subject*-held-out cohort only without restricted HCP family IDs.
It is not a fully independent family-disjoint or external-dataset validation.
Output is PRIVATE and immutable; no MRI or mask files are modified.

Usage: python select_blinded_hcp_test_cohort.py --inventory ... --cohort ...
       --output ... --allow-unknown-family
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
from pathlib import Path


def read_csv(path: Path, expected: set[str], kind: str) -> tuple[list[dict], bytes]:
    data = path.read_bytes()
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not expected.issubset(reader.fieldnames):
            raise ValueError(f"{kind} missing columns: {sorted(expected - set(reader.fieldnames or []))}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{kind} CSV is empty")
    ids = [row["subject_id"].strip() for row in rows]
    if any(not re.fullmatch(r"[0-9]{6}", sid) for sid in ids):
        raise ValueError(f"{kind} contains invalid HCP six-digit subject IDs")
    if len(ids) != len(set(ids)):
        raise ValueError(f"{kind} has duplicate subject IDs")
    return rows, data


def select(
    inventory: list[dict],
    development: list[dict],
    n_test: int,
    n_reserve: int,
    seed: int,
    family_map: dict[str, str] | None = None,
) -> tuple[list[dict], dict]:
    if n_test <= 0 or n_reserve < 0:
        raise ValueError("n_test must be >0; n_reserve must be >=0")
    annotated_ids = {row["subject_id"].strip() for row in development}
    all_ids = {row["subject_id"].strip() for row in inventory}
    if not annotated_ids.issubset(all_ids):
        raise ValueError("Calibration/annotation subject absent from full HCP inventory")
    if family_map is not None:
        if not all_ids.issubset(family_map):
            raise ValueError("Family map lacks one or more inventoried subject IDs")
        if any(not family_map[sid] for sid in all_ids):
            raise ValueError("Family map contains empty groups")
        disallowed_families = {family_map[sid] for sid in annotated_ids}
    else:
        disallowed_families = set()

    candidates = []
    for row in inventory:
        sid = row["subject_id"].strip()
        if sid in annotated_ids or row["status"].strip().upper() != "PASS":
            continue
        if not row.get("crop_t2", "").strip() or not row.get("crop_json", "").strip():
            raise ValueError(f"PASS subject lacks expected crop or JSON paths: {sid}")
        if family_map is not None and family_map[sid] in disallowed_families:
            continue
        candidates.append(row)
    candidates.sort(key=lambda x: x["subject_id"].strip())
    if len(candidates) < n_test + n_reserve:
        raise ValueError(f"Not enough unseen PASS candidates: {len(candidates)}")

    # One deterministic shuffle; no model scores, mask volumes, presence or
    # anatomical judgments enter the order. Reserve replacements are fixed now.
    rng = random.Random(seed)
    rng.shuffle(candidates)
    picks = []
    seen_family = set()
    for row in candidates:
        sid = row["subject_id"].strip()
        group = family_map[sid] if family_map is not None else ""
        if group and group in seen_family:
            continue
        picks.append(row)
        if group:
            seen_family.add(group)
        if len(picks) == n_test + n_reserve:
            break
    if len(picks) != n_test + n_reserve:
        raise ValueError("Too few independent families for target test+reserve sizes")

    result = []
    for index, row in enumerate(picks):
        sid = row["subject_id"].strip()
        result.append({
            "selection_order": index + 1,
            "assignment": "test" if index < n_test else "reserve",
            "subject_id": sid,
            "original_t2": row.get("original_t2", "").strip(),
            "crop_t2": row["crop_t2"].strip(),
            "crop_json": row["crop_json"].strip(),
            "family_group": family_map[sid] if family_map is not None else "",
            "annotation_status": "",
            "annotation_mask": "",
            "qc_notes": "",
        })
    meta = {
        "seed": seed,
        "algorithm": "sort unseen PASS subjects by subject_id; Python random.Random(seed).shuffle; take first n_test then n_reserve",
        "family_grouping_verified": family_map is not None,
        "annotated_calibration_subjects_excluded": len(annotated_ids),
        "inventory_rows": len(inventory),
        "unseen_pass_candidates": len(candidates),
        "test_size": n_test,
        "reserve_size": n_reserve,
        "subject_ids_test": [x["subject_id"] for x in result[:n_test]],
        "subject_ids_reserve": [x["subject_id"] for x in result[n_test:]],
        "selection_warning": "Selection blinded to predictions; without verified HCP family map the test cohort is subject-disjoint but family independence remains unknown.",
        "retrospective_data_note": "An independently selected HCP test is neither another scanner/site nor fully external-domain generalization.",
    }
    return result, meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--cohort", required=True, type=Path, help="All 70 development/calibration subjects, even review or absent")
    parser.add_argument("--output", required=True, type=Path, help="New private CSV; never overwritten")
    parser.add_argument("--seed", type=int, default=20261126)
    parser.add_argument("--n-test", type=int, default=20)
    parser.add_argument("--n-reserve", type=int, default=10)
    parser.add_argument("--family-map", type=Path, help="Optional authorized private CSV: subject_id,family_group, all inventory subjects")
    parser.add_argument("--allow-unknown-family", action="store_true", help="Explicitly accept exploratory, not family-independent HCP sampling")
    args = parser.parse_args()

    if args.family_map is None and not args.allow_unknown_family:
        parser.error("HCP family IDs are unknown. Supply --family-map OR explicit --allow-unknown-family")
    if args.family_map is not None and args.allow_unknown_family:
        parser.error("Choose verified --family-map OR --allow-unknown-family, not both")
    out = args.output
    sidecar = out.with_suffix(".selection.json")
    if out.exists() or sidecar.exists():
        raise FileExistsError("Refusing to replace an already frozen test selection")

    inventory, inv_bytes = read_csv(args.inventory, {"subject_id", "status", "crop_t2", "crop_json"}, "inventory")
    development, cohort_bytes = read_csv(args.cohort, {"subject_id"}, "development cohort")
    family_map = None
    family_bytes = None
    if args.family_map is not None:
        families, family_bytes = read_csv(args.family_map, {"subject_id", "family_group"}, "family map")
        family_map = {row["subject_id"].strip(): row["family_group"].strip() for row in families}
    result, meta = select(inventory, development, args.n_test, args.n_reserve, args.seed, family_map)
    meta["input_sha256"] = {
        "inventory": hashlib.sha256(inv_bytes).hexdigest(),
        "cohort": hashlib.sha256(cohort_bytes).hexdigest(),
    }
    if family_bytes is not None:
        meta["input_sha256"]["family_map"] = hashlib.sha256(family_bytes).hexdigest()

    out.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive mode prevents accidental replacement if a concurrent run wrote it.
    with out.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(result[0]))
        writer.writeheader()
        writer.writerows(result)
    meta["selection_csv_sha256"] = hashlib.sha256(out.read_bytes()).hexdigest()
    sidecar.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"FROZEN blinded CSP queue: {args.n_test} test + {args.n_reserve} reserve")
    print(f"Excluded all {len(development)} original development/calibration subjects; family verified={family_map is not None}")
    print(f"Candidate PASS subjects={meta['unseen_pass_candidates']}")
    print(f"PRIVATE CSV: {out}")
    print(f"PRIVATE provenance: {sidecar}")
    print("Do not run model predictions or inspect other labels before completing blinded test annotations.")


if __name__ == "__main__":
    main()
