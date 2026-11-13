# Stage 2 pilot — rigid alignment (SPECIFICATION, not executed)

**Purpose:** make anatomical localization reproducible without needing whole-brain registered copies or a nonlinear transform. **Owner:** TBD · **State:** NOT RUN.

## Design

- **Moving image:** each unprocessed T2 `SPC1` or `SPC2`, native `.nii.gz`; preserve original bytes, header and affine.
- **Fixed image:** a fixed reference T2 in a consistent coordinate frame. `100206` is a candidate pilot reference; decide on a population template before broader deployment.
- **Control:** affine-only/midline coordinate baseline, evaluated using the same crop coverage metric.
- **Working pyramid:** anti-aliased temporary ~2 mm T2, **not** the native 0.7 mm image used for segmentation.
- **Transform:** rigid 6 DOF (ANTs `-t r` via `antsRegistrationSyNQuick.sh` as a *candidate* command; verify actual optimizer/metric/pyramid in its logs).
- **Outputs to retain:** `.mat` transform, fixed-reference identifier/hash, parameters/software version, runtime/memory, initial/final registration metric, QC review, ROI coordinates, source hash.
- **Do NOT retain:** 1,689 fully warped full-resolution images. Delete temporary 2 mm images/warped outputs only after validating outputs.

## Candidate command (not tested against HCP files)

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
| REG-01 | 1 synthetic 3D image + landmark points | Forward/inverse mapping error within declared numeric tolerance | NOT RUN |
| REG-02 | 20 pilot T2 scans | No unreviewed gross midline/frontal-horn misalignment | NOT RUN |
| REG-03 | Same input twice with pinned seed/settings | Transform differences within declared tolerance | NOT RUN |
| REG-04 | No-reg vs rigid | Report crop coverage, failure rate and wall time; no automatic assumption of superiority | NOT RUN |
| REG-05 | Runtime/memory measurements | All 20 logged; failures diagnosed | NOT RUN |

**Pilot decision gate:** do not approve bulk registration before reviewing all 20. If a landmark-based coarse locator is consistently as accurate and much faster, record the evidence and choose it instead of ANTs.
