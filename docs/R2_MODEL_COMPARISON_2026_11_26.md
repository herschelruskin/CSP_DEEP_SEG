# R2 experiment: frozen U-Net predictions scored against R1 and R2

**Status:** Implemented, synthetic tests added. **No 20-subject R2 model inference has been run yet.** Run only after staging and frozen evidence checks. No network weights will change.

## Scientific purpose and interpretation

The same 20 HCP T2 scans were annotated twice by the same person (R1 and R2), with 17 both CSP-positive, 107018/109325 R1 absent but R2 present, and 102614 both absent. Their prior R1/R2 human intrarater mean Dice was 0.7991 on 17 positive-positive pairs. Comparing a frozen trained model with each label independently quantifies **reference sensitivity**, not independent model performance. Some of these 20 R1 masks were in the original 44-subject training split; the script labels each case **train / val / not_in_model_split**. All 20 belong to the prior crop-calibration/development cohort. Do NOT portray the aggregate as held-out or model-vs-human equivalence.

Primary readout: paired **17 positive-positive** cases only: Dice(model, R1), Dice(model, R2), Dice(R1,R2), paired difference Dice(model,R2)-Dice(model,R1), per-subject FP/FN and signed/absolute volume error. Report 19 R2-positive and 17 R1-positive cases **separately** to avoid mixing different reference denominators. Handle 102614 (both absent) and the two presence disagreements as detection/FP counts, not as convenient Dice=1 or trusted true negatives. Model presence means at least one voxel at fixed threshold 0.5; this is sensitive to small noise and is diagnostic only.

Do not tune thresholds on R2 or retrain with R2 before freezing the comparisons. Preserve private masks.

## Step 1: Windows workstation, package verified 1% crops and R1/R2 references

Use Windows PowerShell. The standalone R2 audit previously verified 19 `<ID>_2.nii` masks and one explicit absent 102614; this package exporter enforces the same R2 full-resolution voxel counts, exact 20 IDs, R1 presence, mask 0/1 binary, physical NIfTI affine and complete mask retention in the prior proportional crop. It refuses to interpret an arbitrary missing mask as an anatomical absence. It reads completed crop files **without recropping**.

If the Windows project clone is `D:\CSP_DEEP_SEG\CSP_crop`, update that checkout from GitHub first. Otherwise, run from whichever local clone includes the current `scripts` folder. Install `nibabel`, `numpy`, and `torch` only if not already present.

```powershell
cd "D:\CSP_DEEP_SEG\CSP_crop"
git switch feature/native-coronal-25d-baseline-20261120
git pull --ff-only
python scripts\prepare_csp25d_r2_eval_inputs.py --crop-root "D:\CSP_DEEP_SEG\derived\roi_batch\cohort" --mask-root "D:\CSP_DEEP_SEG\CSP_Seg" --out "D:\CSP_DEEP_SEG\derived\r2_model_eval_stage"
```

If the local Git folder differs, substitute it; the source data folders are independent. If packaging stops, **do not delete masks or change labels to make it pass**. Share the exact error, especially missing crop/affine/R2-count mismatch. An interrupted stage stays at `r2_model_eval_stage.INCOMPLETE` for inspection; the final directory is only created on success. The output contains compact T2 ROIs and compact masks, NOT original full-resolution scans.

## Step 2: transfer only the new PRIVATE stage to Narval

Create a destination from a Narval SSH shell:

```bash
mkdir -p "$SCRATCH/csp25d_private"
test ! -e "$SCRATCH/csp25d_private/r2_model_eval_stage" || echo "EXISTS: do not overwrite previously transferred R2 stage"
```

Then, from **Windows PowerShell** (not Narval), using the user's existing SSH configuration:

```powershell
scp -r "D:\CSP_DEEP_SEG\derived\r2_model_eval_stage" "hruskin1@narval.alliancecan.ca:/scratch/hruskin1/csp25d_private/"
```

The remote destination must not contain a prior R2 stage. Do NOT push data or private per-subject CSVs to GitHub. Verify Alliance/HCP data-use permissions for private cropped scans as for previous baseline training.

## Step 3: run one original baseline checkpoint on the 20 repeats

In a Narval SSH terminal, on the login node (submission only; GPU inference runs inside Slurm):

```bash
cd ~/CSP_DEEP_SEG
git pull --ff-only
ROOT="$SCRATCH/csp25d_private/baseline_seed843"
export CSP_REPO="$HOME/CSP_DEEP_SEG"
export CSP_VENV="$HOME/venvs/csp25d"
export CSP_PY_MODULE="python/3.11.5"
export CSP_MANIFEST="$ROOT/manifests/model_25d_trainval_seed843_linux.csv"
export CSP_R2_STAGE="$SCRATCH/csp25d_private/r2_model_eval_stage"
export CSP_CHECKPOINT="$ROOT/runs/baseline_20epoch_seed843/best.pt"
export CSP_EVAL_OUT="$ROOT/runs/r2_baseline_seed843_eval"
mkdir -p "$ROOT/logs"
sbatch --account=def-nwc_gpu --gres=gpu:a100_3g.20gb:1 --cpus-per-task=2 --mem=6G --time=00:20:00 --job-name=csp25d-r2-843 --output="$ROOT/logs/r2-seed843-%j.out" --export=ALL scripts/hpc/evaluate_csp25d_r2.sbatch
squeue -u "$USER"
```

A job refuses reused output directories, frozen-manifest hash drift, missing/modified R1/R2 stage, wrong mask geometry or unexpected voxel counts. The R1/R2 masks are never supplied to the U-Net forward pass; predictions depend only on T2. Check completion via `sacct` and read the **private** `$CSP_EVAL_OUT/summary.json` and `per_case_r1_r2_model.csv`. On an empty `squeue`, verify `sacct` rather than assuming completion.

Follow-up: repeat with the other original seeds (844/845) and optionally augmented variants **without changing labels, split or threshold**, with unique output directories. A new untouched test cohort remains necessary before claiming generalization.

## Network reset and data contamination

Loading `best.pt` for inference leaves parameters and batch normalization/group normalization unchanged; `model.eval()` is read-only. R1 training subjects in the R2 queue are in-sample comparisons and remain labelled as such. A future genuine retrain must instantiate a new random-initialized network AND fresh optimizer, exclude all final-test subjects and use final-test masks for evaluation only; model reset does not undo researcher-mediated repeated selection on already inspected validation cohorts.
