# Synthetic import demo

This repo contains a public-safe fixture set that models the import path a real JSONL Vault would need, without using real vault data or real attachments.

```text
fixtures/import-demo/
  markdown/synthetic-project-note.md      # Markdown source with image/embed/link references
  attachments/diagram-alpha.png           # tiny synthetic Markdown embed object
  mail/message-alpha.json                  # synthetic mail envelope/body/attachment manifest
  mail/attachments/briefing-alpha.pdf      # tiny synthetic mail attachment object
  folder-drop/metrics-alpha.csv            # synthetic folder-drop data file
  folder-drop/readme-alpha.txt             # synthetic folder-drop text file
  folder-drop/drop-manifest.json           # synthetic folder-drop manifest
  manifest.json                            # SHA-256/size inventory for fixture files
```

## Safety boundary

- Every fixture is synthetic.
- No real names, emails, paths, screenshots, customer/vendor files, vault exports, or private attachments are allowed.
- Fixture binaries are tiny and exist only to prove content-addressed object handling.
- JSONL records must store metadata, hashes, references and provenance — never base64 payloads.

## Intended 9000x flow

```text
Markdown note with embeds
+ synthetic mail with attachments
+ folder-drop files
  -> deterministic import-demo command
  -> records/files.jsonl + records/attachments.jsonl + records/media_assets.jsonl + records/media_links.jsonl
  -> objects/sha256/<prefix>/<sha256>.<ext>
  -> aggregate report + browsable dashboard
```

Run the generated demo surface:

```bash
python3 scripts/vaultctx.py import-demo
python3 scripts/vaultctx.py render-import-demo-dashboard
```

Generated outputs:

```text
dist/import-demo/records/*.jsonl
  generated source/file/attachment/media records

dist/import-demo/objects/sha256/...
  generated content-addressed synthetic object store

reports/import-demo-dashboard.html
  browsable public-safe flow: source -> occurrence -> file -> object hash -> media asset
```

Media semantics such as OCR, transcripts and vision labels stay out of canonical records. If added later, they should be proposal records with evidence and review status.
