---
name: False positive report
about: A rule fired on code that is actually correct
title: "[false-positive] PLB-XXX-NNN: "
labels: false-positive
---

<!-- This is the single most valuable issue you can file. A noisy analyzer gets
     uninstalled, so we treat every false positive as a precision bug and aim to
     turn it into a fix + regression test. Thank you. -->

## Which rule fired

- **Rule ID:** <!-- e.g. PLB-RES-001 -->
- **Reported severity / confidence:** <!-- e.g. Critical / High -->

## The code it fired on

The smallest snippet that still triggers the finding (please trim to the minimum):

```python
# ...
```

## Why it's a false positive

Explain why this code is actually correct / safe — what the rule missed (a
fallback that exists elsewhere, a framework that handles it, a guard the analyzer
didn't see, etc.).

## Command and output

```bash
plumb scan path/to/file.py
```

```
<paste the finding as Plumbline reported it>
```

## Environment

- Plumbline version: <!-- `plumb --version` -->
- Python version:
- Framework(s) involved:
