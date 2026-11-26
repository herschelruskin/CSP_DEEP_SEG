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


### 2026-11-26 — Augmentation EXP-A: all three BEST checkpoint Dice reported
- From Narval complete 20-epoch histories (`baseline_20epoch_augint_seed843/844/845`; user output), augmented best: **seed843 epoch10 Dice 0.808382** (final .772710), **seed844 epoch7 Dice .786904** (final .744870), **seed845 epoch10 Dice .806997** (final .785251). Exact numbers pasted were rounded to 6 decimal places for best values.
- Frozen nonaugmented best: seed843 epoch7 .790623, seed844 epoch12 .789974, seed845 epoch4 .785182. Paired seed improvements +.017759, −.003070, +.021815. Mean of selected-best scores baseline **.788593** versus augmented **.800761** (exploratory +.012168). Baseline across-seed sample SD ~.00297 vs augmented ~.01202; augmented scores more sensitive to seed. **NOT evidence of external generalization or statistically established benefit**, especially selection of each maximum over 20 epochs on the same 11 development subjects.
- Next: submit existing `scripts/hpc/evaluate_csp25d.sbatch` for the THREE frozen augmented best.pt checkpoints at threshold .5 against the unchanged 11-case validation manifest. Use unique private output dirs `baseline_20epoch_augint_seed{843,844,845}_eval_best`. Then report Dice/recall/FP/FN/mm³ errors vs exact-seed original baseline; assess persistent hard cases 102816,106824,113316 and seed-sensitive 111312. Do not select best model or adjust thresholds from these 11. Independent blinded test cohort and true negatives still outstanding.


### 2026-11-26 — Six-model FROZEN best-checkpoint evaluation completed on 11 positives
- User provided actual completed Narval Slurm jobs **10727728, 10727729, 10727730**, evaluation `csp25d-ae843/844/845`, all `COMPLETED 0:0` with runtimes 7/10/6s. These are augmented model evaluation jobs; all 6 per-case summary CSVs saved PRIVATE under `$SCRATCH/csp25d_private/baseline_seed843/runs/` with matching seed/variant suffixes, not uploaded to GitHub. No model retraining.
- Exact values as pasted (4 decimal Dice/recall, 3 decimal MAE):
  | Seed | Arm | Dice | Recall | Mean abs volume error (mm³) | FP vox | FN vox |
  |---|---|---:|---:|---:|---:|---:|
  |843|baseline|.7906|.8976|3.492|150|44|
  |843|train-only mild intensity augmentation|.8084|.9253|4.022|155|34|
  |844|baseline|.7900|.9318|4.864|186|30|
  |844|augmented|.7869|.8323|2.401|112|79|
  |845|baseline|.7852|.8584|2.744|129|67|
  |845|augmented|.8070|.9239|4.116|159|35|
- Three-seed mean Dice **baseline .7886 vs augmented .80077 (+.01217)**. Mean recall **.89593 vs .89383 (-.00210)**, mean per-subject absolute volume error **3.700 vs 3.513 mm³ (-.187)**, per-run mean FP counts **155 vs 142 (-13)** and FN **47 vs 49.33 (+2.33)**. Mean changes are exploratory and heavily depend on seed 844. Baseline/aug selected checkpoint epochs: 843 7/10, 844 12/7, 845 4/10.
- Paired seed effects: 843 Dice +.0178, recall +.0277, MAE +.530mm³, FP +5 FN -10; 844 Dice -.0031, recall -.0995, MAE -2.463mm³, FP -74 FN +49; 845 Dice +.0218, recall +.0655, MAE +1.372mm³, FP +30 FN -32. Both seeds with Dice improvements actually had WORSE volume MAE; seed844 improved volume MAE while recall declined substantially. A low signed or absolute volume difference does not establish spatially accurate segmentation, because FP and FN counts may cancel in total volume.
- Interpretation: augmentation modestly improves average best-of-20 development-validation Dice, but **does not reproducibly improve morphology/volume error across three seeds**, and the 11 positive subjects were repeatedly used to select best epochs and compare hyperparameters. Need independent unselected and preferably family-aware labelled test subjects; no true-negative specificity tested. **Do not change official baseline checkpoint or claim test-set improvement.** Manual R1/R2 intra-rater reliability (~.799) on a different sample is not a strict performance ceiling or directly comparable model benchmark.
- Next minimal analysis: evaluate six same-subject `per_case_metrics.csv` files together to identify if 102816,106824,113316 remain difficult and whether 111312 stays seed-sensitive after augmentation; then freeze training comparisons and move to blinded new-subject test annotation rather than continuing to optimize same 11 validation cases.


### 2026-11-26 — NEXT ACTIVE EXPERIMENT: frozen model scored against 20 blinded repeat annotations (R1/R2)
- User explicitly prioritized **running existing CSP25D U-Net predictions on the same 20 R2 repeat-annotated HCP T2s** before any architectural changes/additional data experiments. R1 vs R2 human reliability was already computed; neural-network-vs-R2 predictions have **NOT YET BEEN RUN**.
- Implemented `scripts/prepare_csp25d_r2_eval_inputs.py`: Windows workstation input completed original 1% proportional crop directory `D:\\CSP_DEEP_SEG\\derived\\roi_batch\\cohort`, full native masks `D:\\CSP_DEEP_SEG\\CSP_Seg`. Packages the fixed 20 R2 cases, two positive/absent references in compact ROI, verifies exact saved R2 voxel counts, binary labels, physical mask-to-T2 affine and complete crop containment, original 17 both-positive/2 R1-absent R2-present/1 both-absent semantics; no arbitrary missing-mask inferred negative. Output PRIVATE `D:\\CSP_DEEP_SEG\\derived\\r2_model_eval_stage`, never overwritten.
- Implemented `scripts/evaluate_csp25d_r2.py` + `scripts/hpc/evaluate_csp25d_r2.sbatch`: 1 frozen forward-pass prediction per T2, score against independent R1/R2 masks separately, record per-case reference-defined FP/FN, Dice, prediction volume, and explicit TRAIN/VAL/not-in-split membership from the original 44/11 manifest. Check saved checkpoint/frozen training-manifest SHA, stage manifest SHA, exact 20 IDs, positivity/absence and voxel counts; fixed threshold 0.5; **never retrain**.
- Full exact terminal protocol in `docs/R2_MODEL_COMPARISON_2026_11_26.md`: Windows `python scripts\\prepare_csp25d_r2_eval_inputs.py --crop-root "D:\\CSP_DEEP_SEG\\derived\\roi_batch\\cohort" --mask-root "D:\\CSP_DEEP_SEG\\CSP_Seg" --out "D:\\CSP_DEEP_SEG\\derived\\r2_model_eval_stage"`, then `scp -r` private stage to Narval `$SCRATCH/csp25d_private`, then submit original seed843 `best.pt` under Slurm. No MRI/labels committed to GitHub, no claim of independent test performance.
- Synthetic tests added `tests/test_csp25d_r2_eval.py` for zero/negative reference semantics, native affine and exact ROI mask extraction, frozen manifest integrity, different R1-vs-R2 denominators. GitHub Actions run **45895189998 COMPLETED SUCCESS** on CI updated commit `9d053d782ea683abb13d63eea11b6b0af207e6bc`. Actual patient-data stage/evaluation **pending user’s Windows packaging and transfer**; no Narval job submitted by assistant.
- Interpret primary metric as paired 17 both-positive Dice(model,R1) vs Dice(model,R2) and Dice(R1,R2), **stratified R1 train exposure**. R2-only positives 107018/109325 and both-absent 102614 are informative for operational presence, not trusted negative specificity. R1 training exposure means R2 results are **annotation-reference sensitivity/in-sample**, not test generalization. Future clean model reset is possible with fresh network and optimizer; never call old data held-out after repeated use.
