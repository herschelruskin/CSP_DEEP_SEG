"""Fixed, exploratory CSP-positive train/validation split without HCP family metadata.

Uses a *private* source manifest and the post-export *private* successful
55-mask audit. Stratifies across three volume quantiles, then shuffles subjects
with a fixed local random seed. Never changes the source manifest, crops,
labels, or frozen ROI rule.

IMPORTANT: Subject-disjoint DOES NOT guarantee family-disjoint for HCP S1200.
This is an exploratory development split until authorized restricted family
identifiers allow a group-aware split. Never present it as independent HCP
generalization or rely on it for final scientific inference.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path


def load_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stratify_subjects(rows, audit, seed=843, val_fraction=0.20, n_bins=3):
    """Return (subject -> train/val), (subject -> quantile bin).

    Quantiles are based on mask voxel count, hence physical volume for
    homogeneous 0.7-mm-isotropic HCP T2. For other voxel grids, stratify on
    true physical volumes instead. Equal volumes are ordered by subject ID
    to give a completely reproducible deterministic rank.
    """
    if not (0.0 < val_fraction < 1.0) or n_bins < 2:
        raise ValueError("Validation fraction must be (0,1) and n_bins >= 2")
    ids = [row.get("subject_id", "").strip() for row in rows]
    if not all(ids) or len(ids) != len(set(ids)):
        raise ValueError("Empty or duplicate subject IDs in source manifest")
    audit_ids = [row.get("subject_id", "").strip() for row in audit]
    if not all(audit_ids) or len(audit_ids) != len(set(audit_ids)):
        raise ValueError("Empty or duplicate subject IDs in audit report")
    if any(row.get("split", "").strip() != "unassigned" for row in rows):
        raise ValueError("Source manifest contains assigned splits; refuse to overwrite")
    if any(row.get("family_group", "").strip() for row in rows):
        raise ValueError("Family group fields present: use a family-disjoint splitter, not this exploratory fallback")

    eligible = {
        row["subject_id"]: row for row in rows
        if row.get("presence", "").strip().lower() == "present"
        and row.get("qc", "").strip().lower() in ("pass", "provisional")
        and row.get("source_mask", "").strip()
    }
    audited = {}
    for row in audit:
        sid = row["subject_id"]
        if row.get("status", "").strip() != "PASS":
            raise ValueError("Audit contains a nonpassing subject: " + sid)
        if sid not in eligible:
            raise ValueError("Audited subject not eligible for positive supervision: " + sid)
        try:
            count = int(row["mask_voxels"])
        except (KeyError, ValueError) as exc:
            raise ValueError("Missing or invalid mask_voxels for " + sid) from exc
        if count < 1:
            raise ValueError("Nonpositive reference mask for " + sid)
        audited[sid] = count
    if set(audited) != set(eligible):
        raise ValueError("Post-export audit must PASS every eligible positive subject: missing "
                         + str(sorted(set(eligible) - set(audited))))
    if len(audited) <= n_bins:
        raise ValueError("Insufficient eligible subjects for requested stratification")

    ranked = sorted(audited, key=lambda sid: (audited[sid], sid))
    bins = [[] for _ in range(n_bins)]
    for rank, sid in enumerate(ranked):
        bins[min(n_bins - 1, rank * n_bins // len(ranked))].append(sid)
    if any(not b for b in bins):
        raise ValueError("Empty volume bin")
    n_val = max(1, min(len(ranked) - 1, round(len(ranked) * val_fraction)))
    targets = [n_val * len(b) / len(ranked) for b in bins]
    allocations = [int(t) for t in targets]
    remaining = n_val - sum(allocations)
    # Largest-remainder allocation; deterministic tie-break by bin index.
    ordered_bins = sorted(range(n_bins), key=lambda i: (-(targets[i] - allocations[i]), i))
    for index in ordered_bins[:remaining]:
        allocations[index] += 1
    if any(x >= len(b) for x, b in zip(allocations, bins)):
        raise ValueError("Validation allocation leaves no training subject in a volume bin")

    rng = random.Random(seed)
    assignments, bin_ids = {}, {}
    for index, (members, count) in enumerate(zip(bins, allocations)):
        shuffled = members.copy()
        rng.shuffle(shuffled)
        validation = set(shuffled[:count])
        for sid in members:
            assignments[sid] = "val" if sid in validation else "train"
            bin_ids[sid] = index + 1
    assert len(assignments) == len(ranked)
    assert sum(value == "val" for value in assignments.values()) == n_val
    return assignments, bin_ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="PRIVATE original compact-mask manifest")
    parser.add_argument("--audit", required=True, help="PRIVATE passing compact-mask audit CSV")
    parser.add_argument("--output", required=True, help="New PRIVATE train/val manifest CSV")
    parser.add_argument("--report", required=True, help="New PRIVATE per-subject split report CSV")
    parser.add_argument("--seed", type=int, default=843)
    parser.add_argument("--val-fraction", type=float, default=0.20)
    parser.add_argument("--expected-subjects", type=int, default=55)
    parser.add_argument("--allow-unknown-family", action="store_true",
                        help="Required explicit acknowledgment of exploratory HCP split")
    args = parser.parse_args()
    if not args.allow_unknown_family:
        raise SystemExit("REFUSED: HCP family groups unknown. Add --allow-unknown-family for EXPLORATORY subject-disjoint split only")
    paths = [Path(args.manifest).resolve(), Path(args.audit).resolve(),
             Path(args.output).resolve(), Path(args.report).resolve()]
    if len(set(paths)) != len(paths):
        raise SystemExit("Refusing input overwrite or duplicate output paths")
    if paths[2].exists() or paths[3].exists():
        raise SystemExit("Output/report already exists: refusing silent overwrite")
    with Path(args.manifest).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames
        rows = list(reader)
    if not headers or not {"subject_id", "split", "presence", "qc", "source_mask"}.issubset(headers):
        raise SystemExit("Manifest lacks required fields")
    audit = load_csv(args.audit)
    assignments, bin_ids = stratify_subjects(rows, audit, args.seed, args.val_fraction)
    if len(assignments) != args.expected_subjects:
        raise SystemExit(f"REFUSED: expected {args.expected_subjects} eligible cases; got {len(assignments)}")
    for row in rows:
        row["split"] = assignments.get(row["subject_id"], "unassigned")
    for output in paths[2:]:
        output.parent.mkdir(parents=True, exist_ok=True)
    with paths[2].open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    counts_by_sid = {row["subject_id"]: int(row["mask_voxels"]) for row in audit}
    with paths[3].open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["subject_id", "split", "volume_tercile", "mask_voxels"])
        writer.writeheader()
        for sid in sorted(assignments):
            writer.writerow(dict(subject_id=sid, split=assignments[sid],
                                 volume_tercile=bin_ids[sid], mask_voxels=counts_by_sid[sid]))
    train = sum(label == "train" for label in assignments.values())
    val = sum(label == "val" for label in assignments.values())
    print("WARNING: HCP twins/siblings may be split across train/val; NOT family-disjoint.")
    print(f"[EXPLORATORY SPLIT] subjects={len(assignments)} train={train} val={val} "
          f"unassigned={len(rows) - len(assignments)} seed={args.seed} "
          f"volume_bins=3; UNKNOWN FAMILY GROUPS")
    print(f"PRIVATE source manifest SHA256: {sha256(args.manifest)}")
    print(f"PRIVATE source audit SHA256: {sha256(args.audit)}")
    print("PRIVATE split manifest:", args.output)
    print("PRIVATE stratification report:", args.report)


if __name__ == "__main__":
    main()
