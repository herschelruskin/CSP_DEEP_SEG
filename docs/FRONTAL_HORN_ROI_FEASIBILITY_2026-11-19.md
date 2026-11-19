# Frontal-horn-guided CSP ROI — feasibility review (2026-11-19)

**Status:** PROPOSED EXPERIMENT, not a selected/validated model. **Implementation/training:** NOT RUN. **Scope:** triangular/anterior CSP on original unprocessed HCP 3T T2 (approximately 0.7 mm). **Priority:** guarantee safe CSP search-region containment before segmentation optimization.

## Verified repository and user-reported state
- Audited branch: \`main\`; starting HEAD \`1066a69d3bcd1d00c82a8b6c603eb14e7dc3dd79\` (2026-11-18). Repository contains documentation, not an executable model package.
- Filename inventory previously reconciled: 1,689 T2 acquisitions / 1,113 distinct subject IDs; full file/geometry QC still open.
- NEW 2026-11-19 **USER-REPORTED**: 70 manual subjects reviewed, 65 CSP present and 5 absent; approximately 13 need anatomical review. Actual saved mask inventory, geometry and QC-pass counts not audited. Annotation-status spreadsheet column intentionally no longer maintained; do not use as completion evidence.
- An absent or unresolvably tiny CSP is a valid negative reference when confirmed; uncertain is distinct from absent.
- Written CPS 843 instructions cited in repo specify 2026-12-14 23:59 as course deadline, subject to newer course instructions. Research continues afterward.

## Architectural question and working hypothesis
The frontal horns form the lateral boundaries of the septal region and remain present when CSP is absent. But pairwise horn centroids alone cannot safely determine posterior CSP and superior/inferior bounds. Test a **paired medial ventricular geometry / septal corridor with broad AP/SI margins**, not a CSP-brightness detector. Frontal horns are NOT the same as FreeSurfer whole LV labels.

## External evidence verified for planning
- HCP S1200 Appendix III: standard structural preprocessed \`T1w/\` package lists \`aparc+aseg.nii.gz\`, \`T2w_acpc_dc_restore.nii.gz\`, \`T1w_acpc_dc_restore.nii.gz\`. See https://www.humanconnectome.org/storage/app/media/documentation/s1200/HCP_S1200_Release_Appendix_III.pdf (pp. 21–22).
- FreeSurfer LUT: 4=left LV, 43=right LV, 14=third ventricle, 250=fornix. **LUT membership does not imply that label 250 occurs in a given \`aparc+aseg\` or that it correctly traces the forniceal columns.** See https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/AnatomicalROI/FreeSurferColorLUT .
- HCP processing aligns/corrects T2 to T1 anatomical native space; original unprocessed T2 and HCP preprocessed T2 should never be treated as voxel-identical. See https://pmc.ncbi.nlm.nih.gov/articles/PMC3720813/ .
- CSP lies between septal leaves; columns of fornix delimit anterior CSP from posterior cavum vergae; inferiority alone does not define CV. See https://pmc.ncbi.nlm.nih.gov/articles/PMC10607410/ .
- Strong U-Net baselines and rigorous validation are preferable to premature architectural complexity: https://papers.miccai.org/miccai-2024/562-Paper2847.html .
- Heatmap-landmark localization is an established alternative, not proven superior for this task: https://proceedings.mlr.press/v227/pang24a.html .

## Alternatives, in ascending complexity
| Option | Labels / inference dependency | Major failure risk | Role |
|---|---|---|---|
| A. Raw-T2 head/midline geometry + generous box | No new labels; no registration | Variable head pose and posterior extent; box inflation | Mandatory baseline |
| B. Reference-assisted processed-LV corridor | Requires matched HCP \`aparc+aseg\` and verified raw↔processed mapping | Whole LV wrongly treated as frontal horn; label-to-raw misalignment | **First oracle-style anatomical feasibility experiment** |
| C. Direct raw-T2 ventricular-intensity heuristic | No manual labels but image processing | CSF thresholding merges neighboring spaces, bias fields | Optional simple control |
| D. Learned 3D paired-horn heatmaps or extent maps | Automated/checked LV supervision; raw T2 at inference | Poor posterior bounds, heatmap ambiguity | Preferred learned candidate only after B works |
| E. Small 3D ventricular segmentation | Whole LV automated labels; raw T2 at inference | Harder masks/compute; false topology, posterior contamination | Alternative if D not enough |
| F. Direct CSP-area bounding box | Manual region targets including confirmed negatives | Learns CSP visibility/prevalence; misses absent cases | Comparative model, not primary |
| G. Rigid/affine alignment with fixed template box | Existing registration tools/inference cost | Individual septal variability after alignment | Optional comparator |

## Proposed geometry for experiment B (not yet validated)
1. Acquire 5–10 **matched** raw SPC1 T2 / processed T2 / processed \`aparc+aseg\` triplets first, covering positive, absent and unusual cases; record file and transform provenance.
2. Verify orientation, physical coordinate reference, spacing, qform/sform and actual overlays in three views. Derive a transform \`raw_to_processed\` (and inverse) from HCP processing provenance where available; otherwise establish/validate one. Do **not** assume same voxel array or an affine-only relationship.
3. Extract labels 4 and 43, quality-check left/right presence, size, principal components and physical symmetry. Treat as *whole LV*.
4. Build candidate **frontal-region** masks via anterior ventricular extent in an anatomical AP coordinate frame; compare approaches: anterior percentile/slab, paired medial-boundary sampling, and a posterior transition candidate using label 14. The transition is only a heuristic; inspect manually and do not declare foramen of Monro localization established.
5. For each anterior AP station with valid bilateral ventricular evidence, determine a local septal center from the two **medial** boundaries, not the centers of the complete ventricular masks. Define a swept septal corridor; take its conservative 3D bounding box.
6. Enlarge anterior/posterior and superior/inferior bounds in millimetres to cover the expected septum between corpus callosum and fornix, and allow laterally for CSP widening. Initial margins are **development-set-tuned hypotheses**; avoid fixed final dimensions before evaluating mask extents.
7. Map the box corners (or conservative sampled boundary for nonlinear mappings) back to original T2 physical space. Extract on the *native T2 voxel grid*, retaining affine, integer bounding indices, pad widths, and source image hash. Never resample CSP masks with linear interpolation.
8. On missing/asymmetric labels, poor cross-modal overlay, invalid bounds or low geometric certainty, return a large predefined **fallback** box and log failure rather than silently crop too tightly.
9. Run this pipeline on confirmed absent CSPs too: the output must depend on ventricular anatomy, not CSP visibility.

**Critical distinction:** reference-assisted/oracle B is *not deployable raw-T2-only inference* when it uses HCP precomputed FreeSurfer labels. Its purpose is to test whether horn information can yield a good crop. If it does, train D/E on raw, not processed, T2 by transferring anatomical targets; avoid processed→raw domain shift.

## Crop geometry and metrics
Define \`G_i\` = manually QC-approved positive CSP mask in original native coordinates and \`R_i\` = automatically generated native ROI.
- **Whole-mask containment:** \`all(G_i voxel centers inside R_i)\`; also report fractional inclusion \`|G_i ∩ R_i| / |G_i|\`. For empty cases, containment is N/A.
- **Signed minimum face margin:** compute minimum physical-space distance from *every reference mask voxel* to *all six ROI faces*; negative for crop violations. Report each axis/face margin and minimum per subject; ensure interpolation/voxel-extents are accounted for.
- ROI voxel count, mm³ volume, estimated 2.5D inference FLOPs, wall time, peak CPU/GPU memory, and fallback rate.
- Localization quality: anatomical target error in mm and whether *full CSP containment* holds. Center error alone is insufficient.
- Covariates/failures: CSP volume and AP length, unusual lower cavities, asymmetrical or large ventricles, registration errors, absent cases and masks needing adjudication.
- **Geometry test:** exact crop→native and native→crop landmark round trip, including oblique affines, non-unit/negative directions and padded crops; no off-by-one errors.

Engineering targets for development (not empirical results): zero observed full-containment failures on development masks; a safety margin (for example ≥5 mm to each face on development cases) while minimizing crop size; no silent invalid/empty ROI on confirmed absent cases. Retain held-out observations and binomial uncertainty; zero failures on a small sample does not prove 100% population reliability.

## Leakage-safe experiment sequence
0. **ANN-01/DATA-02:** audit local native T2/mask paths, shape, qform/sform, connected components, absent/uncertain/QC flags. Freeze a versioned triangular SOP; do not train from ambiguous fine labels.
1. **SPLIT-01:** freeze subject-level splits, grouping related HCP family IDs where permitted/available. Never put SPC1/SPC2 or siblings across partitions. Set aside a held-out positive/negative and unusual-anatomy sample *before* margin/model tuning.
2. **ROI-A:** simple raw-T2 midline crop (no FreeSurfer/ANTs). Assess on development masks.
3. **ROI-B:** oracle-style, independently derived LV-corridor geometry from HCP processed labels with verified mapping. Evaluate identical containment criteria and compare against A.
4. **Gate:** if B is unreliable even with accurate ventricle masks and generous margins, **do not train D/E yet**; improve the anatomical rule or choose A. If B works, derive and QC weak localizer targets from broader HCP processed segmentation coverage.
5. **ROI-D:** train a minimal ~2–2.5 mm input 3D heatmap/extent localizer (base channels 8–16, batch 1, mixed precision as hardware permits), predict 2 paired anatomical heatmaps and optionally bounds; crop native T2, use validated uncertainty/margin inflation and safe fallback. Compare on identical held-out cases.
6. **SEG:** same compact 2.5D coronal U-Net (initially 5 adjacent native-resolution slices as channels, 1 middle-slice mask) across crop variants; keep image normalization, split, seeds, training budget, label QC and loss fixed as far as practical.
7. **TEST:** independently report crop containment and its confidence interval, positive-case Dice/volume/HD95 or boundary distance, negative-case false-positive burden/presence detection, training/inference time, failed cases and fallback frequency. Five reported negatives are not enough for a strong specificity claim.

**Go/no-go for a learned localizer:** require no additional observed missed CSPs versus best simple crop, compelling reduction in ROI burden and/or segmentation false positives, raw-only inference, reproducible mapping and reliable fallback. If learning only saves a trivial crop fraction while adding material failure risk, retain the simpler baseline.

## Smallest meaningful implementation
A pure Python/nibabel/numpy/scipy **reference-assisted ROI geometry evaluator**, not neural-network training. Functions: validate NIfTI geometry, extract whole LV label masks, form three candidate ventricular-relative boxes, map to raw space, crop/reconstruct, calculate exact containment/margins, export per-subject CSV and QC slices on local machine. Use synthetic NIfTI files for CI/unit tests; never commit private HCP scans, masks or unredacted IDs.

Suggested eventual structure:
\`\`\`text
configs/roi_fixed.yaml
configs/roi_horns_oracle.yaml
configs/localizer_small3d.yaml           # only after feasibility
src/csp_seg/io/geometry.py
src/csp_seg/data/manifest.py
src/csp_seg/roi/fixed.py
src/csp_seg/roi/horn_reference.py
src/csp_seg/roi/crop.py
src/csp_seg/eval/containment.py
src/csp_seg/models/localizer_3d.py       # later
src/csp_seg/models/unet_25d.py           # later
tests/test_geometry.py
tests/test_crop_roundtrip.py
tests/test_empty_masks.py
tests/test_containment.py
\`\`\`

## Exact next bounded action
Before implementation, check 5–10 actual raw-SPC1 / HCP-processed-T2 / \`aparc+aseg\` matched subjects and audit local segmentation masks. Confirm transforms and visually verify anterior ventricular geometry. Then implement ROI-A and reference-assisted ROI-B with synthetic geometry tests and a small development-only containment experiment. **No code or test result described above has been executed in this session.**
