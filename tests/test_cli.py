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
    assert "10015 records across 8 JSONL files" in result.stdout


def test_bundle_contains_citations(tmp_path):
    out = tmp_path / "bundle.json"
    run("bundle", "--goal", "JSONL migration", "--output", str(out))
    bundle = json.loads(out.read_text())
    assert bundle["confidence"] == "medium"
    assert "source.synthetic.chat-001" in bundle["must_cite"]
    assert any(item["record_type"] == "claim" for item in bundle["items"])


def test_sqlite_build_contains_records():
    run("build-sqlite")
    con = sqlite3.connect(ROOT / "dist" / "context.sqlite")
    count = con.execute("select count(*) from records").fetchone()[0]
    assert count == 10015
    columns = [row[1] for row in con.execute("pragma table_info(records)")]
    assert "record_type" in columns
    assert columns[:2] == ["id", "record_type"]
    relation_columns = [row[1] for row in con.execute("pragma table_info(relations)")]
    assert relation_columns[:3] == ["subject_id", "relation_type", "object_id"]


def test_record_model_subtype_fields_match_schema():
    entity = json.loads((ROOT / "records" / "entities.jsonl").read_text().splitlines()[0])
    source = json.loads((ROOT / "records" / "sources.jsonl").read_text().splitlines()[0])
    task = json.loads((ROOT / "records" / "tasks.jsonl").read_text().splitlines()[0])
    relation = json.loads((ROOT / "records" / "relations.jsonl").read_text().splitlines()[0])
    assert entity["entity_type"] == "person"
    assert source["source_type"] == "repo"
    assert task["task_type"] == "pilot"
    assert {"subject_id", "relation_type", "object_id", "source_ids"}.issubset(relation)
    assert {"source_id", "type", "target_id"}.isdisjoint(relation)


def test_render_views_creates_project_view():
    run("render-views")
    view = ROOT / "views" / "markdown" / "projects" / "vault-migration.md"
    assert view.exists()
    assert "Agent-first vault migration" in view.read_text()


def test_render_views_creates_note_views():
    result = run("render-views")
    assert "10000 note views" in result.stdout
    note_views = list((ROOT / "views" / "markdown" / "notes").glob("**/*.md"))
    assert len(note_views) == 10000
    sample = ROOT / "views" / "markdown" / "notes" / "anniversary" / "adoptie" / "00001.md"
    text = sample.read_text()
    assert "record_type: note" in text
    assert "vault_type: anniversary" in text
    assert "category: adoptie" in text
    assert "# Synthetic recurring date — adoptie #00001" in text


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
    assert "OK: validated 10015 records" in result.stdout


def test_generated_dataset_covers_vault_schema_matrix():
    coverage = json.loads((ROOT / "reports" / "vault-schema-coverage.json").read_text())
    assert coverage["record_count"] == 10000
    assert coverage["type_count"] == 11
    assert coverage["category_pair_count"] == coverage["expected_category_pair_count"] == 88
    assert coverage["missing_category_pairs"] == []
    assert set(coverage["type_counts"]) == {
        "anniversary", "chore", "context", "entity", "entry", "health",
        "interaction", "project", "purchase", "reference", "task",
    }
