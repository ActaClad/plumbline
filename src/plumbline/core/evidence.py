"""Project evidence — the non-Python input channel (ADR-0013).

A read-only collector, separate from the AST pipeline, that gives PROJECT-scope
rules access to repo file paths and the *text* of recognized CI config files.
Built once per run and exposed via `ProjectContext.evidence`. Its only v1
consumer is PLB-EVAL-003 (a sanctioned grep rule, CLAUDE.md §1.2).

Deliberately minimal: bytes + paths, no YAML parser (the detection path stays
dependency-free, CLAUDE.md §4). Deterministic: a fixed, closed set of known CI
locations, sorted output, and only the *scanned repo's* files decide — never the
scanning environment.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final, final

# Directories never descended when listing repo files (mirrors the engine's set).
_SKIP_DIRS: Final[frozenset[str]] = frozenset(
    {".git", ".venv", "venv", "node_modules", "build", "dist", "__pycache__", ".tox", ".eggs"}
)

# Fixed, closed set of known CI config locations (ADR-0013 D1) — no arbitrary
# YAML globbing. Single files at the repo root:
_CI_ROOT_FILES: Final[tuple[str, ...]] = (
    ".gitlab-ci.yml",
    ".gitlab-ci.yaml",
    "azure-pipelines.yml",
    "azure-pipelines.yaml",
    "Jenkinsfile",
    "Makefile",
    "tox.ini",
    "noxfile.py",
    ".pre-commit-config.yaml",
    ".travis.yml",
    "bitbucket-pipelines.yml",
)
# Known CI directories whose *.yml/*.yaml contents are read:
_CI_DIRS: Final[tuple[str, ...]] = (".github/workflows", ".circleci")
_CI_SUFFIXES: Final[tuple[str, ...]] = (".yml", ".yaml")


@final
@dataclass(frozen=True, slots=True)
class ProjectEvidence:
    """Non-Python project facts for PROJECT-scope rules (ADR-0013 D1)."""

    repo_files: tuple[str, ...]  # every (non-excluded) file path, POSIX-relative, sorted
    ci_files: Mapping[str, str]  # POSIX-relative CI config path -> UTF-8 text

    @property
    def has_ci(self) -> bool:
        return bool(self.ci_files)


def collect_evidence(root: Path) -> ProjectEvidence:
    """Collect repo file paths and CI config text under `root`. Deterministic."""
    repo_files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip junk dirs but keep .github/.circleci (their CI text is evidence).
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
        for name in filenames:
            repo_files.append(_rel(root, Path(dirpath) / name))

    ci_files: dict[str, str] = {}
    for name in _CI_ROOT_FILES:
        _read_into(root, root / name, ci_files)
    for ci_dir in _CI_DIRS:
        base = root / ci_dir
        if base.is_dir():
            for path in sorted(base.iterdir()):
                if path.is_file() and path.suffix in _CI_SUFFIXES:
                    _read_into(root, path, ci_files)

    return ProjectEvidence(
        repo_files=tuple(sorted(repo_files)), ci_files=dict(sorted(ci_files.items()))
    )


def _read_into(root: Path, path: Path, out: dict[str, str]) -> None:
    if not path.is_file():
        return
    with contextlib.suppress(OSError):  # an unreadable CI file is simply absent evidence
        out[_rel(root, path)] = path.read_text(encoding="utf-8", errors="replace")


def _rel(root: Path, path: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        rel = path
    return str(PurePosixPath(rel))


#: An empty evidence object — used where a ProjectContext is built without a root.
EMPTY_EVIDENCE: Final[ProjectEvidence] = ProjectEvidence(repo_files=(), ci_files={})
