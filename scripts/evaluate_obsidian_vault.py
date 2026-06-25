#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_OUT = Path('.local/vault-eval')
PRIVATE_PATTERN = re.compile(
    r"(/mnt/[a-z]/Users/[^/]+|/Users/[^/]+|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|[0-9]{8,})",
    re.I,
)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
EXT_LINK_RE = re.compile(r"https?://[^\s)]+")
TASK_RE = re.compile(r"^\s*- \[[ xX]\]", re.M)
SOURCE_HINT_RE = re.compile(r"\b(source|bron|url|link|evidence|bewijs|citation|cite)\b", re.I)


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    result: dict[str, str] = {}
    for raw in match.group(1).splitlines():
        if ':' not in raw or raw.startswith(' ') or raw.startswith('-'):
            continue
        key, value = raw.split(':', 1)
        result[key.strip()] = value.strip().strip('"\'')
    return result


def pct(n: int, d: int) -> float:
    return round((n / d * 100), 1) if d else 0.0


def scorecard(metrics: dict) -> dict:
    total = metrics['markdown_files_scanned']
    jsonl_schema = pct(metrics['notes_with_type'] + metrics['notes_with_category'], total * 2)
    provenance = pct(metrics['notes_with_source_hint'], total)
    relation_density = round(metrics['wikilinks_count'] / total, 2) if total else 0
    actionability = pct(metrics['notes_with_tasks'], total)
    md_baseline = round(min(100, 35 + relation_density * 8 + provenance * 0.2 + actionability * 0.2), 1)
    jsonl_target = round(min(100, jsonl_schema * 0.35 + provenance * 0.25 + min(100, relation_density * 20) * 0.2 + actionability * 0.2), 1)
    return {
        'markdown_baseline_score': md_baseline,
        'jsonl_structured_target_score': jsonl_target,
        'schema_coverage_pct': jsonl_schema,
        'provenance_hint_pct': provenance,
        'task_actionability_pct': actionability,
        'relations_per_note': relation_density,
        'interpretation': 'JSONL sidecar/migration is promising if target score exceeds baseline and provenance/schema gaps are visible.'
    }


def render_html(metrics: dict, card: dict) -> str:
    generated_at = html.escape(metrics['generated_at'])
    rows = [
        ('Markdown files scanned', metrics['markdown_files_scanned']),
        ('Frontmatter parse errors', metrics['frontmatter_parse_errors']),
        ('Notes with type', metrics['notes_with_type']),
        ('Notes with category', metrics['notes_with_category']),
        ('Notes with source/evidence hint', metrics['notes_with_source_hint']),
        ('WikiLinks', metrics['wikilinks_count']),
        ('External links', metrics['external_links_count']),
        ('Task checkboxes', metrics['task_checkbox_count']),
    ]
    row_html = ''.join(f'<tr><td>{html.escape(k)}</td><td>{v}</td></tr>' for k, v in rows)
    md_score = card['markdown_baseline_score']
    jsonl_score = card['jsonl_structured_target_score']
    delta = round(jsonl_score - md_score, 1)
    verdict = 'JSONL geeft hier meetbare meerwaarde' if delta > 5 else 'JSONL is hier nog niet overtuigend beter'
    return f'''<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>JSONL vs Obsidian Markdown - lokale vergelijking</title>
<style>
:root {{ color-scheme: dark; --bg:#080b12; --panel:#101724; --panel2:#0d1320; --ink:#edf4ff; --muted:#9aa8bd; --line:#243044; --blue:#7dd3fc; --green:#86efac; --amber:#fcd34d; --violet:#c4b5fd; }}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 20% 0%,#172554 0,#080b12 34rem),var(--bg);color:var(--ink);font:16px/1.55 ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:56px 24px 72px}} .eyebrow{{color:var(--blue);font:700 12px/1 ui-monospace,monospace;letter-spacing:.16em;text-transform:uppercase}}
h1{{font-size:clamp(38px,6vw,78px);line-height:.95;margin:16px 0 20px;letter-spacing:-.055em;max-width:980px}} .lead{{font-size:clamp(18px,2vw,24px);color:#cbd7ea;max-width:860px}}
.grid{{display:grid;grid-template-columns:1.1fr .9fr;gap:22px;margin-top:34px}} .card{{background:linear-gradient(180deg,rgba(255,255,255,.055),rgba(255,255,255,.025));border:1px solid var(--line);border-radius:28px;padding:26px;box-shadow:0 24px 80px rgba(0,0,0,.32)}}
.score{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} .scorebox{{background:var(--panel2);border:1px solid var(--line);border-radius:22px;padding:22px}} .num{{font-size:54px;font-weight:800;letter-spacing:-.06em}} .muted{{color:var(--muted)}}
.delta{{display:inline-flex;gap:8px;align-items:center;margin-top:14px;padding:8px 12px;border-radius:999px;background:rgba(134,239,172,.12);color:var(--green);font-weight:700}}
table{{width:100%;border-collapse:collapse;margin-top:12px}} td{{padding:12px 0;border-bottom:1px solid var(--line)}} td:last-child{{text-align:right;font-variant-numeric:tabular-nums;color:var(--ink);font-weight:700}}
.flow{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:22px}} .step{{border:1px solid var(--line);border-radius:20px;padding:18px;background:#0b1220}} .step b{{color:var(--blue)}}
.bars{{display:grid;gap:12px;margin-top:18px}} .bar{{display:grid;grid-template-columns:180px 1fr 54px;gap:12px;align-items:center}} .track{{height:12px;background:#111827;border-radius:999px;overflow:hidden;border:1px solid #1f2937}} .fill{{height:100%;background:linear-gradient(90deg,var(--blue),var(--violet));border-radius:999px}}
.callout{{margin-top:24px;padding:22px;border:1px solid rgba(252,211,77,.35);background:rgba(252,211,77,.08);border-radius:24px}} code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:#bfdbfe}}
@media(max-width:860px){{.grid,.score,.flow{{grid-template-columns:1fr}} .bar{{grid-template-columns:1fr}} h1{{font-size:42px}}}}
</style>
</head>
<body><main>
  <div class="eyebrow">Local-only · geen GitHub data export · {generated_at}</div>
  <h1>JSONL is niet mooier dan Markdown. Het moet aantoonbaar beter zijn voor agents.</h1>
  <p class="lead">Deze lokale vergelijking scant je Obsidian vault read-only en rapporteert alleen aggregaten. Geen titels, paden, bodytekst, namen of prive-data worden in dit HTML-bestand opgenomen.</p>
  <section class="grid">
    <div class="card">
      <h2>Scorecard</h2>
      <div class="score">
        <div class="scorebox"><div class="muted">Native Obsidian/Markdown</div><div class="num">{md_score}</div><div class="muted">Sterk voor menselijk lezen en schrijven; zwakker op harde contracten/provenance.</div></div>
        <div class="scorebox"><div class="muted">JSONL + generated Markdown</div><div class="num">{jsonl_score}</div><div class="muted">Sterk voor agents: typed records, relaties, validatie, rebuildable views.</div></div>
      </div>
      <div class="delta">Delta {delta:+} · {html.escape(verdict)}</div>
      <div class="bars">
        <div class="bar"><span>Schema coverage</span><div class="track"><div class="fill" style="width:{card['schema_coverage_pct']}%"></div></div><b>{card['schema_coverage_pct']}%</b></div>
        <div class="bar"><span>Provenance hints</span><div class="track"><div class="fill" style="width:{card['provenance_hint_pct']}%"></div></div><b>{card['provenance_hint_pct']}%</b></div>
        <div class="bar"><span>Actionability</span><div class="track"><div class="fill" style="width:{card['task_actionability_pct']}%"></div></div><b>{card['task_actionability_pct']}%</b></div>
      </div>
    </div>
    <div class="card"><h2>Vault aggregate readback</h2><table>{row_html}</table></div>
  </section>
  <section class="card" style="margin-top:22px">
    <h2>Wat JSONL toevoegt boven native Obsidian</h2>
    <div class="flow">
      <div class="step"><b>1 · Contracten</b><br/>JSON Schema zegt exact wat een record is. Markdown frontmatter kan stilletjes drift krijgen.</div>
      <div class="step"><b>2 · Provenance</b><br/>Claims kunnen verplicht naar <code>source_ids</code> en <code>evidence_ids</code> wijzen.</div>
      <div class="step"><b>3 · Runtime</b><br/>SQLite/bundles/embeddings worden rebuildable output in plaats van handwerk.</div>
      <div class="step"><b>4 · Views</b><br/>Markdown blijft bestaan als generated export/view, niet als enige waarheid.</div>
    </div>
    <div class="callout"><b>Beslisregel:</b> migreer niet omdat JSONL technisch netter is. Migreer alleen waar het betere retrieval, traceerbare claims, expliciete relaties of betere taak/action reporting oplevert. Anders blijft Markdown de human UI en wordt JSONL een sidecar.</div>
  </section>
</main></body></html>'''


def main() -> int:
    ap = argparse.ArgumentParser(description='Read-only aggregate Obsidian vault evaluation. Writes local-only redacted reports.')
    ap.add_argument('--vault', type=Path, default=None, help='Local vault root. Can also be set with VAULT_ROOT.')
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT)
    ap.add_argument('--limit', type=int, default=250)
    args = ap.parse_args()
    import os
    vault_arg = args.vault or (Path(os.environ['VAULT_ROOT']) if os.environ.get('VAULT_ROOT') else None)
    if vault_arg is None:
        raise SystemExit('provide --vault or VAULT_ROOT')
    vault = vault_arg.resolve()
    if not vault.exists() or not vault.is_dir():
        raise SystemExit(f'vault not found: {vault}')
    files = []
    for p in vault.rglob('*.md'):
        if '.obsidian' in p.parts or '.git' in p.parts:
            continue
        files.append(p)
        if len(files) >= args.limit:
            break
    metrics = Counter()
    for path in files:
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except Exception:
            metrics['read_errors'] += 1
            continue
        fm = parse_frontmatter(text)
        metrics['markdown_files_scanned'] += 1
        if text.startswith('---') and not fm:
            metrics['frontmatter_parse_errors'] += 1
        if 'type' in fm:
            metrics['notes_with_type'] += 1
        if 'category' in fm:
            metrics['notes_with_category'] += 1
        if SOURCE_HINT_RE.search(text) or any(k in fm for k in ['source','sources','url','evidence']):
            metrics['notes_with_source_hint'] += 1
        if TASK_RE.search(text):
            metrics['notes_with_tasks'] += 1
        metrics['wikilinks_count'] += len(WIKILINK_RE.findall(text))
        metrics['external_links_count'] += len(EXT_LINK_RE.findall(text))
        metrics['task_checkbox_count'] += len(TASK_RE.findall(text))
    for key in ['markdown_files_scanned','frontmatter_parse_errors','notes_with_type','notes_with_category','notes_with_source_hint','notes_with_tasks','wikilinks_count','external_links_count','task_checkbox_count']:
        metrics.setdefault(key, 0)
    result = dict(metrics)
    result['vault_root_redacted'] = '[REDACTED_LOCAL_VAULT]'
    result['sample_limit'] = args.limit
    result['generated_at'] = datetime.now(timezone.utc).isoformat()
    # Intentionally do not include raw category/type values in local reports.
    # Real vault categories can be personal taxonomy and must not leak via JSON/HTML.
    card = scorecard(result)
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    (out/'aggregate-metrics.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    (out/'scorecard.json').write_text(json.dumps(card, indent=2, ensure_ascii=False)+'\n')
    html_text = render_html(result, card)
    if PRIVATE_PATTERN.search(html_text):
        raise SystemExit('privacy guard blocked HTML output')
    (out/'value-prop-comparison.html').write_text(html_text, encoding='utf-8')
    print(json.dumps({'ok': True, 'out': str(out), 'files_scanned': result['markdown_files_scanned'], 'html': str(out/'value-prop-comparison.html'), 'privacy': 'aggregate-only'}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
