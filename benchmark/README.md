# Benchmark — precision/recall measurement

A rule may not ship at **High** confidence without a measured precision number
here (CLAUDE.md §1.3). This directory is both the measurement harness and the
labeled corpus it runs against.

```bash
plumb benchmark                      # runs ./benchmark/corpus, prints the table
plumb benchmark --md benchmark/precision.md   # also writes the report
```

## How it works

The corpus is ordinary Python under `corpus/`, labeled with **inline expectation
markers** placed on the line where a finding is expected:

```python
client.chat.completions.create(model="m", timeout=None)  # plumb-expect: PLB-RES-001
```

The harness runs the engine over the corpus and compares produced findings to
the markers, per rule:

- **True positive (TP):** a finding whose `(file, line, rule)` matches a marker.
- **False positive (FP):** a finding with no matching marker — the rule fired on
  code where it shouldn't.
- **False negative (FN):** a marker with no matching finding — the rule missed a
  real defect.

```
precision = TP / (TP + FP)        recall = TP / (TP + FN)
```

**Precision gates High confidence** (≥ 90%). **Recall is informational**: the v1
taint engine deliberately trades recall for precision (ADR-0003 D6), so a rule
can legitimately ship with high precision and modest recall. We never inflate
confidence to chase recall.

## Corpus design

- Files are **independent, realistic** code — *not* a rule's own `fixtures/`
  (that would be circular). The point is to stress a rule against varied
  idiomatic usage it did not see during authoring.
- Each `*_idiomatic.py` file is deliberately dense with correct patterns and
  carries **no markers**: it measures the false-positive rate, the number that
  actually decides whether a rule is safe to gate a build on.
- Each `*_disabled.py` / defect file carries markers on the genuinely-bad lines.

## Roadmap: real-repo corpus

The v1 corpus is curated micro-programs. The planned expansion (approved
direction) is to vendor **~10 popular Apache/MIT-licensed agentic repositories,
pinned to commit hashes**, snapshotted under `corpus/vendored/<repo>@<sha>/`,
each with a hand-labeled marker pass. Pinning + snapshotting keeps the
measurement reproducible and offline (no network in the harness). Only
permissively-licensed (Apache-2.0/MIT) repos are vendored, to stay compatible
with Plumbline's own Apache-2.0 license.

## Current results

See [`precision.md`](precision.md) (regenerate with `plumb benchmark --md
benchmark/precision.md`). Promotion of a rule from Medium to High happens in a
commit that updates both the rule's `confidence` and `docs/standards-map.md`,
citing the precision number measured here.
