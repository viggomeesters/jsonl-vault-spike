# Vault evaluation plan

This document defines how to test the JSONL-first spike against a real Obsidian vault without publishing or committing private data.

## Safety boundary

The public repo must stay synthetic. Real vault reads are allowed only as local read-only dry-runs. Do not commit generated reports that contain note titles, paths, body text, names, emails, chat ids, filesystem paths, or screenshots.

Recommended local output paths for real-vault experiments:

```text
.local/vault-eval/
/tmp/jsonl-vault-eval/
```

Both should remain untracked.

## What “better than Markdown” must prove

A JSONL-first vault is better only if it beats Markdown on measurable agent tasks:

| Capability | Markdown vault baseline | JSONL-first target | Proof |
| --- | --- | --- | --- |
| Schema validity | YAML/frontmatter may drift | every record validates against JSON Schema | validation error count |
| Retrieval | keyword/file search over prose | typed fields + source/evidence links | golden-query hit rate |
| Provenance | source often implicit | `source_ids` / `evidence_ids` required | orphan-reference count |
| Freshness | stale claims hard to find | review timestamps and freshness fields | stale-claim report |
| Transformability | views are hand-written | Markdown/SQLite/bundles generated | round-trip/render smoke |
| Privacy | accidental private exports possible | explicit privacy + redaction gates | privacy scan |

## Phase 1 — read-only inventory

Run a local-only script against a bounded subset of the vault. The first slice should be small and representative:

```bash
python3 scripts/evaluate_obsidian_vault.py --vault /path/to/local/vault --limit 75 --out .local/vault-eval
```

The script writes a styled local report to:

```text
.local/vault-eval/value-prop-comparison.html
```

That HTML is intentionally local-only and ignored by git.

- 10–25 project notes;
- 10–25 source/reference notes;
- 10–25 task/entry notes;
- optionally one month of daily/entry notes.

Collect only aggregate metrics:

```json
{
  "markdown_files_scanned": 75,
  "frontmatter_parse_errors": 0,
  "notes_with_type": 68,
  "notes_with_category": 61,
  "notes_with_source": 22,
  "wikilinks_count": 310,
  "external_links_count": 48
}
```

Do not write note titles/body/path lists into public artifacts.

## Phase 2 — local JSONL dry-run conversion

Convert the bounded subset into local `.local/vault-eval/records/*.jsonl` records:

- `source` records for original markdown files;
- `note` records for typed note metadata;
- `claim` records only when a claim is explicit enough to cite;
- `relation` records for WikiLinks and source references;
- `task` records for actionable items.

Dry-run output should include:

```text
.local/vault-eval/records/*.jsonl
.local/vault-eval/reports/conversion-summary.json
.local/vault-eval/views/markdown/
.local/vault-eval/context.sqlite
```

## Phase 3 — Markdown generated from JSONL

For the converted subset, generate Markdown views from JSONL and compare to the original Markdown:

- frontmatter fields preserved or normalized;
- source/evidence references visible;
- WikiLink-like relations represented;
- no private data written outside `.local/`;
- generated Markdown is readable enough for Obsidian if needed.

The spike already proves this for synthetic data via:

```bash
python3 scripts/vaultctx.py render-views
```

This generates:

```text
views/markdown/projects/*.md
views/markdown/entities/*.md
views/markdown/notes/<type>/<category>/*.md
```

## Phase 4 — retrieval benchmark

Create 20–50 private local golden queries from real use cases, for example:

```jsonl
{"query":"welke beslissing hadden we over vault schema json canonical","expected_ids":["claim....","project...."]}
{"query":"open taken rond hypotheek of woning","expected_ids":["task...."]}
```

Compare:

1. Markdown baseline: filename/content search.
2. JSONL baseline: typed field search.
3. JSONL + SQLite: structured query.
4. Later: JSONL + embeddings/graph.

Report only aggregate scores publicly:

```json
{"markdown_hit_rate":0.52,"jsonl_hit_rate":0.78,"sqlite_hit_rate":0.84}
```

## Phase 5 — go/no-go criteria

Continue migration only if the bounded dry-run shows at least two concrete improvements:

- fewer ambiguous/orphaned links;
- higher golden-query hit rate;
- better source/evidence traceability;
- easier stale/open-task reporting;
- generated Markdown remains readable enough as an export/view;
- no privacy leaks in local reports.

If JSONL does not beat Markdown on retrieval/provenance/actionability, keep Obsidian/Markdown as the human source and use JSONL only as a generated sidecar.
