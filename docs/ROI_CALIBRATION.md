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

## 2026-11-19 correction — review flag does NOT change presence
The manifest must distinguish CSP `presence` from anatomical-boundary `qc`. A subject on the review list who has a CSP mask remains `present` with `qc=needs_review`, not `uncertain`. Genuine `uncertain` presence can still be specified explicitly via a status CSV and is skipped by the fitter.

**Exploratory ROI envelope:** `calibrate_roi_from_manifest(..., include_review_for_bounds=True)` now includes development positive masks with `qc=needs_review` by default (as well as provisional/pass masks), because large or blurred CSPs may define the required search space. Do not silently exclude very large cases. Missing/invalid masks still fail and their IDs appear in `errors.csv`; hard-excluded QC and truly uncertain presence remain skipped.

`calibrated_rules.json` stores the review-flagged positive count and a `sensitivity_excluding_review` comparison so it is clear how much these cases enlarge the box. This **does not promote their boundaries to approved ground truth for segmentation training**. It is only a conservative exploratory localization test. Preserve untouched subject/family-disjoint test data before making population claims.

For users with the previous Slicer file loaded, replace `scripts/calibrate_csp_roi_slicer.py` with the corrected version, then reload the module in the Slicer console. Rebuild the manifest with the existing explicit absence and review ID lists: expected 65 present / 5 absent / 0 uncertain when matching all 70 user-reported subjects. This is a target count, not a verified real-data result.

## 2026-11-19 outlier-excluded standard crop pilot

The first real HCP calibration read **70/70** original T2/mask pairs without computational errors: 65 CSP-positive, 5 CSP-absent (zero volume), 10 flagged positive masks still included and 13 review flags overall. Entire cohort was development; **no independent held-out cases**.

The extremely large subject **108828** has reported native CSP labelmap volume **2200.0 mm³**, while next-largest masks were 107321=203.4, 101309=200.3, 102008=155.7 and 107725=102.6 mm³. The user elected to remove 108828 from fitting the *standard* crop, not from the cohort, measurement archive or mask evaluation. This is a post-hoc geometry sensitivity test, NOT a random held-out validation set and NOT evidence that 108828 is anatomically nonexistent. The full 65-positive all-inclusive run remains as a comparator.

Updated command (after reloading the latest script inside Slicer):
```python
result = c.calibrate_roi_from_manifest(str(d/'cohort_manifest.csv'), str(d/'results_excluding_108828'), margin_mm=8.0, include_review_for_bounds=True, excluded_from_fit_ids=('108828',))
```
This produces normal `calibrated_rules.json`, `subject_measurements.csv`, `rule_evaluations.csv`, `largest_csp_ranked.csv`, and `leave_one_subject_out.csv` inside a new directory without modifying the all-inclusive results. The primary rules fit **64 positive masks + 5 absent**, while still **measuring, ranking, and auditing all 70** cases; the excluded subject is marked `excluded_from_fit=True` in measurement/audit/rank reports. Leave-one-out applies to **64 fit-positive** masks, not the excluded case. With no kept-aside subjects, do not call the 108828 diagnostic or these LOO results independent validation.

Check the retained median crop fraction, six-face margins, retained CSP voxel fraction for 108828 (possibly less than 100% by design), and whether other subjects set crop extrema. Preserve original `results` to compare the full and trimmed envelope. Independent testing must use newly acquired/unseen family-disjoint subjects.


## 2026-11-20 corrected unshifted proportional baseline — local user results

User manually removed the erroneous 15-voxel distant island from native mask 112112.nii (retaining the anatomically plausible 21-voxel component), then reran both calibration modes to a **new non-overwriting directory**:

    D:\CSP_DEEP_SEG\derived\roi_calibration\results_corrected_112112\

With 108828 excluded **from fitting only**, 70 scans/records processed; 64 positives fitted plus five operational absences, and 108828 still measured/evaluated. **Reported median source fraction**: fixed_mm **1.18%**, proportional **1.00%**. Internal leave-one-subject-out among 64 positive fitted cases: **0/64 containment misses** in each mode. The exceptional genuine 108828 is now **not entirely covered** under the smaller standard crop; do not silently use its standard-crop mask in training, and do not call posthoc outlier exclusion independent validation. All 70 were originally development: held-out crop performance NOT ESTABLISHED.

The user visually trialed the **unshifted proportional** crop on fresh original T2s. A later posterior translation by 0.025 of head foreground AP span created a tight **+2.58-mm anterior RAS-box clearance** in standard subject 103111, while 108828 had **−19.02 mm posterior** clearance. Based on this tradeoff, user chose to **return to the unshifted original proportional rule**; neither the translated nor posterior-extended exploratory JSON is the baseline. These RAS-box clearances are not a claim of independent native-voxel validation.

**Frozen default for 2.5D construction:** the original unshifted proportional JSON at the corrected directory above, and the existing scripts/calibrate_csp_roi_slicer.py::reduce_t2_with_calibrated_rule; no additional shift. This method uses the *foreground-derived per-subject head-relative* AP/SI bounds and LR midpoint and preserves native IJK voxel resolution via offset-affine crop. It does not anatomically identify frontal horns or detect CSP.

A manifest-restricted, 3-subject-first crop helper (scripts/crop_manifest_slicer.py) and full downstream mask geometry checks are described in [CSP 2.5D baseline](CSP_25D_BASELINE.md). Archive an immutable copy and hash of the private calibrated_rules.json for every experimental run. The full numeric JSON has not been uploaded here; source code alone cannot recreate the same learned crop coefficients without the original calibration cohort.
