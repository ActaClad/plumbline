# SARIF → GitHub code scanning

Plumbline emits **SARIF 2.1.0**, the format GitHub's code scanning understands.
Upload it and every finding shows up inline on the **Security → Code scanning
alerts** tab and as annotations on the PR diff — what, where, why, and how to fix,
right next to the code.

This is the highest-leverage way to consume Plumbline: developers see findings
where they already work, without installing anything locally.

## The easy way: the Plumbline Action

The [Plumbline Action](../action.yml) installs Plumbline, scans, writes SARIF,
and uploads it for you. Drop this in `.github/workflows/plumbline.yml`:

```yaml
name: Plumbline
on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read
  security-events: write   # required to upload SARIF to code scanning

jobs:
  plumbline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actaclad/plumbline@v1
        with:
          paths: .
```

That's it. Findings appear under **Security → Code scanning**. By default the job
also fails when the Quality Gate fails (a Blocker or High-confidence Critical);
set `fail-on-findings: false` to upload alerts without blocking the build, or
`upload-sarif: false` to gate without uploading.

### Action inputs

| Input | Default | Description |
|---|---|---|
| `paths` | `.` | Space-separated paths to scan. |
| `version` | latest | Pin a Plumbline version, e.g. `0.0.1`. |
| `sarif-file` | `plumbline.sarif` | Where to write the SARIF report. |
| `upload-sarif` | `true` | Upload to GitHub code scanning. |
| `fail-on-findings` | `true` | Fail the job when the Quality Gate fails. |
| `strict-analyzer-errors` | `false` | Also fail on analyzer errors. |
| `python-version` | `3.12` | Python used to run Plumbline. |
| `args` | — | Extra args appended to `plumb scan`. |

## The manual way: any CI

If you'd rather not use the Action (e.g. you're on GitLab CI, CircleCI, or want
full control), generate SARIF yourself and hand it to the official uploader:

```yaml
permissions:
  contents: read
  security-events: write

jobs:
  plumbline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install actaclad-plumbline
      # Don't let a failed gate stop the upload — capture the exit code instead.
      - run: plumb scan . --sarif plumbline.sarif || echo "gate-failed=$?" >> "$GITHUB_ENV"
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: plumbline.sarif
      - run: '[ -z "$gate_failed" ]'   # fail the job after the upload, if the gate failed
```

The pattern is always: **run the scan, upload the SARIF even on failure, then
enforce the gate.** Uploading inside `if: always()` ensures alerts land even when
the gate fails the build.

## Outside GitHub

The same `plumbline.sarif` file is consumable by any SARIF viewer: VS Code (SARIF
Viewer extension), Azure DevOps, and other code-scanning backends. SARIF is a
standard — Plumbline validates its output against the SARIF 2.1.0 schema in the
test suite, so it interoperates.

## See also

- [`ci-integration.md`](ci-integration.md) — wiring the Quality Gate into CI more
  generally (exit codes, baselines, JSON/HTML reports).
- [`action.yml`](../action.yml) — the Action definition and all inputs/outputs.
