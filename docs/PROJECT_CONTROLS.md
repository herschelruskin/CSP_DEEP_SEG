# Research documentation rules

## Chat continuity and repository-backed handoffs

Treat GitHub as the durable state, not a long-lived chat transcript. At the start of each work session read [../AGENTS.md](../AGENTS.md), [../tracking/HANDOFF.md](../tracking/HANDOFF.md) and the progress/decision logs. After major results or methodological changes, update the living handoff and progress log and commit a dated snapshot if warranted. Shard early on stage boundaries, ambiguous state, or a long/multi-branch conversation. The assistant can make a qualitative continuity check but **cannot measure a numerical context-health percentage**; see [CHAT_CONTINUITY.md](CHAT_CONTINUITY.md).

## Evidence levels

- `PLANNED`: not implemented or tested.
- `IMPLEMENTED-UNVERIFIED`: code exists; limited or no real-data validation.
- `OBSERVED/USER-REPORTED`: supplied in discussion/screenshots/outputs; not necessarily reproducibly verified in this repo.
- `VERIFIED`: linked code commit + complete command + dated inputs/config + output artifact + test log.
- `FAILED`: legitimate test executed and failed; keep failure evidence.

A passing synthetic test is never proof that real HCP files pass. A scanner display adjustment is not an intensity preprocessing step. A model-generated label is not a manual ground truth mask.

## File and version rules

- Every run gets `RUN-YYYYMMDD-NNN`; every test gets a stable `DATA/REG/ROI/ANN/MOD/TRN/VAL-XX` identifier.
- Log **source SHA256, subject/scan key, code commit, config hash, command, software versions, output hash and result**. Local private manifests may include HCP IDs; public logs should use aggregates or nonidentifying run IDs until data-use restrictions are reviewed.
- Each method change must reference an entry in `tracking/DECISIONS.md`, a rerun/test and updated protocol version if it changes definitions or results.
- Do not silently overwrite an analysis run. Use immutable run directories and clearly identify superseded outputs.
- Keep native geometry/units; for masks use nearest-neighbor interpolation only if a mask must be resampled.
- Store each dataset split as an immutable, hashed private manifest before training.

## Project horizons and course reporting constraints

**CSP_DEEP_SEG is a long-term research project, not a project that ends with the class.** The December 2026 submission is one checkpoint. The user-supplied CPS 843/CP 8307 instructions require IEEE double-column, **4–6 pages excluding references**, a code link at the end of the abstract, and deadline **2026-12-14 23:59**. The separate reported December 16 date is unverified. Report the strongest validated work actually available by that deadline; do not manufacture results, relax independent-test rules, or declare incomplete research phases finished to satisfy the course milestone. A baseline and U-Net comparison is a *candidate* course scope, not a mandatory shortcut or the final research endpoint.

The long-term research roadmap retains anatomically defensible labels, scalable cross-dataset localization, model comparisons, independent evaluation, failure analysis, and future external validation. See [ROADMAP.md](ROADMAP.md). The final course report is **not** this protocol and **not** the terminal project report.

## Data and access

Public GitHub must contain **code, README, documentation, synthetic tests and aggregate non-sensitive results**, not source T1/T2 NIfTI, HCP ZIPs, patient-level masks, pseudo-label volumes, model weights derived from restricted data unless terms are checked, credentials, access tokens or raw identifiers beyond documented public example IDs. Use HCP's official data-use terms. Do not upload private scanner metadata if it includes identifying fields.
