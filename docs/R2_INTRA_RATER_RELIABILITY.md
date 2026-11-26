# CSP R1/R2 intra-rater reliability audit — November 26, 2026

## Scope

One rater independently reannotated 20 preselected HCP-YA native T2 images without viewing original R1 annotations or 2.5D U-Net predictions. This is **intra-rater**, not inter-rater, reliability. The rater reported taking more care in R2, so the two annotation conditions are not assumed equivalent. Data must remain unchanged until this analysis is complete.

The selected subjects include 17 with positive R1/R2 masks, one with both sessions operationally absent/unresolvably tiny (102614), and two originally absent but small R2 positives (107018, 109325). Treat absence as zero-volume, not missing; do not assign Dice=1 to two empty masks. For the one absent/positive pair, Dice=0 under the binary operational interpretation. Record presence classification and Cohen's kappa separately.

The original ID.nii and independently reannotated ID_2.nii are saved in the SAME local D:\CSP_DEEP_SEG\CSP_Seg folder. The initial VTK disk-file inspection found 84 masks, 19 populated R2 suffix-2 files and no exported zero-mask file for 102614. Original unsuffixed positive masks were present. This is a file-count/voxel check only, not spatial confirmation.

## Script and execution

On November 26, the user was supplied a downloadable local Slicer script audit_csp_r2_intrarater.py (SHA256 41d9834592df2f57d9dd9eb670401f84bc51310a87d3c3164c0c0120d8b976d1). It was compiled and tested *synthetically* against a complete 20-case fixture with NIfTI qform/sform transforms, no original MRI provided. Real R1/R2 performance numbers are **not available until the user runs the script against their private saved labels and returns the outputs**. Commit the tested analysis script to the repository after successful live execution, rather than treating synthetic outcomes as MRI results.

Place the downloaded Python script in the home PC Downloads directory. In **3D Slicer's Python Console** (not PowerShell), run one line:

~~~python
exec(open(str(__import__('pathlib').Path.home()/'Downloads'/'audit_csp_r2_intrarater.py'), encoding='utf-8').read()); run_r2_reliability()
~~~

Choose D:\CSP_DEEP_SEG\CSP_Seg in the folder dialog. The script requires VTK and NumPy, which ship with Slicer; SciPy (if present) supplies surface-distance analysis. No SimpleITK required. It NEVER modifies any source masks or Slicer scene. It reads original and repeat NIfTI masks, checks 20 expected subject IDs and expected disk-audit voxel counts, verifies consistent dimensions, voxel spacing and qform/sform for each R1/R2 positive-positive pair, and stops on mismatch. This does not prove that the labels correspond to the correct source T2 scan; a later image space/QC audit may be needed.

Outputs written to a **new** separate folder D:\CSP_DEEP_SEG\derived\r2_reliability_20261126 when the chosen masks live in D:\CSP_DEEP_SEG\CSP_Seg:

- r2_per_case_metrics.csv: R1/R2 voxels and volumes, TP overlap, R1-only/R2-only voxels, Dice, Jaccard, precision and recall with R1 as reference, absolute and signed volume differences, 95th-percentile Hausdorff distance and average symmetric surface distance in mm, geometry status, and file provenance.
- r2_reliability_summary.json: mean/median/min/max Dice on 17 positive-positive pairs, pooled Dice, 10,000-sample paired bootstrap interval of mean Dice (seed 843), absolute agreement ICC(A,1) for paired positive volumes, Bland–Altman mean difference and nominal 95% limits, presence agreement and Cohen's kappa over 20, explicit empty-case policy.

Outputs refuse to overwrite existing results. Source MRI masks stay local and must not enter public GitHub.

## Interpretation safeguards

- Dice describes agreement between two segmentations by the **same rater**, not anatomical truth. These measurements cannot establish inter-rater reliability, independent adjudication, or model quality.
- Mask volumes were 16/17 larger on second labelling among cases positive in both sessions. Combined 17-pair R2 volume count increased 702 to 892 voxels (+27.1%). This was observed in preliminary file audit; it does not tell us how spatial masks overlap.
- Cohort deliberately includes small CSP and absent cases. Separate presence agreement, positive-case spatial Dice, and volume ICC to avoid misleading interpretation driven by differences in structure size.
- R2's additional regions and R1/R2 presence disagreements should be adjudicated only AFTER R2 has been frozen. Do not retrain the U-Net on edited labels or recompute checkpoint selection based on reliability examples before protecting the original model and independent evaluation.
- A high ICC with consistently larger R2 masks can coexist with poor absolute within-subject spatial agreement; report direction and magnitude of bias alongside ICC and Dice.
