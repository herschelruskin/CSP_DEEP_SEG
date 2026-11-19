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
