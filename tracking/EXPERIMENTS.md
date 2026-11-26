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
