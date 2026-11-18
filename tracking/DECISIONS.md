# Decision register

Log every scientific or engineering choice and link to confirming tests. Update status when subsequent evidence changes a decision.

| ID | Date | Decision | Rationale | Alternatives / risks | Evidence/status |
|---|---|---|---|---|---|
| D-001 | 2026-11-13 | Start with **T2 only** | CSP CSF appears relatively bright on T2; avoids T1/T2 registration burden | Multimodal T1+T2 might improve specificity | PLANNED; subject 100206 visually inspected only |
| D-002 | 2026-11-13 | Use **rigid 6-DOF reference alignment** initially | Consistent head pose across datasets without deformation | Fixed ROI from native affine may suffice; ANTs may cost unnecessary runtime | PROVISIONAL; compare both in pilot |
| D-003 | 2026-11-13 | Perform registration on temporary **~2 mm** images | Coarse anatomy sufficient for initial ROI placement and faster CPU registration | Downsampling too aggressively may reduce ventricular alignment | PROVISIONAL; benchmark 2 mm vs a fallback resolution if needed |
| D-004 | 2026-11-13 | Segment **native-resolution 3D ROI** | Tiny CSP requires high-resolution boundary information; avoid storing many whole-brain resamples | Crops could omit unusual cavities | PROVISIONAL; measure full mask containment |
| D-005 | 2026-11-13 | Build **small 3D U-Net** before lightweight attention hybrid | Scientifically meaningful baseline, limited labels and compute | Attention may offer benefit, but not assumed | PLANNED |
| D-006 | 2026-11-13 | Target **~120 manual masks**, subject/family controlled | Feasible annotation throughput reported; stronger train/val/test coverage than a tiny set | Annotation QC time and ambiguous anatomy; number not statistically optimized | PLANNED, adapt to pilot |
| D-007 | 2026-11-13 | Keep raw HCP images out of public Git | Data-use terms, storage and reproducibility separation | External storage requires durable manifest/hashes | ACTIVE POLICY |
| D-008 | 2026-11-13 | **Defer comprehensive manual MRI QC** in first pass; use HCP release QC as provisional baseline plus programmatic file/geometry checks, pilot ROI inspection, and review of annotation cases | ~1,100 unique subjects are infeasible to inspect individually under the first-pass timeline | HCP release does not guarantee local CSP quality; subtle motion, contrast and ROI failures may remain undetected | ACTIVE FIRST-PASS POLICY; flag failures, revisit QC if observed issues or evaluation patterns indicate need |
| D-009 | 2026-11-13 | Treat the **December 2026 CPS 843 submission as an interim milestone**, not CSP_DEEP_SEG's end date | Project is intended as a longer-term, potentially thesis/publication-grade research effort; methods and independent evaluation should outlast class deadlines | Limited first-pass deliverables may not yet establish full generalization or publication readiness | ACTIVE SCOPE POLICY; document verified course results separately from longer-term milestones |

| D-010 | 2026-11-13 | Prioritize a **minimal, scientifically defensible proof of concept** for the course, deferring general-purpose tooling, external-cohort robustness and optional architectural complexity | First-pass deadline is tight; demonstrate a working validated method before expanding scope | A preliminary POC cannot establish publication-level accuracy or cross-dataset generalization | ACTIVE; see `docs/ROADMAP.md`, continue development beyond course milestone |
| D-011 | 2026-11-13 | Require **early chat sharding with GitHub-backed Markdown handoffs and explicit continuity checks** | Long conversations can lose decisions or obscure verification; persistent code/docs are more reliable than remembered chat summaries | No numerical chat-health metric or automatic new-thread creation available; procedure depends on periodic reviews and commits | ACTIVE; `AGENTS.md`, `docs/CHAT_CONTINUITY.md`, `tracking/HANDOFF.md` |

## Updates as of 2026-11-18 — superseding first-pass decisions

These decisions refine the first-course-POC scope; the original entries above remain as historical design decisions. **D-002** is now a *candidate comparator* rather than a required preprocessing stage; **D-005** is deferred behind a simpler 2.5D baseline; **D-006** (~120 labels) is retained only as a longer-term, adaptable research target, not the first model gate.

| ID | Date | Decision | Reason | Alternatives / limitations | Status |
|---|---|---|---|---|---|
| D-012 | 2026-11-18 | **Triangular CSP only** for initial class-project masks; record Present/Absent/Uncertain, mask completion and QC | Avoid heterogeneous labeling of oval/fornix-adjacent cavities before anatomic SOP established | Unresolved inferior and anterior/posterior boundaries; collect uncertain cases for adjudication | ACTIVE POC POLICY; SOP not frozen |
| D-013 | 2026-11-18 | **SPC1 per subject** in active manual-label queue; archive other acquisitions | 1,689 scans yield 1,113 unique subject IDs; avoid wasting labeling on repeats in first pass | Replace with SPC2 when SPC1 fails QC; repeats valuable for later reproducibility; family grouping still pending | IMPLEMENTED IN GOOGLE SHEETS, source scans retained |
| D-014 | 2026-11-18 | **20 masks can support a toy/model smoke test**, ~50 a practical next first-pass target; expand beyond as resources permit | Begin learning about pipeline and failure modes now while labels accumulate | 19 positive/1 absent at reported checkpoint means specificity poorly estimated; no guaranteed performance threshold | PLANNING, NOT VALIDATION |
| D-015 | 2026-11-18 | **No-registration raw-T2 septal crop + compact 2.5D U-Net first** | Parsimonious laptop-friendly data-prep and RTX 2060 Super training path; avoids preprocessing dependencies | May miss variable anatomy; must quantify complete-cavity coverage | SELECTED INITIAL BASELINE; NOT TRAINED |
| D-016 | 2026-11-18 | Compare **learned coarse anatomical-region localizer → high-resolution segmenter** against the fixed-crop baseline | Coarse stage can use ventricular/midline context and localize expected septal area even when tiny CSP absent | Small training dataset and missed ROI risk; train with anatomical-region targets, test whole-mask containment | PLANNED COMPARATIVE ARCHITECTURE |
| D-017 | 2026-11-18 | **Do not require ANTs registration, full FreeSurfer or SynthSeg** before testing raw-T2 baseline | Two-case rigid alignment cannot remove substantial intersubject ventricular differences; processed HCP labels may not align to raw T2 | Landmark/rigid/affine localization retained as ablations if simpler approach fails | CURRENT POC POLICY; 20-case pilot still not complete |
| D-018 | 2026-11-18 | Preserve ambiguous inferior/ovoid/fornix-related masks as **Needs review** rather than labeling as definite triangular CSP or true absence | Repeated difficult T2 anatomy; vertical location or disconnected slice shape cannot independently determine CV vs CSP | Needs consistent SOP, slice-wise 3-plane verification and ideally expert adjudication | OPEN LABELING RISK |

## New decision template

```text
ID: D-###  Date: YYYY-MM-DD  Owner:
Question:
Chosen action:
Alternatives considered:
Evidence/test IDs:
Expected benefit and tradeoffs:
Criteria to revisit:
Code/config/protocol version:
```
