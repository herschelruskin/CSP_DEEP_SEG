# CSP_DEEP_SEG

**Anatomically constrained, label-efficient segmentation of the cavum septum pellucidum (CSP) in high-resolution T2-weighted brain MRI.**

**Project:** Independent, long-term CSP segmentation research program with a CPS 843 Computer Vision final-project deliverable · **Started:** 2026-11-13 · **Status:** Data extracted; registration/localization not yet implemented.  
**Course checkpoint:** **2026-12-14, 11:59 PM** per supplied course guidelines (a different date mentioned in discussion remains unconfirmed). **This is not the research project's end date.**  
**Scope:** Independent of the ventricular morphometry and blast-exposure research projects; designed with future thesis/publication-grade work and cross-dataset reproducibility in mind.

## Two horizons: research program and course deliverable

- **Research program (open-ended):** Build, validate and extend a reproducible CSP localization/segmentation method; prioritize anatomical validity, independent evaluation, longitudinal improvements, robustness and future external-dataset testing. Thesis/publication-grade quality is an aspiration, **not a claim of completed validation**.
- **CPS 843 course submission (December 2026):** A bounded, accurately documented snapshot of what has actually been implemented and tested by the submission deadline. Partial results, limitations and unfinished phases are acceptable to report transparently; the course deadline must **not** force scientifically unsound shortcuts or be described as the project's completion.

See [docs/ROADMAP.md](docs/ROADMAP.md) for separation of milestones.

## Research question

Can we automatically localize and accurately segment the small, variable CSP cavity using anatomical constraints and a lightweight 3D segmentation model, while reducing the amount of expert segmentation required?

**Planned models:** classical T2 intensity/anatomy baseline; small 3D U-Net; lightweight 3D TransUNet-style hybrid. A semi-supervised extension using unlabeled scans is conditional on a working, independently evaluated supervised baseline. These are proposed methods, **not results**.

## Seven-stage workflow

| # | Stage | Outcome | Current state |
|---|---|---|---|
| 1 | T2 acquisition, extraction & QC | Reproducible inventory of valid, native T2 scans | **Extracted, QC incomplete** |
| 2 | Rigid alignment | Validated 6-DOF transform from each T2 to a stable reference | **Next** |
| 3 | Parcellation / CSP ROI localization | High-resolution, ventricular-relative 3D search crop | **Planned** |
| 4 | Manual reference labels (parallel) | Anatomically defined labels with train/validation/test provenance | **Planned** |
| 5 | Model construction | Comparable classical, U-Net and hybrid TransUNet implementations | **Planned** |
| 6 | Training | Reproducible supervised runs; optional label-efficient variants | **Planned** |
| 7 | Manual + statistical validation | Independent test-set Dice, volume error, failure/QC analysis | **Planned** |

**Execution details and stage gates:** [docs/SEVEN_STAGE_PROCESS.md](docs/SEVEN_STAGE_PROCESS.md).  
**Single source of truth for progress:** [tracking/PROGRESS.md](tracking/PROGRESS.md).  
**For every fresh AI-assisted work session:** start with [AGENTS.md](AGENTS.md), then [tracking/HANDOFF.md](tracking/HANDOFF.md). See [docs/CHAT_CONTINUITY.md](docs/CHAT_CONTINUITY.md) for early-sharding and verified handoff rules.

## Confirmed vs. unverified (2026-11-13)

- **USER-REPORTED:** 1,689 T2 acquisitions extracted from HCP-YA structural archives; all reported as **0.7 mm isotropic** on an initial geometry audit.
- **USER-REPORTED:** Multiple T2 acquisitions exist for some subjects (`SPC1` and `SPC2`). **1,689 is a scan count, not an independent participant count.** Unique subject count has not been reconciled against the file manifest.
- **OBSERVED IN CONVERSATION:** HCP subject `100206` shows a plausible small midline CSF cavity in three planes after display window/level adjustment; this is **not** a verified reference mask.
- **NOT YET VERIFIED:** complete archive checksum audit, full NIfTI decoding across all scans, label SOP, registration accuracy, crop coverage, segmentation accuracy, or model performance.

## Immediate next task — Stage 2 pilot

1. Freeze a **20-acquisition pilot list** with unique subject identifiers and a mix of SPC1/SPC2, without putting raw HCP data into Git.
2. Choose and version a fixed T2 reference. Subject `100206` is a **pilot option**, not yet the final template.
3. Test a no-registration ROI baseline against **ANTs rigid-only alignment** estimated on temporary ~2 mm isotropic images (original 0.7 mm images remain unchanged).
4. Save only rigid transforms, registration QC metrics, commands, software versions and later the **native-resolution ROI**, not whole-brain registered copies.
5. Inspect orthogonal views and document whether the predicted crop encloses the full septal/CSP search area. Do **not** scale to 1,689 scans until the pilot gate passes.

**Current pilot specification:** [docs/REGISTRATION_PILOT.md](docs/REGISTRATION_PILOT.md).

## Tracking and reproducibility

| Document | What goes there |
|---|---|
| [tracking/PROGRESS.md](tracking/PROGRESS.md) | What is completed, underway, blocked and next |
| [tracking/DECISIONS.md](tracking/DECISIONS.md) | Choices, rationale, alternatives and evidence |
| [tracking/TEST_LOG.md](tracking/TEST_LOG.md) | Individual test outcomes, with input/config/evidence |
| [tracking/EXPERIMENTS.md](tracking/EXPERIMENTS.md) | Training and ablation runs, comparisons and metrics |
| [tracking/ISSUES.md](tracking/ISSUES.md) | Open defects, assumptions and next actions |
| [docs/SEVEN_STAGE_PROCESS.md](docs/SEVEN_STAGE_PROCESS.md) | Scope, procedure and exit criteria for each stage |
| [templates/RUN_RECORD.md](templates/RUN_RECORD.md) | Copy for each actual processing/training run |
| [templates/ANNOTATION_RECORD.md](templates/ANNOTATION_RECORD.md) | Copy for annotation provenance and QC |

### Required scientific controls

- A test metric is only a result when linked to the exact input manifest, held-out split, code revision, configuration and run record.
- Split by subject; keep repeated scans together. Where HCP relatedness data are available, also partition related family members together. **Do not claim family-disjoint evaluation unless verified.**
- The manually reviewed test set must not guide registration tuning, hyperparameters, pseudo-label selection or stopping decisions.
- A genuinely absent or unresolvably tiny CSP is a meaningful **empty reference mask**, not a missing scan. Track resolution limits explicitly.
- Keep raw data, extracted NIfTI, reference masks, predictions and model weights **out of this GitHub repository**. Respect HCP data-use terms.

## Local directory convention (not tracked in Git)

```text
D:\CSP_DEEP_SEG\
  Data\            # HCP ZIPs/checksums; immutable
  T2w\             # Extracted 0.7-mm SPC1/SPC2 NIfTI + metadata
  masks\           # Manual annotation masks and QC
  derived\         # Rigid transforms + crops + processing outputs
  model_runs\      # Checkpoints and actual predictions
  CSP_DEEP_SEG\     # This Git-tracked repository
```

## References

- [HCP Young Adult data releases](https://www.humanconnectome.org/study/hcp-young-adult/data-releases) and [2025 file organization (Appendix III)](https://humanconnectome.org/storage/app/media/documentation/HCP-YA2025/HCP-YA_2025_Release_Appendix_III.pdf)
- [ANTs documentation](https://github.com/ANTsX/ANTs) (rigid registration to be tested, not yet implemented)
- [TransUNet](https://doi.org/10.1016/j.media.2024.103280) (candidate model family; no CSP-specific performance presumed)

See [docs/PROJECT_CONTROLS.md](docs/PROJECT_CONTROLS.md) for evidence standards and reporting conventions.
