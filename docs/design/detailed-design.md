# Plumbline — Detailed Design (v1)

**Status:** Phase 1 design, awaiting review. Companion:
`implementation-plan.md` (M0–M9 task breakdown).
**Governed by:** `CLAUDE.md`; decisions in ADR-0001 … ADR-0010.

This document ties the ADRs and component specs into one coherent picture of
the v1 system. It adds no new decisions — where it appears to, the decision
lives in the referenced ADR.

---

## 1. System overview

```
                 ┌────────────────────────── detection path (deterministic) ─────────────────────────┐
 paths, config   │                                                                                    │
 ──────────────► │ discover files ─► per file: parse (ast_layer) ─► adapters annotate ─► taint        │
                 │   (sorted)         ADR-0009                       ADR-0004            ADR-0003     │
                 │                                                                                    │
                 │ ─► file-scope rules ─► project-scope rules ─► dedupe+sort ─► suppressions          │
                 │      ADR-0005/0010        ADR-0010             ADR-0002       ADR-0006             │
                 └────────────────────────────────────────────────────────────────────────────────────┘
                          │                                  │
                          ▼                                  ▼
                  scoring (ADR-0008)                 Quality Gate (ADR-0007)
                          │                                  │
                          └────────────► reporters ◄─────────┘
                                cli │ sarif │ json │ html   (ADR-0006 for SARIF)
                                          │
                       optional AI remediation enrichment (text only, M8)
```

The dashed box is the deterministic core: no network, clock, randomness, or
environment dependence (ADR-0002 D3). Everything to its right consumes an
already-final findings list.

### Same knowledge, three lifecycle surfaces (ADR-0011)

A rule's knowledge is deployed at three points, from **one** authored source
(the rule module + its fixtures — no separate "knowledge" artifact):

- **Authoring / prevention:** `plumb export-skills` mechanically serializes the
  rule registry into a markdown skill-pack that agentic coding tools read to
  *generate* compliant code. Probabilistic is acceptable here — mistakes are
  cheap; the verifier catches them. Not the gate, not a substitute for the
  engine (ADR-0011 D4).
- **Verification:** the deterministic engine above — the authority that gates
  CI.
- **Remediation:** AI tailors fix *text* at output time (M8, ADR-0001 D2).

The exporter is mechanical (no LLM), lives in the deterministic toolchain, and
is byte-reproducible like every other output.

## 2. Module responsibilities

| Module | Owns | Key contracts |
|---|---|---|
| `model.py` | `Severity`, `Confidence`, `Pillar`, `SemanticTag`, `Resolved`, `SemanticNode`, `Finding`, `AnalyzerError` | public; changes need an ADR (ADR-0002) |
| `config.py` | TOML loading, validation, `Config` dataclass, Quality Gate evaluation | ADR-0007 |
| `core/ast_layer.py` | parse, parent map, scope table, source segments, comment/suppression scan | ADR-0009 |
| `core/values.py` | constant folding, client-default linking, framework-default merging | ADR-0004 D3, adapter-contract §4 |
| `core/taint.py` | label propagation, summaries, witness paths, `TaintView` | ADR-0003, taint-engine spec |
| `adapters/base.py` + `adapters/*` | `Adapter` protocol, registration list, `openai_sdk` → `langchain` → `crewai` | ADR-0004, adapter-contract |
| `rules/base.py` | `Rule`, `Scope`, `AnalysisContext`, `ProjectContext`, finding-builder helper, discovery/validation | ADR-0005, ADR-0010, rule-plugin-contract |
| `engine.py` | orchestration, error containment, dedupe/sort, suppression application | architecture §3 |
| `scoring/` | pillar scores, Readiness Score, N/A semantics | ADR-0008 |
| `reporters/` | cli / sarif / json / html | ADR-0006 |
| `skills/` | `export-skills`: mechanical render of the rule registry to a markdown skill-pack (M3+) | ADR-0011 |
| `cli.py` | `plumb scan`, `plumb baseline`, `plumb rules`, `plumb export-skills`; exit codes | ADR-0007 D5, ADR-0011 |

Layout deltas vs `architecture.md` §1 (recorded in ADR-0004/0009): add
`core/values.py`; `libcst` leaves the runtime dependencies.

### Where the rule-facing types live

`model.py` holds pure data only. `AnalysisContext` / `ProjectContext` /
`Rule` / the finding-builder live in `rules/base.py` — they are the rule
contract, and rules import only `plumbline.model` and `plumbline.rules.base`.
Nothing in `rules/` imports `engine.py` (no cycles; rules are leaves).

### `AnalysisContext` (per file)

```python
@dataclass(frozen=True)
class AnalysisContext:
    file: PurePosixPath            # relative to scan root
    tree: SourceTree               # ast_layer wrapper (AST + scopes + segments)
    semantics: SemanticIndex       # query by tag / by node, sorted views
    taint: TaintView               # taint-engine spec §5
    config: Config
    def finding(self, node, message, **overrides) -> Finding:
        """Build a Finding with the rule's metadata, location, snippet and
        fingerprint filled in. The ONLY sanctioned way to create findings."""
```

`ProjectContext` (ADR-0010) wraps the sorted list of `AnalysisContext`s plus
aggregate indexes (semantic nodes by tag across files, model literals, eval/
test-file detection).

## 3. The engine pass structure

1. **Discover** files under `[scan].include` minus excludes/gitignore,
   sorted (ADR-0002 D3). Only `.py` files in v1.
2. **Per file** (sequential in v1 — parallelism is a post-launch
   optimization; it must preserve output identity, so it lands behind the
   double-run test): parse → on syntax error, record `AnalyzerError`, skip
   file. Run gated adapters → semantic index. Run taint **only if** the file
   has semantic nodes or built-in sources (taint-engine §7).
3. **File-scope rules** run in sorted (file, rule-ID) order; each call is
   wrapped: an exception becomes an `AnalyzerError(rule, file)`, never an
   abort (CLAUDE.md §4).
4. **Project-scope rules** run once, sorted by rule ID, same containment.
5. **Post:** dedupe by fingerprint → apply config disables/overrides → apply
   baseline + inline suppressions (mark, don't drop) → final sort.
6. **Score** (suppressed and Low-confidence excluded) → **gate** → **report**.

The engine returns a single immutable `ScanResult` (findings, analyzer
errors, scores, gate verdict) that every reporter consumes — reporters never
recompute anything.

## 4. The first rule, end-to-end (worked thread)

PLB-RES-001 traces the whole system; this is the M1 acceptance story:

1. `fixtures/PLB-RES-001/bad_no_timeout.py` — bare `OpenAI()` client + bare
   `create()` call.
2. `openai_sdk` adapter emits `LLM_CLIENT_CREATE` (timeout `Absent`) and
   `LLM_CALL` with merged `timeout: Absent` (adapter-contract §5).
3. The detector: for each `LLM_CALL`, fire iff `attrs["timeout"] is Absent`
   **and** no enclosing call-level mechanism resolves it. `Unknown` → silent
   (precision rule, adapter-contract §2).
4. `ctx.finding(...)` fills location, snippet, fingerprint (ADR-0002 D2).
5. CLI reporter renders it; SARIF reporter emits it; both byte-stable across
   runs; the good fixture (`OpenAI(timeout=30)`) stays silent.

Every subsequent rule copies this shape (CONTRIBUTING.md).

## 5. Error-handling model

- **User errors** (bad path, bad config) → exit 2 with a clear message
  (ADR-0007 D3/D5).
- **Per-file/per-rule failures** → `AnalyzerError`, run continues, errors
  summarized in CLI output and SARIF notifications (ADR-0006 D3); exit code
  unaffected unless `--strict-analyzer-errors`.
- **Engine/rule-load failures** → exit 3, loud (ADR-0005 D2). A gate tool
  must never silently pass because it half-loaded.
- Dev mode (`PLUMB_DEV=1`... no — env-dependence violates determinism):
  instead, `--debug` flag re-raises analyzer errors with tracebacks. Flags,
  not environment, alter behavior.

## 6. Performance budget (v1 targets, measured in benchmark/)

- Clean 100-file non-AI repo: < 2s end-to-end (gating: import-trigger check
  is a source scan; no taint, no adapters run).
- 100-kLOC mixed repo: < 30s single-process.
- Memory: bounded by retained `AnalysisContext`s (ADR-0010 D4); measure on
  the corpus before optimizing.

## 7. Public contracts (the change-requires-ADR list)

1. `Finding` schema + fingerprint algorithm + sort key (ADR-0002).
2. Rule contract: `Rule` fields, `detect` signatures, `AnalysisContext` /
   `ProjectContext` surface (ADR-0005/0010, rule-plugin-contract).
3. `TaintView` query API (ADR-0003 / taint-engine §5).
4. `SemanticTag` vocabulary semantics + `Resolved` tri-state (ADR-0004).
5. Config schema semantics + exit codes (ADR-0007).
6. SARIF mapping + baseline format (ADR-0006).
7. Scoring formula (ADR-0008).

## 8. Testing strategy (cross-cutting)

| Layer | Strategy |
|---|---|
| model/fingerprint | unit + property tests (stability under line-shift, ordinal behavior) |
| ast_layer/values | unit tests per resolution rule, syntax-error containment |
| taint | the executable spec: one test per propagation row + boundary negatives (taint-engine §8) |
| adapters | golden `(tag, line, attrs)` assertions per pattern row (adapter-contract §6) |
| rules | shared fixture harness: every `bad_*` fires, every `good_*` silent; meta-test enforces fixture existence for every discovered rule (ADR-0005 D2) |
| reporters | SARIF schema validation (vendored schema), golden outputs |
| engine | double-run byte-equality over the whole fixture corpus (ADR-0002 D3); analyzer-error containment |
| scoring | ADR-0008 D4 worked example as a test vector |
| CLI | end-to-end subprocess tests: exit codes, `plumb scan fixtures/...` |
| benchmark | precision harness over a labeled corpus of real OSS agentic repos; required before any rule ships High (CLAUDE.md §1.3) |

CI = `ruff check` + `ruff format --check` + `mypy --strict src` + `pytest`
on 3.11/3.12/3.13.

## 9. Known inconsistencies in existing docs (surfaced, per CLAUDE.md §2)

1. **HTML reporter timing:** `architecture.md` M2 lists HTML; CLAUDE.md §3
   step 4 and architecture M7 ("HTML polish") do not/contradict. Resolution
   adopted: HTML ships in **M7** with scoring (it is a score report; before
   scoring exists it has nothing to show). CLAUDE.md wins (constitution).
2. **SARIF in M1 vs M2:** START-HERE and architecture M1 say the first rule
   "appears in CLI and SARIF"; M2 is "Reporters + Gate." Resolution: M1
   includes a *minimal but schema-valid* SARIF emitter; M2 completes JSON,
   baseline, suppressions, gate wiring.
3. **`pyproject.toml`:** `libcst` (ADR-0009) and the dead `tomli` conditional
   (ADR-0007 D1) are removed in M0.
4. **PLB-RES-001/002 vs SDK defaults:** the OpenAI/Anthropic SDKs ship
   default timeouts and `max_retries=2`. The catalog's detection text
   ("no timeout argument and no client-level timeout") would flag code that
   is actually bounded by SDK defaults. Resolution: adapter reports
   framework defaults with provenance (adapter-contract §4.3) and the rules
   target *effectively unbounded / explicitly disabled* configurations. The
   rules' detector specs in M1/M3 must encode this; the catalog's intent
   ("can hang indefinitely") governs over its literal detection sketch.
