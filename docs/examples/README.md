# Example reports

Self-contained sample outputs you can open in a browser — no install required.

## `llm-sample-report.html`

A real `plumb scan` of **[simonw/llm](https://github.com/simonw/llm)** (a widely
used CLI for LLMs), pinned at commit `0d593ea`, scanned with no configuration:

```bash
git clone https://github.com/simonw/llm && cd llm && git checkout 0d593ea
plumb scan . --html llm-sample-report.html
```

**Result:** 49 files, 12 LLM calls detected (raw OpenAI adapter), **3 findings**,
Readiness Score **93/100**:

- **2 × PLB-OUT-001** (Critical/High) — `json.loads(...)` on model-generated
  function-call arguments with no guard; malformed output crashes the parse.
  These are **genuine true positives** (verified by hand — see
  [`benchmark/real-repos.md`](../../benchmark/real-repos.md)).
- **1 × PLB-OBS-001** (Major/Medium, advisory) — no in-code tracing detected.

No false positives. This is a deliberately *honest* sample: a well-engineered
real tool, a high score, and a small number of real, actionable findings — not a
contrived repo cherry-picked to look alarming. Third-party source is **not**
vendored here; only the report is.
