#!/usr/bin/env python3
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FORBIDDEN = [
    "Viggo", "Anne", "Duco", "JJ", "Waspik", "8340627826", "22843",
    "/mnt/c/Users", "/Users/viggomeesters", "viggomeesters@", "@gmail", "@icloud",
    "Syncthing/vault", "iCloud~md~obsidian",
]
ALLOWED_GUARD_FILES = {"scripts/validate_repository.py", "scripts/generate_synthetic_dataset.py", "jsonl_vault_spike/cli.py", "AGENTS.md"}
REQUIRED_PATHS = [
    "README.md", "LICENSE", "CHANGELOG.md", "SUPPORT.md", "SECURITY.md", "CODE_OF_CONDUCT.md",
    "CONTRIBUTORS.md", "NOTICE.md", "AGENTS.md", "Makefile", "pyproject.toml", "MANIFEST.in",
    "scripts/generate_synthetic_dataset.py", "scripts/evaluate_obsidian_vault.py", "reports/vault-schema-coverage.json", "schema/note.schema.json", "records/notes.jsonl",
    "assets/jsonl-vault-spike-hero.svg", "docs/ARCHITECTURE.md", "docs/ROADMAP.md",
    "docs/PACKAGE.md", "docs/HERO_PROMPT.md", "docs/VAULT_EVALUATION.md", "docs/MAINTAINER_CHECKLIST.md", "docs/REPO_COMPLETE.md",
    ".github/pull_request_template.md", ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/bug_report.yml", ".github/ISSUE_TEMPLATE/design_question.yml", ".github/CODEOWNERS",
]
GENERATED_UNTRACKED = ["dist/context.sqlite", "dist/bundles/migration-demo.json"]
IDENTITY_STRINGS = ["jsonl-vault-spike", "jsonl_vault_spike", "vaultctx"]


def tracked_files() -> list[str]:
    out = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    return [line for line in out.splitlines() if line]


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def main() -> int:
    errors: list[str] = []
    files = tracked_files()
    tracked = set(files)
    for rel in REQUIRED_PATHS:
        if rel not in tracked and not (ROOT / rel).exists():
            fail(f"missing required repo-complete file: {rel}", errors)
    for rel in GENERATED_UNTRACKED:
        if rel in tracked:
            fail(f"generated runtime artifact must not be tracked: {rel}", errors)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for s in IDENTITY_STRINGS:
        if s not in readme:
            fail(f"README missing identity string {s!r}", errors)
    if "Synthetic" not in readme or "No real personal data" not in readme:
        fail("README must state synthetic/no-real-personal-data boundary", errors)
    for rel in files:
        if rel.startswith(".git/") or rel.startswith(".venv/"):
            continue
        path = ROOT / rel
        if path.suffix in {".pyc", ".sqlite", ".duckdb"}:
            fail(f"tracked forbidden generated/binary artifact: {rel}", errors)
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for token in PUBLIC_FORBIDDEN:
            if token in text and rel not in ALLOWED_GUARD_FILES:
                fail(f"public-data token {token!r} found in {rel}", errors)
    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        return 1
    print(f"OK: repository guard passed ({len(files)} tracked files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
