# Issues, blockers and assumptions

| ID | Severity | State | Issue | Action / closure evidence |
|---|---|---|---|---|
| I-001 | High | PARTIALLY CLOSED | CSV/Google Sheets filename census reconciled: 1,689 acquisitions, 1,113 unique subject IDs, 576 extra acquisitions | Distinct scan keys verified from filename manifest; whole-file integrity and cohort eligibility still separate |
| I-002 | High | OPEN | Real-data archive/NIfTI full integrity QC not confirmed | Test ZIP MD5 where available, gzip/pixel decoding; log failure cases |
| I-003 | High | OPEN | Operational CSP posterior/anterior anatomical stopping rules not frozen | Version manual SOP and examples before creating reference masks |
| I-004 | Medium | OPEN | No stable T2 template chosen or fixed reference version; raw-T2 baseline may avoid registration | Compare fixed crop against learned anatomical locator; use registration only if helpful |
| I-005 | High | OPEN | User-reported two-subject ANTs transform does not establish numerical round-trip or crop-to-native accuracy | Run synthetic landmark and masked-crop coordinate round-trip tests, verify Slicer geometry |
| I-006 | High | OPEN | Intersubject ventricular differences may exceed rigid + fixed ROI | Measure full reference mask containment and margins; adaptive fallback |
| I-007 | High | OPEN | HCP families/relatedness may cause train-test leakage | Acquire permissible family metadata or disclose limitation; never split repeat scans |
| I-008 | Medium | OPEN | CSP tiny-object class imbalance / absent-case evaluation | Define loss and metric policies before model selection |
| I-009 | Medium | OPEN | Initial ≥20 manual subjects USER-REPORTED (Nov 17); current saved and QC-pass count not audited; ~50 pragmatic next target; 120 longer-term planning only | Audit mask paths, geometry, empty masks, ambiguous/QC masks and actual current count |
| I-010 | Medium | OPEN | Course deadline reported as both Dec 14 and Dec 16 | Use written Dec 14 date until confirmed otherwise |

| I-011 | High | OPEN | Inferior septal/ovoid-looking cavities and questionable fornix boundaries seen repeatedly on native T2; no frozen triangular-only segmentation SOP | Retain original masks, set Needs review, adjudicate a small reference set and freeze inclusion/exclusion landmarks before fine-mask training |
| I-012 | High | OPEN | No reliable full-CSP crop-containment report; fixed two-case ROI appeared overlarge and intersubject anatomy varies | Implement anatomical midline ROI then report full-mask inclusion and margin; test learned coarse anatomical localizer as alternative |
| I-013 | High | OPEN | Only one absent subject among the initial 20 reported labels; absent-case specificity cannot be credibly estimated | Continue representative annotation, retain true absent and uncertain categories, define negative-case evaluation separately |
| I-014 | High | OPEN | No complete native-mask file inventory, locked subject/family partition or ground-truth geometry audit | Produce private mask census with shape/affine match, QC flags and frozen split hashes |
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
