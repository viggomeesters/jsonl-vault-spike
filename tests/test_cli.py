from pathlib import Path
import json
import os
import sqlite3
import subprocess
import sys
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, str(ROOT / "scripts" / "vaultctx.py")]


def run(*args):
    return subprocess.run(CLI + list(args), cwd=ROOT, text=True, capture_output=True, check=True)


def test_validate_records():
    result = run("validate")
    assert "OK: validated" in result.stdout
    assert "10020 records across 11 JSONL files" in result.stdout


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
    assert count == 10020
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


def test_media_file_records_are_metadata_only_and_public_safe():
    file_rec = json.loads((ROOT / "records" / "files.jsonl").read_text().splitlines()[0])
    asset_rec = json.loads((ROOT / "records" / "media_assets.jsonl").read_text().splitlines()[0])
    link_rec = json.loads((ROOT / "records" / "media_links.jsonl").read_text().splitlines()[0])
    assert file_rec["record_type"] == "file"
    assert file_rec["storage_ref"].startswith("blob://sha256/")
    assert file_rec["sha256"] in file_rec["storage_ref"]
    assert {"content", "content_b64", "content_bytes", "path"}.isdisjoint(file_rec)
    assert asset_rec["record_type"] == "media_asset"
    assert asset_rec["file_id"] == file_rec["id"]
    assert link_rec["record_type"] == "media_link"
    assert link_rec["target_id"] == asset_rec["id"]
    assert link_rec["resolution_status"] == "found"


def test_sqlite_build_contains_media_tables():
    run("build-sqlite")
    con = sqlite3.connect(ROOT / "dist" / "context.sqlite")
    media_links = con.execute("select count(*) from media_links").fetchone()[0]
    files = con.execute("select count(*) from files").fetchone()[0]
    assert media_links == 2
    assert files == 2


def test_inspect_synthetic_media_metadata(tmp_path):
    png = tmp_path / "synthetic.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + (13).to_bytes(4, "big") + b"IHDR" + (4).to_bytes(4, "big") + (3).to_bytes(4, "big") + b"\x08\x02\x00\x00\x00")
    result = run("inspect-media", "--path", str(png), "--max-size-bytes", "1000")
    meta = json.loads(result.stdout)
    assert meta["mime_type"] == "image/png"
    assert meta["width"] == 4
    assert meta["height"] == 3
    assert meta["semantic_extraction"] == "not_implemented"
    too_large = subprocess.run(CLI + ["inspect-media", "--path", str(png), "--max-size-bytes", "3"], cwd=ROOT, text=True, capture_output=True)
    assert too_large.returncode != 0
    assert "file too large" in too_large.stderr


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
    assert "OK: validated 10020 records across 11 JSONL files" in result.stdout


def test_generated_dataset_covers_vault_schema_matrix():
    coverage = json.loads((ROOT / "reports" / "vault-schema-coverage.json").read_text())
    assert coverage["record_count"] == 10000
    assert coverage["type_count"] == 11
    assert coverage["category_pair_count"] == coverage["expected_category_pair_count"] == 88
    assert coverage["missing_category_pairs"] == []
    assert coverage["variant_schema"] == {
        "source": "schema/note.schema.json",
        "enforces_vault_type_enum": True,
        "enforces_category_per_vault_type": True,
        "enforces_area_per_vault_type_category": True,
        "all_of_rule_count": 99,
        "expected_rule_count": 99,
    }
    assert set(coverage["type_counts"]) == {
        "anniversary", "chore", "context", "entity", "entry", "health",
        "interaction", "project", "purchase", "reference", "task",
    }


def test_note_schema_rejects_invalid_vault_schema_variants():
    schema = json.loads((ROOT / "schema" / "note.schema.json").read_text())
    validator = Draft202012Validator(schema)
    records = [json.loads(line) for line in (ROOT / "records" / "notes.jsonl").read_text().splitlines()]
    record = next(r for r in records if r["vault_type"] == "interaction" and r["category"] == "meeting")
    assert record["area"] == "work"
    assert list(validator.iter_errors(record)) == []

    wrong_category = dict(record, category="adoptie")
    assert list(validator.iter_errors(wrong_category)), "interaction/adoptie must be rejected"

    wrong_area = dict(record, area="home")
    assert list(validator.iter_errors(wrong_area)), "interaction/meeting/home must be rejected"

    wrong_type = dict(record, vault_type="not-a-vault-type")
    assert list(validator.iter_errors(wrong_type)), "unknown vault_type must be rejected"
