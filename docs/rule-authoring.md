# Rule Authoring Guide

A practical, copy-this walkthrough for adding a rule. The formal contract is in
`specs/rule-plugin-contract.md`; this is the "just show me" version.

## The 5-minute mental model

A rule answers one question about agentic code that can be decided **from the
code alone, deterministically**. If answering it needs runtime data, it belongs
in Phase 2 (trace integration), not here — note it in `backlog.md`.

## Steps

1. **Claim an ID.** Pick the next free `PLB-<CAT>-<NNN>` in your category
   (categories: RES, AGT, MDL, OUT, TOOL, RAG, PRM, EVAL, OBS, COST, SEC, GOV).
   Confirm it's listed (or add it) in `specs/rule-catalog.md`.

2. **Decide severity and confidence honestly.**
   - Will a false positive break someone's CI? Then it's not High.
   - Severity = blast radius if the defect ships (Blocker = takes the service
     down / is directly exploitable; down to Info = awareness only).

3. **Copy the nearest existing rule** in the same category as your skeleton —
   module + fixtures + test. Don't start from scratch.

4. **Write the failing fixture first** (`fixtures/PLB-XXX-NNN/bad_*.py`). Make it
   realistic framework code. Then the clean one (`good_*.py`).

5. **Write the detector.** Consume `ctx.framework` (normalized tags) and
   `ctx.taint` (dataflow) — avoid re-parsing or regexing raw source unless the
   rule is genuinely a pattern rule. Keep it pure.

6. **Write the test.** bad→fires, good→silent, plus the edge cases that worry
   you. Run `pytest` on just your test.

7. **Eyeball real output:** `plumb scan fixtures/PLB-XXX-NNN/bad_example.py`.
   Is the message clear? Is the fix actionable? Would *you* act on it?

8. **Update docs:** `rule-catalog.md` (if new), `standards-map.md` (mapping +
   later the precision number).

9. **ADR?** Only if you made a non-trivial *design* decision (a new taint
   source category, a scoring change, a contract tweak). A normal rule needs no
   ADR.

## Quality bar (what reviewers check)

- Deterministic: no I/O/clock/network/randomness in `detect`.
- Has bad + good fixtures; test proves both.
- Confidence justified; High needs a precision number.
- "why_it_matters" names a concrete production failure, not an abstraction.
- Remediation has a bad and a good example and stands alone without the AI layer.
- Message points at the exact line and is specific.

## Anti-patterns to avoid

- A rule that fires on idiomatic, correct framework usage (noisy → uninstalled).
- "Security theater" rules that restate OWASP without a real code signal.
- Rules that need cross-module dataflow before the engine supports it — defer.
- Bundling several checks into one rule — one rule, one question.
