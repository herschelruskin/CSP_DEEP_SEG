# 2.5D CSP U-Net — controlled seed-replication experiment (November 26, 2026)

## Purpose

Assess seed-to-seed variability of the **already implemented** seven-slice native-coronal CSP U-Net on the **unchanged** 44-train/11-validation seed-843 *subject partition* after the 20-epoch baseline achieved best validation Dice 0.790623 at epoch 7. This is NOT independent test-set evaluation or architecture comparison. No R2 labels are substituted. Subject IDs, images, masks and provenance remain private.

## Frozen comparison

- Same source manifest `model_25d_trainval_seed843_linux.csv`; **keep its original SHA256** unchanged; same subject partition, crop rules, mask versions and binary labels. The word `seed843` in this manifest name denotes the frozen *split*, not a requirement that every model use training RNG seed 843.
- Identical network: seven consecutive T2 coronal channels; center-slice binary logits; GroupNorm U-Net, width 16 (~489k parameters); same positive/negative slice class+subject balancing; AdamW LR=3e-4, BCE + positive-slice soft Dice, 20 epochs, boundary-ignore=1.
- Same fixed validation 11 cases, checkpoint chosen by mean 3D case Dice; probability threshold 0.5. Do not pick the best-seed checkpoint after inspecting these 11 and claim external generalization.
- Compare original best.pt (20 epochs, seed843, epoch7 validation mean Dice 0.790623) to **new independent training runs with seed 844 and 845**. Their random sampling and parameter initialization differ but they must not change the subject-level train/val partition.
- Training code remains unchanged; Slurm wrapper now accepts `CSP_SEED` environment variable and protects existing run directories from overwrite.

## Narval commands

Run from the **Narval login shell** only; `sbatch` schedules GPU work. The private frozen corrected ROI rules file must be the same one used in the original run; do NOT infer its path from a different calibration.

```bash
cd "$HOME/CSP_DEEP_SEG"
git fetch origin
git switch feature/native-coronal-25d-baseline-20261120
git pull --ff-only
bash -n scripts/hpc/train_csp25d.sbatch
ROOT="$SCRATCH/csp25d_private/baseline_seed843"
export CSP_REPO="$HOME/CSP_DEEP_SEG"
export CSP_VENV="$HOME/venvs/csp25d"
export CSP_PY_MODULE="python/3.11.5"
export CSP_MANIFEST="$ROOT/manifests/model_25d_trainval_seed843_linux.csv"
export CSP_EPOCHS=20
mkdir -p "$ROOT/logs"
find "$ROOT" -name calibrated_rules.json -type f -print
```

Set **CSP_RULE_JSON** explicitly to the correct private *results_corrected_112112* rule file returned by the `find` command (or existing path used by the first 20-epoch training job). Verify it is not an older rules candidate; if absent, retrieve from the original authorized private transfer rather than recalibrating:

```bash
export CSP_RULE_JSON='PASTE_VERIFIED_NARVAL_PRIVATE_CALIBRATED_RULE_JSON_PATH_HERE'
test -f "$CSP_RULE_JSON" && test -f "$CSP_MANIFEST"
sha256sum "$CSP_MANIFEST" "$CSP_RULE_JSON"
```

Expected **original frozen manifest SHA256**: `3498caf14cddb7fa56e50b26333a2374d49ac472170231a92a2886b977291229`. If the manifest differs, **STOP** and investigate. The original frozen crop JSON hash should be compared to the earlier run log if available. The Slurm wrapper repeats the manifest and rule hashes.

Submit **seed 844** once:

```bash
export CSP_SEED=844
export CSP_OUT="$ROOT/runs/baseline_20epoch_seed844"
sbatch --account=def-nwc_gpu --gres=gpu:a100_3g.20gb:1 --cpus-per-task=4 --mem=16G --time=01:00:00 --job-name=csp25d-s844 --output="$ROOT/logs/seed844-%j.out" --export=ALL scripts/hpc/train_csp25d.sbatch
```

Submit **seed 845** independently (may queue):

```bash
export CSP_SEED=845
export CSP_OUT="$ROOT/runs/baseline_20epoch_seed845"
sbatch --account=def-nwc_gpu --gres=gpu:a100_3g.20gb:1 --cpus-per-task=4 --mem=16G --time=01:00:00 --job-name=csp25d-s845 --output="$ROOT/logs/seed845-%j.out" --export=ALL scripts/hpc/train_csp25d.sbatch
```

Slurm jobs continue on allocated GPU nodes even when the SSH client disconnects. Check `squeue -u "$USER"` and later `sacct -u "$USER" -S 2026-11-26 --format=JobID,JobName,State,ExitCode,Elapsed` (historical timestamp just for this experiment). Inspect `*.out` for failures; do not run training on the login node.

## Compare completed runs without selecting a winner

Use after both jobs are COMPLETED with exit code 0:

```bash
python - <<'PY'
import csv, json, os
from pathlib import Path
root=Path(os.environ['SCRATCH'])/'csp25d_private'/'baseline_seed843'/'runs'
for seed in (843,844,845):
    path=root/f'baseline_20epoch_seed{seed}'
    cfg=json.loads((path/'config.json').read_text())
    rows=list(csv.DictReader((path/'history.csv').open()))
    best=max(rows,key=lambda r:float(r['val_positive_case_mean_dice']))
    print(seed,'train=',cfg['train_subjects'],'val=',cfg['val_subjects'],'rng=',cfg['seed'],'manifest=',cfg['manifest_sha256'],'best_epoch=',best['epoch'],'best_val_dice=',best['val_positive_case_mean_dice'],'epoch20_dice=',rows[-1]['val_positive_case_mean_dice'],'checkpoint_bytes=',(path/'best.pt').stat().st_size)
PY
```

Interpret variability of the checkpoint-selected validation Dice across runs as **exploratory training stability**, not a statistical CI for generalization. If code revisions differ between seed843 and 844/845, record Git revision and review the substantive diff before attributing the change entirely to randomness.

## Subsequent prioritized work

1. Evaluate frozen epoch7 predictions on separately staged **uncertain/non-supervised** development cases (original absent group and `needs_review` positives) **only as exploratory anatomical QC**. Existing absent labels are demonstrably uncertain: 107018 and 109325 were subsequently annotated positive in R2, while 102614 remained absent. No hard-negative specificity claim from these cases.
2. Plan a truly independent 15–20-subject test set from unannotated HCP crops with blinded labels, and preferably family-aware split if restricted HCP family IDs become available. Do not tune model selection on it.
3. One **predeclared** training modification (e.g. mild T2 intensity augmentation) with identical train/val split and seeds, then compare Dice **and** mm³ volume error and spurious connected components. Avoid repeatedly trying many arbitrary settings on 11 validation subjects.
4. Once anatomical QC clarifies high-confidence absent and ambiguous boundaries, consider a presence/absence classifier and uncertainty-aware segmentation; do not force tiny unresolvable possible CSPs into definite-negative labels.

## User-provided annotation reliability benchmark

Separate R1 vs R2 20-case intra-rater study (one annotator) gave 17 positive-pair mean Dice 0.79905 (95% bootstrap CI 0.7445–0.8541), absolute-agreement volume ICC(A,1)=0.8867, positive-pair R2 cumulative volume +27.1%, and presence agreement 90% (kappa 0.459). These are not directly comparable with the 11-case U-Net validation Dice.

