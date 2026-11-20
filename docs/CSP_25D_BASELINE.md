# CSP_DEEP_SEG — December 2026 native coronal 2.5D baseline

**Status 2026-11-20: IMPLEMENTED; synthetic CPU-tested (5 passed); no HCP/GPU model run.**

This source is the first simple model baseline for the December checkpoint, not a claim of segmentation accuracy or validated clinical performance.

## Frozen method choices for baseline 25D-v1

1. **Modality/resolution:** raw HCP S1200 3T **T2-weighted SPC1**, nominal 0.7 mm isotropic. Neither the cropper nor loader downsamples/interpolates the T2 or CSP reference mask; high resolution is essential for small CSPs.
2. **Localization:** original, **unshifted head-foreground-proportional** 3D crop fitted by scripts/calibrate_csp_roi_slicer.py. Use precisely the USER-LOCAL rules file at D:\CSP_DEEP_SEG\derived\roi_calibration\results_corrected_112112\calibrated_rules.json, mode proportional and 8-mm fitted margin. It is **head foreground-relative**, not a brain-mask, midline or registration model. Do not substitute posterior-shifted variants or older calibrations.
3. **Reported crop evidence:** after correcting the disconnected 112112 mask and excluding true unusual 108828 **from crop fitting only**, the user-reported proportional crop retained ~**1.00% median original source voxels** with **0/64 internal leave-one-positive-out misses** for fit-positive masks. The exceptionally large 108828 is **not entirely contained** by that standard rule, remains a documented outlier, and requires special handling; its exclusion was post hoc. No independently held-out crop sensitivity is established.
4. **Spatial provenance:** every Slicer-derived crop has matched NIfTI and adjacent .crop.json, preserving the native integer IJK start/end, source/output IJK→RAS affine and original shape. The training loader crops a native, original-T2-aligned binary mask using **exact integer indices**, never resamples; it rejects shape, affine and incomplete-CSP mismatches. Native orientation must have I,J,K corresponding predominantly to LR, AP, SI so J is approximately coronal; other axis orders stop with a clear error, not silent reorientation.
5. **Network:** seven neighboring coronal slices as seven 2D channels, **center-slice-only** 1-channel binary logits. Four-scale compact 2D U-Net, base 16 channels, GroupNorm, bilinear upsampling; **489,281 parameters** by the synthetic smoke test. The input stack spans 4.2 mm between first and last centers at 0.7 mm. A CSP may have only one or many positive central slices; sliding inference reconstructs full 3D probability maps.
6. **Intensity:** per-subject clipped 1st–99th percentile of positive T2 values, output 0–1; CSF remains bright. No learned global histogram parameters; no arbitrary intensity inversion.
7. **Optimization:** AdamW, learning rate 3e-4, seed 843, initially 20 epochs, batch size 1 to preserve variably sized native coronal images. Positive/negative center-slice balancing with replacement; BCE-with-logits everywhere plus soft Dice *only for positive center slices*. Empty slices contribute BCE, not misleading empty-vs-empty Dice=1. Save checkpoint selected by mean positive-reference subject Dice on validation; report empty-reference false-positive mm³ separately.
8. **Label confidence:** manual 70-subject Quick Log = 65 present, 5 operationally absent. At least three absent cases are flagged review; two are described as potentially tiny. **Unresolvable ≠ proven absence**; 7 mm³ is NOT a validated detection threshold. Baseline supervised eligibility: present + QC pass/provisional + binary native mask; needs_review positives excluded until adjudication; absent only with QC pass **and explicit negative_confidence=high**. Negative central slices exactly one slice adjacent to each labeled CSP AP endpoint are skipped for training by default to soften imperfect manual boundary labels. Do not discard absence observations from descriptive datasets, but do not force doubtful negatives into hard supervision.
9. **Partition:** explicit subject-disjoint train/val/test file, no automatic split. Keep SPC1/SPC2 of the same subject together and group relatives together where HCP family metadata can be obtained. Any missing family_group is warned as **family safety not verified**. The original ROI envelope was fitted with all reviewed subjects in development; splitting those 70 for model training is **not independent end-to-end localization validation**. Need new unseen subjects and ideally independently adjudicated tiny CSP cases before research conclusions.
10. **Future, not in v1:** 3/5/7-slice context ablation, richer uncertainty maps, anatomical QC, 3D U-Net, TransUNet, learned horn-based locator, contrast/augmentation studies, self-/semi-supervision, pseudo-label noise/randomization, and varying labeled-sample budgets. Compare only on frozen splits and meaningful morphometric metrics.

## Files introduced

- scripts/csp25d_baseline.py — PyTorch U-Net, original-mask→crop alignment, confident-label policy, subject-disjoint CSV loader, positive/negative slice sampling, train/evaluation, prediction→original MRI reconstruction; run outside Slicer.
- scripts/crop_manifest_slicer.py — manifest-restricted Slicer batch helper; calls existing calibrated native cropper and logs each operation, never uses the subject's CSP reference mask to localize.
- tests/test_csp25d_baseline.py — synthetic shape/stack/affine/mask/gradient/uncertain-label checks.
- requirements-25d.txt — package minimums. GPU PC should install the correct CUDA-enabled PyTorch build from official instructions rather than assuming plain pip torch matches the driver.

## Local Slicer instructions: exactly the unshifted ~1% crop

Original scan path: D:\CSP_DEEP_SEG\T2w\<ID>\<ID>_3T_T2w_SPC1.nii.gz  
Native binary reference labelmap: D:\CSP_DEEP_SEG\CSP_Seg\<ID>.nii  
Original frozen rule JSON: D:\CSP_DEEP_SEG\derived\roi_calibration\results_corrected_112112\calibrated_rules.json  
Slicer crop script dependencies: scripts/reduce_t2_slicer.py and scripts/calibrate_csp_roi_slicer.py (existing), plus scripts/crop_manifest_slicer.py (new).

Place these three scripts together in D:\CSP_DEEP_SEG\CSP_reduced_T2_crop_scaffold\scripts, or add each containing folder to the Python import path. **Paste these as one line each into Slicer**:

    import sys; sys.path.insert(0,r'D:\CSP_DEEP_SEG\CSP_reduced_T2_crop_scaffold\scripts'); import calibrate_csp_roi_slicer as c; import crop_manifest_slicer as b; print(c.__file__,b.__file__)

Three-scan proof first:

    import crop_manifest_slicer as b; b.crop_manifest(r'D:\CSP_DEEP_SEG\derived\roi_calibration\cohort_manifest.csv',r'D:\CSP_DEEP_SEG\derived\roi_calibration\results_corrected_112112\calibrated_rules.json',r'D:\CSP_DEEP_SEG\derived\roi_calibration\model_25d_crops',limit=3)

After checking source IDs, crop faces, NIfTI affine and masks, change to limit=None to crop **only the subjects in the 70-row manifest**, rather than enumerating all 1,113 HCP SPC1 scans. Existing outputs are skipped without overwrite; failures are recorded in local manifest_crop_report.csv. Originals, manual masks and local crop JSON are not committed to Git.

**Reproducibility requirement:** SHA-256 hash and archive a copy of the exact local calibrated_rules.json with each model run. The specific numerical rule coefficients are **not** in GitHub; they currently exist only on the user's drive and need a reviewed, sanitized versioned-release procedure.

## Prepare PRIVATE model manifest and train (PowerShell, GPU PC)

Create a project virtual environment with NumPy, nibabel, pytest and the correct CUDA-enabled torch. From repository root:

    python scripts\csp25d_baseline.py smoke
    python -m pytest -q tests\test_csp25d_baseline.py

Generate editable manifest:

    python scripts\csp25d_baseline.py build-manifest --cohort "D:\CSP_DEEP_SEG\derived\roi_calibration\cohort_manifest.csv" --crop-dir "D:\CSP_DEEP_SEG\derived\roi_calibration\model_25d_crops" --output "D:\CSP_DEEP_SEG\derived\model_25d_manifest.csv"

This private CSV has these columns: subject_id, split, family_group, crop_t2, crop_json, source_mask, presence, qc, negative_confidence. Existing 'dev' is converted to **unassigned**, not silently treated as train; user must explicitly allocate train, val, test and audit mask paths/QC before training. For family-aware split use HCP family identifiers where legitimately available; do not invent them.

The loader requires masks in the same full original T2 grid and affine, with one 0/1 triangular-CSP label. Existing Slicer masks may need export as full original-T2-aligned labelmaps, **without introducing image interpolation**. Absent cases need no physical mask only if confidently adjudicated. The code raises an error on mismatch rather than silently dropping cases. The exceptional positive 108828 will fail containment under standard crop, appropriately requiring fallback/review.

Pilot (only after manifest, QC and crop checks):

    python scripts\csp25d_baseline.py train --manifest "D:\CSP_DEEP_SEG\derived\model_25d_manifest.csv" --out "D:\CSP_DEEP_SEG\model_runs\baseline_25d_v1" --epochs 20 --slices 7 --width 16 --seed 843

This writes local config.json, history.csv and best.pt. Log the actual GPU model/VRAM, torch/CUDA versions, Git revision, crop-rule hash, manifest hash and training time. The repository provides no current HCP Dice or runtime estimate.

Inference:

    python scripts\csp25d_baseline.py infer --manifest "D:\CSP_DEEP_SEG\derived\model_25d_manifest.csv" --checkpoint "D:\CSP_DEEP_SEG\model_runs\baseline_25d_v1\best.pt" --subject-id YOUR6DIGITID --out "D:\CSP_DEEP_SEG\model_runs\baseline_25d_v1\predictions"

It writes subject-ID crop probability NIfTI plus a full original-grid native binary segmentation. **Inference never loads manual reference masks**. The output cannot recover CSP voxels outside the chosen crop.

## Test status and immediate gates

| Check | Status |
|---|---|
| Synthetic 7-channel 73×55→1-channel 73×55 forward and parameter count | **VERIFIED CPU** |
| Synthetic coronal edge stacking and native IJK affine-mask crop | **VERIFIED CPU** |
| Finite BCE/soft Dice on positive and empty slices | **VERIFIED CPU** |
| Review-flagged absent excluded from strict negative supervision | **VERIFIED CPU** |
| Nibabel + actual Slicer crop NIfTI/JSON and saved mask integration | **NOT RUN** |
| Family-disjoint split and actual training inclusion/QC audit | **NOT DONE** |
| First GPU training, subject-level validation Dice, runtime | **NOT RUN** |
| External/held-out localization recall and research-grade performance | **NOT RUN** |

Five tests passed on local CPU with torch 2.10.0; nibabel was not installed in that test environment, so real NIfTI ingestion is still untested. Avoid reporting a model performance result before local HCP integration, tiny-subset overfit, validation and manual adjudication.
