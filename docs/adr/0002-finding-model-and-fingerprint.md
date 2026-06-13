# ADR-0002 — Finding data model, fingerprint algorithm, and determinism strategy

- **Status:** Accepted
- **Date:** 2026-06-10
- **Deciders:** ActaClad founding team
- **Supersedes:** none

> ADRs are immutable once Accepted. To change a decision, write a new ADR that
> supersedes this one. Number ADRs sequentially. Keep them short.

---

## Context

`architecture.md` §2 sketches the Finding model and requires a `fingerprint`
that is "stable across runs given the same code" for SARIF baselining,
suppression, and determinism testing. It does not specify the fingerprint
algorithm, the concrete Python types, or how determinism is enforced and
tested. The Finding schema is a public contract (CLAUDE.md §4), so these
choices must be recorded before M0 implements `model.py`.

## Decision

### D1 — Types

`model.py` contains only pure data, no behavior beyond construction helpers:

- `Severity`, `Confidence`, `Pillar` are `enum.IntEnum`-backed enums with
  explicit ordinal values so ordering and gate comparisons are total and
  deterministic: `Blocker=50, Critical=40, Major=30, Minor=20, Info=10`;
  `High=3, Medium=2, Low=1`. `Pillar` members: `RELIABILITY, ARCHITECTURE,
  HARNESS, SECURITY`, each with a `display` string ("Architecture & Agentic
  Maturity", "Harness Engineering", …).
- `Finding` is a **frozen dataclass** with exactly the fields in
  `architecture.md` §2. `file` is stored **relative to the scan root, with
  POSIX separators**, so output is machine-independent. `line`/`end_line`
  are 1-based; `column` is 0-based internally (Python `ast` convention) and
  converted to 1-based only at the SARIF boundary (ADR-0006).
- Findings carry **effective** severity/confidence (after any `.plumbline.toml`
  per-rule override, ADR-0007). The rule's defaults remain available via the
  rule registry; reporters that need both read the registry.

Rejected: Pydantic models (a runtime dependency the detection path does not
need; `dataclasses` + `mypy --strict` give the same safety), and mutable
findings (mutation after creation is how nondeterminism sneaks in).

### D2 — Fingerprint algorithm (v1)

The fingerprint must survive *unrelated* edits (a baseline must not churn when
line numbers shift) and must distinguish *identical* defects that occur twice.
Line numbers are therefore **excluded** from the hash. Algorithm:

```
anchor  = source text of the smallest statement containing the finding's
          primary node, whitespace-normalized (runs of whitespace → single
          space, stripped)
k       = 0-based ordinal of this finding among findings with the identical
          (rule_id, file, anchor) key, ordered by (line, column)
payload = rule_id + "\0" + file + "\0" + anchor + "\0" + str(k)
fingerprint = sha256(payload.encode("utf-8")).hexdigest()[:16]
```

The algorithm is versioned **externally**: the SARIF `partialFingerprints` key
is `plumblineFingerprint/v1` and the baseline file records `"algorithm": "v1"`
(ADR-0006). Changing the algorithm is a new ADR and a `v2` key.

Properties: stable under edits elsewhere in the file; stable under
reformatting that does not change the statement's tokens' spelling beyond
whitespace; changes when the file is renamed (accepted — regenerate the
baseline) or when the flagged statement itself is edited (correct — it is a
different occurrence).

Rejected alternatives: line-number-based hashes (churn on every unrelated
edit — the failure mode that makes teams abandon baselines); SARIF's
`primaryLocationLineHash` alone (same problem); full-AST structural hashing
(more machinery for marginal gain; revisit only if the anchor approach proves
unstable in practice).

### D3 — Determinism strategy (engine-wide invariants)

1. File discovery yields paths sorted lexicographically (bytewise on the
   POSIX-relative path).
2. Findings are deduplicated by fingerprint, then sorted by
   `(file, line, column, rule_id, fingerprint)` before scoring/reporting.
3. No detector, adapter, or core component may iterate an unsorted `set`/`dict`
   when the iteration order can reach output; helpers in the engine expose
   sorted views.
4. No wall-clock, network, randomness, environment-variable, or locale
   dependence anywhere in the detection path. SARIF output omits timestamps
   (they are optional in the schema) so output is byte-reproducible.
5. **Enforced by test, not convention:** the test suite runs the full pipeline
   twice over the fixture corpus (in the same process and across processes,
   i.e. across differing `PYTHONHASHSEED`) and asserts byte-identical JSON
   and SARIF output.

## Consequences

- Baselines survive normal development; file renames invalidate that file's
  entries (documented behavior, `plumb baseline` regenerates).
- The double-run byte-equality test makes the determinism principle
  (CLAUDE.md §1.1) mechanically enforced from M0 onward.
- Storing effective severity on the Finding keeps reporters simple; the SARIF
  reporter reads rule defaults from the registry where it needs them.
- The Finding schema, the fingerprint algorithm, and the sort key are all
  public contract — changes require a superseding ADR.
