# Progress tracker — CSP_DEEP_SEG

**Last updated:** 2026-11-13 · **Snapshot:** documentation created; no registration, ROI or model results yet.

| Step | Status | What we have | What remains | Gate / next proof |
|---|---|---|---|---|
| 1. T2 extraction & QC | **DONE-REPORTED / QC OPEN** | User reports 1,689 extracted HCP T2 scans, all 0.7 mm isotropic; SPC1/SPC2 present | Unique-subject census, full integrity/QC, error manifest | `DATA-01..04` with real evidence |
| 2. Rigid alignment | **NEXT** | Design: ~2 mm temporary images, rigid 6 DOF, native transform retention | Pick reference; build 20-scan pilot and test against no-registration | `REG-01..05` |
| 3. Parcellation / ROI | **PENDING** | Septum/frontal horns identified as relevant anatomical anchors | Versioned ROI in mm, transform mapping, visual and containment tests | `ROI-01..05` |
| 4. Manual annotations | **PENDING (parallel)** | Target ~120 manually reviewed subjects proposed | Freeze anatomy SOP and splits; draw masks, QC and repeat subset | `ANN-01..05` |
| 5. Models | **PENDING** | Classical, 3D U-Net and bottleneck-attention TransUNet planned | Implement fair baselines and memory tests | `MOD-01..05` |
| 6. Training | **PENDING** | Label-efficient extension considered | Train-only normalization/splits, seed/optimizer configs, logs | `TRN-01..05` |
| 7. Validation | **PENDING** | Dice + volume/error/failure evaluation planned | Locked test set, manual review and statistical intervals | `VAL-01..06` |

## Next action queue (in priority order)

- [ ] `DATA-01` count **unique subjects and per-subject SPC1/SPC2**, not just acquisitions.
- [ ] `DATA-02` complete integrity checks or explicitly flag incompletely verified scans.
- [ ] `REG-00` decide stable fixed T2 reference and pin its source/hash.
- [ ] `REG-01` implement forward/inverse coordinate mapping unit test.
- [ ] `REG-02` benchmark no-registration and ANTs rigid on a fixed 20-scan pilot.
- [ ] `ROI-01` define generous septal box in physical millimetres and inspect pilot crops.
- [ ] `ANN-00` freeze CSP annotation inclusion/exclusion and posterior stopping rule **before** formal labeling.
- [ ] `ANN-01` reserve subject/family-disjoint held-out set; begin manually reviewed masks independently of alignment development.

## Running notes

| Date | Event | Evidence | Interpretation |
|---|---|---|---|
| 2026-11-13 | User reports all T2s extracted; 1,689 scans, 0.7 mm isotropic | Conversation report; local audit not attached | Stage 1 extraction reported, QC not yet closed |
| 2026-11-13 | Seven-stage approach agreed, ANTs rigid proposed | Architecture discussion | Stage 2 remains unimplemented |
| 2026-11-13 | Git-ready starter docs created | This commit / package | Tracking initialized; no scientific claims verified |
