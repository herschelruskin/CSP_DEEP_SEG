# Stage 3 — minimal reduced-T2 search-space generator (first scaffold)

This utility **does not detect CSP**. It removes broad anatomical regions that are unlikely to contain a triangular/anterior CSP, preserving the *original T2 voxel data*, orientation, spacing, and original-space positions in a smaller NIfTI. Intended for the 0.7-mm HCP SPC1 T2 images. The bounds are **not yet empirically approved** against manually reviewed CSP masks.

## Install / run in 3D Slicer

- Place `scripts/reduce_t2_slicer.py` in your local clone of `CSP_DEEP_SEG`. No added pip packages; it uses Slicer's existing NumPy and native volume APIs.
- Open the **original T2** in 3D Slicer. Make sure it is selected as the background/active volume in the slice views.
- Open Slicer's **Python Console** (`View` → `Python Interactor`) and paste **one line**:

```python
exec(open(r'D:\CSP_DEEP_SEG\CSP_DEEP_SEG\scripts\reduce_t2_slicer.py', encoding='utf-8').read()); reduce_active_t2(r'D:\CSP_DEEP_SEG\derived\reduced_t2')
```

The console prints source/crop sizes and % voxels retained. The scene gains a new `_reduced` volume; source volume is unchanged. The destination receives `*_reduced.nii.gz` and `*_reduced.crop.json` (native IJK bounds/affines/config/QC status). Paths above are examples matching our proposed Windows folder layout; change them if your actual clone or data is elsewhere.

### First batch test (three scans only)

```python
exec(open(r'D:\CSP_DEEP_SEG\CSP_DEEP_SEG\scripts\reduce_t2_slicer.py', encoding='utf-8').read()); batch_reduce_t2(r'D:\CSP_DEEP_SEG\T2w', r'D:\CSP_DEEP_SEG\derived\reduced_t2', limit=3)
```

Searches recursively for `*_3T_T2w_SPC1.nii.gz`, writes a CSV `batch_reduced_t2_report.csv`, unloads source and output nodes after processing each file, and does not overwrite previously cropped files. **Do not bulk-run all subjects until Slicer reload/overlap and mask containment pass.** Later use `limit=None` to process all SPC1 images after validation.

### Test CSP containment for an already loaded annotation

With exactly one segment in a loaded segmentation node:

```python
exec(open(r'D:\CSP_DEEP_SEG\CSP_DEEP_SEG\scripts\reduce_t2_slicer.py', encoding='utf-8').read()); reduce_active_t2(r'D:\CSP_DEEP_SEG\derived\reduced_t2', segmentation_node=slicer.util.getNode('Segmentation'))
```

Use `segment_id=...` if the segmentation node contains more than one segment. The crop sidecar and console report fractional inclusion and **signed six-face margin in millimetres**. An intentionally empty CSP reference is reported as `empty-reference`, not as a failed positive. A flagged anatomy case should **not** be counted as QC-approved for performance reporting.

For another run with the same input name, choose a new output folder or deliberately set `overwrite=True`.

## How the proposed (unvalidated) crop works

1. Sample every fourth voxel, threshold positive intensities to estimate coarse head foreground and its robust anatomical RAS bounds.
2. Estimate approximate LR midline as midpoint of robust x bounds (no formal midsagittal symmetry estimation yet).
3. Construct a generous six-sided RAS-aligned box: ±35 mm LR, trim 20% posterior / 5% anterior / 15% inferior / 3% superior of the measured foreground range. **These are development hypotheses, not safe cutoffs.**
4. Convert the box through the original 4×4 IJK-to-RAS image affine, conservatively enclose all eight RAS box corners on the native IJK grid, and extract native voxels (no interpolation or ANTs).
5. Shift the output origin by the native IJK start index, preserving all included original voxel world coordinates; log the coordinates in JSON.

The actual crop can exceed the requested RAS box in oblique images because it is kept native-voxel-aligned. The script prints a clipping note if the RAS box extends beyond source image coverage.

### Adjust settings only on development cases

```python
cfg=CropSettings(lr_half_width_mm=40, posterior_trim_fraction=0.10, anterior_trim_fraction=0.0, inferior_trim_fraction=0.10, superior_trim_fraction=0.0)
```

Pass `cfg=cfg` to `reduce_active_t2(...)` or `batch_reduce_t2(...)`. Wider/less trimmed crops are safer but require more network compute. The input data must be a native, untransformed scalar T2; if a parent transform exists the script rejects it to avoid incorrect coordinates.

## Validation and limitations

- **Implemented and locally tested:** pure-NumPy crop arithmetic, voxel identity/native affine round-trip, oblique box, synthetic positive/empty-mask checks.
- **NOT RUN:** executing in 3D Slicer on a real HCP scan, saved NIfTI reloading, cohort mask audit, crop containment rates, actual GPU model performance.
- **Required before accepting crop:** (i) inspect original/cropped T2 overlay on at least a few positive/negative and unusual cases; (ii) verify geometry after saving and reloading; (iii) compute full-mask coverage and minimum margins over QC-approved development masks; (iv) reserve family/subject-disjoint final testing; (v) tune sizes only on development cases.
- This threshold-based center is **not a validated anatomical midsagittal plane**. It may be biased by facial structures, FOV/background artifacts, off-center head positions, unusual anatomy, and head rotation. Add symmetry-based estimation only if measured failures justify it.
- Slicer-dependent actions are **untested in this environment**; synthetic tests only validate mathematical functions. Do not make claims of successful HCP processing until it has been run locally and logs are inspected.
- No original MRI or mask is changed, and no private HCP files should be committed to GitHub.

Run synthetic unit tests locally outside Slicer with `python -m pytest -q tests/test_reduce_t2_geometry.py` (requires NumPy and pytest).