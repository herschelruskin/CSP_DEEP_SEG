# CSP_DEEP_SEG: cohort-derived standardized crop (first implementation)

**Status: implemented and synthetic-tested, not evaluated on real HCP CSP masks.**

This utility uses native T2 and corresponding 3D Slicer CSP masks to estimate **one shared ROI rule**. Two alternatives are evaluated:

1. `fixed_mm` — lateral half-width, AP limits and SI limits are fixed physical-mm offsets relative to each subject's detected foreground bounds.
2. `proportional` — lateral half-width and AP/SI limits are fractions of each subject's detected foreground dimensions. The safety margin remains in mm.

Both rules re-center left/right on that subject's approximate foreground midpoint. AP and SI are **not** centered; their bounds come from the measured CSP extrema in development subjects. No learning model or registration is required.

**Anatomical caveat:** current foreground bounds are derived from robust intensity thresholding of *head foreground* (not a skull-stripped brain, intracranial volume, skull measurement or a fitted midsagittal plane). Therefore `proportional` is **head-foreground-relative**, only a proxy for the requested cranial-dimension model. Compare its variability and suitability with `fixed_mm`; replace the anchor with a verified brain/skull mask if required. Large yaw/pitch/roll or variable neck field of view may undermine either method.

## How to run from 3D Slicer (one line per step)

Extract the ZIP so that these two files reside together:

- `D:\CSP_DEEP_SEG\CSP_reduced_T2_crop_scaffold\scripts\reduce_t2_slicer.py`
- `D:\CSP_DEEP_SEG\CSP_reduced_T2_crop_scaffold\scripts\calibrate_csp_roi_slicer.py`

This example assumes original scans under `D:\CSP_DEEP_SEG\T2w\<subject ID>\<ID>_3T_T2w_SPC1.nii.gz` and segmentations in `D:\CSP_DEEP_SEG\masks`. Change the mask path if your actual saved masks are elsewhere. **The script never renames or modifies them.**

### 1. Create the initial subject manifest

First edit the included `absent_ids.txt` to contain your five confirmed absent subject IDs (one per line). For flagged ambiguous cases, edit `needs_review_ids.txt` similarly. Neither list should contain arbitrary example IDs.

```python
import sys; sys.path.insert(0,r'D:\CSP_DEEP_SEG\CSP_reduced_T2_crop_scaffold\scripts'); from calibrate_csp_roi_slicer import make_roi_manifest; make_roi_manifest(r'D:\CSP_DEEP_SEG\T2w',r'D:\CSP_DEEP_SEG\masks',r'D:\CSP_DEEP_SEG\derived\roi_calibration\cohort_manifest.csv',absent_ids_file=r'D:\CSP_DEEP_SEG\CSP_reduced_T2_crop_scaffold\absent_ids.txt',review_ids_file=r'D:\CSP_DEEP_SEG\CSP_reduced_T2_crop_scaffold\needs_review_ids.txt')
```

You may instead use an exported local `status_csv=` with columns `subject_id,presence,qc,split,notes`. It can hold the five absences, review flags, and your note identifying the unusually large CSP. The first command only adds subjects with a discovered mask or an explicit status record; it does not enumerate the other 1,000+ unannotated HCP subjects.

Review `cohort_manifest.csv` before proceeding. The important columns are:

| Column | Values | Meaning |
| --- | --- | --- |
| `subject_id` | e.g., HCP subject ID | Match by an exact six-digit token in filename or parent folder |
| `presence` | `present`, `absent`, `uncertain` | Absence is **not** inferred from missing masks |
| `qc` | `pass`, `provisional`, `needs_review` | `needs_review` cases are excluded; `provisional` results are explicitly preliminary |
| `split` | `dev`, `holdout` | **Set subject/family-safe splits before calibration.** Defaults to `dev` only for preliminary exploration |
| `source_t2` | Original `SPC1` T2 | Never use reduced T2 as input to calibration |
| `mask_path` | CSP .seg.nrrd or native-grid .nii(.gz)/.nrrd | May be empty **only if** presence = absent |
| `segment_id` | Optional Slicer segment ID/name | Required if saved .seg.nrrd has >1 segment; choose triangular CSP |
| `label_value` | Optional integer | Required if a native-grid labelmap has >1 nonzero value |
| `notes` | Free text | Preserve large/uncertain anatomy flags |

A subject with an uncertain cavity or unverified non-CSP compartments must be excluded from the **definitive** calibration until adjudicated; initial provisional runs are exploratory only. Check the QC review flags from the user-maintained records. Do not rely on the discontinued annotation-status column.

### 2. Calibrate both rules and evaluate development cases

```python
from calibrate_csp_roi_slicer import calibrate_roi_from_manifest; calibrate_roi_from_manifest(r'D:\CSP_DEEP_SEG\derived\roi_calibration\cohort_manifest.csv',r'D:\CSP_DEEP_SEG\derived\roi_calibration\results',margin_mm=8.0)
```

This processes subjects sequentially inside Slicer. It uses the input native voxel grid and original IJK-to-RAS matrices; image/mask geometry must match. Slicer `.seg.nrrd` segments are mapped into the T2 reference geometry with Slicer's supported API. Multi-segment and multi-label inputs **require an explicit selection**. Error/uncertain subjects are recorded, never silently treated as zero CSP.

By default, `holdout` scans and masks are **not even loaded**; they remain protected. They can be evaluated once the candidate rules and margins are frozen by running with `unlock_holdout=True`. No subsequent parameter tuning may use those results.

Files written **locally**:

- `subject_measurements.csv` — all positive CSP extents in RAS, offsets from foreground, normalized extents, true voxel volume. Confirmed absences are zero volume, with no positive extrema.
- `largest_csp_ranked.csv` — descending CSP volume and LR/AP/SI spans; preserve and inspect the unusually large case, plus source notes.
- `calibrated_rules.json` — `fixed_mm` and `proportional` parameters, foreground estimation settings and development counts. Both candidate rules are marked `UNVALIDATED_CANDIDATE`.
- `rule_evaluations.csv` — subject-by-subject containment, minimum six-face margin, fraction retained, candidate mode, split and QC.
- `leave_one_subject_out.csv` — development-only stress test. Important for understanding whether one extreme CSP determines the crop box.
- `errors.csv` — missing/mismatched masks, invalid statuses, unresolved anatomy cases and any failed loads.

### 3. Apply the selected rule on one original T2

```python
from calibrate_csp_roi_slicer import reduce_t2_with_calibrated_rule; import slicer; reduce_t2_with_calibrated_rule(slicer.util.getNode('114217_3T_T2w_SPC1'),r'D:\CSP_DEEP_SEG\derived\roi_calibration\results\calibrated_rules.json',r'D:\CSP_DEEP_SEG\derived\roi_calibration\cropped_test',mode='proportional')
```

It writes a native-resolution reduced T2 and an adjacent JSON record, without overwriting the original image. Replace `mode='proportional'` with `fixed_mm` for an alternative comparison. Inspect the crop alongside the original in axial/coronal/sagittal views and verify the CSP remains covered.

Optional smoke test on three original SPC1 scans only:

```python
from calibrate_csp_roi_slicer import batch_apply_calibrated_rule; batch_apply_calibrated_rule(r'D:\CSP_DEEP_SEG\T2w',r'D:\CSP_DEEP_SEG\derived\roi_calibration\results\calibrated_rules.json',r'D:\CSP_DEEP_SEG\derived\roi_calibration\cropped_test',mode='proportional',limit=3)
```

Full-cohort batch processing (`limit=None`) requires `allow_full_cohort=True` **after** independent review and validation. Keep original scan files unchanged; do not push scans, masks, subject manifests or derived metrics to the public GitHub repository.

## Scientific and geometric checks

- Compare modes on mean and maximum crop fraction, positive-mask whole-containment and *worst* face margin in mm. The smallest average box is not necessarily the best if it excludes one anatomically plausible CSP.
- Distinguish **maximum CSP volume** from **maximum width/AP/SI extent**. Different subjects may determine different faces of the pooled ROI.
- Inspect confirmed absent cases: zero-volume masks are valid but do not define extrema. Missing scans/masks must trigger errors, not automatic absence.
- One unusually large real CSP should be included if it passes anatomical QC. If it is the dominant extreme, leave-one-subject-out results will reveal the sensitivity; do not delete it just because it enlarges the ROI.
- The pooled extreme of the reviewed development masks is **not** proof that the box covers the largest possible CSP in the full HCP population. Reserve untouched subjects/families for independent testing, assess abnormal anatomy and keep physical safety margins.
- **Use the original MRI affine and native voxel grid**. Crop boundaries in RAS are converted conservatively to IJK, keeping original voxel data, spacing and directions. Recheck saved NIfTI geometry on an actual scan before deployment.
- If proportional cropping is unstable because the initial foreground includes variable neck/scalp or different head tilt, keep the fixed-mm baseline and investigate a cheap brain mask or better midline/AC-PC reference instead of adding a deep localizer prematurely.

## Test status

The included Python tests check geometry, negative references, maximum-extreme calibration, proportional versus fixed-mm scaling, correct exclusion of ambiguous/missing subjects, exact sparse-mask containment, manifest generation and holdout isolation on synthetic images. The **actual 70 HCP scans are not accessible** in this tool environment; no cohort numerical results or Slicer end-to-end execution are claimed.