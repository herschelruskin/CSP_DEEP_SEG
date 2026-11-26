# Experiment registry

Every training or comparison run gets its own copied `templates/RUN_RECORD.md`. This table is an index, not a substitute for raw logs.

| Run ID | Question / variant | Train/val/test split hash | Labels / unlabeled | Code/config | Primary metric | Status |
|---|---|---|---|---|---|---|
| — | No training experiments executed | — | — | — | — | NOT STARTED |

## Current first-pass experiment queue (2026-11-18; **nothing trained yet**)

| Experiment ID | Design | Primary evaluation | Gate / constraints |
|---|---|---|---|
| POC-00 | Native-T2 septal fixed-crop localization | Whole triangular CSP mask containment, crop margin and runtime | Audit local labels/geometry first; absent cases still get a defined septal ROI |
| POC-01 | Compact 2.5D U-Net on original 0.7 mm T2 crops | Positive-case Dice, absolute/signed volume errors, false positives in empty cases | Subject/family-disjoint splits; QC-pass masks only, reproducible configs |
| POC-02 | Downsampled-T2 learned **septal anatomical region localizer** + same POC-01 segmenter | Containment/failure/runtime, then identical segmentation metrics | Predict anatomical region even for no visible CSP; fair matched splits |
| POC-03 | Compact 3D U-Net versus 2.5D baseline | Segmentation accuracy versus memory/runtime | Only if POC-01 reliable and resources allow |
| POC-04 | Rigid-ANTs/landmark/affine crop versus learned/fixed crop | Robustness and full-mask containment, latency | Not mandatory if simple raw-T2 crop meets coverage |
## Planned, **not executed**, comparisons

| Design ID | Comparison | Outcome / confounders |
|---|---|---|
| EXP-A | Native-affine ROI versus ANTs rigid ROI | Full septal reference coverage; compute cost |
| EXP-B | Classical intensity + anatomy versus small 3D U-Net | Manual CSP Dice, signed/absolute volume error |
| EXP-C | Matched-budget 3D U-Net versus attention hybrid | Whether attention improves tiny-CSP segmentation |
| EXP-D (optional) | Purely supervised versus pretraining/pseudo-labels | Label efficiency; pseudo-label error amplification |
| EXP-E (optional) | Intensity normalization/augmentation settings | Scanner/scan contrast robustness; avoid fitting on test set |

No unrun comparisons should be described as results in the course report.

## Actual three-seed results (2026-11-26)

User confirmed seed-844 and seed-845 Slurm jobs 10722026 and 10722028 completed and read each completed run's `config.json` / `history.csv`. All three runs report same private frozen 44/11 manifest SHA256: `3498caf14cddb7fa56e50b26333a2374d49ac472170231a92a2886b977291229`.

| Seed | Best epoch | Best case-mean validation Dice | Epoch-20 Dice |
| --- | ---: | ---: | ---: |
| 843 | 7 | 0.7906230871477724 | 0.7877458006371768 |
| 844 | 12 | 0.7899741330553649 | 0.7398608441703682 |
| 845 | 4 | 0.7851818946927506 | 0.7607746156541676 |

Mean of three best scores = 0.7885930383; range = 0.7851818947 to 0.7906230871; spread = 0.0054411925. Best-checkpoint selection occurs on the **same eleven subjects** for each run, so similarity of selected-best scores is exploratory training stability, NOT independent generalization or a reliable Dice ceiling. Final-epoch performance varies more, consistent with training/validation fluctuation.

## Immediate next action: per-subject validation

Run the existing GPU evaluation sbatch `scripts/hpc/evaluate_csp25d.sbatch` separately for seed 844 and seed 845 with private original manifest, best.pt per run and distinct output directories under `$SCRATCH/csp25d_private/baseline_seed843/runs/baseline_20epoch_seed844_eval_best` and `...seed845_eval_best`. The evaluator asserts checkpoint manifest SHA256 and produces `per_case_metrics.csv` + `summary.json`. Compare seed-wise per-case Dice, signed and absolute volume error, recall and FP voxels. Seed843 already evaluated as `runs/baseline_20epoch_seed843_eval_best/`. No HCP data should be committed to public GitHub.

Then consider the already proposed incremental intensity augmentation experiment only after noting across-seed hard cases, and prioritize new untouched annotated evaluation cases, confident-negative adjudication and an independent family-aware split. R1/R2 reliability study (mean Dice 0.799) was on a **different cohort** and must not be equated directly with these validation scores.

## 2026-11-26: Three-seed per-case evaluation and controlled intensity-augmentation experiment

The user completed saved-best-checkpoint evaluations for all 3 seeds with the SAME frozen 11 positive validation subjects (manifest SHA256 `3498caf14cddb7fa56e50b26333a2374d49ac472170231a92a2886b977291229`):

| Seed | Case-mean Dice | Mean recall | Mean abs volume error (mm³) | 11-case FP voxels | 11-case FN voxels |
|---|---:|---:|---:|---:|---:|
| 843 | 0.790623 | 0.8976 | 3.492 | 150 | 44 |
| 844 | 0.789974 | 0.9318 | 4.864 | 186 | 30 |
| 845 | 0.785182 | 0.8584 | 2.744 | 129 | 67 |

Cases persistently below 0.80 for all seeds: 102816 (three-seed average Dice 0.614), 106824 (0.707), 113316 (0.733). Seed-sensitive: 111312 Dice 0.708 / 0.870 / 0.667 (range 0.203); 106319 0.727 / 0.710 / 0.815 (range 0.105). All three models substantially overpredict compared with R1 masks at fixed threshold 0.5, but R1/R2 human annotation variability means reference-defined FP may represent uncertain additional CSP.

Implemented exactly ONE optional mild T2 photometric data-augmentation experiment (no baseline code path change by default): `scripts/csp25d_baseline.py` gains `--intensity-augment`; per-sample, all seven coronal input channels receive the same shared uniform gain in [0.90,1.10] and offset in [-0.03,0.03], preserving zero background and no geometry or label changes. Separate seeded CPU Generator (`args.seed + 100000`) avoids perturbing sampler/model RNG. `scripts/hpc/train_csp25d.sbatch` accepts `CSP_INTENSITY_AUGMENT=1`; immutable original run folders protected by preexisting overwrite guards.

Added 3 synthetic CPU tests for determinism, unchanged segmentation labels/zero backgrounds, shared channel transform, RNG isolation, bad arguments. GitHub workflow `CSP 2.5D synthetic CPU tests` run `45890068803` **COMPLETED SUCCESS** on test-bearing commit `31ce1657cfcd16863e31b90d8780e7740fb76f7a`. Code and job script commits `bfd552be...`, `62e17402...`. Full pre-registered experiment instructions in `docs/INTENSITY_AUGMENTATION_2026_11_26.md`. **No augmentation GPU jobs yet submitted.** Target fresh 20-epoch runs seeds 843,844,845 (unchanged split, labels, architecture, loss, epochs, threshold); pre-commit to compare all augmented seeds, not cherry-pick one. On Narval verify calibrated private rule file, manifest hash and Slurm account before submitting. Later separately evaluate 11 subjects per checkpoint and report Dice, FP/FN and volume error.

Interpretation: selected-best Dice within ~0.0054 for three baseline seeds is suggestive of stable signal, not independent performance or guaranteed ceiling; differences in recall/volume/FP and consistently difficult cases motivate better anatomical QC and a genuinely independent test cohort. Mild intensity augmentation may or may not help attached ventricular false positives and should be treated as a controlled exploratory hypothesis, not a promised performance improvement.
