# Seven-stage implementation protocol

**Protocol:** CSP-PIPELINE-001 · **Version:** 0.1.1 · **Date:** 2026-11-13  
**Status vocabulary:** `DONE-VERIFIED` = logged test with evidence; `DONE-REPORTED` = user reports completion but not independently audited; `IN-PROGRESS`; `PENDING`; `BLOCKED`; `CONDITIONAL`.

**Scope note:** These seven stages define the **long-term research pipeline**. The December 2026 CPS 843 deliverable is an interim, evidence-based progress report—not the deadline for full seven-stage completion. Future thesis/publication-grade work may extend the pipeline and its validation requirements. See [ROADMAP.md](ROADMAP.md).

## Project-wide invariants

- **Immutable native-space data:** Raw T2 images and their NIfTI affines are never overwritten. All intensity scaling and spatial changes create derivatives with recorded provenance.
- **One subject is the independent unit:** SPC1 and SPC2 from one person are never separated across train/validation/test. Respect known HCP family relationships if legitimately available; otherwise disclose the limitation.
- **Geometry before pixel indices:** Use physical coordinates and saved transforms, not a fixed coronal slice number or a per-slice registration.
- **ROI recall before model accuracy:** If a crop omits a true CSP, no segmentation network can recover it. Verify coverage of reference anatomy before proceeding.
- **Truth categories:** Manual segmentation is reference data. Anatomical candidate masks and pseudo-labels are *not* ground truth.
- **Locked evaluation:** Freeze the final test partition in advance. Do not use its scans to tune ROI size or model hyperparameters; use a separate localization development set.
- **Uncertainty is a result:** Record failures, uncertain boundaries, empty CSPs and missing files explicitly.

## 1 — Data acquisition, extraction and QC

**Objective.** Make a reproducible inventory of usable HCP-YA unprocessed 3T T2 SPACE scans, including first/second acquisitions and metadata.

**Why.** Incomplete downloads, corrupted gzip streams, mismatched orientation and duplicate acquisitions can silently invalidate downstream segmentation or inflate evaluation sample sizes.

**Current evidence.** User reports extracting **1,689 T2 acquisitions** at **0.7 mm isotropic**, with duplicate acquisitions for some subjects. Full integrity, unique-subject count and per-scan quality are *not yet verified*.

**Execution.** (a) Enumerate `T2w_SPC1` and `T2w_SPC2`; (b) collect subject ID, series ID, path, byte size, SHA256, shape, spacing, orientation, affine/qform/sform, optional JSON and source ZIP; (c) reconcile expected archive inventory; (d) validate available ZIP MD5 checksums and NIfTI compression/readability (header-only is insufficient for complete corruption testing); (e) flag incomplete, duplicated or geometrically unusual files. Preserve ZIPs and native compressed NIfTIs.

**Tests / acceptance.** `DATA-01` complete manifest with unique `(subject, series)` rows; `DATA-02` all candidate scans can be read and pass configured integrity checks; `DATA-03` number of subjects vs acquisitions reconciled; `DATA-04` sample tri-planar QC; failures listed, never silently dropped. **Gate:** usable subset explicitly declared; not all 1,689 are presumed valid.

**Artifacts.** `manifest.csv` (private), checksum report, QC summary, failures, source download provenance. **State:** `DONE-REPORTED / QC IN-PROGRESS`.

## 2 — Rigid alignment to a stable T2 reference

**Objective.** Estimate a repeatable 6-DOF anatomical transform (rotation + translation) for each scan without warping the CSP.

**Why.** A CSP's pixel/slice coordinates vary with head pose and orientation. Rigid alignment is simpler than deformable registration and sufficient to attempt coarse localization; it does **not** eliminate individual differences in ventricular anatomy.

**Implementation choice (provisional).** ANTs rigid-only. Benchmark against a **no-registration, affine-based ROI** to show whether registration adds value. Fix a versioned reference (pilot: 100206; evaluate a population template before full deployment).

**Execution.** Reorient geometry consistently; estimate low-resolution registration images by Gaussian smoothing/anti-aliasing and resampling to ~2 mm isotropic in the same physical field of view; register moving to fixed T2 with rigid 6-DOF at multiresolution; retain forward/inverse transform, actual command, ANTs version, optimizer logs, timing/CPU/RAM. Do not persist full-resolution warped brains. **Do not assume the quick wrapper performs the exact desired pyramid without verifying its settings**; version the full command/config.

**Tests / acceptance.** `REG-01` physical-coordinate transform direction round-trip; `REG-02` successful alignment of midline and frontal horns on a fixed 20-scan development pilot, including repeat acquisitions; `REG-03` reproducibility on repeated runs; `REG-04` compare to no-registration baseline; `REG-05` log wall time and peak RAM. Failures/poor alignment must be flagged for review. **Gate:** documented success on pilot, explicit review of outliers; scale only after Stage 3 coverage checks.

**Artifacts.** `.mat` transform, versioned template ID, per-acquisition QC summary and failures. **State:** `PENDING`.

## 3 — Anatomical parcellation/localization and 3D ROI extraction

**Objective.** Map a generously bounded, ventricular-relative **septal search volume** to each native T2, then extract a consistent high-resolution input crop. Full-brain parcellation is **not required unless localization fails**.

**Why.** CSP is small and lies around the septum between the frontal horns. Limiting the search volume reduces compute and false positives, but tightly sized crops could systematically miss uncommon large or shifted cavities.

**Execution.** Define a 3D reference ROI in millimetres around septal/ventricular landmarks; transfer via the saved rigid transform. First try a coarse template ROI; add local bright-CSF/frontal-horn landmark refinement only if coverage is inadequate. Crop at native resolution and save mapping from crop coordinates to original voxels and world space. A provisional **80 × 96 × 96** voxel crop is a hypothesis, **not** an established boundary. For future scans with different voxel sizes, define field of view in **millimetres** and choose sampling policy explicitly.

**Tests / acceptance.** `ROI-01` visually inspect all pilot cases in coronal/axial/sagittal planes; `ROI-02` every manually delineated pilot CSP is completely inside ROI, with a documented margin; `ROI-03` localization works for absent/equivocal CSP cases without relying on detecting a bright cavity; `ROI-04` crop-to-native coordinate round-trip on synthetic landmarks; `ROI-05` record crop size, failure rates and time. Pilot target is **20/20 coverage**, not proof of population-wide 100% recall; expand testing before bulk use. **Gate:** complete containment on frozen development cases and explicit failure handling.

**Artifacts.** ROI specification, native-space box/crop affine, QC thumbnails, failure report. **State:** `PENDING`.

## 4 — Partial manual reference labeling (can run in parallel with 2–3)

**Objective.** Create consistent reference masks in native T2 image space for a targeted, diverse subset, currently **~120 subjects** as a *planning* target, dependent on annotation and QC throughput.

**Why.** Standard TransUNet supervised segmentation requires labels. Unlabeled images can support pretraining and semi-supervision, but cannot establish true CSP boundaries or validation accuracy by themselves.

**Execution.** First finalize an anatomical SOP (classical/anterior CSP vs cavum vergae, ambiguous ovoid/fornix spaces, ventricle connections, absent/unresolvable tiny cavities). Coronal-primary segmentation with axial/sagittal confirmation; no smoothing/interpolation of final manual mask. Record source volume SHA, labels, slice bookends, reviewer, uncertainty and QC. Store masks aligned exactly to native T2 geometry. The provisional **80 train / 20 validation / 20 test** breakdown must be finalized before tuning and adjusted to subject/family structure; no test leakage. Collect a mixture of small, large, ambiguous and empty examples, plus an unbiased sample for prevalence-relevant evaluation. Repeat a subset for annotation consistency.

**Tests / acceptance.** `ANN-01` mask affine/shape identical to source; `ANN-02` boundary/anatomical SOP agreed and versioned; `ANN-03` tri-planar review and presence/absence status; `ANN-04` repeat-annotation agreement for a subset; `ANN-05` frozen subject/family-disjoint train/val/test manifests. **Gate:** labels are released to training only after QC; test labels remain sequestered.

**Artifacts.** Private masks, per-subject annotation records, anatomical SOP, partition hashes. **State:** `PENDING`.

## 5 — Model construction

**Objective.** Implement independently testable baseline(s) and a small attention hybrid on identical crop definitions.

**Why.** A transformer is not automatically better at tiny objects. Low-resolution patch tokenization can erase a CSP; a U-Net baseline tests whether attention actually adds benefit. Both should receive the same standardized spatial input.

**Models.** `BASE-0`: local T2 intensity + anatomical constraints/connected components; `BASE-1`: compact 3D U-Net; `HYBRID-1`: comparable 3D encoder/decoder with transformer attention at bottleneck and full-resolution skip connections. Track parameter count, receptive field, memory and inference time. Avoid claiming vanilla 2D TransUNet is already a validated 3D CSP model.

**Tests / acceptance.** `MOD-01` synthetic forward pass/output shape; `MOD-02` parameter count and VRAM; `MOD-03` tiny test-set overfit diagnostic on training cases only; `MOD-04` output-to-native geometry and empty-mask handling; `MOD-05` no withheld mask access. **Gate:** baseline and hybrid train end-to-end on a few training cases, produce valid probability maps and save versioned checkpoints.

**Artifacts.** Source, lockfile/environment, configs, architecture diagram, unit tests. **State:** `PENDING`.

## 6 — Training and label-efficient experiments

**Objective.** Train reproducibly with limited trusted labels and evaluate whether unlabeled HCP crops add value.

**Why.** CSP occupies very few voxels; foreground imbalance and weak boundaries make naive training unreliable. Semi-supervised learning is optional and must be shown to improve manual-test performance rather than agreement with pseudo-labels.

**Execution.** Fit intensity normalization only on training data where fitting is required; start with robust percentiles and train-time intensity/geometry augmentation; optionally test N4/histogram standardization only if pilot evidence warrants it. Use Dice+cross-entropy (or justified alternative), balanced positive/negative sampling without distorting evaluation. Log dataset split hashes, package versions, random seeds, voxel resolution, crops, epochs, optimizer/schedule, learning-rate, batch size, GPU, wall time, energy/resource metrics if available. Use HCP unlabeled data only from allowed training partitions for SSL/pseudo-label experiments. Plan label-budget comparisons (e.g. 20/40/80) if feasible.

**Tests / acceptance.** `TRN-01` no subject/family leakage; `TRN-02` loss decreases on small training subset; `TRN-03` reproducibility with saved seed/config and weights; `TRN-04` validation-only checkpoint selection; `TRN-05` pseudo-label confidence and audit records if used. **Gate:** at least one fully reproducible baseline run before optional methods.

**Artifacts.** Per-run config, commit, checkpoint hash, learning curves, logs, derived prediction files (private). **State:** `PENDING`.

## 7 — Independent manual and statistical validation

**Objective.** Quantify image-level and subject-level accuracy relative to locked, reviewed manual masks; examine failure modes and algorithmic tradeoffs.

**Why.** High prevalence makes simple CSP presence accuracy uninformative; Dice alone is unstable for tiny structures and undefined for some empty-mask comparisons. We need results that reflect volumetry, detection and localization separately.

**Evaluation.** Patient-level Dice for nonempty reference masks; absolute volume error in mm³; signed volume bias; sensitivity of detecting visible CSP; false-positive voxel volume and false positives on genuinely absent/unresolvable cases; HD95 or surface distance only when valid for tiny masks; localization coverage; inference latency and memory. Report per-subject distributions, segmentation-size strata with predefined cutoffs, confidence intervals/bootstrap resampling by subject (and family if possible), and tri-planar qualitative error examples. For an empty reference, do **not** silently assign Dice=1 to empty predictions; report an explicit empty-case policy.

**Tests / acceptance.** `VAL-01` test partition untouched until final; `VAL-02` metric sanity checks on synthetic masks; `VAL-03` exact pipeline re-run from versioned config; `VAL-04` manual review of false positives/negatives; `VAL-05` uncertainty intervals and limitations; `VAL-06` figures/tables reproducible from results scripts. **Gate:** independently tested results with defensible methods, uncertainty and failure analysis. An interim subset may be documented in the December 2026 IEEE course report; full research validation remains a separate later milestone.

**Artifacts.** Locked predictions, aggregate tables, comparison figures, limitations, final report. **State:** `PENDING`.

## Dependencies, sequence, and stop conditions

- Main sequence: **1 → 2 → 3 → 5 → 6 → 7**. **Stage 4 labels are parallel to 2–3** but must have a frozen anatomical protocol and feed into training/validation.
- Stage 2 alone is not complete until Stage 3 demonstrates useful anatomical coverage.
- Stop before bulk registration if inputs fail QC. Stop before training if masks/crops have mismatched geometry. Stop before publication if independent test data influenced method selection.
- Every modification to crop dimensions, reference, intensity normalization or model definition creates a new versioned decision entry and relevant retesting.

## References used for planning

- [HCP Young Adult releases](https://www.humanconnectome.org/study/hcp-young-adult/data-releases) and [HCP-YA 2025 Appendix III](https://humanconnectome.org/storage/app/media/documentation/HCP-YA2025/HCP-YA_2025_Release_Appendix_III.pdf)
- [ANTs](https://github.com/ANTsX/ANTs), rigid-only reference registration (to be benchmarked)
- [TransUNet](https://doi.org/10.1016/j.media.2024.103280) (model design reference; not a CSP validation study)
- Provided CPS 843 project guidelines and final project rubric (course-specific constraints)
