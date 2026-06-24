from pathlib import Path
import json
import os
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, str(ROOT / "scripts" / "vaultctx.py")]


def run(*args):
    return subprocess.run(CLI + list(args), cwd=ROOT, text=True, capture_output=True, check=True)


def test_validate_records():
    result = run("validate")
    assert "OK: validated" in result.stdout


def test_bundle_contains_citations(tmp_path):
    out = tmp_path / "bundle.json"
    run("bundle", "--goal", "JSONL migration", "--output", str(out))
    bundle = json.loads(out.read_text())
    assert bundle["confidence"] == "medium"
    assert "source.synthetic.chat-001" in bundle["must_cite"]
    assert any(item["kind"] == "claim" for item in bundle["items"])


def test_sqlite_build_contains_records():
    run("build-sqlite")
    con = sqlite3.connect(ROOT / "dist" / "context.sqlite")
    count = con.execute("select count(*) from records").fetchone()[0]
    assert count >= 10


def test_render_views_creates_project_view():
    run("render-views")
    view = ROOT / "views" / "markdown" / "projects" / "vault-migration.md"
    assert view.exists()
    assert "Agent-first vault migration" in view.read_text()


def test_module_cli_validates_from_outside_checkout(tmp_path):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [sys.executable, "-m", "jsonl_vault_spike.cli", "validate"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "OK: validated 15 records" in result.stdout
