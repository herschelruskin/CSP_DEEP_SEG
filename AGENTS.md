# CSP_DEEP_SEG — instructions for AI coding/research assistants

**Purpose:** Persistent, repository-backed operating instructions. Read before proposing edits or running analyses. These instructions cover both the CPS 843 proof of concept and the longer-term research project.

## At the start of every new chat or working session

1. Fetch and read **this `AGENTS.md`**, **`tracking/HANDOFF.md`**, **`tracking/PROGRESS.md`**, **`tracking/DECISIONS.md`**, and relevant stage documentation (particularly `docs/SEVEN_STAGE_PROCESS.md`).
2. Confirm the **actual GitHub default-branch HEAD** and inspect relevant files before changing code or assuming anything described in a previous chat was committed.
3. Summarize in 2–4 sentences: the immediate objective, verified current state, unresolved blockers, and next reproducible action.
4. Check **conversation continuity** using `docs/CHAT_CONTINUITY.md`. Do not claim access to a numerical context-window utilization, internal chat-health score, or automatic thread creation.
5. Prefer one bounded implementation/experiment goal per chat. If a thread becomes sprawling, **handoff early**, then start a fresh chat using the copyable boot prompt in `tracking/HANDOFF.md`.

## Evidence and scientific integrity

- Do not reconstruct code, test data, results, plots or completed analyses from conversational memory.
- Treat **USER-REPORTED**, **IMPLEMENTED-UNVERIFIED**, **VERIFIED**, **FAILED** and **PLANNED** as distinct statuses; see `docs/PROJECT_CONTROLS.md`.
- Before claiming a result, inspect relevant scripts/commit, input and split manifests, command/config, output file and logs. No invented times, Dice scores, QC passes or hardware benchmarks.
- Keep native NIfTI image/mask spatial geometry intact; preserve originals and transforms; do not insert MRI files or restricted outputs in Git.
- Repeated acquisitions of one subject stay in one split, and HCP family links should remain together when available. Final test data are not for tuning.
- The December 2026 CPS 843 deadline is a **proof-of-concept checkpoint**; the research itself continues. Favor a minimal defensible pipeline now, extensibility later.

## How to work

- Propose a small bounded change with explicit assumptions and expected tests. Avoid redesigning all seven stages at once.
- Run or request the smallest meaningful verification; label unrun checks **NOT RUN**. Never turn a suggested command into an alleged executed experiment.
- Record important scope/method changes in `tracking/DECISIONS.md` and evidence in `tracking/TEST_LOG.md` or `tracking/EXPERIMENTS.md`.
- At each substantive milestone, update `tracking/PROGRESS.md` **and `tracking/HANDOFF.md`** with exact file paths, Git refs, tests, blockers and next steps.
- When working on GitHub, fetch current contents and SHA before replacing files; avoid overwriting concurrent work. Confirm updates by reading files back.
- Do not assume Windows paths under `D:\CSP_DEEP_SEG` are accessible from the current tool/runtime; they describe the user's local machine, not files in the repository.
- Be concise in conversational responses. Discuss implementation piece by piece as requested rather than launching later stages prematurely.

## Early-sharding rule

**Continuity beats thread length.** At a major decision, a stage boundary, a significant debugging detour, after roughly 10–20 substantive exchanges, or if information must be repeatedly recovered, stop and produce a verified handoff before opening a fresh chat. This is a planning heuristic, **not** a measurement of context capacity.

The handoff must be independently sufficient: current goal, tested vs untested facts, repo commit, exact files changed, experiments and failures, pending decisions, next command/test and relevant local-only prerequisites. See `docs/CHAT_CONTINUITY.md`.

## Current pointers

- Seven stages: `docs/SEVEN_STAGE_PROCESS.md`
- Two-horizon roadmap: `docs/ROADMAP.md`
- Registration pilot: `docs/REGISTRATION_PILOT.md`
- Latest continuity snapshot: `tracking/HANDOFF.md`
- Research progress: `tracking/PROGRESS.md`
- Methods decisions: `tracking/DECISIONS.md`
