# CSP_DEEP_SEG — current state and next avenues

**Snapshot date:** 2026-11-18  
**Scope:** Triangular cavum septum pellucidum (CSP) in native, unprocessed HCP Young Adult 3T T2-weighted MRI (~0.7 mm isotropic). The December 2026 CPS 843 deliverable is a **proof-of-concept checkpoint**, not the end of the research project. The written course instructions archived in this repository state **December 14, 2026, 23:59**; confirm independently if later instructions supersede this.

> **Evidence labeling:** Values below are a combination of user-reported local experiments and a Google Sheets/CSV manifest review in the project conversation. GitHub currently holds documentation, not the executable local registration pipeline or the private MRI/mask files. No segmentation-network performance has been measured.

## Inventory and annotation

- A generated local filename manifest contained **1,689 distinct T2 acquisitions**, **1,113 unique subject IDs**, and **576 additional acquisitions**, with no duplicate acquisition keys. This reconciles filenames, **not** complete NIfTI integrity, geometry, or MRI quality. Full data QC remains open.
- Working annotation queue contains the **1,113 SPC1 acquisitions**, one per subject. SPC2 acquisitions remain preserved in a full-acquisition registry/backup, to substitute when SPC1 fails QC or for future repeatability checks. **Do not delete source scans**. Train/test partitions must be by subject; HCP family structure remains to be addressed.
- As of **2026-11-17**, user reported **20 or more manually reviewed cases**, with a checkpoint of **19 CSP-present and one CSP-absent** among the initial 20. Further labeling after that checkpoint may have occurred; **the current number of saved and QC-passed masks is not independently verified here**.
- User manually inspects and saves native-T2 segmentations in Slicer/SlicerSALT. The low-friction tracker records scan key, **triangular CSP present / absent / uncertain**, annotation status, QC and optional notes. Paths, sizes, bounding boxes and quantitative measurements should be extracted from saved masks by script; no extra hand-entered morphology grade.
- **Target is triangular/anterior CSP only for the first iteration**. Do not assume that a lower/oval-looking cavity is an independent compartment, or that an inferior extension is cavum vergae: cavum vergae is defined in relation to the **fornix columns posteriorly**, not simply vertical position or shape. Several observed HCP T2 cases exhibit ambiguous inferior bright spaces and possible partial connections; preserve provisional masks and mark QC **Needs review** rather than forcing an unsupported anatomical cut. Resolve a reproducible annotation SOP, optionally with expert neuroradiology adjudication, before using these cases as trusted fine-segmentation ground truth.
- **Absent** = no resolvable triangular CSP following review (a legitimate empty mask when confirmed); **uncertain** must not be coded absent or silently treated as negative.

## Registration and localization — observed pilots, not deployment validation

- Local Windows/Docker image `ventricle-antspy:0.1` (ANTsPy) reportedly ran synthetic registration and a **two-subject real-T2 ~2 mm rigid smoke test**: fixed HCP **100206** and moving **100307**. A resulting rigid affine was also applied to the moving original 0.7 mm image on the fixed native grid. Example local-only outputs under `D:\CSP_DEEP_SEG\registration_smoke_test\`: `fixed_2mm.nii.gz`, `moving_2mm.nii.gz`, `registered_T2_2mm.nii.gz`, `rigid_0GenericAffine.mat`, `registered_native_100307_to_100206.nii.gz`.
- Slicer review suggested global orientation alignment but appreciable residual septal/ventricular anatomical variability. Rigid alignment **cannot** force CSP anatomy to coincide between individuals. The originally envisioned rigid-registration-for-everyone plan is therefore **not settled**.
- A Slicer fixed-box experiment (~15.3 mm LR × 59.8 mm AP × 19.2 mm SI) visually encompassed candidate regions in two inspected cases but is **not validated for the cohort**; the required crop appeared overly generous/fragile. Do not claim a containment percentage.
- An HCP processed `aparc+aseg` labelmap over corresponding `T2w_restore` was inspected for 100206. Labels **4 and 43** provided LV anatomy; **label 72 (fifth ventricle/CSP) was absent (0 voxels)** even though a septal cavity appeared visually plausible. Processed FreeSurfer labels are **neither reliable CSP ground truth nor evidence of anatomical absence**. Their availability/alignment to unprocessed T2 cannot be presumed. A proposed fornix label lookup (250) was **not verified**.
- Prefer a **raw-T2-only first baseline**, avoiding mandatory FreeSurfer/SynthSeg and potentially avoiding ANTs at inference. Preserve the original 0.7 mm native image for the segmentation target.

## Modeling direction (design, no training yet)

1. **Baseline A — simple anatomical midline/septal crop** on raw T2 (with a documented fallback, physical-mm bounds and complete positive-mask containment tests). Begin with a compact **2.5D U-Net** on cropped native-resolution T2, optimized for the limited laptop/home-GPU budget.
2. **Candidate B — coarse-to-fine cascade:** small downsampled T2 **anatomical-region localizer** predicting where the septal region is expected **even when triangular CSP is absent**; extract native 0.7 mm ROI; apply the same 2.5D segmentation network. Train locator for the anatomical neighborhood, *not* merely a low-resolution bright-CSP detector, because tiny CSP may vanish at coarse resolution. Compare fairly against A using the same subjects, split and segmenter.
3. **Next ablations:** smaller 3D U-Net (if GPU allows), localizer variants, crop-size/ROI margins and candidate 3D attention/TransUNet only after a reproducible classical/small U-Net baseline. Other possibilities: ventricular landmarks, light affine/rigid alignment where demonstrated beneficial, fixed search slabs with local refinement. Escalate to nonlinear registration/whole-brain parcellation only if evidence demands them.
4. **Evaluation:** subject-disjoint (ideally family-disjoint) train/validation/test; prevent repeat scans crossing partitions. Report CSP-positive mask Dice, volume error, false positives in empty cases, presence detection, and **whole-mask crop containment and margin**. At the 20-case checkpoint (~19 positive, 1 absent), a toy training experiment is feasible, **but absence-specificity is not estimable reliably**. Set aside ambiguous masks until adjudicated.
5. **Compute:** work laptop (Intel Iris Xe) for Slicer annotations, data parsing/geometry and CPU smoke tests; RTX 2060 Super home PC for initial 2D/2.5D runs; Alliance/Compute Canada for larger 3D models or sweeps. No training run or speed result is logged yet.

## Immediate reproducible next actions

| Priority | Next action | Evidence required |
|---|---|---|
| 1 | Inventory local saved masks and check **actual** complete/QC-reviewed count and filename-to-subject matching | Automated report: positive/empty masks, dimensions, affine equality, missing masks, split-safe IDs |
| 2 | Freeze concise **triangular CSP boundary SOP** and adjudicate inferior/ovular/fornix-ambiguous scans | Versioned rules, a few reviewed examples, recorded exclusions/uncertainty |
| 3 | Define a simple raw-T2 septal crop and test **complete CSP containment** using the first masks | Crop-in-native-space code and per-case containment/margin report |
| 4 | Implement 2.5D U-Net dataset loader, loss, synthetic tests and tiny CPU training smoke test | Committed code/config, output-shape and native-grid round-trip tests |
| 5 | First small GPU run using subject-level partition; report honest provisional results | Seed, device, split hash, checkpoints, reproducible metrics; no test-set tuning |
| 6 | Train and compare a lightweight learned coarse anatomical localizer | Matched split/crops, coverage/failure/runtime comparisons against fixed crop |
| 7 | Extend annotations toward **~50** first-pass cases and diversify size/absence representation without reclassifying true tiny CSPs as absent | QC-reviewed manifest and error analysis |

**Important operational distinction:** The numbers in the initial filename manifest and Google Sheet are not themselves a published QC outcome. The user has not provided current source MRI, mask set, code, per-subject QC logs, or training results to this repository. Do not report Dice, high ROI recall, registration accuracy or successful model training without run artifacts.

## Repository and continuity

- [Progress tracker](../tracking/PROGRESS.md) · [Decisions](../tracking/DECISIONS.md) · [Living handoff](../tracking/HANDOFF.md)
- [Seven-stage long-term protocol](SEVEN_STAGE_PROCESS.md) · [Two-horizon roadmap](ROADMAP.md) · [Registration pilot](REGISTRATION_PILOT.md)
- Read [../AGENTS.md](../AGENTS.md) before resuming. Keep restricted/private HCP images, masks, raw manifest and Google Sheets access URLs out of this public repository.
