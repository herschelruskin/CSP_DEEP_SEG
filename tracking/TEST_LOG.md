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
