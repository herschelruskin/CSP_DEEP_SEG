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
