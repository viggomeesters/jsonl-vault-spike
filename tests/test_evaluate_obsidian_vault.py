from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_obsidian_vault.py"


def test_evaluate_obsidian_vault_writes_aggregate_only_outputs(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    private_title = "PRIVATE_TITLE_SHOULD_NOT_LEAK"
    private_body = "PRIVATE_BODY_SHOULD_NOT_LEAK"
    private_category = "PRIVATE_CATEGORY_SHOULD_NOT_LEAK"
    (vault / "note.md").write_text(
        f"---\ntype: project\ncategory: {private_category}\n---\n"
        f"# {private_title}\n"
        f"{private_body}\n"
        "[[Some Link]]\n"
        "- [ ] one task\n"
        "Source: https://example.invalid/source\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--vault", str(vault), "--out", str(out), "--limit", "10"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert '"privacy": "aggregate-only"' in result.stdout
    metrics = json.loads((out / "aggregate-metrics.json").read_text())
    assert metrics["markdown_files_scanned"] == 1
    assert metrics["notes_with_type"] == 1
    assert metrics["notes_with_category"] == 1
    assert metrics["wikilinks_count"] == 1
    html = (out / "value-prop-comparison.html").read_text()
    combined = json.dumps(metrics) + html + (out / "scorecard.json").read_text()
    assert private_title not in combined
    assert private_body not in combined
    assert private_category not in combined
    assert str(vault) not in combined
    assert "[REDACTED_LOCAL_VAULT]" in combined
