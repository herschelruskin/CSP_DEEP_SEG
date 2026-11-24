# Test execution log

**Not a checklist of imagined successes.** Append one record per execution with exact command, tested input and evidence. Empty results mean not run.

| Execution ID | Date | Test | Input / split | Code/config commit | Result | Evidence / notes |
|---|---|---|---|---|---|---|
| — | — | — | — | — | **NO VERIFIED REAL-DATA EXECUTIONS YET** | — |

## Conversation-observed / user-reported activity (NOT VERIFIED as reproducible repository tests)

| Event | Date | Inputs / command context | Evidence level | Limitation and follow-up |
|---|---|---|---|---|
| Synthetic ANTsPy registration + 2-subject real HCP T2 rigid smoke test | 2026-11-17 | Local Docker `ventricle-antspy:0.1`; fixed 100206 / moving 100307 at ~2 mm; rigid affine later applied to original 0.7 mm moving image | USER-REPORTED local outputs and Slicer observation | Need actual command/config, transform-direction round-trip, registration metrics and reproducible bundle; not REG-02 (20-case) pass |
| Slicer candidate ROI on 2 subjects | 2026-11-17 | Approx. 15.3 mm LR × 59.8 mm AP × 19.2 mm SI | CONVERSATION-OBSERVED visual exploratory placement | Not ROI-01/02 pass; no quantitative mask containment or held-out cases |
| Processed HCP FreeSurfer ventricular labels | 2026-11-17 | One HCP case: aparc+aseg labels 4/43 extracted; FreeSurfer CSP label 72 yielded zero voxels | Python-console output USER-REPORTED | CSP absence not inferred; processed-to-native geometry unverified |
| HCP filename inventory and Quick Log import | 2026-11-17 | Local directory CSV imported into Google Sheets; 1,689 unique scan keys from 1,113 subjects | CONNECTOR-RECONCILED filename inventory | Data-01 *filename census* only; not MRI file checksum/full decode/QC |
| Triangular CSP manual review | 2026-11-17 | ≥20 subjects user-reported; first checkpoint 19 present, 1 absent | USER-REPORTED local annotation | Need native-mask files and actual QC-pass count; no Dice/test split |
## Test registry

| Identifier | Purpose | Minimum outcome |
|---|---|---|
| DATA-01 | Reconcile unique subjects, acquisitions, scan orientation | Complete valid/invalid manifest |
| DATA-02 | ZIP/gzip integrity + pixel decoding | Verifiable pass/fail for every processed file |
| DATA-03 | Repeated acquisitions | No duplicate subject counted as independent |
| DATA-04 | Tri-planar image visual audit | Flags and examples |
| REG-01 | Forward/inverse transform and coordinate round-trip | Numerical accuracy below declared tolerance |
| REG-02 | Rigid alignment | Midline/ventricle agreement evaluated |
| REG-03 | Determinism/reproducibility | Parameter/seed-dependent tolerance documented |
| REG-04 | Affine-only vs ANTs | Coverage/failure/runtime comparison |
| REG-05 | Runtime/memory | Each pilot scan logged |
| ROI-01..05 | Septal crop evaluation | Visual tri-planar, mask containment, boundary margin, empty cases |
| ANN-01..05 | Manual mask QC | Geometry, anatomy, repeat annotation, split safety |
| MOD-01..05 | Architecture smoke/unit tests | Shape, memory, train step, native-space reconstruction |
| TRN-01..05 | Training reproducibility | No leakage, recorded settings, valid checkpoint |
| VAL-01..06 | Held-out metrics | Verified evaluation scripts and uncertainty |

## Execution template

```text
Execution ID: TEST-YYYYMMDD-NNN
Test ID:
Date/time and executor:
Dataset/source SHA256 (private manifest ref):
Subject/scan count and split hash:
Exact command and configuration path/hash:
Git commit; software/OS/CPU/GPU:
Expected result / tolerance (declared before run):
Observed metrics, wall time, peak RAM:
Status: PASS | FAIL | INCONCLUSIVE
Evidence artifacts and output SHA256:
Issues and follow-up decision:
```

## 2026-11-19: synthetic reduced-T2 crop geometry tests

- **Test ID:** ROI-SYN-001; **Status:** VERIFIED LOCAL SYNTHETIC PYTEST ONLY.
- **Command:** `pytest -q tests/test_reduce_t2_geometry.py` (run against source content later committed to `scripts/reduce_t2_slicer.py` and `tests/test_reduce_t2_geometry.py`).
- **Result:** `4 passed in 0.60s` after fixing a percentile-threshold edge case on a constant-intensity synthetic foreground.
- **Tested:** KJI array slicing and IJK-to-RAS origin shift, left-right-flipped anisotropic synthetic geometry, oblique ROI enclosure, whole-mask inclusion vs out-of-crop voxel, empty-mask handling, invalid settings and singular matrix rejection.
- **Not tested:** 3D Slicer API end-to-end integration, actual `.nii.gz` saved spatial fields, HCP file loading, manual mask quality, real anatomical ROI containment, runtime/VRAM, or reliability across subjects. No real source data available in the testing runtime.
- **Next test ID:** ROI-REAL-001: original HCP T2 -> saved reduced NIfTI -> reload -> physical-voxel mapping and trim containment check in Slicer, single subject first.

## ROI-SLICER-API-001 — 2026-11-19
- **USER-REPORTED FAILURE:** `reduce_active_t2` raised `AttributeError` because `vtkMRMLSelectionNode` has no `GetReferenceActiveVolumeID` getter, on local Slicer in `D:\CSP_DEEP_SEG\CSP_reduced_T2_crop_scaffold`.
- **FIX IMPLEMENTED:** select background volume from Red slice view, falling back to supported `GetActiveVolumeID`; direct `reduce_volume_t2(source_node, ...)` also bypasses selection lookup.
- **TESTS VERIFIED LOCALLY:** 6/6 synthetic/monkeypatched pytest tests pass (four prior geometry tests + two API regression tests); full Slicer runtime save/reload and actual HCP ROI validation remain **NOT RUN**.

## ROI-REAL-001 — 2026-11-19 initial HCP output (USER-REPORTED)
- **PARTIAL PASS / validation incomplete:** User successfully ran `reduce_volume_t2` on Slicer's Red background volume. File and crop JSON reported saved; actual file reloading and anatomical overlap not yet independently verified.
- Native HCP T2 source: `114217_3T_T2w_SPC1.nii.gz`; KJI shape 320×320×256. Reduced output: 262×252×123, 31.0% retained (~69.0% eliminated). Start IJK [66,55,12], end-exclusive [189,307,274]. Local output under `D:\CSP_DEEP_SEG\derived\reduced_t2\`.
- Printed output affine is numerically consistent with original IJK-to-RAS and crop start (reported matrices satisfy origin shift to numerical precision). This does NOT prove that saved/reloaded NIfTI geometry is correct.
- User log: `mask_audit=None`. Still **NOT RUN:** manual-CSP mask containment, voxel-by-voxel equality of saved crop versus original, loaded overlay in three planes, independent sample assessment. Initial cropping algorithm uses foreground-centered RAS bounding box, not a fully fitted midsagittal symmetry plane.

## ROI-COHORT-SYN-001 — 2026-11-19
- **STATUS: VERIFIED LOCAL SYNTHETIC ONLY**. Command: `python -m pytest -q tests/` run against new `scripts/calibrate_csp_roi_slicer.py`, `tests/test_calibrate_csp_roi.py`, and existing cropper/tests in local staging. Result: **15 passed in 0.67s** (9 new tests + 6 existing).
- New tests: confirmed absent zero vs missing mask; nonempty mask invalid for absent; fit fixed-mm and proportional rules enclosing synthetic development CSPs across different affine scales; variable-size responsive proportional boxes; exact sparse/dense containment; automatic original-SPC1/mask pairing; ambiguous-multiple-mask rejection; leave-one-subject-out outlier sensitivity; Slicer-runner mock writes local outputs, respects split and excludes protected holdout. Includes oblique/native geometry tests from existing suite.
- **NOT RUN:** code inside real Slicer on the user's 70 T2/mask pairs; actual background/brain or intracranial anchor validation; true midsagittal plane fit; family-disjoint validation; holdout performance; batch generation of calibrated reduced T2s. No benchmarked HCP coverage percentages or learned safe crop dimensions.
- **Next test:** `ROI-COHORT-REAL-001`: auto-manifest original masks, reconcile 65 positive/5 absent/flagged QC, freeze dev/holdout, run cohort RAS bound extraction and compare coverage/margins, manually inspect largest subject and minimum-margin cases.

## ROI-MANIFEST-REVIEW-001 — 2026-11-19
- **USER-REPORTED FAILURE:** 70 manifest rows but presence counts were 55 present / 5 absent / 10 uncertain. Underlying cause: review-list membership converted mask-containing CSP-positive subjects to uncertain presence.
- **FIX:** presence is explicit `absent` when listed, otherwise `present` for mask-discovered rows unless overridden by an explicit status CSV; review only changes `qc`. Calibration now accepts `qc=needs_review` positive masks for *exploratory* envelope fitting (default) while preserving sensitivity excluding them.
- **VERIFIED LOCAL SYNTHETIC TESTS:** `python -m pytest -q` in `/mnt/data/csp_roi_calibration`, **17 passed in 0.71s**. New regression tests assert that a review-listed mask remains positive, the large review-flagged mask expands the fit, ranking preserves its QC, and sensitivities are recorded.
- **NOT RUN:** real-data 70-subject rerun; no claim of true CSP containment or accurate manual boundaries.

## ROI-OUTLIER-001 — 2026-11-19
- Rationale: User explicitly selected atypically large 108828 (2200 mm³) for exclusion from standard crop fitting, but not from measurement or audit.
- Source implementation `scripts/calibrate_csp_roi_slicer.py`: new `excluded_from_fit_ids` argument; validates ID and dev designation, fits on remaining development masks, preserves excluded case in `subject_measurements.csv`, `largest_csp_ranked.csv`, `rule_evaluations.csv`, and does not include it in LOO training.
- **Local verification:** `python -m pytest -q` in `/mnt/data/csp_roi_outlier_patch`: 19 passed in 0.76 s. New regression test models a large outlier and asserts it is absent from fit but still audited/ranked; another prevents silently ignoring an unknown excluded ID.
- **Not yet run on real 70 subjects:** output crop dimensions and missed-mask rates for outlier-excluded fit. 108828 was examined before selection and hence is not a valid independent test case.


## MOD-25D-001 — 2026-11-20 synthetic CPU checks (VERIFIED LOCAL; HCP NOT RUN)

- Script: tests/test_csp25d_baseline.py against scripts/csp25d_baseline.py, torch **2.10.0+cpu**, pytest **9.0.2**.
- Command: python -m pytest -q tests/test_csp25d_baseline.py → **5 passed** (approx. 1–2 s in local runtime).
- Checks: odd-height/width shape preservation by seven-channel U-Net; coronal J-axis nearest-edge replication; exact IJK crop and affine-offset native mask extraction with wrong-affine rejection; finite gradient for positive and empty-reference BCE/Dice loss; filter rejecting provisional/needs-review absent subjects as strict negatives.
- Command: python scripts/csp25d_baseline.py smoke → **passed**, 7-channel 73×55 → 1-channel 73×55, **489,281 parameters**.
- **NOT RUN:** nibabel installed/imported for actual scan, Slicer crop manifesto loop, HCP mask affine round-trip, GPU training or inference, cohort-level effectiveness/accuracy. These have no measured results.


## MOD-25D-002 — 2026-11-23 GitHub Actions synthetic CPU run

- **Source:** https://github.com/herschelruskin/CSP_DEEP_SEG/actions/runs/45209618429
- **Commit:** 9b12b023230a790dc3c58324b2f9d19452b63d on feature/native-coronal-25d-baseline-20261120.
- **Status:** VERIFIED CI PASS, CPU synthetic tests only. GitHub Ubuntu runner, Python 3.11, pip CPU PyTorch and nibabel.
- **Command:** python -m pytest -q tests/test_csp25d_baseline.py tests/test_csp25d_integration.py
- **Observed:** 10 passed in 1.95s. Additional model smoke confirmed 489,281 parameters and correct output dimensions.
- **Scope:** Existing 5 smoke tests plus 5 synthetic integration/sampling tests: per-subject sampler class weights, original NIfTI-to-crop integer voxel/affine roundtrip, modified-pixel detection, wrong-rule rejection and copied-crop subject mismatch.
- **Caveat:** Real-HCP Slicer files, family metadata, saved label QC, Alliance CUDA runtime, actual MRI segmentation accuracy and image-level validation remain NOT RUN. Later commit added a synthetic volume-error test; re-check latest CI before claiming 11 passed.


## MOD-25D-003 — 2026-11-23 latest corrected CPU CI, exact native reconstruction and overfit

- **Status: VERIFIED CI PASS**, latest tested code commit 6efb84e94235b7d4f3086370a279339a23901e0b, workflow https://github.com/herschelruskin/CSP_DEEP_SEG/actions/runs/45210799717.
- Command: python -m pytest -q tests/test_csp25d_baseline.py tests/test_csp25d_integration.py, plus python -m compileall, bash -n scripts/hpc/train_csp25d.sbatch, and python scripts/csp25d_baseline.py smoke.
- **Observed: 13 passed in 2.88s**, model CPU smoke passed with 489,281 parameters. CI job completed success.
- New checks beyond MOD-25D-002: one-voxel mm3 Dice/recall/false-positive/volume-error semantics; exact crop-mask-to-source-grid reconstruction and wrong-shape rejection; synthetic positive-mask overfit via actual optimizer steps.
- **Limitations:** tests use tiny synthetic NIfTI images and generated masks, not real Slicer/HCP T2 files or Alliance GPUs. No quantitative original-HCP audit, job runtime, VRAM benchmark, Dice or independent ROI sensitivity measured.

## MOD-25D-004 — 2026-11-23 existing-batch reuse and real-label diagnostic (VERIFIED SYNTHETIC CPU ONLY)

- **Code branch:** feature/native-coronal-25d-baseline-20261120; **tested commit:** 9446c05bbab284f87754d872636d40b7a3e0816f.
- **Evidence:** GitHub Actions https://github.com/herschelruskin/CSP_DEEP_SEG/actions/runs/45233936711, completed **success**. Ubuntu runner, Python 3.11, CPU torch, NumPy and nibabel.
- **Exact CI check:** `python -m compileall -q scripts/csp25d_baseline.py scripts/audit_csp25d_manifest.py scripts/inventory_csp25d_crops.py scripts/overfit_csp25d_real.py scripts/reconcile_csp25d_manifest.py scripts/relocate_csp25d_manifest.py`; `bash -n scripts/hpc/train_csp25d.sbatch`; `python -m pytest -q tests/test_csp25d_baseline.py tests/test_csp25d_integration.py`; `python scripts/csp25d_baseline.py smoke`.
- **Observed:** **20 tests passed in 2.69s**; 489,281 model parameters. New tests check saved crop/source NIfTI equality under synthetic geometry, wrong frozen crop rule and offset, staging-vs-final output inventory, maximum-positive-center-slice extraction and strict train-only overfit usage, exact crop-path manifest reconciliation and duplicate/mismatched subject rejection.
- **Scope:** Verified script syntax and unit/integration logic with fabricated masks, not actual HCP image/annotation integration. No evidence of original batch file integrity, label QC, real train-only overfit success, Alliance access, memory/runtime, real Dice or independent held-out results.
- **Next gate:** run `scripts/inventory_csp25d_crops.py` locally on actual final cohort ROI directory with original T2 root and frozen corrected-112112 rules. Confirm 1,112 completed claims, identify the single exception, run limited voxel-equality sampling, then `scripts/reconcile_csp25d_manifest.py` and label-aware `scripts/audit_csp25d_manifest.py` before transferring any private data.


### 2026-11-24 — Narval deployment and original NIfTI orientation verification

- **USER-EXECUTED Narval:** Python 3.11.5; PyTorch 2.14.1+ComputeCanada with CUDA runtime 13.2; 20/20 existing synthetic tests passed in 168.12 s on login node (avoid heavy repeated tests there). Actual A100 MIG GPU performed synthetic seven-channel CSP U-Net forward/backprop: output 1x1x128x128, 489,281 parameters and Torch peak allocated 30.46 MB for that input only. The interactive allocation subsequently reached its time limit. No real T2 training or Dice result.
- **USER-EXECUTED Windows:** 1,112/1,113 source scans passed saved crop file/provenance/affine inventory; one known atypically large case lacks standard crop. 69/70 manually reviewed subjects reconciled. All 55 provisional CSP-positive masks passed original-grid mask geometry and whole-mask crop containment (without original-source voxel check).
- **CROSS-TOOL ORIENTATION DIAGNOSIS:** Previous original-source --verify-original audit reported affine mismatch because Slicer imported one native HCP T2 with its K axis reversed relative to NiBabel. User ran independent corrective comparison: max affine residual 1.0567e-5 mm, maximum source/crop voxel difference 0, and matching crop shape. Demonstrated for that one subject only.
- **IMPLEMENTED:** Shared scripts/native_nifti_orientation.py identifies unique signed axis permutations with no resampling; scripts/audit_csp25d_manifest.py and scripts/inventory_csp25d_crops.py use it. Synthetic NumPy validation of nine mappings passed locally; repository regression tests added. Check GitHub Actions result separately before claiming latest complete suite success.
- **PENDING:** Rerun --verify-original --eligible-only for all 55 on user's Windows workstation; real MRI GPU overfit and family-disjoint evaluation not yet run.

- **GitHub Actions VERIFIED after correction:** CI run https://github.com/herschelruskin/CSP_DEEP_SEG/actions/runs/45456978796 at commit 04f1ea1c5de3207df2124f97ed8f700f27961647: **25/25 synthetic CPU tests passed in 3.34 s**, U-Net forward smoke 489,281 parameters. Earlier intermediate regression run at 071aa7f8 failed because it incorrectly expected swapped native axes to pass the coronal-model restriction; the test was corrected and the subsequent complete suite passed. No MRI-derived HCP training result was created by this CI.

- **USER-VERIFIED 2026-11-24, Windows original-source preflight:** Updated orientation-aware `scripts/audit_csp25d_manifest.py --verify-original --eligible-only` completed against the private 69-subject manifest and corrected frozen rule JSON: **55 selected subjects, failures=0**. Report saved privately at `D:\CSP_DEEP_SEG\derived\model_25d_mask_source_voxel_audit.csv`. This extends single-subject exact-source proof to all 55 provisional positives. Does not attest anatomical annotation perfection or family-independent model generalization.

- **2026-11-24 compact-mask implementation (CI VERIFIED):** Added compact ROI uint8 .nii.gz mask exporter with strict original-positive count preservation and source/ROI affine checks; baseline loader now supports either original full-grid or crop-grid binary labels. GitHub Actions CI at https://github.com/herschelruskin/CSP_DEEP_SEG/actions/runs/45468468705 reports **28/28 tests passed in 2.77 s**, with 489,281-param CPU smoke passed. New tests cover lossless crop mask export/reload, wrong affine, nonbinary mask and incomplete full-native mask containment. User still needs to run exporter on actual 100408 mask and stage result on Narval.

### 2026-11-24 — First real HCP CSP U-Net overfit SUCCESS (train-only; not held-out)

- **User-run Narval GPU batch** Slurm JobID 10446859, name `csp100408`, status `COMPLETED`, elapsed 00:00:15, exit 0:0, on compute node `ng20304`, A100-SXM4-40GB physical GPU with allocated MIG 20GB slice. No GPU driver errors during job.
- **Private data:** HCP `100408` cropped T2 (51x70x68 IJK), binary compact cropped mask (42 total labeled 3D voxels, 1,344 bytes), audited on Windows against original and on Narval with `failures=0`. Frozen rule SHA256 4195a852095b50e5f0e9980bc73140d6a04354ca8dd819ef7a2afd9893764f66. One TRAIN subject, no family_group; warning expected.
- **Experiment:** `scripts/overfit_csp25d_real.py --manifest <private pilot_100408_compact_linux.csv> --subject-id 100408 --steps 150 --report-every 10 --slices 7 --width 16 --lr 0.001`. U-Net 489,281 params; repeatedly optimized maximum reference-positive coronal slice. `training_loss` 2.16257 (step 1) -> 1.10872 (step 150), monotonic at printed checkpoints. Thresholded TRAIN-slice Dice zero through step 110, 0.800 (step 120), 0.888889 (130), **best observed 0.909091 (140)**, 0.857143 (150). Internal elapsed ~2.359 s, full Slurm job elapsed 15 s. Outputs `overfit_run1/{config.json,history.csv,train_slice_metrics.csv,overfit_debug.pt}` are private scratch artifacts. Final training metric CSV not yet separately inspected.
- **Interpretation:** Successful real-data train-only single-slice memorization; not validation, no evidence for unseen subject Dice, anatomical correctness, or negative-case false-positive control. Since 3D reference has only 42 voxels and chosen slice even fewer, Dice is highly discrete/sensitive to small voxel changes. Need inspection of actual final predicted/reference slice voxel counts from `train_slice_metrics.csv`; then expand to subject/family-safe multi-subject baseline and held-out validation.

- **2026-11-24 confirmed real-data overfit final metric CSV:** Slurm job 10446859 output `train_slice_metrics.csv` has subject `100408`, center coronal `j=50`, Dice `0.8571428571428571`, `reference_area_voxels=12`, `predicted_area_voxels=9`, absolute 3-voxel volume difference `1.0289999348448582 mm^3`. From Dice=18/21, inferred TP=9, FP=0, FN=3; **precision 1.0, recall 0.75** for that TRAIN slice only. Final saved files `config.json` (360 B), `history.csv` (631 B), `overfit_debug.pt` (~1.9 MB), `train_slice_metrics.csv` (169 B). Reference total 3D mask has 42 voxels, not 12. No 3D or held-out Dice measured.

- **2026-11-24 exploratory volume split regression CI PASSED:** GitHub Actions https://github.com/herschelruskin/CSP_DEEP_SEG/actions/runs/45472899918 at source commit f59e477493806ac0140e29f7172648aac34de51b: **30/30 synthetic tests passed in 2.73s**, 489,281-parameter CPU forward smoke passed. `scripts/split_csp25d_exploratory.py` creates fixed-seed rank-volume-tercile 44-train/11-val 55-positive subject-only partition; refuses unknown-family fallback without explicit opt-in, missing/nonpassing reference audit, preassigned splits, or any populated family identifiers. No empirical held-out 3D Dice yet.
