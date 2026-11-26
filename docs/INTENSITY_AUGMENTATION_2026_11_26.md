# CSP25D-v1 controlled T2 intensity augmentation — 2026-11-26

## Interpretation motivating experiment

Three independent identical-architecture 20-epoch runs on frozen 44/11 positive-only development split:

| RNG seed | Best epoch | Best val macro Dice | Mean recall | Mean abs volume error (mm³) | FP voxels (11) | FN voxels (11) |
|---|---:|---:|---:|---:|---:|---:|
|843|7|0.790623|0.8976|3.492|150|44|
|844|12|0.789974|0.9318|4.864|186|30|
|845|4|0.785182|0.8584|2.744|129|67|

Consensus lower-accuracy cases: 102816 (three-seed mean Dice ~0.614), 106824 (~0.707) and 113316 (~0.733). Model predictions for 111312 were seed-sensitive (0.667–0.870). **Reference-defined FP does not automatically mean anatomical error.** R2 intra-rater annotation n=17 mean Dice 0.799 and R2 masks +27.1% more total volume; its sample differs from network validation and therefore is not a model-performance ceiling.

## Single predeclared experimental modification

Test whether mild imaging-intensity perturbations improve cross-seed repeatability or reduce false-positive/volume errors. **This is exploratory**: given HCP-only scanner/sequence and robust per-volume percentile normalization, an improvement is not guaranteed, and intensity augmentation may not fix anatomically attached ventricular leakage.

- **Unchanged:** the exact R1 native labels, 44/11 subject partition, source crop/affine, 7-channel stack, 489k-parameter U-Net, optimizer/loss, sampling, `boundary_ignore=1`, seed set (843, 844, 845), 20-epoch budget, checkpoint selection and inference threshold 0.5.
- **Augmented arm:** each sampled train stack receives one shared gain `U(0.90,1.10)` and offset `U(-0.03,+0.03)` on the original 0–1 normalized nonzero T2 intensities; values clipped back to `[0,1]`, zero background unchanged. The same transform is applied to all 7 coronal channels so spatial and relative cross-slice context remain consistent. No geometry, resolution, masks, validation or inference changes.
- An opt-in CLI flag `--intensity-augment` activates it. The default leaves the existing baseline training computation unmodified. `CSP_INTENSITY_AUGMENT=1` passes the flag through the Narval sbatch wrapper. A CPU generator seeded by `seed + 100000` isolates photometric random draws from the global model/sampler RNG.
- **Primary descriptive comparison**: paired-by-seed mean positive-case validation Dice at best checkpoint. **Secondary**: 11-case mean abs volume error mm³, mean recall, FP/FN burden, and subjects with large Dice variation. Evaluate each best checkpoint using the already versioned `evaluate_csp25d_checkpoint.py` and the immutable original 44/11 manifest.
- We will report all three augmented seeds, including worsening results. The 11 validation subjects have already been used extensively for model development/early stopping, so **no independent generalization claim** or multiple-comparison-adjusted statistical test here. New external testing must remain the next dataset milestone.

## Verification before GPU runs

On Narval after `git pull --ff-only`, check `bash -n scripts/hpc/train_csp25d.sbatch`, `python scripts/csp25d_baseline.py train --help` includes `--intensity-augment`, and that GitHub Actions `CSP 2.5D synthetic CPU tests` succeeded for this code revision. Every baseline and augmented run gets its own directory; do not overwrite seed843/844/845 original checkpoints.

## Submitting the three planned augmented training runs

**Preferred one-command verified workflow** (Narval SSH; no here-document):

```bash
cd ~/CSP_DEEP_SEG
git pull --ff-only
bash scripts/hpc/submit_csp25d_intensity_aug.sh
```

The helper checks the unchanged private manifest SHA256, finds exactly one original
private `calibrated_rules.json` (or uses an explicitly exported `CSP_RULE_JSON`),
checks files, then submits seed 843/844/845 as separate, safe Slurm GPU jobs.
It skips a seed if its output directory or pending/running job is already present,
and prints the current job list. If multiple rule files exist, it stops and
asks for a verified path instead of guessing. The underlying GPU sbatch
uses exactly the same code/config as the manual submissions below.

### Manual submission alternative

Narval SSH terminal (not 3D Slicer, not Windows PowerShell):

```bash
cd "$HOME/CSP_DEEP_SEG"
git switch feature/native-coronal-25d-baseline-20261120
git pull --ff-only
bash -n scripts/hpc/train_csp25d.sbatch
ROOT="$SCRATCH/csp25d_private/baseline_seed843"
export CSP_REPO="$HOME/CSP_DEEP_SEG"
export CSP_VENV="$HOME/venvs/csp25d"
export CSP_PY_MODULE="python/3.11.5"
export CSP_MANIFEST="$ROOT/manifests/model_25d_trainval_seed843_linux.csv"
export CSP_EXPECT_MANIFEST_SHA256="3498caf14cddb7fa56e50b26333a2374d49ac472170231a92a2886b977291229"
export CSP_EPOCHS=20
export CSP_INTENSITY_AUGMENT=1
mkdir -p "$ROOT/logs"
find "$ROOT" -type f -name calibrated_rules.json
```

Set `CSP_RULE_JSON` to the **verified original corrected-112112 calibrated_rules.json path** found above, ideally identical SHA256 to original seed843 training. **Do not guess among multiple files**.

```bash
export CSP_RULE_JSON='PASTE_VERIFIED_ORIGINAL_PRIVATE_RULE_PATH_HERE'
if [[ ! -f "$CSP_RULE_JSON" ]]; then echo 'Calibration file missing: do not submit jobs'; else echo 'Calibration file verified'; fi
sha256sum "$CSP_MANIFEST" "$CSP_RULE_JSON"
```

Run each of the next three submissions separately (a Slurm job is asynchronous, and it can stay queued after closing SSH):

```bash
for SEED in 843 844 845; do
    export CSP_SEED="$SEED"
    export CSP_OUT="$ROOT/runs/baseline_20epoch_augint_seed${SEED}"
    if [[ -e "$CSP_OUT" ]]; then echo "Output already exists: $CSP_OUT — SKIP"; continue; fi
    sbatch --account=def-nwc_gpu --gres=gpu:a100_3g.20gb:1 \
      --cpus-per-task=4 --mem=16G --time=01:00:00 \
      --job-name="csp25d-ai${SEED}" \
      --output="$ROOT/logs/augint-${SEED}-%j.out" \
      --export=ALL scripts/hpc/train_csp25d.sbatch
done
squeue -u "$USER"
```

## Collect outputs

Only after completed exit code `0:0`, read each augmented run's `config.json` and `history.csv`. Compare `intensity_augment=true`, same manifest SHA256 and three paired seeds. Preserve and evaluate all best.pt models in separate output folders; do not promote a new checkpoint on the basis of a single 11-subject best Dice alone.

Next priorities after this controlled comparison: separately adjudicated and untouched test subjects, training data family grouping when possible, and cautious exploration of mask boundary uncertainty / presence discrimination. The initial augmented arm is neither an anatomical localizer nor a detector of CSP absence.



## Final exploratory six-checkpoint evaluation results (2026-11-26)

All augmented saved-best evaluation jobs completed successfully on Narval: `10727728` (843), `10727729` (844), `10727730` (845), `COMPLETED 0:0`. User reports:

| Seed | Arm | Best val mean Dice | Recall | Mean abs volume error mm³ | FP vox | FN vox |
|---|---|---:|---:|---:|---:|---:|
|843|Original|0.7906|0.8976|3.492|150|44|
|843|Augmented|0.8084|0.9253|4.022|155|34|
|844|Original|0.7900|0.9318|4.864|186|30|
|844|Augmented|0.7869|0.8323|2.401|112|79|
|845|Original|0.7852|0.8584|2.744|129|67|
|845|Augmented|0.8070|0.9239|4.116|159|35|

Mean over seeds: Dice original .7886 vs augmented .8008 (+.0122); recall .8959 vs .8938; mean abs volume error 3.700 vs 3.513 mm³; FP voxels averaged per run 155 vs 142; FN 47 vs 49.3. Changes are inconsistent across seeds: augmentation improves Dice on 843/845 **while increasing their volume errors**; for 844 it reduces excess FP/volume error while substantially worsening recall (49 additional FN voxels). Thus **higher Dice does not consistently yield more accurate CSP volume**. Neither variant has a reliable demonstration of independent generalization, nor were definite-negative controls evaluated.

### Read-only per-subject six-run comparison

A new versioned script `scripts/compare_csp25d_variants.py` loads all six private `per_case_metrics.csv` outputs, verifies matching subject IDs/reference voxel counts, and displays by-subject three-seed mean Dice, FP/FN and seed sensitivity. Run from Narval login, **no GPU necessary**:

```bash
cd ~/CSP_DEEP_SEG
git pull --ff-only
python3 scripts/compare_csp25d_variants.py --runs-root "$SCRATCH/csp25d_private/baseline_seed843/runs"
```

Its synthetic checks are `tests/test_csp25d_variant_comparison.py`, included in the GitHub CPU CI. The script never trains, infers or modifies labels. Once the per-case comparison is reviewed, stop experimenting on the same 11 cases; prioritize a blinded independent set from as-yet-unlabelled HCP subjects, including a presence/absence evaluation and appropriate family partitioning where possible.
