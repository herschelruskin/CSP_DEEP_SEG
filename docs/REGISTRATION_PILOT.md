# Stage 2 pilot — rigid alignment (two-subject smoke test observed; full pilot NOT executed)

**Purpose:** determine whether rigid alignment materially improves anatomical crop placement compared with raw-T2 native/landmark localization. **Owner:** TBD · **State:** 2-subject local ANTsPy smoke test USER-REPORTED; full comparison and reproducible logs **NOT RUN**.

## Local pilot observation (2026-11-17; not independently reproduced from this repository)

- User locally ran synthetic registration and HCP real-T2 rigid registration in Docker/ANTsPy (image `ventricle-antspy:0.1`), fixed `100206` and moving `100307`; optimization on temporary ~2-mm inputs, followed by application of the rigid affine to native 0.7-mm moving T2 on the fixed image grid.
- Local-only output folder: `D:\CSP_DEEP_SEG\registration_smoke_test\` with files `fixed_2mm.nii.gz`, `moving_2mm.nii.gz`, `registered_T2_2mm.nii.gz`, `rigid_0GenericAffine.mat`, `registered_native_100307_to_100206.nii.gz`.
- Slicer visual check found overall orientation plausible but individual ventricular/CSP anatomy did not line up precisely. **Not a quantitative crop-containment or registration-accuracy test.** No verified runtime/RAM/landmark round-trip/log bundle committed.
- For the December POC, a **raw-T2 septal anatomical crop** and compact 2.5D segmenter are the first path. Treat ANTs as a comparator, not a prerequisite for all 1,113 subjects. If a learned coarse anatomical localizer outperforms rigid and no-registration options, it can supersede the rigid stage.

## Design

- **Moving image:** each unprocessed T2 `SPC1` or `SPC2`, native `.nii.gz`; preserve original bytes, header and affine.
- **Fixed image:** a fixed reference T2 in a consistent coordinate frame. `100206` is a candidate pilot reference; decide on a population template before broader deployment.
- **Control:** affine-only/midline coordinate baseline, evaluated using the same crop coverage metric.
- **Working pyramid:** anti-aliased temporary ~2 mm T2, **not** the native 0.7 mm image used for segmentation.
- **Transform:** rigid 6 DOF (ANTs `-t r` via `antsRegistrationSyNQuick.sh` as a *candidate* command; verify actual optimizer/metric/pyramid in its logs).
- **Outputs to retain:** `.mat` transform, fixed-reference identifier/hash, parameters/software version, runtime/memory, initial/final registration metric, QC review, ROI coordinates, source hash.
- **Do NOT retain:** 1,689 fully warped full-resolution images. Delete temporary 2 mm images/warped outputs only after validating outputs.

## Candidate command (illustrative shell command; differs from the locally reported ANTsPy smoke-test execution)

```bash
antsRegistrationSyNQuick.sh \
  -d 3 \
  -f reference_T2_2mm.nii.gz \
  -m subject_T2_2mm.nii.gz \
  -o subject_registered_ \
  -t r \
  -n 4
```

Interpret forward versus inverse transforms using a point/landmark round-trip unit test before mapping a reference ROI back into native subject space. `antsRegistrationSyNQuick.sh` may write extra images; keep transforms and QC logs, clean extra files after confirmation.

## Suggested experiment (20 acquisitions; unique-subject-based sampling)

1. Select 20 volumes spanning initial head orientations and both SPC1/SPC2, with repeated acquisitions retained as distinct scans but same subject identity.
2. Run `control` and `rigid` on each and measure wall time, peak RAM and outcomes. Record all failures.
3. Define a generous septal ROI in the fixed reference **in mm**, map it back to each native scan and save a crop coordinate file.
4. Inspect midline, frontal horns and septal region in all three views. For manual reference examples, compute containment and minimum margin.
5. Choose the simplest approach meeting the specified coverage criterion; otherwise refine ventricle landmarks before scaling.

## Explicit tests

| Test ID | Input | Pass definition | Result |
|---|---|---|---|
| REG-01 | 1 synthetic 3D image + landmark points | Forward/inverse mapping error within declared numeric tolerance | Synthetic registration USER-REPORTED; numerical landmark round-trip NOT VERIFIED |
| REG-02 | 20 pilot T2 scans | No unreviewed gross midline/frontal-horn misalignment | 2-subject smoke test USER-REPORTED; 20-scan pilot NOT RUN |
| REG-03 | Same input twice with pinned seed/settings | Transform differences within declared tolerance | NOT RUN |
| REG-04 | No-reg vs rigid | Report crop coverage, failure rate and wall time; no automatic assumption of superiority | NOT RUN |
| REG-05 | Runtime/memory measurements | All 20 logged; failures diagnosed | NOT RUN |

**Pilot decision gate:** do not approve bulk registration before reviewing all 20. If a landmark-based coarse locator is consistently as accurate and much faster, record the evidence and choose it instead of ANTs.
