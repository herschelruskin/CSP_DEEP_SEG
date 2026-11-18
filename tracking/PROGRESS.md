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
