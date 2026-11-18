# Roadmap — coursework proof of concept and longer-term research

**Updated:** 2026-11-18  
**Scope policy:** CSP_DEEP_SEG is a long-term research project. The December 2026 CPS 843 final-project submission is an **interim proof-of-concept checkpoint**, not an endpoint or a claim of clinical/publication readiness.

## Current November 2026 implementation priority

**Use [CURRENT_STATE.md](CURRENT_STATE.md) and [tracking/PROGRESS.md](../tracking/PROGRESS.md) for latest status.** The earlier rigid-first and 3D/TransUNet-first stages below are **historical candidates** and no longer mandatory critical-path prerequisites for the first class-project experiment.

- **Now:** triangular CSP only, native HCP 0.7-mm T2 masks, at least 20 manually reviewed subjects reported Nov 17 (initial 19 positive, one absent); approximately 50 is the next *practical* initial annotation goal, not a universal threshold. Require mask geometry audit and review of ambiguous lower/ovoid/fornix-related cavities before fine-segmentation ground truth.
- **First feasibility model:** simple **raw-T2 septal crop + lightweight 2.5D U-Net**. On ~20 subjects, evaluate engineering feasibility, not robust population performance; only one absent sample at the initial checkpoint prevents a credible estimate of negative specificity.
- **Second comparison:** lightweight coarse model predicts the *anatomical septal region*, regardless of CSP presence; crop native-resolution original T2 and apply the same segmenter. Measure complete CSP containment, failure cases, runtime and positive/negative outcomes versus the fixed-crop baseline.
- **Retained alternatives:** anatomically guided ventricular landmarks, low-resolution ANTs rigid or affine alignment, compact 3D U-Net, TransUNet/attention or semi-supervised use of unlabeled HCP T2, **only after relevant baseline evidence**. Existing two-subject rigid smoke test is not a validated localization method.
- **Compute:** development/labeling on Intel Iris Xe laptop; first CUDA runs on RTX 2060 Super; Alliance cluster for larger experiments.

## Horizon A — first-pass proof of concept (CPS 843)

**Question:** Can we reproducibly locate the septal region in high-resolution T2-weighted MRI and train/evaluate an automated CSP segmentation method against independent manual masks?

Keep this implementation **simple and evidence-led**:

1. **Data:** Use the already-extracted HCP T2 acquisitions. Reconcile subject-vs-acquisition counts and run essential automated integrity/geometry checks; rely provisionally on HCP's existing acquisition QC rather than manually inspecting the full cohort.
2. **Alignment/localization comparison:** Start with a native-T2 septal crop and measure complete-reference-mask containment; compare against low-resolution ANTs rigid alignment or ventricular landmarks *if* the simple baseline misses cases.
3. **Localization:** Make a generous 3D septal ROI in physical coordinates; verify anatomical coverage in the pilot without imposing unnecessary full-brain parcellation or nonlinear registration.
4. **Manual masks:** Focus on triangular CSP only, freeze anatomic stopping rules, and audit/QC native masks. Approximately 50 is the next practical first-pass target, while ~120 remains a longer-term adaptable planning figure. Preserve subject/family partitions.
5. **Models:** Implement compact **2.5D U-Net on native-T2 anatomical crops** first, then compare a coarse learned septal-region detector with the same fine segmenter. Small 3D U-Net and TransUNet-style hybrid remain optional follow-on architectures.
6. **Training:** Produce at least one fully reproducible training run. Optional semi-supervision and large-scale unlabeled pretraining are **not prerequisites** for the first-pass result.
7. **Evaluation:** Use untouched manual test cases, Dice where defined, volume errors in mm³ and honest failure analysis. The December report should describe actual evidence, whether results are preliminary or partial.

### First-pass completion criteria

- A runnable, versioned path from native T2 to localization crop to an evaluated CSP prediction (or, if a model stage is incomplete by the course checkpoint, a clear, reproducible account of completed stages and blockers).
- Every reported measurement links to a run/config/input subset, with failures recorded.
- A course report is submitted by the verified course deadline; **this does not close any unfinished research milestones**.

### Explicitly deferred unless needed to unblock the POC

- Exhaustive manual QC of ~1,100 subjects.
- Full-cohort rigid registration before the pilot succeeds.
- Nonlinear registration or complete ventricular/whole-brain parcellation.
- Multi-contrast T1+T2 integration.
- Production packaging, deployment, general-purpose external-dataset interface.
- Extensive architecture optimization, self-supervised pretraining, or cross-site generalization claims.

## Horizon B — research development after the course checkpoint

Continue the same seven-stage framework with stronger evidence and broader applicability:

- Larger and more diverse manually annotated reference datasets, boundary-consistency studies and adjudication.
- Better localization failure handling, anatomical landmark refinement, systematic quality flags and multicenter robustness.
- Carefully tested semi-supervised methods, architecture and label-budget comparisons, uncertainty estimation.
- External cohorts, different scanners and voxel sizes, acquisition/domain shift and reproducible preprocessing.
- Larger independent evaluation with statistically appropriate uncertainty, bias analysis and failure stratification.
- Reusable package/API, automated tests, documentation and deployable workflows **after** the core method has proven useful.

## Change policy

A POC shortcut is acceptable only when documented with scope and limitations. It must not silently become a permanent research assumption. Record decisions in `tracking/DECISIONS.md`, evidence in `tracking/TEST_LOG.md`, and stage status in `tracking/PROGRESS.md`.
