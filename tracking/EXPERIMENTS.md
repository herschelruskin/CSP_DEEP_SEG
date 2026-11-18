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
