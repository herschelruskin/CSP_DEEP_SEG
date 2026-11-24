# Native CSP prediction spatial QC and home Slicer inspection

This is a private reproducibility/inspection workflow for the **frozen epoch-1 checkpoint**
from the November 24, 2026 two-epoch 44/11 pilot. It does not train,
change manual masks, resample, recalibrate the ROI, optimize thresholds,
or run new test-set model selection.

## Why this is necessary

The first 11 reference-positive validation subjects yielded mean whole-ROI
3D Dice 0.708307 and mean recall 0.895078 at threshold 0.5. The pooled
prediction contained 690 voxels versus 469 manual voxels, with 422 true
positives, 268 false positives and 47 false negatives. All 11 predicted
volumes exceeded their reference volumes. Overlap counts **do not tell us**
whether the errors are one expanded CSP, adjacent ventricle leakage or
multiple disjoint blobs. The spatial export answers that question.

The existing 44/11 split is subject-disjoint but family independence is
unknown, because restricted HCP family metadata were not available. The
crop rule was also calibrated using development masks. Therefore all
results remain exploratory, not a publication-ready independent test.

## Narval export

Run these commands from your existing **Narval Linux shell**.
Do not invoke expensive multi-subject inference on the login node;
the job script requests a GPU. Keep the private output in scratch.

~~~bash
cd ~/CSP_DEEP_SEG
git pull --ff-only

ROOT="$SCRATCH/csp25d_private/baseline_seed843"
export CSP_REPO="$HOME/CSP_DEEP_SEG"
export CSP_VENV="$HOME/venvs/csp25d"
export CSP_PY_MODULE="python/3.11.5"
export CSP_MANIFEST="$ROOT/manifests/model_25d_trainval_seed843_linux.csv"
export CSP_CHECKPOINT="$ROOT/runs/pilot_2epoch/best.pt"
export CSP_PRIOR_METRICS="$ROOT/runs/pilot_2epoch_eval_best/per_case_metrics.csv"
export CSP_SPATIAL_OUT="$ROOT/runs/csp25d_spatial_qc"
mkdir -p "$ROOT/logs"

sbatch --account=def-nwc_gpu \
  --gres=gpu:a100_3g.20gb:1 --cpus-per-task=2 --mem=4G --time=00:15:00 \
  --job-name=csp25d-qc --output="$ROOT/logs/spatial-qc-%j.out" \
  --export=ALL "$CSP_REPO/scripts/hpc/export_csp25d_spatial_qc.sbatch"
~~~

The exporter checks that the checkpoint matches the exact original
manifest SHA256, requires best.pt from epoch 1, reproduces all 11 previous
per-case TP/FP/FN and Dice values, verifies native image alignment, and
exports all 11 validation subjects. It creates a private ZIP:

    /scratch/hruskin1/csp25d_private/baseline_seed843/runs/csp25d_spatial_qc.zip

No whole-brain T2 data or original full-brain segmentations are included.
The source crops and manual reference files are never modified.

## Private transfer ZIP layout

The ZIP contains a directory csp25d_spatial_qc. Each cases/SUBJECT_ID
subdirectory contains:

- T2_crop.nii.gz — byte-identical saved native cropped T2 scan
- manual_CSP.nii.gz — manually labelled CSP, binary 0/1
- predicted_CSP.nii.gz — model CSP at frozen threshold >= 0.5
- probability_CSP.nii.gz — continuous 0–1 sigmoid probability (no thresholding)
- error_TP1_FP2_FN3.nii.gz — categorical 0 background; 1 true positive,
  2 false positive, 3 false negative

All NIfTI files have the same original cropped affine/shape/voxel
coordinates. No smoothing, relabeling, resampling or segmentation
morphology operations are applied.

The package also has:

- component_report.csv — 6- and 26-connectivity predicted and FP-only
  counts, largest predicted component size/fraction, FP attached to
  main predicted component and FP outside that main component
- manual_review_template.csv — one row per subject to document visual QC
- summary.json — immutable checkpoint/manifest hashes, summary counts
- file_sha256.csv — per-file hashes and file sizes
- slicer_csp25d_qc_loader.py — Slicer loader and error overlay
- README_QC.txt — short in-bundle directions

## Download on your home Windows computer

After the export job is COMPLETED, use **Windows PowerShell**:

~~~powershell
$dest = "$env:USERPROFILE\Downloads"
scp -o ServerAliveInterval=30 "hruskin1@narval.alliancecan.ca:/scratch/hruskin1/csp25d_private/baseline_seed843/runs/csp25d_spatial_qc.zip" "$dest\csp25d_spatial_qc.zip"
Get-FileHash "$dest\csp25d_spatial_qc.zip" -Algorithm SHA256
Expand-Archive "$dest\csp25d_spatial_qc.zip" -DestinationPath $dest
~~~

Compare the SHA256 from PowerShell against the hash printed by the Narval
exporter before reading. All MRI-derived files remain private; do not
push this ZIP, images, review sheets or manifests to public GitHub.

## Load cases for manual QC in 3D Slicer

Open 3D Slicer > View > Python Interactor.
Paste this as **one line** in Slicer's Python Console:

~~~python
exec(open(str(__import__('pathlib').Path.home()/'Downloads'/'csp25d_spatial_qc'/'slicer_csp25d_qc_loader.py'),encoding='utf-8').read()); load_csp25d_qc()
~~~

Choose a directory under Downloads/csp25d_spatial_qc/cases/SUBJECT_ID.
The loader asks before clearing the Slicer scene, preserving a chance
to save your manual work. It shows the T2 crop as the background,
and the categorical error volume as a semi-transparent labelmap:

- GREEN: predicted CSP coincides with manual annotation (TP)
- RED: predicted CSP not in manual annotation (FP)
- BLUE: annotated CSP omitted from prediction (FN)

Both manually labelled and predicted CSP are also loaded into separate
initially hidden segmentation nodes. Toggle them in the Data or
Segmentations module. Coronal view is first priority, followed by axial
and sagittal. Use the same level/window approach for each case.
Save screenshots or scene snapshots locally only.

## What to inspect and record

In manual_review_template.csv, for each case, record whether the
largest predicted component overlaps the correct CSP, whether it
overshoots AP / SI / LR boundaries, whether it leaks into the lateral
ventricles or cavum vergae region, whether disconnected extra islands
exist and whether the reference annotation itself appears uncertain.
Keep labels objective, and do not revise ground truth during this
inspection. The initial cases with lower Dice are good candidates for
review alongside one high-Dice case, but review all 11 if possible.

### How to interpret component counts

- 26-neighbor connectivity regards face, edge **and corner** touching
  voxels as connected. 6-connectivity requires a shared voxel face.
- A single 26-connected predicted component plus all false positives
  inside that main component is consistent with one enlarged blob,
  **but does not establish** whether it represents anatomically
  plausible boundary expansion or leakage into adjacent CSF.
- More than one 26-connected predicted component establishes
  multiple predicted islands; inspect their sizes and locations.
- FP-only connected component counts are not equivalent to
  prediction component counts: the manual CSP can partition an
  oversized continuous prediction into several FP-only regions.
- A difference between 6- and 26-component counts indicates
  edge/corner-only connections, which may be fragile under thresholding.
- Spatial error measurements at one threshold do not measure
  specificity on truly absent CSPs, which this sample lacks.

After QC, preserve original 2-epoch checkpoint as frozen baseline and
pursue a separate longer-training run without reinterpreting the same
validation subjects as an untouched independent test set.
