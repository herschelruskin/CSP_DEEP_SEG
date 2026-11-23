# Progress tracker — CSP_DEEP_SEG

**Last updated:** 2026-11-18. **Status levels:** USER-REPORTED / CONVERSATION-OBSERVED / CONNECTOR-RECONCILED / NOT YET VERIFIED as independent executable runs. This repo still contains documentation rather than a completed runnable segmentation package.

**Current snapshot:** See [docs/CURRENT_STATE.md](../docs/CURRENT_STATE.md). **December is a CPS 843 proof-of-concept checkpoint**, not the end of the research program.

| Stage | Current state | What exists | Next proof or dependency |
|---|---|---|---|
| 1. T2 acquisition/QC | **Filename census reconciled; full QC open** | 1,689 T2 acquisitions / 1,113 subject IDs / 576 additional acquisitions in local manifest and Google Sheets; one SPC1 per subject in active annotation queue | File integrity, voxel geometry and image QC audit; subject/family split strategy |
| 2. Registration | **Two-case smoke test observed; benchmark not complete** | Synthetic ANTs test and rigid T2 2 mm moving 100307 → fixed 100206, with transform applied to native 0.7 mm grid (local-only) | Reproducible command/log, coordinate round-trip, no-registration comparison and several held-out ROI cases |
| 3. Septal ROI | **Exploratory, not accepted** | Rough Slicer physical ROI tried on two subjects; processed LV labels 4/43 explored; label 72 absent in one example | Reproducible raw-T2 midline crop and per-mask full-containment/margin measurements |
| 4. Triangular CSP annotation | **Active** | ≥20 manual subjects reported on 2026-11-17; initial checkpoint 19 present, 1 absent; simple Google Sheets Quick Log; subject-level SPC1 queue | Actual saved-mask inventory, native-grid verification and annotation SOP for inferior/ovoid/fornix-ambiguous cases |
| 5. Model code | **Planned** | Design: fixed-crop 2.5D U-Net baseline; coarse anatomical localizer as comparative second stage | Implement preprocessing, data loader, model, native-grid reconstruction and CPU smoke tests |
| 6. Training | **Not run** | Intel Iris Xe laptop for annotations/CPU tests; home RTX 2060 Super and Alliance GPU available | Fixed training/validation partition and first reproducible run; log seeds, configs, checkpoint, metrics |
| 7. Evaluation | **Not run** | Defined targets: complete ROI containment, positive-case Dice/volume errors, empty-case false positives | Protected subject/family test split; avoid specificity claims from only one absent example |

## Key methodological state

- **Target:** triangular CSP only, not all septal cavity morphologies. Presence and absent/uncertain status recorded separately from annotation completion/QC.
- **Training labels:** Use native 0.7 mm T2 masks; don't use missing FreeSurfer CSP label 72 as absence evidence. QC questionable inferior expansions rather than accepting them automatically.
- **Localization:** prioritize native T2. Large septal anatomical differences make blanket rigid alignment and fixed-template crops uncertain; compare simple midline crop against learned coarse anatomical region detection, both evaluated on whole-mask containment.
- **Data partition:** one SPC1 per subject for manual queue; retain SPC2 in private registry for QC fallback. No repeated acquisitions from same person across splits; HCP family-aware separation to be addressed.
- **Evidence:** no published or GitHub-verified Dice, registration accuracy, training outcome, crop recall, or current reviewed-mask count beyond the user's earlier report.

## Next actions (ordered)

- [ ] **ANN-00:** create versioned triangular-CSP anatomical SOP resolving inferior cavity boundaries near fornix and posterior/other midline cavities; adjudicate ambiguous examples.
- [ ] **ANN-01:** script audit of saved native masks vs the 1,113-case annotation queue (present/absent/uncertain, empty/nonempty, shape, affine, mismatch and QC). Update the actual counts.
- [ ] **ROI-00:** implement *no-registration* native-T2 anatomical septal crop, with mm-based margins and fallback for absent or unusual cavities.
- [ ] **ROI-01/02:** test crop coverage and minimum margins on the available positive reference masks; don't claim 20/20 containment until measured.
- [ ] **MOD-01/03:** implement 2.5D U-Net data pipeline, synthetic smoke test and tiny training-subset overfit diagnostic (CPU feasible for smoke tests).
- [ ] **TRN-01:** choose subject-disjoint provisional split, include QC-pass masks only, and train first GPU baseline. Treat ≤20 labels as feasibility rather than robust validation.
- [ ] **EXP:** compare learned coarse septal region localizer against the fixed-crop baseline using identical segmenter/split and report any missed anatomy.
- [ ] **DATA-02:** complete full file-integrity and geometry audit separately from the name-only census.

## Dated activity register

| Date | Event | Evidence category | Interpretation |
|---|---|---|---|
| 2026-11-13 | Repo initialized; 7-stage workflow, long research/course distinction, continuity policy | GitHub-committed docs | Documentary baseline only |
| 2026-11-17 | Windows/Docker synthetic plus two-subject real-T2 ~2 mm rigid alignment performed | User-reported local test + Slicer review | Partial proof command can run; does not establish clinical/anatomical accuracy or full pilot success |
| 2026-11-17 | Tested coarse septal ROI, processed FreeSurfer LV labels 4/43 and missing CSP label 72 in one example | User screenshots and Python-console outputs | ROI localization needs improvement; missing label 72 not true absence |
| 2026-11-17 | CSV/Google Sheets count: 1,689 distinct acquisitions, 1,113 subject IDs, 576 extra scans; SPC1-only visible quick queue | Connector-reconciled manifest | **DATA-01 filename census completed**; MRI integrity not verified |
| 2026-11-17 | Manual triangular-CSP reviews reached ≥20; initial 19 present, one absent; multiple ambiguous inferior cavities | User report + screenshots | Masks exist locally; exact count and segmentation QC not independently audited |
| 2026-11-18 | Coarse-to-fine anatomical region detector + fine segmenter adopted as primary comparative *design*, with simple crop/2.5D U-Net baseline first | Architecture discussion; no model training | Prior rigid-first, 3D/TransUNet-first ordering no longer required for December feasibility |

## Continuity

Read [HANDOFF.md](HANDOFF.md) and [../AGENTS.md](../AGENTS.md) before each work session. Keep new run/test evidence in [TEST_LOG.md](TEST_LOG.md) / [EXPERIMENTS.md](EXPERIMENTS.md), and decision changes in [DECISIONS.md](DECISIONS.md).

## 2026-11-19 follow-up (USER-REPORTED / PLANNING)

- Manual review count revised by user to **70 subjects: 65 present and 5 absent**; ~13 flagged for anatomical review. Saved mask files, native geometry and QC-pass counts still **NOT independently audited**. Spreadsheet annotation-status column is intentionally discontinued; do not use it to infer completion.
- Reviewed HCP S1200 official processed structural directory: `T1w/aparc+aseg.nii.gz` and `T1w/T2w_acpc_dc_restore.nii.gz` are documented; individual processed-file availability, frontal-horn pseudo-label feasibility and raw-T2 spatial mapping remain **UNVERIFIED**.
- Stage 3 planning: first test fixed raw-T2 ROI and **processed-LV reference-assisted oracle-style ROI** on development masks, then evaluate whether a tiny raw-T2 localizer is warranted. No ROI containment or neural training has been run. Full plan: [Frontal horn feasibility](../docs/FRONTAL_HORN_ROI_FEASIBILITY_2026-11-19.md).

## 2026-11-19 localization simplification decision (PLANNED; NOT RUN)

- User selected an inexpensive **geometry-only generous midline 3D crop** as the leading Stage 3 localization approach. Start with orientation-aware/header-centered box, optionally estimate midsagittal symmetry, and trim LR/AP/SI using conservative physical-space bounds. No FreeSurfer labels, ANTs or learned localizer are required for initial test.
- Immediate experiment: audit native mask geometry, then compute whole-positive-CSP containment and six-face margins across the QC-approved development masks; use held-out subjects only for independent evaluation. Confirm valid crops for absent subjects; ambiguous labels stay in QC review. Ensure crop reconstruction exactly preserves original voxel/world coordinates.
- Frontal-horn oracle and learned localizer remain optional comparators **only if objective crop errors or segmentation failures justify them**. No crop experiment has been executed or validated.

## 2026-11-19 Stage 3 crop scaffold — IMPLEMENTED, REAL-DATA VALIDATION OPEN

- **Committed:** `scripts/reduce_t2_slicer.py` (Slicer-console functions `reduce_active_t2` and `batch_reduce_t2`), `tests/test_reduce_t2_geometry.py`, and `docs/REDUCED_T2_CROP.md`. Native-voxel extraction, preserved world geometry by affine shift, JSON crop provenance, optional loaded-mask six-face containment audit and three-case batch smoke-test mode are implemented.
- **TESTED LOCALLY on synthetic NumPy arrays:** `pytest -q tests/test_reduce_t2_geometry.py` — **4 passed**, using synthetic scalar arrays, flipped/aniso/oblique image matrices, positive/empty reference masks and invalid configuration checks. This does **not** validate Slicer integrations, output NIfTI serialization, real HCP scan quality, or containment on the 70 user-reviewed subjects.
- **NOT RUN:** first real Slicer crop of a native HCP T2, save/reload voxel+affine check, manual-mask and QC reconciliation, six-face containment on development cases, batch full-cohort processing, and segmentation training. Do not bulk-run or use for model training until these checks pass.
- Default preliminary crop: coarse foreground RAS center; LR half-width 35 mm; conservative fraction-based AP/SI trimming. All cuts **provisional**. See [usage and limitations](../docs/REDUCED_T2_CROP.md).

### 2026-11-19 Slicer API compatibility fix
- Local user smoke test failed before crop calculation: `GetReferenceActiveVolumeID()` is not a Slicer getter. Updated `reduce_active_t2` to prefer Red slice background, with `GetActiveVolumeID()` fallback. 6/6 local synthetic/API-mock tests passed; real T2 save/reload remains **NOT RUN**.

### 2026-11-19 first real HCP reduced T2 output (USER-REPORTED)
- Local Slicer execution with direct Red-background-volume workaround generated `114217_3T_T2w_SPC1_reduced.nii.gz`, source KJI 320×320×256 → 262×252×123; 31.0% voxels retained. JSON geometry record and Slicer output volume node reported.
- **Not yet validated:** mask containment, anatomical safety, visual overlap, disk reload geometry, cross-subject generalizability. Run a cropped-native-voxel and world-coordinate check and tri-planar review before batch processing. The local extracted scaffold may still have the old Slicer API bug even though GitHub has the fix.

### 2026-11-19 proposed 114217 aggressive crop pilot (NOT RUN)
- Initial 31%-retained crop in user's axial screenshot appears overly broad for the thin midline CSP search task; this is qualitative evidence of excess background, **not** proof of safe anatomical margins.
- Proposed isolated folder `D:\CSP_DEEP_SEG\derived\reduced_t2_aggressive_test` and settings: LR half-width 22 mm; posterior/anterior trims 35%/20%; inferior/superior trims 35%/20%. Original raw T2 remains the input and is not overwritten.
- **Must verify:** true CSP whole-mask coverage in each plane, including posterior/inferior boundaries, native coordinates, six-face margins and subject variation. No real mask audit has been run for this preset. See D-021.

### 2026-11-19 data-derived standardized ROI proposal (NOT RUN)
- Next geometry experiment should calculate per-QC-positive CSP mask left/right deviations from an estimated per-person midline, plus AP/SI extrema *normalized to corresponding subject brain/foreground bounds*, not the raw image center.
- Aggregate development-subject extreme coordinates, convert to one common set of crop rules and add a physical safety margin. The rule adapts to individuals' head sizes/positions, without a learned locator; reserve subject/family held-out subjects for independent containment testing. Confirmed absent scans must still obtain valid crops; ~13 anatomical-review cases cannot silently enter definitive reference set.
- Current crop generator uses coarse thresholded *head foreground*, not a true brain mask or fitted midsagittal plane; robust brain bounds and LR symmetry are candidates to compare before refining the preset.

### ROI-COHORT-CAL-001 — 2026-11-19 implemented scaffold, local subject runs pending
- Added `scripts/calibrate_csp_roi_slicer.py`: auto-discovers subject-matched original SPC1 T2 and segmentation files, imports optional absences/review flags, produces editable subject manifest, reads masks safely (one triangle segment or explicit segment/label choice), calculates per-subject native RAS CSP extrema and actual voxel volume, ranks largest subjects and fits `fixed_mm` and `proportional` ROI rules with mm safety margin.
- `proportional` scales with robust **head foreground dimensions**, not actual cranial/brain segmentation and not yet a fitted midsagittal symmetry plane. Compare against `fixed_mm`; no unsupported claim of intracranial normalization.
- Generates `subject_measurements.csv`, `largest_csp_ranked.csv`, `calibrated_rules.json`, `rule_evaluations.csv`, `leave_one_subject_out.csv`, `errors.csv`; protected holdouts are not even loaded without explicit unlock; an optional batch cropper starts with `limit=3`.
- Synthetic tests **15 passed** on local Python/pytest (9 new cohort-calibration cases + six existing crop tests). Slicer runtime and full HCP cohort were **NOT RUN** here; actual mask folder, five absent IDs, ~13 review flags and subject/family grouping remain local dependencies. See `docs/ROI_CALIBRATION.md` and `tracking/TEST_LOG.md`.

### 2026-11-19 local path correction
- User identified actual CSP manual segment directory as `D:\CSP_DEEP_SEG\CSP_Seg` with subject-ID files, not `D:\CSP_DEEP_SEG\masks`; raw T2 directory `D:\CSP_DEEP_SEG\T2w\<ID>\` confirmed.
- Manifest candidate-suffix matcher extended to `.nifti` (in addition to normal NIfTI extensions); **no cohort manifest/calibration outcome yet verified**, and whether Slicer opens a literal `.nifti` suffix needs checking. For local ZIP, update the script before use if that suffix applies.

### 2026-11-19 local cohort-manifest reconciliation (USER-REPORTED + CONNECTOR-READ; masks not audited)
- User's `make_roi_manifest` run discovered **64 masks** and reported 64 `present`, 0 `absent`, 0 `uncertain`; this is due to mask-based discovery with empty/nonpopulated status/absence inputs, **not** a validated 64/0 prevalence estimate.
- Read user's live Quick Log first 70 reviewed cases: **65 present, 5 absent**; **13** `Needs review` flags. Matching the 64 discovered mask IDs against the reviewed entries revealed **one additional present subject without a discovered mask**. No auto-absence inference.
- Generated a private 70-row `cohort_status_from_quick_log.csv` plus absent/review ID text files (delivered in chat, **not committed publicly**) for `make_roi_manifest(..., status_csv=...)`. Initial status CSV: 54 provisional present, 2 provisional absent, 10 flagged present, 3 flagged absent, plus 1 additional present flagged because its mask is missing. All splits are **TEMPORARILY dev**, not heldout/family-safe.
- Crucial: very large CSP candidates in Quick Log are among `Needs review`; calibration currently skips these until adjudicated, so **do not treat resulting extrema as safely representing the largest CSP**. Real crop-bound fitting remains **NOT RUN**.

### 2026-11-19 correction — exploratory ROI should include review-flagged CSP positives
- Local user manifest had 70 subjects but incorrectly reported 55 present, 5 absent, 10 uncertain. **Cause found and fixed:** the manifest builder treated `needs_review` as uncertain `presence`. The 10 flagged CSP-positive masks should be `present` with `qc=needs_review`. The 13 review flags remain visible (10 present, 3 absent).
- `scripts/calibrate_csp_roi_slicer.py` now fits the primary exploratory envelope using available review-flagged positive masks by default, while preserving their QC labels and reporting a `sensitivity_excluding_review` alternative. Missing/unreadable masks still fail and are logged.
- **Local source tests:** 17/17 pass (15 previous + 2 regression tests). **Not run:** actual 70-subject calibration; cannot claim all 65 masks passed native-space QC or were successfully read in Slicer.

### 2026-11-19 first real 70-subject calibration (USER-REPORTED)
- Slicer `calibrate_roi_from_manifest(..., margin_mm=8.0, include_review_for_bounds=True)` completed: **n_manifest=70, n_read=70, n_errors=0, n_dev=70, heldout=0**, positive=65, absent=5 (zero volume), positive `needs_review`=10, `qc_counter` provisional=57/needs_review=13.
- User-reported unusually large 108828=**2200.0 mm³** (extremely large, difficult lateral-ventricle boundary), followed by 107321=203.4, 101309=200.3, 102008=155.7, 107725=102.6 mm³. No anatomical QC pass inferred from successful file processing; these are native labelmap voxel volumes.
- Files saved locally: `D:\CSP_DEEP_SEG\derived\roi_calibration\results\{calibrated_rules.json,subject_measurements.csv,rule_evaluations.csv,leave_one_subject_out.csv,largest_csp_ranked.csv,errors.csv}`. Files are **not** in the repository or tool context; exact crop dimensions/coverage unknown until user shares audits.
- **Critical:** ALL 70 entered development fitting; 0 untouched held-out. Any in-sample full containment would be built-in (calibration extrema guarantee coverage on same cases), not independent validation. Next inspect LOO missed positives and median crop retention for fixed-mm vs proportional, six-face margins and 108828 extent. Freeze and test on *new* subjects / family-aware holdout prior to deployment.

### 2026-11-19 reported ROI rule metrics
- User supplied calibrated candidates (all 65 CSP-present masks included; margin 8 mm):
  - **Fixed-mm:** LR half width before margin 21.8184 mm; AP from 27.5652 to 146.5651 mm relative to foreground minimum; SI from 102.7083 to 134.6647 mm. Approx requested RAS dimensions including both 8mm margins: **59.64 × 135.00 × 47.96 mm**. Median retained original volume **6.33%**.
  - **Proportional:** LR half width 0.124323 of foreground LR span; AP 0.127236–0.663198 of foreground AP span; SI 0.480660–0.619645 of SI span. Median retained volume **5.97%**.
  - **LOO:** 1 missed positive mask out of 65 for each mode; same single case. This is an internal robustness check, NOT untouched validation; all 70 subjects were used in original fitting.
- Next: identify which of six reference-space extrema set each face; inspect LOO missed mask's per-face clearance and annotation/foreground geometry, plus the impact of the very large boundary-uncertain mask on box dimensions. Avoid auto-tightening AP or reducing 8mm margin until face-specific tests and new-subject validation.

### 2026-11-19 post-hoc 108828 exclusion experiment (IMPLEMENTED; COHORT RERUN PENDING)
- User elected to **exclude 108828 (2200.0 mm³)** from *standard ROI crop boundary fitting only*, preserving the entire 70-subject dataset and explicit QC. Next largest are 107321=203.4, 101309=200.3, 102008=155.7, 107725=102.6 mm³; no prevalence estimate among 1,113 HCP participants can be inferred from these.
- Added `excluded_from_fit_ids` to `calibrate_roi_from_manifest`; still loads/measures/evaluates 108828, keeps its row in ranked and evaluation CSV, and flags exclusion. LOO restricted to remaining 64 fit positives. Original all-inclusive results preserved by using `results_excluding_108828` output directory. This is a post-hoc sensitivity experiment, not an independent holdout.
- **Local synthetic tests:** 19/19 passed on updated script + outlier regression cases (existing 17 + two). No user real-data rerun of exclusion candidate yet.

### 2026-11-19 108828-excluded real calibration comparison (USER-REPORTED)
- User reran script with `excluded_from_fit_ids=('108828',)`: 70/70 measured; no errors; `n_dev=69` including 64 positive + 5 absent; `n_excluded_from_fit=1`; original 108828 kept in ranking and evaluated. `n_holdout_reserved=0`.
- **Fixed-mm** median source voxel fraction retained **6.33%** (same rounded result as 65-positive baseline); **proportional** retained **5.74%**, compared with **5.97%** baseline (0.23 percentage-point improvement, approx 3.85% relative crop-size reduction).
- Both outlier-excluded ROI rules still contain **100% of 108828 mask voxels** (`fraction_inside=1.0, whole_mask_contained=True`). This indicates this anomalously high-volume labelmap does not require expansion beyond the observed 64-subject fitted envelope, including current margins.
- LOO (outlier-excluded *fit* positives only) again misses one subject **112112** for each mode, 1/64 LOO misses. It is not independent held-out validation. Next: investigate 112112 exact missed face/extent and six-face constraint-setters; compare mask size/shape and geometry before further tightening.


## 2026-11-20 December 2.5D baseline — IMPLEMENTED / SYNTHETIC-VERIFIED ONLY

- **New files:** scripts/csp25d_baseline.py (native NIfTI+mask loader, 7-channel coronal U-Net, loss, training, per-subject validation and native-space inference), scripts/crop_manifest_slicer.py (only listed manifest subjects, three-first batch), tests/test_csp25d_baseline.py, requirements-25d.txt, docs/CSP_25D_BASELINE.md. The model has **489,281 parameters** with 16 base channels.
- **Local CPU evidence:** 5/5 synthetic tests passed; standalone torch forward smoke passed at input [1,7,73,55] and output [1,1,73,55]. TEST LOG updated. **Nibabel not installed** on test container; no end-to-end crop/NIfTI/mask roundtrip or GPU/HCP model training tested. This is a software scaffold, not performance.
- **User-reported correct ROI:** re-run after removing incorrect 112112 remote component: fixed-mm median 1.18% and proportional **1.00%** source voxels; 0/64 internal positive-case LOO misses; 108828 genuine exceptional CSP excluded only from rule fit and **not fully contained**. All original 70 are development, so independent generalization remains open. Final candidate is **unshifted corrected proportional**; posterior-shift variations rejected for first baseline.
- **Train/val policy:** create private manifest with explicit train/val/test and family grouping where available; no automatic assignments. Present provisional/pass masks eligible, needs_review excluded; operational absences are not strict negatives without adjudicated QC pass + high negative confidence. Positive-case Dice checkpoint selection, empty FP mm³ reported separately. No model Dice recorded.
- **Immediate next:** synchronize new scripts to the local GPU PC/Slicer, crop three specifically listed native T2s using unshifted rule, verify NIfTI affine/orientation and mask crop, generate train/val manifest, run tiny development-only overfit, log all failures and model/VRAM/time. Do NOT run all 1,113 yet.


## 2026-11-23 CSP 2.5D audit and preferred Alliance deployment (feature branch)

- Audited real source branch and draft PR #1, rather than reconstructing. Prior 5 CPU synthetic checks, no real HCP NIfTI integration or training. Frozen unshifted ~1% crop remains unchanged. Existing ROI calibration is development-only; no new independent anatomical claim.
- **IMPLEMENTED:** improved per-subject-within-class 50/50 slice sampler; mandatory CUDA option for cluster jobs; measured per-epoch elapsed time and peak PyTorch GPU allocated bytes; binary positive-case recall and mm³ volume-error evaluation. No claim of GPU speed or segmentation Dice.
- **IMPLEMENTED:** scripts/audit_csp25d_manifest.py (real input validation, optional original-T2 voxel equality, frozen-rule comparison, private CSV), scripts/relocate_csp25d_manifest.py (Windows to Alliance Linux paths), scripts/hpc/train_csp25d.sbatch (single-GPU, 2-epoch pilot, fail if CUDA missing), synthetic NIfTI integration tests, GitHub Actions CPU suite. Private original T2 path added to generated model manifest for Windows QA.
- **USER PREFERENCE:** Use Alliance/Compute Canada GPU by default because home RTX 2060 Super is not at office; no cluster login, scheduler job, filesystem permissions or HCP transfer confirmed. Documented exact workflow at docs/ALLIANCE_GPU_BASELINE.md; stage only crop NIfTIs, matched JSON/masks and private manifest.
- **ACTUAL CPU CI EVIDENCE:** GitHub Actions run 45209618429 on feature commit 9b12b023230a790dc3c58324b2f9d19452b63d passed **10/10 synthetic tests in 1.95s** and model smoke, 489,281 parameters. Later edits add metric checks; inspect newer CI run before claiming its result.
- **NOT DONE:** actual Slicer batch-crop integration, actual mask spatial alignment and source pixel reconstruction on HCP, complete sample QC, family-safe partition, permission-checked HCP transfer, actual GPU Slurm submission, measured VRAM/time, real Dice/sensitivity/volume error, unseen held-out validation.
- **NEXT:** On office Windows, sync scripts and run 3-scan frozen-rule Slicer crop, build private manifest, run scripts/audit_csp25d_manifest.py with --verify-original for three IDs, then establish QC and family-aware train/val/test. Only afterward stage private reduced scans/masks to an authorized Alliance cluster and submit scripts/hpc/train_csp25d.sbatch.
