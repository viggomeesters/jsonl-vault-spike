#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, mimetypes, shutil, sqlite3, sys
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
OBJECTS = DATA_ROOT / "objects" / "sha256"
FIXTURES = DATA_ROOT / "fixtures" / "import-demo"
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"
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
    "attachments.jsonl": "attachment.schema.json",
    "files.jsonl": "file.schema.json",
    "media_assets.jsonl": "media_asset.schema.json",
    "media_links.jsonl": "media_link.schema.json",
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
        for field in ("subject_id", "source_id", "target_id", "project_id", "file_id"):
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
        for field in ("subject_id", "source_id", "target_id", "project_id", "file_id"):
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



def write_jsonl_file(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def copy_to_demo_object_store(src: Path, out_root: Path) -> tuple[str, int, str]:
    digest = sha256_file(src)
    size = src.stat().st_size
    ext = src.suffix.lower()
    object_rel = f"objects/sha256/{digest[:2]}/{digest}{ext}"
    dst = out_root / object_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return digest, size, object_rel


def import_demo(args) -> int:
    fixture_root = Path(args.fixture_root) if args.fixture_root else FIXTURES
    out_root = Path(args.output)
    if not fixture_root.exists():
        print(f"fixture root not found: {fixture_root}", file=sys.stderr)
        return 1
    if out_root.exists() and not args.keep_existing:
        shutil.rmtree(out_root)
    records_dir = out_root / "records"
    report_dir = out_root / "reports"
    manifest = json.loads((fixture_root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("synthetic_only") is not True:
        print("import-demo only accepts synthetic fixtures", file=sys.stderr)
        return 1

    sources = [
        {"id":"source.importdemo.markdown-note","record_type":"source","source_type":"markdown_fixture","privacy":"public","summary":"Synthetic Markdown note with media embeds and a missing media case.","synthetic":True,"locator":{"type":"fixture","ref":"markdown/synthetic-project-note.md"}},
        {"id":"source.importdemo.mail-message","record_type":"source","source_type":"mail_fixture","privacy":"public","summary":"Synthetic mail envelope with attachment manifest.","synthetic":True,"locator":{"type":"fixture","ref":"mail/message-alpha.json"}},
        {"id":"source.importdemo.folder-drop","record_type":"source","source_type":"folder_drop_fixture","privacy":"public","summary":"Synthetic folder-drop manifest with two items.","synthetic":True,"locator":{"type":"fixture","ref":"folder-drop/drop-manifest.json"}},
    ]
    files = []
    attachments = []
    media_assets = []
    media_links = []
    source_for_role = {
        "markdown_embed": "source.importdemo.markdown-note",
        "mail_attachment": "source.importdemo.mail-message",
        "folder_drop_item": "source.importdemo.folder-drop",
    }
    attachment_type_for_role = {
        "markdown_embed": "note_embed",
        "mail_attachment": "mail_attachment",
        "folder_drop_item": "linked_file",
    }
    link_type_for_role = {
        "markdown_embed": "embedded_image",
        "mail_attachment": "mail_attachment",
        "folder_drop_item": "folder_drop_item",
    }
    media_type_for_mime = {
        "image/png": "image",
        "application/pdf": "pdf",
        "text/csv": "document",
        "text/plain": "document",
    }
    for idx, item in enumerate(manifest["fixtures"], 1):
        src = fixture_root / item["relative_path"]
        digest, size, object_rel = copy_to_demo_object_store(src, out_root)
        if digest != item["sha256"] or size != item["size_bytes"]:
            print(f"fixture manifest drift: {item['relative_path']}", file=sys.stderr)
            return 1
        mime_type = mimetypes.guess_type(src.name)[0] or "application/octet-stream"
        slug = Path(item["relative_path"]).stem.replace("_", "-")
        file_id = f"file.importdemo.{slug}"
        source_id = source_for_role[item["fixture_role"]]
        files.append({"id":file_id,"record_type":"file","privacy":"public","file_type":"image" if mime_type.startswith("image/") else "document","sha256":digest,"size_bytes":size,"mime_type":mime_type,"storage_ref":f"blob://sha256/{digest}","object_path":object_rel,"source_ids":[source_id],"synthetic":True,"summary":f"Generated import-demo file record for synthetic {item['fixture_role']} fixture."})
        attachments.append({"id":f"attachment.importdemo.{idx:03d}","record_type":"attachment","privacy":"public","attachment_type":attachment_type_for_role[item["fixture_role"]],"source_id":source_id,"file_id":file_id,"resolution_status":"found","source_ids":[source_id],"synthetic":True,"summary":f"Generated import-demo attachment occurrence for {file_id}."})
        media_id = f"media.importdemo.{slug}"
        asset = {"id":media_id,"record_type":"media_asset","privacy":"public","media_type":media_type_for_mime.get(mime_type, "document"),"file_id":file_id,"mime_type":mime_type,"source_ids":[source_id],"synthetic":True,"summary":f"Generated import-demo media asset for {file_id}."}
        dims = png_dimensions(src) if mime_type == "image/png" else None
        if dims:
            asset["width"], asset["height"] = dims
        media_assets.append(asset)
        media_links.append({"id":f"medialink.importdemo.{idx:03d}","record_type":"media_link","privacy":"public","source_id":source_id,"target_id":media_id,"target_ref":item["relative_path"],"target_hash":digest,"link_type":link_type_for_role[item["fixture_role"]],"resolution_status":"found","source_ids":[source_id],"synthetic":True,"summary":f"Generated import-demo media link from {source_id} to {media_id}."})
    media_links.append({"id":"medialink.importdemo.missing-audio","record_type":"media_link","privacy":"public","source_id":"source.importdemo.markdown-note","target_ref":"missing-demo-audio.mp3","link_type":"embedded_audio","resolution_status":"missing","source_ids":["source.importdemo.markdown-note"],"synthetic":True,"summary":"Generated missing media case from the Markdown fixture."})

    write_jsonl_file(records_dir / "sources.jsonl", sources)
    write_jsonl_file(records_dir / "files.jsonl", files)
    write_jsonl_file(records_dir / "attachments.jsonl", attachments)
    write_jsonl_file(records_dir / "media_assets.jsonl", media_assets)
    write_jsonl_file(records_dir / "media_links.jsonl", media_links)
    report = {
        "synthetic_only": True,
        "source_fixtures": {"markdown": 1, "mail": 1, "folder_drop": 1},
        "counts": {"sources": len(sources), "files": len(files), "attachments": len(attachments), "media_assets": len(media_assets), "media_links": len(media_links), "objects": len(files)},
        "media_links_by_status": {"found": len(media_links) - 1, "missing": 1},
        "binary_payloads_in_jsonl": False,
        "output_contract": "generated demo records and objects under dist/import-demo; canonical records are not overwritten",
    }
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "import-demo-summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out_root.relative_to(ROOT) if out_root.is_relative_to(ROOT) else out_root}")
    return 0


def render_import_demo_dashboard(args) -> int:
    demo_root = Path(args.input)
    if not (demo_root / "records").exists():
        print(f"import-demo records not found: {demo_root / 'records'}", file=sys.stderr)
        return 1
    report_path = demo_root / "reports" / "import-demo-summary.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    def rows(name: str) -> list[dict]:
        path = demo_root / "records" / f"{name}.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
    sources = rows("sources")
    files = rows("files")
    attachments = rows("attachments")
    assets = rows("media_assets")
    links = rows("media_links")
    files_by_id = {row["id"]: row for row in files}
    assets_by_id = {row["id"]: row for row in assets}
    html_rows = []
    for att in attachments:
        file_rec = files_by_id.get(att["file_id"], {})
        asset = next((a for a in assets if a.get("file_id") == att["file_id"]), {})
        link = next((l for l in links if l.get("target_id") == asset.get("id")), {})
        html_rows.append(
            f"<tr><td><code>{att['source_id']}</code></td><td><code>{att['attachment_type']}</code></td>"
            f"<td><code>{att['file_id']}</code></td><td>{file_rec.get('mime_type','')}</td>"
            f"<td><code>{str(file_rec.get('sha256',''))[:12]}…</code></td><td>{asset.get('media_type','')}</td>"
            f"<td>{link.get('resolution_status','found')}</td></tr>"
        )
    missing_rows = [l for l in links if l.get("resolution_status") != "found"]
    cards = "".join(f"<div class='card'><strong>{k}</strong><span>{v}</span></div>" for k, v in sorted((report.get("counts") or {}).items()))
    missing = "".join(f"<li><code>{m.get('target_ref')}</code> from <code>{m.get('source_id')}</code> → {m.get('resolution_status')}</li>" for m in missing_rows) or "<li>None</li>"
    html = f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>JSONL Vault Spike — Synthetic Import Demo</title>
<style>
body{{font-family:Inter,system-ui,sans-serif;margin:0;background:#0f172a;color:#e2e8f0}}main{{max-width:1120px;margin:0 auto;padding:40px 24px}}h1{{font-size:34px}}.lede{{color:#cbd5e1;max-width:760px;line-height:1.6}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:24px 0}}.card{{background:#111827;border:1px solid #334155;border-radius:14px;padding:16px}}.card span{{display:block;font-size:28px;margin-top:8px;color:#38bdf8}}.flow{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin:28px 0}}.step{{background:#172554;border:1px solid #2563eb;border-radius:14px;padding:14px}}table{{width:100%;border-collapse:collapse;background:#111827;border-radius:14px;overflow:hidden}}th,td{{padding:10px;border-bottom:1px solid #334155;text-align:left;font-size:14px}}th{{background:#1e293b}}code{{color:#93c5fd}}.ok{{color:#86efac}}.warn{{color:#facc15}}</style></head>
<body><main>
<h1>JSONL Vault Spike — synthetic import demo</h1>
<p class=\"lede\">Public-safe end-to-end proof: Markdown embeds + synthetic mail attachments + folder-drop files become generated JSONL records, content-addressed objects, aggregate reports, and this dashboard. No private paths, real attachments, OCR, transcripts, thumbnails, or binary payloads in JSONL.</p>
<section class=\"grid\">{cards}</section>
<section class=\"flow\"><div class=\"step\">1. Synthetic source fixtures</div><div class=\"step\">2. Attachment/media links</div><div class=\"step\">3. File records</div><div class=\"step\">4. SHA-256 objects</div><div class=\"step\">5. Media assets + report</div></section>
<h2>Resolved flow</h2><table><thead><tr><th>Source</th><th>Occurrence</th><th>File</th><th>MIME</th><th>SHA-256</th><th>Media type</th><th>Status</th></tr></thead><tbody>{''.join(html_rows)}</tbody></table>
<h2>Missing/external cases</h2><ul>{missing}</ul>
<p class=\"ok\">Synthetic only: {str(report.get('synthetic_only') is True).lower()} · Binary payloads in JSONL: {str(report.get('binary_payloads_in_jsonl') is True).lower()}</p>
</main></body></html>"""
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    return 0

def build_sqlite(_args=None) -> int:
    DIST.mkdir(exist_ok=True)
    db = DIST / "context.sqlite"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.execute("create table records(id text primary key, record_type text not null, privacy text not null, summary text, json text not null)")
    con.execute("create table relations(subject_id text, relation_type text, object_id text, json text not null)")
    con.execute("create table files(id text primary key, sha256 text not null, mime_type text not null, size_bytes integer not null, storage_ref text not null, json text not null)")
    con.execute("create table attachments(id text primary key, source_id text not null, file_id text not null, attachment_type text not null, resolution_status text not null, json text not null)")
    con.execute("create table media_assets(id text primary key, file_id text not null, media_type text not null, mime_type text not null, json text not null)")
    con.execute("create table media_links(source_id text not null, target_id text not null, link_type text not null, resolution_status text not null, json text not null)")
    for rec in load_records().values():
        con.execute("insert into records values(?,?,?,?,?)", (rec["id"], rec["record_type"], rec.get("privacy"), rec.get("summary") or rec.get("title") or rec.get("display_name"), json.dumps(rec, ensure_ascii=False, sort_keys=True)))
        if rec["record_type"] == "relation":
            con.execute("insert into relations values(?,?,?,?)", (rec["subject_id"], rec["relation_type"], rec["object_id"], json.dumps(rec, ensure_ascii=False, sort_keys=True)))
        if rec["record_type"] == "file":
            con.execute("insert into files values(?,?,?,?,?,?)", (rec["id"], rec["sha256"], rec["mime_type"], rec["size_bytes"], rec["storage_ref"], json.dumps(rec, ensure_ascii=False, sort_keys=True)))
        if rec["record_type"] == "attachment":
            con.execute("insert into attachments values(?,?,?,?,?,?)", (rec["id"], rec["source_id"], rec["file_id"], rec["attachment_type"], rec["resolution_status"], json.dumps(rec, ensure_ascii=False, sort_keys=True)))
        if rec["record_type"] == "media_asset":
            con.execute("insert into media_assets values(?,?,?,?,?)", (rec["id"], rec["file_id"], rec["media_type"], rec["mime_type"], json.dumps(rec, ensure_ascii=False, sort_keys=True)))
        if rec["record_type"] == "media_link":
            con.execute("insert into media_links values(?,?,?,?,?)", (rec["source_id"], rec.get("target_id", ""), rec["link_type"], rec["resolution_status"], json.dumps(rec, ensure_ascii=False, sort_keys=True)))
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
    for sub in [VIEWS / "projects", VIEWS / "entities", VIEWS / "notes", VIEWS / "media", VIEWS / "attachments"]:
        sub.mkdir(parents=True, exist_ok=True)
        for old in sub.rglob("*.md"):
            old.unlink()
    rendered_notes = 0
    for rec in records.values():
        if rec["record_type"] == "project":
            claims = [r for r in records.values() if r.get("record_type") == "claim" and r.get("subject_id") == rec["id"]]
            relations = [r for r in records.values() if r.get("record_type") == "relation" and r.get("subject_id") == rec["id"]]
            lines = [f"# {rec['title']}", "", rec["summary"], "", f"Status: `{rec['status']}`", "", "## Claims", ""]
            lines += [f"- {c['statement']} (confidence: {c['confidence']})" for c in claims] or ["- none"]
            lines += ["", "## Relations", ""]
            lines += [f"- {r['relation_type']}: {r['object_id']}" for r in relations] or ["- none"]
            (VIEWS / "projects" / f"{rec['id'].split('.')[-1]}.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
        if rec["record_type"] == "entity":
            lines = [f"# {rec['display_name']}", "", rec["summary"], "", f"Privacy: `{rec['privacy']}`"]
            (VIEWS / "entities" / f"{rec['id'].split('.')[-1]}.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
        if rec["record_type"] == "note":
            type_dir = VIEWS / "notes" / rec["vault_type"] / rec["category"]
            type_dir.mkdir(parents=True, exist_ok=True)
            (type_dir / f"{rec['id'].split('.')[-1]}.md").write_text(render_note_view(rec), encoding="utf-8")
            rendered_notes += 1
    media_assets = [r for r in records.values() if r.get("record_type") == "media_asset"]
    attachments = [r for r in records.values() if r.get("record_type") == "attachment"]
    media_lines = ["# Synthetic media assets", "", "| id | media_type | file_id | summary |", "| --- | --- | --- | --- |"]
    media_lines += [f"| `{markdown_escape(r['id'])}` | `{markdown_escape(r['media_type'])}` | `{markdown_escape(r['file_id'])}` | {markdown_escape(r.get('summary', ''))} |" for r in sorted(media_assets, key=lambda x: x["id"])] or ["| none | | | |"]
    (VIEWS / "media" / "index.md").write_text("\n".join(media_lines)+"\n", encoding="utf-8")
    attachment_lines = ["# Synthetic attachment occurrences", "", "| id | source_id | file_id | status |", "| --- | --- | --- | --- |"]
    attachment_lines += [f"| `{markdown_escape(r['id'])}` | `{markdown_escape(r['source_id'])}` | `{markdown_escape(r['file_id'])}` | `{markdown_escape(r['resolution_status'])}` |" for r in sorted(attachments, key=lambda x: x["id"])] or ["| none | | | |"]
    (VIEWS / "attachments" / "index.md").write_text("\n".join(attachment_lines)+"\n", encoding="utf-8")
    print(f"rendered markdown views ({rendered_notes} note views, {len(media_assets)} media assets, {len(attachments)} attachments)")
    return 0



def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def png_dimensions(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) >= 24 and header.startswith(b"\x89PNG\r\n\x1a\n") and header[12:16] == b"IHDR":
        return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")
    return None


def inspect_media(args) -> int:
    path = Path(args.path)
    if not path.is_file():
        print(f"file not found: {path}", file=sys.stderr)
        return 1
    size = path.stat().st_size
    if size > args.max_size_bytes:
        print(f"file too large for metadata extraction: {size} > {args.max_size_bytes}", file=sys.stderr)
        return 1
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if mime_type == "application/octet-stream":
        print(f"unsupported file type for metadata extraction: {path.name}", file=sys.stderr)
        return 1
    out = {
        "record_type": "file_metadata",
        "sha256": sha256_file(path),
        "size_bytes": size,
        "mime_type": mime_type,
        "semantic_extraction": "not_implemented",
        "metadata_extractor": {"type": "deterministic", "version": "synthetic-media-metadata-v1"},
    }
    if mime_type == "image/png":
        dims = png_dimensions(path)
        if dims:
            out["width"], out["height"] = dims
    print(json.dumps(out, sort_keys=True))
    return 0


def verify_objects(_args=None) -> int:
    records = load_records()
    errors = []
    checked = 0
    for rec in records.values():
        if rec.get("record_type") != "file":
            continue
        object_path = rec.get("object_path")
        if not object_path:
            errors.append(f"{rec['id']}: missing object_path")
            continue
        if object_path.startswith("/") or ".." in Path(object_path).parts:
            errors.append(f"{rec['id']}: unsafe object_path {object_path!r}")
            continue
        path = DATA_ROOT / object_path
        if not path.exists():
            errors.append(f"{rec['id']}: missing object {object_path}")
            continue
        digest = sha256_file(path)
        if digest != rec.get("sha256"):
            errors.append(f"{rec['id']}: sha256 mismatch {digest} != {rec.get('sha256')}")
        if path.stat().st_size != rec.get("size_bytes"):
            errors.append(f"{rec['id']}: size mismatch {path.stat().st_size} != {rec.get('size_bytes')}")
        checked += 1
    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        return 1
    print(f"OK: verified {checked} content-addressed synthetic objects")
    return 0


def render_media_report(_args=None) -> int:
    records = load_records()
    REPORTS.mkdir(exist_ok=True)
    files = [r for r in records.values() if r.get("record_type") == "file"]
    attachments = [r for r in records.values() if r.get("record_type") == "attachment"]
    media_assets = [r for r in records.values() if r.get("record_type") == "media_asset"]
    media_links = [r for r in records.values() if r.get("record_type") == "media_link"]
    def counts(rows, key):
        out = defaultdict(int)
        for row in rows:
            out[row.get(key, "unknown")] += 1
        return dict(sorted(out.items()))
    report = {
        "synthetic_only": True,
        "binary_payloads_in_jsonl": False,
        "semantic_media_extraction": "proposal-only future work; not implemented",
        "counts": {
            "files": len(files),
            "attachments": len(attachments),
            "media_assets": len(media_assets),
            "media_links": len(media_links),
            "total_file_bytes": sum(r.get("size_bytes", 0) for r in files),
        },
        "files_by_mime_type": counts(files, "mime_type"),
        "attachments_by_status": counts(attachments, "resolution_status"),
        "media_links_by_status": counts(media_links, "resolution_status"),
        "media_assets_by_type": counts(media_assets, "media_type"),
        "privacy_note": "Report is aggregate-only: no local paths, filenames from private sources, OCR text, transcripts, thumbnails, or real media content.",
    }
    out = REPORTS / "media-mvp-summary.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")
    return 0

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Synthetic JSONL vault/context MVP CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    q = sub.add_parser("query"); q.add_argument("terms", nargs="+"); q.add_argument("--limit", type=int, default=10)
    b = sub.add_parser("bundle"); b.add_argument("--goal", required=True); b.add_argument("--limit", type=int, default=8); b.add_argument("--output")
    idemo = sub.add_parser("import-demo"); idemo.add_argument("--fixture-root"); idemo.add_argument("--output", default="dist/import-demo"); idemo.add_argument("--keep-existing", action="store_true")
    dash = sub.add_parser("render-import-demo-dashboard"); dash.add_argument("--input", default="dist/import-demo"); dash.add_argument("--output", default="reports/import-demo-dashboard.html")
    sub.add_parser("build-sqlite")
    sub.add_parser("verify-objects")
    sub.add_parser("render-media-report")
    sub.add_parser("render-views")
    im = sub.add_parser("inspect-media"); im.add_argument("--path", required=True); im.add_argument("--max-size-bytes", type=int, default=1_000_000)
    args = parser.parse_args(argv)
    return {"validate": validate, "query": query, "bundle": bundle, "import-demo": import_demo, "render-import-demo-dashboard": render_import_demo_dashboard, "build-sqlite": build_sqlite, "verify-objects": verify_objects, "render-media-report": render_media_report, "render-views": render_views, "inspect-media": inspect_media}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
