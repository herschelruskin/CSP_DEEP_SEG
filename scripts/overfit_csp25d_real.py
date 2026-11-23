"""Deliberate real-mask memorization check for CSP 2.5D U-Net.

Use ONLY QC-approved TRAIN subjects. This evaluates the exact training slices
used for gradient updates, NOT held-out performance or anatomical validity.
Run after the Windows crop/mask audit and transfer to Alliance.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch

from csp25d_baseline import (
    CoronalUNet25D, bce_dice_loss, extract_coronal_stack,
    load_case, read_manifest, seed_all, usable_for_supervision,
)


def prepare_examples(rows, slices=7):
    """One maximum-CSP-area center slice from each trusted positive subject."""
    examples = []
    for row in rows:
        if row["split"] != "train" or row["presence"].strip().lower() != "present":
            raise ValueError("Overfit check requires positive TRAIN subjects only")
        if not usable_for_supervision(row):
            raise ValueError("Positive train mask has insufficient QC or is missing")
        img, mask, affine, _ = load_case(
            row["subject_id"], row["crop_t2"], row["crop_json"],
            row["source_mask"], row["presence"])
        area = np.count_nonzero(mask, axis=(0, 2))
        if not np.any(area):
            raise ValueError("No positive coronal slice for " + row["subject_id"])
        j = int(np.argmax(area))
        x = torch.from_numpy(extract_coronal_stack(img, j, slices)[None].copy())
        y = torch.from_numpy(mask[:, j, :].T.astype(np.float32)[None, None].copy())
        examples.append((x, y, row["subject_id"], j, float(np.abs(np.linalg.det(affine[:3, :3])))))
    if not examples:
        raise ValueError("No trusted positive training examples selected")
    return examples


@torch.no_grad()
def training_slice_scores(model, examples, device):
    model.eval()
    scores = []
    for x, y, sid, j, voxel_volume in examples:
        pred = torch.sigmoid(model(x.to(device))) >= 0.5
        truth = y.to(device) > 0.5
        tp = int((pred & truth).sum().item())
        n_pred = int(pred.sum().item())
        n_true = int(truth.sum().item())
        dice = (2 * tp / (n_pred + n_true)) if n_pred + n_true else 1.0
        scores.append(dict(subject_id=sid, coronal_j=j, train_slice_dice=dice,
                           reference_area_voxels=n_true, predicted_area_voxels=n_pred,
                           absolute_slice_volume_error_mm3=abs(n_pred - n_true) * voxel_volume))
    return scores


def run(args):
    rows = read_manifest(args.manifest)
    requested = set(args.subject_id)
    selected = [row for row in rows if row["subject_id"] in requested]
    if len(selected) != len(requested):
        raise ValueError("Not every requested subject was in the PRIVATE manifest")
    if args.steps < 1 or args.report_every < 1:
        raise ValueError("steps and report-every must be positive")
    seed_all(args.seed)
    examples = prepare_examples(selected, args.slices)
    device = torch.device("cpu" if args.cpu else "cuda")
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("No CUDA device available; use --cpu only for a CPU diagnostic")
    net = CoronalUNet25D(slices=args.slices, width=args.width).to(device)
    optimizer = torch.optim.AdamW(net.parameters(), lr=args.lr)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    info = dict(mode="TRAIN_SLICE_OVERFIT_NOT_GENERALIZATION", subject_count=len(examples),
                seed=args.seed, lr=args.lr, steps=args.steps,
                slices=args.slices, width=args.width, device=str(device),
                torch=str(torch.__version__), cuda_runtime=torch.version.cuda,
                gpu_name=torch.cuda.get_device_name(0) if device.type == "cuda" else None,
                manifest_sha256=hashlib.sha256(Path(args.manifest).read_bytes()).hexdigest())
    (out / "config.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    start = time.monotonic()
    with (out / "history.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["step", "training_loss",
                                                      "train_slice_mean_dice", "elapsed_seconds"])
        writer.writeheader()
        for step in range(1, args.steps + 1):
            x, y, _, _, _ = examples[(step - 1) % len(examples)]
            net.train()
            optimizer.zero_grad(set_to_none=True)
            loss = bce_dice_loss(net(x.to(device)), y.to(device))
            loss.backward()
            optimizer.step()
            if step == 1 or step % args.report_every == 0 or step == args.steps:
                scores = training_slice_scores(net, examples, device)
                mean_dice = float(np.mean([score["train_slice_dice"] for score in scores]))
                record = dict(step=step, training_loss=float(loss.item()),
                              train_slice_mean_dice=mean_dice,
                              elapsed_seconds=round(time.monotonic() - start, 3))
                writer.writerow(record)
                handle.flush()
                print("[TRAIN-ONLY OVERFIT]", record)
    scores = training_slice_scores(net, examples, device)
    with (out / "train_slice_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(scores[0]))
        writer.writeheader()
        writer.writerows(scores)
    torch.save({"state_dict": net.state_dict(), "config": info}, out / "overfit_debug.pt")
    print("Diagnostic outputs (NOT validation):", out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--subject-id", required=True, action="append",
                        help="Repeat for a few distinct trusted train positives")
    parser.add_argument("--out", required=True)
    parser.add_argument("--steps", type=int, default=150)
    parser.add_argument("--report-every", type=int, default=10)
    parser.add_argument("--slices", type=int, default=7)
    parser.add_argument("--width", type=int, default=16)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--seed", type=int, default=843)
    parser.add_argument("--cpu", action="store_true", help="Only for a slower CPU test")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
