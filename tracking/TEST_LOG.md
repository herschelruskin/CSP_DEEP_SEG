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
