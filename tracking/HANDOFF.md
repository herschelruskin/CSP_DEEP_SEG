# Current handoff — CSP_DEEP_SEG

**Updated:** 2026-11-18. **Repository:** https://github.com/herschelruskin/CSP_DEEP_SEG · **Branch:** main (re-read HEAD at session start). **Primary status source:** [CURRENT_STATE](../docs/CURRENT_STATE.md) and [PROGRESS](PROGRESS.md).

## Goal and scope

Create a robust, eventually cross-dataset **triangular CSP** detector/segmenter in original HCP 3T T2 MRIs (~0.7 mm isotropic). December 2026 CPS 843 is only a preliminary proof-of-concept checkpoint; written project instructions indicate **December 14, 23:59**, verify if updated. Preserve scientifically sound ground truth and future thesis/publication extensibility.

## What we actually have

- **Inventory reconciled from local CSV/Google Sheets:** 1,689 distinct acquisition keys; 1,113 unique HCP subject IDs; 576 repeat acquisitions. Quick Log presents SPC1 per subject and preserves all SPC2 entries in a private hidden acquisition backup. Counts describe filenames, not full file-integrity QC.
- **Annotations:** user reported ≥20 reviewed/manual-mask subjects on 2026-11-17, initially 19 triangular-CSP present and one absent. More were potentially labeled afterward; exact current number of saved QC-pass masks **UNKNOWN** until auditing local files. Slicer manual native-T2 segmentation; status dropdowns Present / Absent / Uncertain, Complete and QC. Rough masks are useful for localization but must be reviewed before serving as fine-boundary reference.
- **Anatomy blocker:** recurring ambiguous lower/ovoid-looking anterior midline CSF regions, occasionally seemingly connected/disconnected from superior cavity across adjacent coronal slices. Do not declare separate cavity types from shape; assess relation to septal leaflets, fornix body/columns and adjacent CSF spaces. Posterior cavum vergae is not defined by inferior position. Flag **Needs review** where uncertain; freeze reproducible triangular-only SOP.
- **ANTs pilot:** user ran synthetic plus two-subject 2 mm rigid T2 smoke tests in local Docker image `ventricle-antspy:0.1`; fixed 100206, moving 100307; applied estimated rigid transform to moving native 0.7 mm image. Files under local `D:\CSP_DEEP_SEG\registration_smoke_test\`. Gross alignment observed, but residual anatomical variability remains. Repo does not yet contain exact commands/logs, registration tests or programmatic outputs.
- **Slicer ROI and HCP processing:** generous ~15.3 × 59.8 × 19.2 mm ROI considered overlarge/fragile from two examples, not validated across subjects. Processed `aparc+aseg` 4 and 43 delineated lateral ventricle vicinity for one subject; label 72 was absent despite visible candidate CSP. Processed labels are NOT CSP ground truth. Native T2 and processed-MNI images may not align without verified coordinate mapping.
- **Implementation:** No committed runnable model/data pipeline, no training results, no measured Dice/specificity, no validated crop containment, no locked subject/family-disjoint split yet. Keep all claims bounded.

## Current architecture and alternatives

1. **First baseline:** raw native-T2 simple midline/septal anatomical ROI (physical-mm definition), then compact **2.5D U-Net** to predict triangular-CSP mask at 0.7 mm. This avoids obligatory FreeSurfer, SynthSeg or ANTs on every test case.
2. **Second candidate:** small downsampled-T2 **coarse anatomical-region localizer**, trained to find where CSP should be even when absent, then crop original full-resolution native T2 and apply same segmenter. Focus on full-mask ROI containment and absent-case robustness, not perfect intersubject correspondence.
3. **Only later if justified:** small 3D U-Net, transformer/TransUNet bottleneck, ventricular-landmark-guided localizer, verified rigid/affine registration, optional semi-supervised models. Fair ablations required.

**Compute:** work laptop Intel Iris Xe for Slicer/CPU data prep; home RTX 2060 Super for first GPU 2.5D experiments; Alliance/Compute Canada for large 3D/sweeps.

## The next bounded task

1. Obtain actual local **segmentation mask directory + filenames** (private), and audit shape/affine match, mask count, number positive/empty, stray islands and any QC flag. Keep public GitHub aggregate-only.
2. Resolve/freeze concise **triangular-only boundary SOP** with a few adjudicated unusual cases. Do not force questionable lower structures into positive/negative labels.
3. Implement raw-T2 simple septal crop; test every available positive reference mask for **whole-mask containment** and margin, on development subjects only. Document failure cases.
4. Implement same 2.5D segmenter on fixed crops; smoke-test on laptop CPU then transfer real training to GPU. Lock subject-level splits; reserve final holdout from tuning.
5. Add learned coarse anatomical localizer only after baseline containment and segmentation are measured. Keep provenance of every run.

## Operating rules

- Read `AGENTS.md`, `tracking/DECISIONS.md`, `tracking/PROGRESS.md`, `docs/CURRENT_STATE.md`, `docs/SEVEN_STAGE_PROCESS.md`; check actual GitHub HEAD.
- Do not silently reinterpret 120 labels as an achieved count: first practical annotation milestone discussed is approximately 50, and a 20-case run would be proof-of-concept only.
- Keep HCP MRI, masks, unredacted manifests and private Google Sheet URLs **out of GitHub**.
- Do not claim the 20-subject ANTs validation, whole-mask ROI recall or first neural-network model as completed.
- Early-shard complex chats and refresh this handoff/progress/docs after material milestones.

## Next-chat start prompt

Continue CSP_DEEP_SEG at https://github.com/herschelruskin/CSP_DEEP_SEG. Read AGENTS.md, docs/CURRENT_STATE.md, tracking/PROGRESS.md, tracking/DECISIONS.md, tracking/HANDOFF.md and verify HEAD. Focus on triangular CSP only; as of Nov 17 ≥20 manual masks reported, but verify current files/QC. First audit local masks, freeze inferior/fornix boundary SOP, implement raw-T2 septal ROI containment and compact 2.5D U-Net smoke test. Treat a learned coarse anatomical locator as comparison, not completed code. Keep reproducibility, subject/family splits and December course milestone vs long-term thesis distinct.

## 2026-11-19 planning update — frontal-horn ROI (supersedes older count, not older experimental evidence)

- **USER-REPORTED:** 70 reviews, 65 CSP present, 5 absent; ~13 anatomically flagged. Local mask geometry, saved mask counts and QC-pass counts not verified. The annotation-status spreadsheet field is no longer maintained and is not completion evidence.
- **NEW DESIGN REVIEW ONLY:** [Frontal-horn ROI feasibility](../docs/FRONTAL_HORN_ROI_FEASIBILITY_2026-11-19.md). HCP preprocessed `aparc+aseg` label 4/43 is whole LV, not frontal horn; raw→processed correspondence is unverified. Avoid learned-localizer training until an oracle-style geometry crop and a simple raw-T2 crop are tested for whole positive-CSP containment.
- **NEXT SMALL ACTION:** match 5–10 raw and HCP-processed subjects, verify spatial transforms and inspect horn subregions; audit raw CSP masks; implement native-space ROI containment and exact crop roundtrip on development cases. Tests NOT RUN; no model trained.

## 2026-11-19 latest localization decision (supersedes earlier stage-3 proposals)

**ACTIVE DESIGN DIRECTION:** Do not start frontal-horn extraction/network training first. Implement and evaluate a **simple orientation-aware, generous midline crop** on raw HCP T2: start from image axis geometry/rough centered brain bounds; refine a midsagittal plane with symmetry only if needed; trim anterior/posterior/superior/inferior conservatively in physical mm. Preserve native 0.7-mm array and coordinate mapping. User wants cheapest fast, easily validated search-space reduction, not precise CSP localization.

**NEXT EXPERIMENT (NOT RUN):** reconcile saved masks, native affines and QC status; freeze development/held-out family-aware split; test six-face positive-mask containment plus minimum physical margins and absent-case valid crops. Do not claim arbitrary percentages/cuts guarantee full coverage. Frontal-horn reference/learned localization is deferred unless failure analysis merits it. See D-020.

## 2026-11-19 scaffold now committed — next execution on local Slicer

- **CODE NOW EXISTS:** [Slicer cropper](../scripts/reduce_t2_slicer.py), [four synthetic unit tests](../tests/test_reduce_t2_geometry.py), [run instructions](../docs/REDUCED_T2_CROP.md). Committed on `main` after prior D-020 decision. No installed models or HCP images in Git.
- **VERIFIED (synthetic only):** 4/4 NumPy/pytest tests pass; confirm native array crop, shifted physical geometry, oblique bounds, positive vs empty-mask logic, invalid-parameter rejection. Track in `tracking/TEST_LOG.md`.
- **NOT VERIFIED:** Slicer console execution, save/reload NIfTI geometry, CSP safety margins for actual HCP subjects, source-mask geometry and QC counts; **do not bulk process** until verified on the local workstation.
- **NEXT ACTION:** paste the one-line command from [run instructions](../docs/REDUCED_T2_CROP.md) into Slicer with one original T2 loaded; visually compare original/reduced volume in all planes; reload saved NIfTI and check world-space alignment, then audit QC-approved positive CSP masks on development subjects. Expand to batch `limit=3` only after the single-scan check.

### Slicer active-volume API fix (2026-11-19)
- **Observed error:** local `reduce_active_t2` failed on nonexistent `vtkMRMLSelectionNode.GetReferenceActiveVolumeID()`.
- **Patched GitHub script:** now accesses Red slice background volume or falls back to `GetActiveVolumeID`. The user downloaded an older ZIP under `D:\CSP_DEEP_SEG\CSP_reduced_T2_crop_scaffold`; it must be replaced with patched file or bypass `reduce_active_t2` using `reduce_volume_t2(slicer.app.layoutManager().sliceWidget('Red').sliceLogic().GetBackgroundLayer().GetVolumeNode(), output_dir, keep_output_in_scene=True)`.
- **Verified:** 6 local synthetic / mocked-Slicer tests pass. **Not yet verified:** actual Slicer crop generation on one HCP T2, persistence of geometry in saved/reloaded NIfTI, whole-CSP reference mask containment.

### First real HCP crop (114217) — 2026-11-19
- User successfully ran `reduce_volume_t2` on the Red-background node from the older local Slicer scaffold (bypassing the bad selection-node getter). User-reported output under `D:\CSP_DEEP_SEG\derived\reduced_t2\114217_3T_T2w_SPC1_reduced.nii.gz`; 320×320×256 → 262×252×123 KJI, 31.0% retained, JSON generated. `mask_audit=None` — no anatomical mask containment was tested.
- NEXT: check voxel equality and affine crop-origin mapping for IJK start [66,55,12], inspect original/reduced T2 overlay in all three planes, pass the QC-reviewed 114217 CSP mask into the cropper or audit its containment. Avoid batch runs until these checks are completed. Replace the local extracted script with the patched GitHub version to repair `reduce_active_t2`.

### Proposed aggressive crop test on subject 114217 (2026-11-19)
- User visually observed broad axial anatomy in the 31%-retained reduced T2; suggested more aggressively cropping background. This is qualitative only.
- Next Slicer command: load existing `reduce_t2_slicer.py`; call `reduce_volume_t2(slicer.util.getNode('114217_3T_T2w_SPC1'), r'D:\CSP_DEEP_SEG\derived\reduced_t2_aggressive_test', cfg=CropSettings(lr_half_width_mm=22, posterior_trim_fraction=.35, anterior_trim_fraction=.20, inferior_trim_fraction=.35, superior_trim_fraction=.20), keep_output_in_scene=True)`.
- **Important:** this crop has NOT been run, nor validated for mask containment. Avoid batch use until native-space QC-approved CSP masks show complete coverage and comfortable six-face margins; don't infer safety from one screenshot. Log the new shape/fraction and visually inspect all planes.

### Proposed data-derived crop calibration (2026-11-19)
- User's revised goal: ONE standardized 3D ROI rule, **centered in LR on each individual's midline**, with **AP and SI explicitly offset toward the anterior septal anatomical region**, *not* centered at half brain AP/height. Estimate each person's brain/foreground extent and compute relative CSP mask AP/SI extrema across QC-approved development labels. Pool maximum extents + mm safety margins, then test untouched held-out subjects.
- Current implementation's x-center is midpoint of sparse foreground bounds, not a true symmetry midline; its AP/SI fractions also refer to thresholded head foreground, not brain tissue. Those choices require QC and potentially low-cost symmetry/brain-bound refinements. No learned network or ANTs required for the first method.
- NEXT: audit raw masks, generate per-subject normalized CSP bound CSV, fit a candidate ROI rule, and run six-face containment and robustness tests (including absent and anatomical outliers). This analysis remains NOT RUN.

### CSP ROI cohort calibration: current executable (2026-11-19)
- **Verified GitHub source:** `scripts/calibrate_csp_roi_slicer.py`, `tests/test_calibrate_csp_roi.py`, `docs/ROI_CALIBRATION.md`, `templates/ROI_ABSENT_IDS.txt`, `templates/ROI_NEEDS_REVIEW_IDS.txt`, `templates/ROI_COHORT_STATUS.csv`. Existing `scripts/reduce_t2_slicer.py` required and bundled. New synthetic + old crop tests: 15 passed in isolated Python, actual 3D Slicer integration and HCP data NOT TESTED here.
- **User goal:** derive the smallest plausible shared CSP search box from 65 positive manually reviewed cases and five absent (zero-volume) cases, with subject-relative LR midpoint, anteriorly biased AP/SI boundaries, and compare fixed-mm to proportional head-foreground geometry. The extremely large manual case is retained *if QC-approved*; rank by both volume and spatial extent.
- **First local command:** extract package into the local scaffold directory; edit five absent IDs and any flagged review IDs or supply a `status_csv`. In Slicer generate an editable manifest with `make_roi_manifest` (see guide); check labels and native geometry, protect subject/family holdout before choosing margins, then run `calibrate_roi_from_manifest` to create local CSV/rules. Missing masks not treated as absent. Do NOT bulk-process 1,113 scans until ROI containment and output geometry checked.
- **Restrictions:** no HCP inputs or final ROI measurements were available in this tool session. All candidate crop rules are UNVALIDATED. Existing project local annotation-status column is discontinued; use explicit present/absent and QC. New code's proportional model uses head foreground, **not verified intracranial anatomy**.

### 2026-11-19 actual local dataset paths clarified
- User confirmed: original T2 scans under `D:\CSP_DEEP_SEG\T2w\<six-digit-ID>\<ID>_3T_T2w_SPC1.nii.gz`, manual CSP label files directly under `D:\CSP_DEEP_SEG\CSP_Seg\` named by subject ID (extension user called `.nifti`; verify exact filename suffix). **Earlier `D:\CSP_DEEP_SEG\masks` assumption was wrong**.
- Correct manifest second argument to `D:\CSP_DEEP_SEG\CSP_Seg`. GitHub `scripts/calibrate_csp_roi_slicer.py` now recognizes `.nifti` filenames as a candidate in addition to `.nii`, `.nii.gz`, `.nrrd`, `.seg.nrrd`. Users with previously extracted ZIP need to update local copy if actual suffix `.nifti`. Slicer reading literal `.nifti` is NOT YET VERIFIED.
- Confirm absents and needs-review lists are filled before fitting; matching `subject_id` alone is not a QC pass. Next: inspect discovered manifest IDs and validate geometry and labels on representative cases.

### 2026-11-19 64-mask/70-review discrepancy and private status file
- User ran `make_roi_manifest` with actual `D:\CSP_DEEP_SEG\T2w` and `D:\CSP_DEEP_SEG\CSP_Seg`, receiving **64 matched mask files**, all provisional `present`, zero absent. This is a manifest discovery issue, not a measurement of anatomy.
- Live Quick Log has **70 reviewed**: 65 present, 5 absent, 13 explicitly `Needs review`. Comparison against user-pasted 64 mask IDs shows **one positive subject without a discovered mask**. One additional QC flag was added to the status package for that missing positive mask. Keep subject IDs out of this public file.
- Private status package given to user includes `cohort_status_from_quick_log.csv`, `absent_ids.txt`, and `needs_review_ids.txt`. To regenerate 70-row manifest, use `make_roi_manifest(T2w, CSP_Seg, cohort_manifest_csv, status_csv=<local cohort_status_from_quick_log.csv>)`; do NOT need the two ID-list args when status CSV is used.
- Before fitting: verify masked images' native affine/shape and zero/presence semantics; resolve extreme CSP flagged as needs review; establish subject/family heldout split and QC approvals. Calibration including provisional mask is exploratory only. No cohort measurements or ROI accuracy has yet been validated.
