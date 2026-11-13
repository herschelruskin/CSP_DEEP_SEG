# Current handoff — CSP_DEEP_SEG

**Updated:** 2026-11-13  
**Purpose:** Small, current, independently usable project-state summary for starting a fresh chat. Rewrite after each milestone. Keep history in dated `tracking/handoffs/` files.

## Repository and project scope

- Repository: https://github.com/herschelruskin/CSP_DEEP_SEG
- Branch: `main`. **At the next chat start, fetch HEAD; do not rely on the SHA from this snapshot after further commits.**
- Long-term goal: Automated, anatomically defensible CSP segmentation in high-resolution T2 MRI, later adaptable to other cohorts.
- Immediate course horizon: CPS 843 **preliminary proof of concept** due in December 2026 according to supplied guidelines; **not** the long-term project's endpoint.
- Workflow: 1 extraction/QC → 2 rigid registration → 3 CSP ROI localization; 4 manual labels in parallel; then 5 models → 6 training → 7 independent validation.

## State of evidence

- **USER-REPORTED:** HCP Young Adult T2 images extracted from ZIPs on a Windows local drive, totaling **1,689 acquisitions**, all 0.7 mm isotropic; some subjects have `SPC1` and `SPC2` scans. Number of distinct participants has **not** been independently reconciled. Do not treat 1,689 as independent subjects.
- **USER-REPORTED / PRELIMINARY:** One T2 example (subject 100206) was visually reviewed and appeared suitable for identifying a septal cavity after display windowing; no validated segmentation from that observation.
- **POLICY:** For initial POC, provisionally rely on HCP release-level MRI QC, plus automated file/geometry checks, 20–30 registration/ROI pilot checks and targeted label QC; do not manually review all participants.
- **DESIGN PROVISIONAL:** Low-resolution (~2 mm) rigid alignment (ANTs candidate) against a stable T2 reference, compared to simpler affine-only crop placement. Map ROI to native 0.7 mm T2 using physical transforms; avoid full-brain registered image copies.
- **NOT IMPLEMENTED / NOT RUN:** Rigid registration, cropped ROI, manual reference mask set for this project, model training, Dice evaluation and full NIfTI integrity audit.
- **ANNOTATION PLAN, NOT COMMITMENT:** Approximately 120 manually labeled subjects is a research planning target, not a course POC gate; write a formal anatomical labeling SOP and lock subject/family-disjoint splits.

## Next bounded workstream: Stage 2 registration pilot

1. Inspect actual local T2 manifest or ask user to provide a small de-identified sample/summary; reconcile unique subject count and scan names, check manifest geometry and missing/corrupt-file indicators.
2. Select/version the fixed T2 reference and 20-acquisition pilot list. Design comparison: affine-only ROI vs 6-DOF ANTs rigid registration on temporary ~2 mm images. Preserve native inputs.
3. Implement a minimal reproducible registration runner and forward/inverse coordinate test, then validate on accessible pilot data. Record command, ANTs version, runtime, failures and crop coverage. **Do not report successful execution until measured.**

## Local environment constraints

- HCP data are stored on the user's Windows PC in the `D:\CSP_DEEP_SEG\` hierarchy (e.g., `T2w\`). These images are not in GitHub or necessarily accessible in ChatGPT runtime.
- Public GitHub must hold code, documentation, configs and aggregate non-sensitive evidence only; do not upload raw NIfTI volumes, masks or HCP ZIPs.
- Windows GPU reportedly RTX 2060 Super (8 GB); Stage 2 rigid ANTs is CPU-bound. Alliance/Compute Canada is optional after local benchmark.

## Research records and operating rules

- Read `AGENTS.md`, `docs/CHAT_CONTINUITY.md`, `docs/SEVEN_STAGE_PROCESS.md`, `docs/REGISTRATION_PILOT.md`, `tracking/PROGRESS.md` and `tracking/DECISIONS.md`.
- Re-verify current GitHub commits, actual file contents and test logs rather than trusting this prose if contradicted by newer evidence.
- Keep exchanges **piece by piece**, shard early, and update this handoff plus progress tracking before changing chats.
- Decision register through **D-010**: T2-only, provisional rigid approach and downsampling, native ROI, baselines, tentative manual-label target, data restrictions, pragmatic QC, course-vs-research separation, POC-first approach.

## Ready-to-copy next-chat prompt

Continue **CSP_DEEP_SEG** using https://github.com/herschelruskin/CSP_DEEP_SEG. First inspect **AGENTS.md**, **tracking/HANDOFF.md**, **tracking/PROGRESS.md**, and **tracking/DECISIONS.md**, verify current GitHub HEAD, then execute only the next bounded Stage 2 pilot task. Keep all claims evidence-based, keep the December 2026 course project separate from long-term research scope, log changes/tests to GitHub and produce an updated Markdown handoff before the chat becomes too long.
