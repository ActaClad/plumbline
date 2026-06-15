---
name: Bug report
about: Plumbline crashed, errored, or behaved incorrectly
title: "[bug] "
labels: bug
---

<!-- For a finding you think is wrong (fired when it shouldn't), please use the
     "False positive report" template instead — that's our most important signal. -->

## What happened

A clear description of the bug.

## To reproduce

The exact command you ran:

```bash
plumb scan ...
```

A minimal code snippet or file that triggers it (smaller is better):

```python
# ...
```

## Expected vs actual

- **Expected:** what you thought would happen.
- **Actual:** what actually happened (paste output / traceback).

```
<paste full output or traceback here>
```

## Environment

- Plumbline version: <!-- `plumb --version` -->
- Python version: <!-- `python --version` -->
- OS:
- Framework(s) in the scanned code (OpenAI / Anthropic SDK, LangChain, CrewAI, ...):

## Anything else

Config (`.plumbline.toml`), relevant flags, or context that might help.
