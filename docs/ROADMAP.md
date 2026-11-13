# Roadmap — coursework proof of concept and longer-term research

**Updated:** 2026-11-13  
**Scope policy:** CSP_DEEP_SEG is a long-term research project. The December 2026 CPS 843 final-project submission is an **interim proof-of-concept checkpoint**, not an endpoint or a claim of clinical/publication readiness.

## Horizon A — first-pass proof of concept (CPS 843)

**Question:** Can we reproducibly locate the septal region in high-resolution T2-weighted MRI and train/evaluate an automated CSP segmentation method against independent manual masks?

Keep this implementation **simple and evidence-led**:

1. **Data:** Use the already-extracted HCP T2 acquisitions. Reconcile subject-vs-acquisition counts and run essential automated integrity/geometry checks; rely provisionally on HCP's existing acquisition QC rather than manually inspecting the full cohort.
2. **Alignment:** Pilot a simple native-affine locator against low-resolution ANTs rigid alignment on ~20 scans. Choose based on measured crop coverage, failure modes and runtime—not because ANTs is customary.
3. **Localization:** Make a generous 3D septal ROI in physical coordinates; verify anatomical coverage in the pilot without imposing unnecessary full-brain parcellation or nonlinear registration.
4. **Manual masks:** Establish a concise CSP anatomical labeling SOP; collect reliable native-space labels in parallel. The ~120 annotation target is an **initial research planning figure**, not a requirement to complete the coursework POC. Preserve subject/family partitions.
5. **Models:** Implement a compact, technically defensible baseline (classical or 3D U-Net) before adding a lightweight TransUNet-style hybrid if time and measurements support doing so.
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
