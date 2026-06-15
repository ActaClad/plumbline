<!-- Thanks for contributing to Plumbline! Keep diffs small and reviewable. -->

## What this changes

<!-- One or two sentences. Link the issue it closes, e.g. "Closes #123". -->

## Type

- [ ] New rule
- [ ] Bug fix / false-positive fix
- [ ] Framework adapter
- [ ] Engine / core
- [ ] Docs only

## Checklist

- [ ] `pytest`, `ruff check .`, and `mypy src` all clean
- [ ] **Determinism:** no network, clock, or randomness in the detection path
- [ ] All commits are **signed off** (`git commit -s`) — DCO
- [ ] An **ADR** was added under `docs/adr/` if a non-trivial decision was made

### If this PR adds or changes a rule

- [ ] Detector module under `src/plumbline/rules/<category>/`
- [ ] A **failing fixture** (`fixtures/<RULE_ID>/bad_*.py`) that MUST trigger
- [ ] A **passing fixture** (`fixtures/<RULE_ID>/good_*.py`) that MUST NOT trigger
- [ ] A test asserting both
- [ ] Confidence justified — **High requires a measured precision number in `/benchmark`**
- [ ] Standards mapping added (OWASP / NIST / CWE) or explicitly "none"
- [ ] `docs/specs/rule-catalog.md` (and `docs/standards-map.md` if mapped) updated

## Notes for the reviewer

<!-- Anything non-obvious: tradeoffs, why dataflow vs. structural, edge cases. -->
