#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import shutil
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT.parent / "vault-schema" / "vault-schema.json"
AREAS = ["home", "self", "social", "work"]
EMBEDDED_DATA = ROOT / "jsonl_vault_spike" / "data"
PUBLIC_FORBIDDEN = [
    "Viggo", "Anne", "Duco", "JJ", "Waspik", "8340627826", "22843",
    "/mnt/c/Users", "/Users/viggomeesters", "viggomeesters@", "@gmail", "@icloud",
    "Syncthing/vault", "iCloud~md~obsidian",
]
TYPE_TITLES = {
    "entity": "Synthetic entity profile",
    "interaction": "Synthetic interaction log",
    "purchase": "Synthetic purchase decision",
    "anniversary": "Synthetic recurring date",
    "health": "Synthetic health observation",
    "entry": "Synthetic journal entry",
    "task": "Synthetic task note",
    "project": "Synthetic project context",
    "reference": "Synthetic reference note",
    "chore": "Synthetic household routine",
    "context": "Synthetic context packet",
}


def slug(s: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in s).strip("-")


def load_matrix(schema_path: Path) -> list[dict]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    matrix = []
    for vault_type in sorted(schema["type_category_area"]):
        for category in sorted(schema["type_category_area"][vault_type]):
            allowed = schema["type_category_area"][vault_type][category].get("allowed_areas") or AREAS
            matrix.append({"vault_type": vault_type, "category": category, "allowed_areas": sorted(allowed)})
    return matrix


def make_record(idx: int, combo: dict, area: str, coverage_seed: bool) -> dict:
    vault_type = combo["vault_type"]
    category = combo["category"]
    day = date(2026, 1, 1) + timedelta(days=(idx - 1) % 365)
    title = f"{TYPE_TITLES.get(vault_type, 'Synthetic vault note')} — {category} #{idx:05d}"
    summary = f"Synthetic {vault_type}/{category} note for {area} area coverage."
    body = (
        f"This is public-safe synthetic test data for vault schema type '{vault_type}' "
        f"and category '{category}'. It resembles a structured personal vault note pattern "
        f"without using real people, places, accounts, messages, paths, or private facts."
    )
    return {
        "id": f"note.synthetic.{idx:05d}",
        "record_type": "note",
        "vault_type": vault_type,
        "category": category,
        "area": area,
        "title": title,
        "summary": summary,
        "body": body,
        "privacy": "private",
        "source_ids": ["source.synthetic.seed"],
        "evidence_ids": ["source.synthetic.seed"],
        "created_at": day.isoformat(),
        "synthetic": True,
        "coverage_seed": coverage_seed,
    }


def generate(count: int, schema_path: Path) -> tuple[list[dict], dict]:
    matrix = load_matrix(schema_path)
    note_schema = write_note_schema(matrix, schema_path)
    if count < len(matrix):
        raise ValueError(f"count {count} is smaller than required coverage matrix {len(matrix)}")
    records = []
    idx = 1
    for combo in matrix:
        records.append(make_record(idx, combo, combo["allowed_areas"][0], True))
        idx += 1
    while idx <= count:
        combo = matrix[(idx - 1) % len(matrix)]
        area = combo["allowed_areas"][(idx - 1) % len(combo["allowed_areas"])]
        records.append(make_record(idx, combo, area, False))
        idx += 1
    coverage = build_coverage(records, matrix, count, note_schema)
    return records, coverage


def build_coverage(records: list[dict], matrix: list[dict], count: int, note_schema: dict) -> dict:
    type_counts = Counter(r["vault_type"] for r in records)
    category_counts = Counter(f"{r['vault_type']}/{r['category']}" for r in records)
    area_counts = Counter(r["area"] for r in records)
    expected_pairs = {f"{m['vault_type']}/{m['category']}" for m in matrix}
    observed_pairs = set(category_counts)
    missing_pairs = sorted(expected_pairs - observed_pairs)
    return {
        "record_count": len(records),
        "target_count": count,
        "vault_schema_version_source": "../vault-schema/vault-schema.json",
        "type_count": len(type_counts),
        "category_pair_count": len(category_counts),
        "expected_category_pair_count": len(expected_pairs),
        "missing_category_pairs": missing_pairs,
        "variant_schema": {
            "source": "schema/note.schema.json",
            "enforces_vault_type_enum": True,
            "enforces_category_per_vault_type": True,
            "enforces_area_per_vault_type_category": True,
            "all_of_rule_count": len(note_schema.get("allOf", [])),
            "expected_rule_count": len(type_counts) + len(expected_pairs),
        },
        "type_counts": dict(sorted(type_counts.items())),
        "area_counts": dict(sorted(area_counts.items())),
        "category_pair_counts": dict(sorted(category_counts.items())),
    }



def build_note_schema(matrix: list[dict], schema_contract: dict) -> dict:
    """Build the public note-record envelope plus vault-schema-derived variant constraints."""
    vault_types = sorted({m["vault_type"] for m in matrix})
    categories_by_type: dict[str, list[str]] = defaultdict(list)
    all_categories = set()
    all_areas = set()
    pair_rules = []
    for combo in matrix:
        vault_type = combo["vault_type"]
        category = combo["category"]
        allowed_areas = sorted(combo["allowed_areas"])
        categories_by_type[vault_type].append(category)
        all_categories.add(category)
        all_areas.update(allowed_areas)
        pair_rules.append({
            "if": {
                "properties": {
                    "vault_type": {"const": vault_type},
                    "category": {"const": category},
                },
                "required": ["vault_type", "category"],
            },
            "then": {"properties": {"area": {"enum": allowed_areas}}},
        })
    type_rules = []
    for vault_type in vault_types:
        type_rules.append({
            "if": {"properties": {"vault_type": {"const": vault_type}}, "required": ["vault_type"]},
            "then": {"properties": {"category": {"enum": sorted(categories_by_type[vault_type])}}},
        })
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Synthetic vault note record",
        "description": (
            "Generated from vault-schema type_category_area. Enforces record envelope, "
            "vault_type/category validity, and category-specific allowed area values."
        ),
        "type": "object",
        "additionalProperties": False,
        "required": [
            "id", "record_type", "vault_type", "category", "area", "title", "summary",
            "body", "privacy", "source_ids", "evidence_ids", "created_at", "synthetic",
        ],
        "properties": {
            "id": {"type": "string", "pattern": "^note\\.synthetic\\.[0-9]{5}$"},
            "record_type": {
                "const": "note",
                "description": "Technical JSONL record discriminator. Domain-specific subtype fields live on typed records such as entity_type, source_type, relation_type, task_type, claim_type, or vault_type.",
            },
            "vault_type": {"type": "string", "enum": vault_types},
            "category": {"type": "string", "enum": sorted(all_categories)},
            "area": {"type": "string", "enum": sorted(all_areas)},
            "title": {"type": "string", "minLength": 1},
            "summary": {"type": "string", "minLength": 1},
            "body": {"type": "string", "minLength": 1},
            "privacy": {"type": "string", "enum": ["public", "private", "sensitive"]},
            "source_ids": {"type": "array", "items": {"type": "string"}},
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
            "created_at": {"type": "string"},
            "synthetic": {"const": True},
            "coverage_seed": {"type": "boolean"},
        },
        "x-vault-schema-source": {
            "version": schema_contract.get("version"),
            "field": "type_category_area",
            "type_count": len(vault_types),
            "type_category_pair_count": len(matrix),
        },
        "allOf": type_rules + pair_rules,
    }


def write_note_schema(matrix: list[dict], schema_path: Path) -> dict:
    schema_contract = json.loads(schema_path.read_text(encoding="utf-8"))
    note_schema = build_note_schema(matrix, schema_contract)
    out = ROOT / "schema" / "note.schema.json"
    out.write_text(json.dumps(note_schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return note_schema

def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records), encoding="utf-8")


def sync_embedded_data() -> None:
    normalize_demo_records()
    for sub in ["records", "schema", "raw", "retrieval", "evals"]:
        dst = EMBEDDED_DATA / sub
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(ROOT / sub, dst)
    (EMBEDDED_DATA / "README.md").write_text(
        "# Embedded demo data\n\n"
        "Synthetic dataset bundled with the package so `vaultctx validate` works outside a source checkout.\n\n"
        "The repository root files remain the canonical editable demo dataset when running inside a checkout.\n",
        encoding="utf-8",
    )


def normalize_demo_records() -> None:
    """Keep hand-authored demo records aligned with the public record_type model."""
    # The bulk generator owns notes.jsonl. Other small demo files are authored,
    # but must keep subtype fields in sync before embedded package data is copied.
    for path in (ROOT / "records").glob("*.jsonl"):
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("record_type") == "source":
                row.setdefault("source_type", (row.get("locator") or {}).get("type", "synthetic"))
            elif row.get("record_type") == "entity":
                parts = row["id"].split(".")
                row.setdefault("entity_type", parts[1] if len(parts) > 2 else "synthetic_entity")
                row.setdefault("category", "synthetic_example")
            elif row.get("record_type") == "task":
                row.setdefault("task_type", "pilot")
                row.setdefault("category", "migration")
            elif row.get("record_type") == "claim":
                row.setdefault("claim_type", "architecture")
                row.setdefault("category", "migration")
            elif row.get("record_type") == "relation":
                if "source_id" in row:
                    row["subject_id"] = row.pop("source_id")
                if "target_id" in row:
                    row["object_id"] = row.pop("target_id")
                if "type" in row:
                    row["relation_type"] = row.pop("type")
                row.setdefault("source_ids", row.get("evidence_ids") or ["source.synthetic.seed"])
            rows.append(row)
        write_jsonl(path, rows)


def assert_public_safe(records: list[dict]) -> None:
    text = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
    for token in PUBLIC_FORBIDDEN:
        if token in text:
            raise ValueError(f"forbidden public-data token in generated records: {token!r}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate public-safe synthetic note records covering vault-schema type/category matrix.")
    parser.add_argument("--count", type=int, default=10_000)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--output", type=Path, default=ROOT / "records" / "notes.jsonl")
    parser.add_argument("--coverage", type=Path, default=ROOT / "reports" / "vault-schema-coverage.json")
    args = parser.parse_args(argv)
    records, coverage = generate(args.count, args.schema)
    assert_public_safe(records)
    write_jsonl(args.output, records)
    args.coverage.parent.mkdir(parents=True, exist_ok=True)
    args.coverage.write_text(json.dumps(coverage, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    sync_embedded_data()
    print(f"generated {len(records)} note records covering {coverage['category_pair_count']} type/category pairs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
