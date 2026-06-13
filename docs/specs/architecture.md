# Spec: Architecture & Build Plan

**Status:** authoritative for structure and sequencing.
**Read alongside:** `CLAUDE.md` §3 (build sequence), ADR-0001 (D3, D6, D8).

This spec is what Claude Code implements the skeleton from. It defines the
module boundaries, the data model, and the order of construction. It does not
restate principles — those live in `CLAUDE.md`.

---

## 1. Repository layout (target)

```
plumbline/
├── CLAUDE.md                     # constitution (read every session)
├── README.md
├── CONTRIBUTING.md
├── LICENSE                       # Apache-2.0
├── pyproject.toml                # package: actaclad-plumbline; CLI: plumb
├── docs/
│   ├── adr/                      # numbered decision records
│   ├── specs/                    # this dir — component specs
│   │   ├── architecture.md       # (this file)
│   │   ├── rule-plugin-contract.md
│   │   ├── adapter-contract.md
│   │   ├── taint-engine.md
│   │   └── rule-catalog.md       # the canonical rule list
│   ├── rule-authoring.md
│   ├── standards-map.md          # OWASP/NIST/CWE coverage matrix
│   └── backlog.md                # discovered-but-deferred work
├── src/plumbline/
│   ├── __init__.py
│   ├── cli.py                    # `plumb` entrypoint
│   ├── config.py                 # config loading + Quality Gate config
│   ├── model.py                  # Finding, Severity, Confidence, Pillar, etc.
│   ├── engine.py                 # orchestrates: parse → adapt → taint → rules
│   ├── core/
│   │   ├── ast_layer.py          # Python AST/libcst wrapper
│   │   └── taint.py              # sources→sinks dataflow engine
│   ├── adapters/
│   │   ├── base.py               # adapter contract
│   │   ├── openai_sdk.py
│   │   ├── langchain.py
│   │   └── crewai.py
│   ├── rules/
│   │   ├── base.py               # rule contract + discovery
│   │   ├── res/                  # reliability
│   │   ├── agt/                  # agent control flow
│   │   ├── mdl/ out/ tool/ rag/ prm/ eval/ obs/ cost/ sec/ gov/
│   ├── scoring/
│   │   ├── pillars.py            # pillar scores
│   │   └── readiness.py          # composite Readiness Score (NOT "Trust Score")
│   └── reporters/
│       ├── cli.py                # human-readable terminal output
│       ├── sarif.py              # SARIF 2.1.0
│       ├── json.py
│       └── html.py
├── fixtures/                     # <RULE_ID>/bad_*.py, good_*.py
├── tests/
└── benchmark/                    # precision/recall datasets + harness
```

## 2. The Finding data model (the central contract)

`model.py` defines the types every layer speaks. This is a public contract —
changing it requires an ADR.

```
Severity   = Blocker | Critical | Major | Minor | Info
Confidence = High | Medium | Low
Pillar     = Reliability | Architecture | Harness | Security

Finding:
    rule_id: str            # "PLB-RES-001"
    title: str
    category: str           # "RES"
    pillar: Pillar
    severity: Severity
    confidence: Confidence
    message: str            # the specific instance ("LLM call on line 42 ...")
    why_it_matters: str     # the concrete production failure
    file: str
    line: int
    column: int | None
    end_line: int | None
    snippet: str | None
    standards: list[str]    # ["OWASP-LLM01", "CWE-78"]
    remediation: str        # static fix text (AI may enrich at output time)
    fingerprint: str        # stable hash for dedupe across runs (determinism)
```

`fingerprint` must be stable across runs given the same code (used for SARIF
baseline/suppression and for determinism testing).

## 3. The analysis pipeline (`engine.py`)

```
discover files (respect .gitignore / config includes-excludes)
  → for each file: parse to AST (core/ast_layer)
  → adapters annotate AST nodes with framework semantics
      (this call is an LLM call / agent loop / tool def / retriever / prompt)
  → taint engine computes source→sink reachability over the annotated graph
  → rule engine runs every discovered rule's detector against the
      (AST + framework annotations + taint graph) context
  → collect Findings, dedupe by fingerprint, sort deterministically
  → scoring computes pillar scores + Readiness Score
  → Quality Gate evaluates pass/fail
  → reporters emit (cli | sarif | json | html)
```

Determinism requirements: file iteration order is sorted; finding order is
sorted by (file, line, rule_id); no detector may depend on iteration order of
dicts/sets without sorting; no network/clock/randomness in any of the above.

Robustness: a detector or adapter that raises on a file is caught at the engine
boundary, recorded as an `AnalyzerError` (distinct from a Finding), and does not
abort the run.

## 4. The taint engine (`core/taint.py`)

Built before rules (ADR-0001 D3). Full spec in `taint-engine.md`. Summary:

- **Sources** (untrusted): function params on request handlers, user input,
  retriever/RAG outputs, tool/function return values, MCP responses, prior
  conversation turns, external HTTP responses.
- **Sinks** (dangerous): prompt construction where the call has tools enabled;
  `eval`/`exec`/`compile`; `subprocess`/`os.system` (esp. `shell=True`);
  raw SQL execution; file open/path join; outbound HTTP URL; HTML/template
  render; another agent's input.
- v1 scope: **intra-procedural** taint with simple inter-procedural propagation
  through direct local calls. Full inter-module taint is deferred (write an ADR
  when it's added). Record this scope limit so rule confidence is set honestly.

## 5. Framework adapters (`adapters/`)

Adapters are the reason one rule covers many frameworks. Each adapter inspects
AST nodes and tags them with normalized semantics (LLM_CALL, AGENT_LOOP,
TOOL_DEF, RETRIEVER, PROMPT_BUILD, MEMORY_APPEND, ...). Rules consume the
normalized tags, not framework-specific call signatures. Contract in
`adapter-contract.md`. Build order: openai_sdk → langchain/langgraph → crewai.

## 6. Reporters (`reporters/`)

- `cli` — human-readable, grouped by file, severity-colored, with fix snippets.
- `sarif` — SARIF 2.1.0, MUST validate against the official schema; one `rule`
  per Plumbline rule, with `properties` carrying pillar/confidence/standards.
- `json` — stable machine format (the Finding model serialized).
- `html` — a shareable report with the Readiness Score and pillar breakdown.

## 7. Scoring (`scoring/`)

- Pillar score (0–100): severity-weighted penalty over that pillar's findings,
  Low-confidence excluded. Exact formula specified in a dedicated ADR before
  implementation (so it's tunable and documented).
- Readiness Score: weighted composite (suggested: Reliability 35, Architecture
  25, Harness 20, Security 20 — tune on real repos). Dashboard/marketing only.
  NEVER named "Trust Score."

## 8. Quality Gate (`config.py`)

Default: fail if any Blocker, or any High-confidence Critical. Fully
configurable per repo (`.plumbline.toml`): severity thresholds, per-rule
enable/disable, per-rule severity override, baseline/suppression file, paths.

## 9. Milestones (maps to CLAUDE.md §3)

- **M0 Substrate:** layout, `pyproject.toml`, Finding model, config loader,
  AST layer, openai_sdk adapter. No rules. CLI prints "no rules loaded."
- **M1 Taint + first rule:** taint engine + `PLB-RES-001` end-to-end with
  fixtures and tests; appears in CLI + SARIF.
- **M2 Reporters + Gate:** SARIF/JSON/CLI/HTML + Quality Gate; runs in CI.
- **M3 Reliability core:** remaining High-confidence RES/OUT/COST rules.
- **M4 Adapters + agentic rules:** langchain/crewai + AGT/TOOL rules.
- **M5 Harness pillar:** EVAL + OBS.
- **M6 Security pillar:** SEC + GOV.
- **M7 Scoring + HTML polish.**
- **M8 AI-assisted remediation.**
- **M9 (Phase 2):** trace ingestion bridge to AgentGuard.

Each milestone ends green (tests, lint, types) and shippable.
