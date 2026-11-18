# CSP_DEEP_SEG

**Anatomically constrained, label-efficient segmentation of the cavum septum pellucidum (CSP) in high-resolution T2-weighted brain MRI.**

**Project:** Independent, long-term CSP segmentation research program with a CPS 843 Computer Vision final-project deliverable · **Started:** 2026-11-13 · **Status (2026-11-18):** 1,113-subject filename inventory reconciled; ≥20 manual subjects reported; two-case rigid-registration smoke test observed; localization and model training not validated.  
**Course checkpoint:** **2026-12-14, 11:59 PM** per supplied course guidelines (a different date mentioned in discussion remains unconfirmed). **This is not the research project's end date.**  
**Scope:** Independent of the ventricular morphometry and blast-exposure research projects; designed with future thesis/publication-grade work and cross-dataset reproducibility in mind.

## Two horizons: research program and course deliverable

- **Research program (open-ended):** Build, validate and extend a reproducible CSP localization/segmentation method; prioritize anatomical validity, independent evaluation, longitudinal improvements, robustness and future external-dataset testing. Thesis/publication-grade quality is an aspiration, **not a claim of completed validation**.
- **CPS 843 course submission (December 2026):** A bounded, accurately documented snapshot of what has actually been implemented and tested by the submission deadline. Partial results, limitations and unfinished phases are acceptable to report transparently; the course deadline must **not** force scientifically unsound shortcuts or be described as the project's completion.

See [docs/ROADMAP.md](docs/ROADMAP.md) for separation of milestones.

## Research question

Can we automatically localize and accurately segment the small, variable CSP cavity using anatomical constraints and a lightweight 3D segmentation model, while reducing the amount of expert segmentation required?

**Current modeling priority:** raw-T2 anatomical septal crop plus a small **2.5D U-Net**, followed by comparison against a lightweight **coarse anatomical-region detector → native-resolution segmenter**. Small 3D U-Net, TransUNet/attention, rigid alignment and semi-supervision remain potential ablations, **not validated results**. [Current state and avenues](docs/CURRENT_STATE.md).

## Seven-stage workflow

| # | Stage | Outcome | Current state |
|---|---|---|---|
| 1 | T2 acquisition, extraction & QC | Inventory of native T2 scans | **1,689 acquisitions / 1,113 unique subject IDs in filename manifest; integrity/QC open** |
| 2 | Rigid alignment (candidate) | Pilot ANTs low-res transform vs no-registration | **Synthetic + 2-subject smoke test reported; 20-subject comparison not run** |
| 3 | Anatomical ROI localization | Complete native-resolution septal search crop | **Two-case exploratory ROI only; containment not validated** |
| 4 | Manual triangular CSP labels (parallel) | Native T2 masks and absent/uncertain reference cases | **≥20 subjects reported as of Nov 17; boundaries/QC under review** |
| 5 | Model construction | Fixed-crop 2.5D U-Net baseline then coarse-to-fine localization | **Design selected for pilot; not implemented or trained in repository** |
| 6 | Training | Reproducible supervised runs; optional label-efficient variants | **Planned** |
| 7 | Manual + statistical validation | Independent test-set Dice, volume error, failure/QC analysis | **Planned** |

**Execution details and stage gates:** [docs/SEVEN_STAGE_PROCESS.md](docs/SEVEN_STAGE_PROCESS.md).  
**Single source of truth for progress:** [tracking/PROGRESS.md](tracking/PROGRESS.md).  
**For every fresh AI-assisted work session:** start with [AGENTS.md](AGENTS.md), then [tracking/HANDOFF.md](tracking/HANDOFF.md). See [docs/CHAT_CONTINUITY.md](docs/CHAT_CONTINUITY.md) for early-sharding and verified handoff rules.

## Current operational snapshot (2026-11-18)

- **Filename census:** A local CSV manifest and live Google Sheet reconciliation yielded **1,689 distinct acquisitions from 1,113 subjects**, hence **576 repeat acquisitions**. Quick Log now shows one **SPC1 per subject**; SPC2 remain archived as possible QC fallbacks. This is **not** a full NIfTI integrity audit.
- **Manual annotation:** User reported **20+ subjects** reviewed by Nov 17; first checkpoint **19 positive / one absent** for triangular CSP. Current saved-mask and QC-pass counts must be audited; anatomy for some inferior/ovoid-looking cavities remains **uncertain**. Only triangular/anterior CSP is in scope for the first experiment.
- **Alignment:** ANTsPy Docker synthetic and two-subject low-res rigid **smoke tests** occurred locally (100206 fixed; 100307 moving). No validated cohort-wide registration. Individual septal anatomy remains variable despite rigid global alignment.
- **Localization:** A generous fixed midline crop was explored on two scans, not shown to cover a held-out population. Processed HCP ventricular labels (4/43) were inspected as coarse anatomical references; missing FreeSurfer label 72 is **not** proof of CSP absence.
- **Next technical path:** audit local masks and freeze annotation SOP; evaluate a **raw-T2 fixed anatomical crop** for complete-CSP containment; train first small **2.5D U-Net**; compare fairly with a **learned coarse anatomical localizer**. Only then consider 3D/TransUNet, registration, self-supervision or more elaborate methods.
- **Compute:** Intel Iris Xe work laptop for annotation/CPU pipeline tests; home RTX 2060 Super for first GPU models; Alliance/Compute Canada as needed. **No trained model or Dice result is logged.**

**Living details and progression options:** [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md).

## Immediate next task — mask audit and first segmentation baseline

1. Inventory native-T2 segmentations saved locally and reconcile the real number of **complete, empty and QC-needs-review** masks against subject identifiers.
2. Version a **triangular-only anatomical segmentation SOP**, especially lower septal/fornix ambiguity and cavum-vergae boundaries; do not coerce uncertain masks into ground truth.
3. Define a simple native-T2 septal crop in physical millimetres and measure positive-mask **complete containment** and margins. Keep absent cases locatable without a visible CSP.
4. Implement a 2.5D U-Net smoke test and subject-disjoint first training run on available compute. Compare the same segmenter with a learned coarse region detector only after baseline results.
5. Log actual commands, configs, software versions, masks/splits, metrics and failures; keep private HCP data out of this repository.

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

See [docs/PROJECT_CONTROLS.md](docs/PROJECT_CONTROLS.md) for evidence standards and reporting conventions. The prior seven-stage plan remains a long-term framework; its initial numerical annotation target and registration-first ordering are **superseded for the first proof of concept** by the current staged baseline.
