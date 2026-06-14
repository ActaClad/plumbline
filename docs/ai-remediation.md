# AI-assisted remediation (optional)

Plumbline's detection is **100% deterministic** — pure AST + dataflow, no network,
no LLM. Running a scan twice on the same code always produces identical findings,
fingerprints, and the same Quality Gate verdict.

The **one** place an LLM may be used is to tailor a finding's *remediation text*
to your specific code — turning the generic "use parameterized queries" into
guidance that names your variables. This is **off by default** and, by design,
**cannot change what Plumbline detects** (CLAUDE.md §1.1, ADR-0015).

## The firewall (why it's safe)

- Enrichment runs **after** the scan is complete and the gate is decided — in the
  CLI layer, never inside the analysis engine. Any programmatic caller of the
  engine gets AI-free detection by construction.
- It may rewrite **only** the `remediation` string. Fingerprints exclude
  remediation, so **baselines never churn** when you toggle AI. The gate is
  computed on the deterministic result and is never recomputed.
- A test runs the engine with a fake LLM that rewrites *every* remediation and
  asserts every finding's fingerprint/severity/confidence/location, the gate
  verdict and reasons, and the CLI exit code are **byte-identical** to the AI-off
  run — only the remediation text (labelled `(AI-assisted)`) differs.

## Determinism note

With enrichment **on**, the remediation text varies run-to-run (it's an LLM) — so
the AI-on output is intentionally *not* byte-reproducible. Everything that matters
for CI — findings, fingerprints, baselines, the gate, the Readiness Score — stays
stable, because none of them include remediation text. Keep enrichment **off** in
CI; turn it on locally when you want tailored fixes.

## Enabling it

1. Install the extra: `pip install actaclad-plumbline[ai]`
2. Set your key: `export ANTHROPIC_API_KEY=...`
3. Enable it in `.plumbline.toml`:

   ```toml
   [ai]
   enrich_remediation = true
   ```

If enrichment is enabled but the extra isn't installed or no key is set, Plumbline
prints a notice and falls back to the static remediation — detection and exit code
are unchanged, you're just told it couldn't enrich.

Enriched fixes are marked `(AI-assisted)` in the CLI and `"remediation_is_ai":
true` in JSON. SARIF carries the static rule remediation (it's the machine
contract); the AI text is a local convenience.
