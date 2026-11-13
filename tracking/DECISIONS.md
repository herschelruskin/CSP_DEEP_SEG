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
