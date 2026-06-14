# ADR-0014 — Finding code-flow (taint witness paths)

- **Status:** Accepted
- **Date:** 2026-06-14
- **Deciders:** ActaClad founding team
- **Amends:** ADR-0002 (adds one optional field to `Finding`/`FindingDraft`)

> ADRs are immutable once Accepted. To change a decision, write a new ADR that
> supersedes this one.

---

## Context

ADR-0006 D3 already promises that "taint-rule witness paths are emitted as
`codeFlows`" in SARIF, but the implementation was deferred (M1 backlog: "until
the first taint-based rule that wants it — M6 SEC rules"). M6's security rules
are taint source→sink rules whose whole value is *showing the path* (untrusted
source → … → dangerous sink). The taint engine computes a witness per
`(node, label)` (`TaintView.witness`), but `Finding` (ADR-0002) carries no field
to hold it, and `Finding`'s field set is a fixed public contract. So surfacing
witnesses needs a schema extension — hence this ADR.

## Decision

### D1 — One optional `code_flow` field on `Finding` and `FindingDraft`

```python
@dataclass(frozen=True, slots=True)
class CodeFlowStep:
    file: str            # POSIX-relative
    line: int
    column: int | None
    message: str         # e.g. "USER_INPUT via parameter 'q'"

# Finding / FindingDraft gain:
    code_flow: tuple[CodeFlowStep, ...] = ()   # source → … → sink; empty for non-taint rules
```

`code_flow` is ordered source-first, sink-last. It is optional and defaults to
empty: every existing rule and the whole non-taint path are unaffected. Taint
rules populate it from `TaintView.witness` via a shared helper.

### D2 — `code_flow` is EXCLUDED from the fingerprint

`compute_fingerprint` stays `(rule_id, file, normalized-anchor, ordinal)` —
unchanged. The witness path must never enter the fingerprint: taint propagation
can shift the path without the defect changing, and a fingerprint that moved
with the witness would churn every baseline on every engine tweak. A test
asserts a finding's fingerprint is identical with and without a `code_flow`.

### D3 — SARIF emission

`Finding.code_flow`, when non-empty, becomes one `result.codeFlows[0]
.threadFlows[0].locations[*]` entry (one threadFlow; each step a `location` with
`physicalLocation` + `message`). Order is the `code_flow` tuple order, which the
taint engine already makes deterministic (lexicographically-first witness per
label, ADR-0003 D5) — the reporter does not re-sort. Empty `code_flow` ⇒ no
`codeFlows` key (byte-stability preserved).

## Consequences

- `Finding`/`FindingDraft` grow exactly one optional, defaulted field; the
  change is additive and back-compatible (ADR-0002's "exact fields" is amended,
  not broken — recorded here per CLAUDE.md §4).
- The contract change is provable in isolation by retrofitting the existing
  taint rule **OUT-001** with a witness, before any SEC rule exists.
- SARIF consumers (GitHub code scanning) render the source→sink path for taint
  findings; baselines remain stable because fingerprints ignore the path.
