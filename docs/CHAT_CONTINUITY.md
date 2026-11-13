# Chat continuity, early sharding and verified handoffs

**Policy:** Prefer short, self-contained chats over one massive conversation. Preserve *project state* in versioned Markdown and code, not in a model's chat memory. **There is no reliable numerical chat-health meter available to the assistant.** Use the qualitative checks below, and shard proactively.

## Three-part continuity check (at the start and end of work, and after complex tool runs)

1. **Recoverability:** Could a fresh assistant, with GitHub access but no previous chat, know the exact next action from the README, `AGENTS.md`, `tracking/PROGRESS.md` and `tracking/HANDOFF.md`?
2. **Verification:** Is each claimed completion supported by a GitHub commit and/or a saved test/run record? Are local-only files and outstanding tests clearly identified?
3. **Scope:** Are we still performing one bounded task, or is the discussion drifting into a different stage or accumulating unresolved alternatives?

**Green:** current files/commit/recent tests are known; one bounded goal.  
**Amber:** many branches or hypotheses, changing assumptions, unresolved evidence, several tool/debug loops. Update handoff and consider moving.  
**Red:** uncertainty about last commit/output, forgotten tests, contradictions, inaccessible prior artifacts, repeated attempts to recover context. Stop substantive edits, inspect the repository, reconstruct the facts, write a handoff and start a new chat.

These indicators are **operational heuristics**, not actual model context occupancy.

## When to shard

- After any stage milestone, significant design decision or working experimental result.
- Before starting a new workstream (e.g., moving from rigid registration to localization or model training).
- After approximately **10–20 substantive exchanges** if work remains ongoing, **earlier** when complexity is high.
- As soon as there are contradictory assumptions, tool limitations or repeated context-recovery requests.
- Before a large edit/long debugging session if the new work can be isolated.

Do **not** force a shard during a brief, coherent exchange; use judgment. A new chat requires the user to open it; the assistant must not claim it can automatically open or monitor threads.

## Handoff preparation (mandatory before each deliberate shard)

1. Read the latest GitHub README/AGENTS/protocol/progress/decision log and confirm repository/branch and HEAD.
2. Distinguish **verified** outcomes from **reported**, **proposed** and **not run**. Include failed tests and caveats; no result should rely only on an unverified previous-chat assertion.
3. Update `tracking/HANDOFF.md` (the *single current* handoff) and `tracking/PROGRESS.md`.
4. Make a dated, immutable Markdown snapshot in `tracking/handoffs/YYYY-MM-DD-topic.md` for nontrivial milestones. Link the code commit(s), commands, files changed, run IDs and issue IDs. Do not include medical data, PHI or large outputs.
5. Commit the handoff and verify GitHub returns the expected content.
6. Give the user a short copy/paste **new-chat boot prompt** referencing `AGENTS.md` and `tracking/HANDOFF.md`. Do not depend on lengthy pasted recollections alone.

## Minimum handoff schema

```markdown
# Handoff — YYYY-MM-DD / topic
Repository: https://github.com/herschelruskin/CSP_DEEP_SEG
Branch + verified HEAD: <sha; label unverified when unknown>
Objective of next chat:
Project horizon: CPS 843 POC / long-term research
Last verified state:
User-reported or still-unverified state:
Changed files and commits:
Tests/run records (including FAIL and NOT RUN):
Open issues / decisions:
Local-only dependencies (paths are *not* GitHub attachments):
Next three precise actions:
Do-not-assume / hazards:
```

## Boot prompt for a new chat

> Continue CSP_DEEP_SEG from https://github.com/herschelruskin/CSP_DEEP_SEG. **First fetch AGENTS.md, tracking/HANDOFF.md, tracking/PROGRESS.md, tracking/DECISIONS.md and relevant stage docs from GitHub; verify current HEAD.** Treat GitHub and logged test artifacts as the source of truth, not an earlier chat's remembered claims. Work on the single next task specified in the handoff, report what is verified versus planned, update GitHub tracking after meaningful progress, and make a fresh Markdown handoff **early** if the thread grows. The December CPS 843 deadline is only an interim POC milestone.

## What not to do

- Do not state a numeric health percentage, available-token count or guarantee that context is safe.
- Do not claim updates, code, data, QC or metrics exist without inspecting actual files.
- Do not append huge unstructured transcript dumps to `tracking/HANDOFF.md`; the handoff should be compact and operational.
- Do not carry over obsolete assumptions when newer committed evidence contradicts them.
