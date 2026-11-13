# Issues, blockers and assumptions

| ID | Severity | State | Issue | Action / closure evidence |
|---|---|---|---|---|
| I-001 | High | OPEN | 1,689 T2 acquisitions reported, unique-subject count not verified | Reconcile `SPC1`/`SPC2` by subject and document exclusions |
| I-002 | High | OPEN | Real-data archive/NIfTI full integrity QC not confirmed | Test ZIP MD5 where available, gzip/pixel decoding; log failure cases |
| I-003 | High | OPEN | Operational CSP posterior/anterior anatomical stopping rules not frozen | Version manual SOP and examples before creating reference masks |
| I-004 | Medium | OPEN | No stable T2 template chosen or fixed reference version | Compare reference candidates; record fixed image SHA |
| I-005 | High | OPEN | Transform direction and physical-space ROI mapping untested | Synthetic landmark round-trip, verify against 3D Slicer |
| I-006 | High | OPEN | Intersubject ventricular differences may exceed rigid + fixed ROI | Measure full reference mask containment and margins; adaptive fallback |
| I-007 | High | OPEN | HCP families/relatedness may cause train-test leakage | Acquire permissible family metadata or disclose limitation; never split repeat scans |
| I-008 | Medium | OPEN | CSP tiny-object class imbalance / absent-case evaluation | Define loss and metric policies before model selection |
| I-009 | Medium | OPEN | 120 manual labels are a target, not achieved data | Record annotation throughput, errors and QC before revising goal |
| I-010 | Medium | OPEN | Course deadline reported as both Dec 14 and Dec 16 | Use written Dec 14 date until confirmed otherwise |

## New issue template

```text
ID / severity / owner / opened:
Reproduction steps and affected scan count:
Observed behavior vs expected:
Consequence for scientific validity:
Workaround or corrective action:
Linked tests, code changes, decision IDs:
Closure evidence / date:
```
