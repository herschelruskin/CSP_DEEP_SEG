# Test execution log

**Not a checklist of imagined successes.** Append one record per execution with exact command, tested input and evidence. Empty results mean not run.

| Execution ID | Date | Test | Input / split | Code/config commit | Result | Evidence / notes |
|---|---|---|---|---|---|---|
| — | — | — | — | — | **NO VERIFIED REAL-DATA EXECUTIONS YET** | — |

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
