# Security Policy

Plumbline is a static analyzer that engineers wire into their CI pipelines, so we
take the security of the tool itself seriously. This document explains how to
report a vulnerability and what to expect in return.

## Scope

This policy covers security issues **in Plumbline itself** — for example:

- a crafted input file that causes code execution, a crash that aborts a CI run,
  or resource exhaustion in the analyzer;
- a flaw that causes Plumbline to exfiltrate source code or secrets (note: the
  detection path makes **no network calls** — see below);
- a vulnerability in the optional AI-remediation path (`plumb` with enrichment
  enabled) or the GitHub Action / pre-commit integrations.

A missed detection or a false positive in a rule is **not** a security
vulnerability — please file those as a regular issue (bug report or
false-positive report) so they get the right triage.

### No network in the detection path

By design, Plumbline's detection path performs **no network calls and collects no
telemetry** — analysis is local and deterministic. The only optional network use
is the AI-remediation layer, which contacts an LLM provider *only* when you
explicitly enable it to enrich fix text. If you believe detection is making a
network call, that itself is a security bug — please report it.

## Supported versions

Plumbline is pre-1.0 and ships from a single active line. Security fixes land on
the latest released version; please upgrade to the latest release before
reporting.

| Version | Supported |
|---|---|
| Latest release (`0.x`) | ✅ |
| Older `0.x` | ❌ (upgrade to latest) |

Once we reach `1.0`, this table will track supported majors.

## Reporting a vulnerability

**Please do not open a public issue for a security vulnerability.**

Report privately through GitHub's **private vulnerability reporting**:

1. Go to the repository's **Security** tab → **Report a vulnerability**, or
2. Visit `https://github.com/actaclad/plumbline/security/advisories/new`.

If you cannot use GitHub Security Advisories, email **security@actaclad.com**.

Please include:

- a description of the issue and its impact;
- the Plumbline version (`plumb --version`) and how you invoked it;
- a minimal reproduction (input file + command) where possible;
- any suggested remediation.

## What to expect

- **Acknowledgement within 3 business days.**
- An initial assessment and severity rating within ~7 days.
- We will keep you updated as we work on a fix, and credit you in the advisory
  and release notes unless you prefer to remain anonymous.
- We follow **coordinated disclosure**: we ask that you give us a reasonable
  window to ship a fix before any public disclosure, and we commit to moving
  quickly. When the fix ships, we publish a GitHub Security Advisory.

Thank you for helping keep Plumbline and the people who depend on it safe.
