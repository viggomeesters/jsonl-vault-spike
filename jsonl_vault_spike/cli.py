#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sqlite3, sys
from collections import defaultdict
from pathlib import Path
from jsonschema import Draft202012Validator

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
EMBEDDED_DATA = Path(__file__).resolve().parent / "data"
if (Path.cwd() / "records").exists() and (Path.cwd() / "schema").exists():
    ROOT = Path.cwd()
    DATA_ROOT = ROOT
else:
    ROOT = Path.cwd()
    DATA_ROOT = EMBEDDED_DATA
RECORDS = DATA_ROOT / "records"
SCHEMA = DATA_ROOT / "schema"
DIST = ROOT / "dist"
VIEWS = ROOT / "views" / "markdown"
PRIVATE_PATTERNS = ["/Users/", "/mnt/c/Users/", "iCloud~md~obsidian", "Syncthing/vault", "@gmail.com", "@icloud.com"]
SCHEMA_BY_FILE = {
    "entities.jsonl": "entity.schema.json",
    "projects.jsonl": "project.schema.json",
    "sources.jsonl": "source.schema.json",
    "claims.jsonl": "claim.schema.json",
    "relations.jsonl": "relation.schema.json",
    "tasks.jsonl": "task.schema.json",
    "decisions.jsonl": "decision.schema.json",
    "notes.jsonl": "note.schema.json",
}


def read_jsonl(path: Path):
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                yield idx, json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.relative_to(ROOT)}:{idx}: invalid JSON: {exc}") from exc


def load_records() -> dict[str, dict]:
    records = {}
    for path in sorted(RECORDS.glob("*.jsonl")):
        for _, rec in read_jsonl(path):
            if rec["id"] in records:
                raise ValueError(f"duplicate id: {rec['id']}")
            records[rec["id"]] = rec
    return records


def validate(_args=None) -> int:
    errors = []
    all_ids = set()
    records_by_file = {}
    for file_name, schema_name in SCHEMA_BY_FILE.items():
        path = RECORDS / file_name
        if not path.exists():
            errors.append(f"missing record file: records/{file_name}")
            continue
        schema = json.loads((SCHEMA / schema_name).read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        records_by_file[file_name] = []
        for line_no, rec in read_jsonl(path):
            rel = f"records/{file_name}:{line_no}"
            if rec.get("id") in all_ids:
                errors.append(f"{rel}: duplicate id {rec.get('id')}")
            all_ids.add(rec.get("id"))
            for err in sorted(validator.iter_errors(rec), key=lambda e: list(e.path)):
                loc = ".".join(str(p) for p in err.path) or "<root>"
                errors.append(f"{rel}: {loc}: {err.message}")
            text = json.dumps(rec, ensure_ascii=False)
            for pattern in PRIVATE_PATTERNS:
                if pattern in text and rec.get("privacy") != "sensitive":
                    errors.append(f"{rel}: possible private pattern {pattern!r} without sensitive privacy")
            records_by_file[file_name].append(rec)
    records = {rec["id"]: rec for rows in records_by_file.values() for rec in rows if "id" in rec}
    for rec in records.values():
        for field in ("source_ids", "evidence_ids"):
            for ref in rec.get(field, []) or []:
                if ref not in records:
                    errors.append(f"{rec['id']}: {field} references missing id {ref}")
        for field in ("subject_id", "source_id", "target_id", "project_id"):
            ref = rec.get(field)
            if ref and ref not in records:
                errors.append(f"{rec['id']}: {field} references missing id {ref}")
    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        return 1
    print(f"OK: validated {len(records)} records across {len(SCHEMA_BY_FILE)} JSONL files")
    return 0


def search_records(query: str) -> list[dict]:
    terms = [t.lower() for t in query.split() if t.strip()]
    results = []
    for rec in load_records().values():
        hay = json.dumps(rec, ensure_ascii=False).lower()
        score = sum(1 for t in terms if t in hay)
        if score:
            results.append((score, rec["id"], rec))
    return [rec for _, _, rec in sorted(results, key=lambda x: (-x[0], x[1]))]


def query(args) -> int:
    for rec in search_records(" ".join(args.terms))[: args.limit]:
        print(f"{rec['id']} [{rec['record_type']}] {rec.get('title') or rec.get('display_name') or rec.get('summary')}")
    return 0


def bundle(args) -> int:
    records = load_records()
    hits = search_records(args.goal)[: args.limit]
    hit_ids = {r["id"] for r in hits}
    include = dict((r["id"], r) for r in hits)
    for rec in list(include.values()):
        for field in ("source_ids", "evidence_ids"):
            for ref in rec.get(field, []) or []:
                if ref in records:
                    include[ref] = records[ref]
        for field in ("subject_id", "source_id", "target_id", "project_id"):
            ref = rec.get(field)
            if ref in records:
                include[ref] = records[ref]
    out = {
        "bundle_id": "bundle.synthetic." + str(abs(hash(args.goal)))[:8],
        "goal": args.goal,
        "item_ids": sorted(include),
        "items": [include[k] for k in sorted(include)],
        "must_cite": sorted({sid for rec in include.values() for sid in (rec.get("source_ids") or rec.get("evidence_ids") or []) if sid in records}),
        "warnings": ["Synthetic data only; do not infer personal facts."],
        "gaps": [] if hit_ids else ["No matching records found."],
        "confidence": "medium" if hit_ids else "low",
    }
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def build_sqlite(_args=None) -> int:
    DIST.mkdir(exist_ok=True)
    db = DIST / "context.sqlite"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.execute("create table records(id text primary key, kind text not null, privacy text not null, summary text, json text not null)")
    con.execute("create table relations(source_id text, type text, target_id text, json text not null)")
    for rec in load_records().values():
        con.execute("insert into records values(?,?,?,?,?)", (rec["id"], rec["record_type"], rec.get("privacy"), rec.get("summary") or rec.get("title") or rec.get("display_name"), json.dumps(rec, ensure_ascii=False, sort_keys=True)))
        if rec["record_type"] == "relation":
            con.execute("insert into relations values(?,?,?,?)", (rec["source_id"], rec["type"], rec["target_id"], json.dumps(rec, ensure_ascii=False, sort_keys=True)))
    con.commit(); con.close()
    print(f"built {db.relative_to(ROOT)}")
    return 0


def markdown_escape(value: str) -> str:
    return str(value).replace("|", "\\|")


def frontmatter(rec: dict) -> str:
    lines = ["---"]
    for key in ["id", "record_type", "vault_type", "category", "area", "privacy", "created_at", "synthetic", "coverage_seed"]:
        if key in rec:
            value = rec[key]
            if isinstance(value, bool):
                value = "true" if value else "false"
            lines.append(f"{key}: {value}")
    for key in ["source_ids", "evidence_ids"]:
        if key in rec:
            lines.append(f"{key}:")
            for item in rec.get(key) or []:
                lines.append(f"  - {item}")
    lines.append("---")
    return "\n".join(lines)


def render_note_view(rec: dict) -> str:
    return "\n".join([
        frontmatter(rec),
        "",
        f"# {rec['title']}",
        "",
        rec["summary"],
        "",
        "## Body",
        "",
        rec["body"],
        "",
        "## Record",
        "",
        f"- Type: `{markdown_escape(rec['vault_type'])}`",
        f"- Category: `{markdown_escape(rec['category'])}`",
        f"- Area: `{markdown_escape(rec['area'])}`",
        f"- Synthetic: `{str(rec['synthetic']).lower()}`",
        "",
    ])


def render_views(_args=None) -> int:
    records = load_records()
    for sub in [VIEWS / "projects", VIEWS / "entities", VIEWS / "notes"]:
        sub.mkdir(parents=True, exist_ok=True)
        for old in sub.rglob("*.md"):
            old.unlink()
    rendered_notes = 0
    for rec in records.values():
        if rec["record_type"] == "project":
            claims = [r for r in records.values() if r.get("subject_id") == rec["id"]]
            lines = [f"# {rec['title']}", "", rec["summary"], "", f"Status: `{rec['status']}`", "", "## Claims", ""]
            lines += [f"- {c['statement']} (confidence: {c['confidence']})" for c in claims] or ["- none"]
            (VIEWS / "projects" / f"{rec['id'].split('.')[-1]}.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
        if rec["record_type"] == "entity":
            lines = [f"# {rec['display_name']}", "", rec["summary"], "", f"Privacy: `{rec['privacy']}`"]
            (VIEWS / "entities" / f"{rec['id'].split('.')[-1]}.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
        if rec["record_type"] == "note":
            type_dir = VIEWS / "notes" / rec["vault_type"] / rec["category"]
            type_dir.mkdir(parents=True, exist_ok=True)
            (type_dir / f"{rec['id'].split('.')[-1]}.md").write_text(render_note_view(rec), encoding="utf-8")
            rendered_notes += 1
    print(f"rendered markdown views ({rendered_notes} note views)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Synthetic JSONL vault/context MVP CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    q = sub.add_parser("query"); q.add_argument("terms", nargs="+"); q.add_argument("--limit", type=int, default=10)
    b = sub.add_parser("bundle"); b.add_argument("--goal", required=True); b.add_argument("--limit", type=int, default=8); b.add_argument("--output")
    sub.add_parser("build-sqlite")
    sub.add_parser("render-views")
    args = parser.parse_args(argv)
    return {"validate": validate, "query": query, "bundle": bundle, "build-sqlite": build_sqlite, "render-views": render_views}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
