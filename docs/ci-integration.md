# CI integration

Plumbline is built to gate a pipeline. The `plumb scan` Quality Gate runs by
default and communicates pass/fail through the **exit code** (ADR-0007 D5):

| Exit | Meaning |
|---|---|
| 0 | Scan completed, gate passed |
| 1 | Scan completed, gate **failed** (a Blocker, or a High-confidence Critical) |
| 2 | Usage/config error (bad flags, invalid config or baseline) |
| 3 | Internal error (engine bug, rule-load failure) |

Per-file analyzer errors (a file that fails to parse, a detector that raises)
do **not** fail the gate by default — they are reported and surfaced in SARIF
notifications. Add `--strict-analyzer-errors` to treat them as a failure.

## GitHub Actions

```yaml
name: plumbline
on: [push, pull_request]

jobs:
  plumbline:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write   # to upload SARIF to code scanning
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install actaclad-plumbline

      # Scan and emit SARIF. `|| true` lets us upload SARIF even on gate failure;
      # the explicit gate step below is what fails the build.
      - run: plumb scan . --sarif plumbline.sarif || true

      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: plumbline.sarif

      # Fail the job on the gate verdict.
      - run: plumb scan .
```

The two-scan pattern keeps SARIF upload and the pass/fail decision independent;
findings show up in the **Security → Code scanning** tab either way. Fingerprints
are stable across runs (ADR-0002), so alerts don't churn on unrelated edits.

## GitLab CI

```yaml
plumbline:
  image: python:3.12
  script:
    - pip install actaclad-plumbline
    - plumb scan . --sarif gl-plumbline.sarif
  artifacts:
    when: always
    paths: [gl-plumbline.sarif]
```

## Pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: plumbline
        name: plumbline
        entry: plumb scan
        language: system
        pass_filenames: false
        types: [python]
```

## Adopting on an existing repo (baseline)

A repo with pre-existing findings shouldn't fail CI on day one. Accept the
current set as a baseline, then gate only on **new** findings:

```bash
plumb baseline .                 # writes .plumbline-baseline.json — commit it
git add .plumbline-baseline.json
```

Point config at it (default name is already `.plumbline-baseline.json`):

```toml
# .plumbline.toml
[baseline]
file = ".plumbline-baseline.json"
```

Baselined findings are still reported (and appear in SARIF as suppressed), but
they don't fail the gate. As you fix them, regenerate the baseline to shrink it.
Inline, a single finding can be accepted with a reason:

```python
resp = client.chat.completions.create(..., timeout=None)  # plumb: ignore[PLB-RES-001] -- batch job, no SLA
```

(A bare `# plumb: ignore` with no rule ID is rejected — blanket suppression
must be explicit.)

## Tuning the gate

```toml
# .plumbline.toml — defaults shown
[gate]
fail_on_severity = ["Blocker"]                    # any confidence
fail_on_high_confidence_severity = ["Critical"]   # High confidence only
```

See [`.plumbline.toml.example`](../.plumbline.toml.example) for the full schema.
