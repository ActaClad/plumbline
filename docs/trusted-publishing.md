# Trusted publishing to PyPI (token-free releases)

Plumbline publishes to PyPI with **trusted publishing** — PyPI verifies a
short-lived OIDC token minted by GitHub Actions for a specific workflow, so there
are **no API tokens stored in the repo or in GitHub secrets**. Cutting a GitHub
Release builds the sdist + wheel and publishes them automatically.

The workflow is [`.github/workflows/publish.yml`](../.github/workflows/publish.yml)
(`on: release: published`). Everything on the GitHub side is already in place:

| Piece | State |
| --- | --- |
| `publish.yml` workflow (OIDC, `id-token: write`, `skip-existing`) | ✅ in repo |
| GitHub environment `pypi` | ✅ created |

**One step remains, and it can only be done in the PyPI web console.**

## Configure the PyPI trusted publisher (once)

> ⚠️ **Order matters.** The OIDC token exchange happens on *every* publish run,
> **before** `skip-existing` is ever evaluated. If the trusted publisher is not
> configured on PyPI, the publish job fails at authentication — `skip-existing`
> does not save you. **Configure this on PyPI first, then create any GitHub
> Release.**

1. Log in to <https://pypi.org> as the account that owns `actaclad-plumbline`.
2. Go to the project → **Manage** → **Publishing** (or, to pre-authorize before
   the project exists, **Your account → Publishing → Add a pending publisher**).
3. Add a **GitHub** trusted publisher with these **exact** values:

   | Field | Value |
   | --- | --- |
   | PyPI Project Name | `actaclad-plumbline` |
   | Owner | `ActaClad` |
   | Repository name | `plumbline` |
   | Workflow name | `publish.yml` |
   | Environment name | `pypi` |

   The project name is the **PyPI package** name (`actaclad-plumbline`), not the
   repo name (`plumbline`) — these differ. All five must match or the token
   exchange is rejected.
4. Save.

That's it — no token to copy anywhere.

## Cut a release

Once the publisher is configured, publishing a GitHub Release runs the pipeline:

```bash
# bump version in pyproject.toml first, then tag + release
gh release create v0.0.2 \
  --repo ActaClad/plumbline \
  --title "Plumbline v0.0.2" \
  --notes-file docs/launch/release-notes-v0.0.2.md
```

The `v0.0.1` release is a safe first test: `0.0.1` was hand-uploaded to claim the
name, so the publish step hits `skip-existing: true` and no-ops gracefully — you
get a green end-to-end run without a duplicate-file error.

## Verifying it works

- GitHub → **Actions** → the **Publish** run should show `build` then `publish`
  green.
- The `publish` job logs an OIDC exchange, then either uploads or prints
  `Skipping … already exists` (for `0.0.1`).
- PyPI → project → **Releases** shows the new version (for a fresh version).

## Why trusted publishing

- **No long-lived secret** to leak, rotate, or scope. A stolen API token can
  publish forever; an OIDC token is minted per-run and expires in minutes.
- **Scoped to one workflow in one repo.** Only `publish.yml` in `ActaClad/plumbline`,
  running in the `pypi` environment, can publish — enforced by PyPI, not by us.
- **Auditable.** Every publish is tied to a GitHub Release and its Actions run.
