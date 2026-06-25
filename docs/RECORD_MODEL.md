# Record model

This repo is a public-safe example. It is not a claim that a real Obsidian vault should be blindly converted note-for-note into JSONL.

## The core distinction

Markdown vaults often contain implicit structure:

- folders imply type;
- templates imply category;
- WikiLinks imply relations;
- prose implies claims;
- checkboxes imply tasks;
- file history implies source/evidence.

The JSONL layer makes those signals explicit and machine-checkable.

```text
Markdown note
  -> source record
  -> entity / project / task / claim / relation / event records
  -> generated Markdown, SQLite, bundles, search indexes
```

## Naming convention

Use `record_type` as the technical JSONL discriminator. Avoid vague discriminator names that can be confused with vault `type`, entity subtype, or category.

| Field | Meaning | Example |
| --- | --- | --- |
| `record_type` | technical record class | `entity`, `source`, `relation`, `claim`, `task`, `note` |
| `<domain>_type` | subtype inside that record class | `entity_type: person`, `source_type: obsidian_markdown` |
| `vault_type` | original/target vault-schema note type | `project`, `reference`, `entry`, `health` |
| `category` | business/schema category | `company`, `person`, `sap`, `finance` |

## Primary keys and foreign keys

Every record gets a stable `id`. References are stored as IDs, not embedded blobs.

```jsonl
{"record_type":"source","id":"source.note.abc123","source_type":"obsidian_markdown","path_hash":"sha256:..."}
{"record_type":"entity","id":"entity.person.alex-example","entity_type":"person","display_name":"Alex Example","source_ids":["source.note.abc123"]}
{"record_type":"entity","id":"entity.company.example-co","entity_type":"company","display_name":"Example Co","source_ids":["source.note.abc123"]}
{"record_type":"relation","id":"relation.synthetic.001","relation_type":"works_at","subject_id":"entity.person.alex-example","object_id":"entity.company.example-co","source_ids":["source.note.abc123"]}
```

Conceptually:

- `id` = primary key;
- `source_ids`, `subject_id`, `object_id`, `project_id`, `entity_id` = foreign keys;
- validation and SQLite projections can enforce referential integrity later.

## Entity categories

Keep one `entities.jsonl` file for entities, not one file per entity subtype.

Good:

```jsonl
{"record_type":"entity","entity_type":"person","category":"professional_contact",...}
{"record_type":"entity","entity_type":"company","category":"customer",...}
{"record_type":"entity","entity_type":"product","category":"software",...}
```

Avoid prematurely splitting into:

```text
persons.jsonl
companies.jsonl
products.jsonl
```

The shared entity contract is valuable: aliases, display name, privacy, source IDs, confidence, created/updated fields, and relations all work the same way.

## What goes where?

| Record type | Question it answers | Example |
| --- | --- | --- |
| `source` | where did this come from? | original Markdown note, chat excerpt, repo file |
| `entity` | who/what is this? | person, company, product, system |
| `relation` | how are two records connected? | works_at, uses_product, part_of, involved_in |
| `claim` | what do we believe/know, with evidence? | ACME uses SAP for finance |
| `task` | what should happen? | follow up, review, migrate, decide |
| `decision` | what was decided and why? | JSON canonical, YAML generated |
| `note` | public-safe synthetic note-shaped fixture | vault-schema type/category coverage |

## Migration strategy

Do not start with a big-bang rewrite.

1. **Inventory sources**
   Create local `source` records for Markdown files. Hash paths/content. Do not expose private paths.

2. **Extract entities**
   Turn existing entity notes into `entity` records. Preserve source links and confidence.

3. **Extract relations**
   Convert WikiLinks, frontmatter references, and obvious fields into `relation` records.

4. **Extract tasks and claims**
   Pull checkboxes into `task` records and evidence-backed statements into `claim` records.

5. **Generate views**
   Generate Markdown/SQLite/context bundles from JSONL. Humans can still read Markdown; agents use typed JSONL.

6. **Promote only where useful**
   If JSONL improves retrieval, provenance, relations, or task reporting, keep it. If not, keep Markdown as the human source and use JSONL as a sidecar.

## What this repo demonstrates

This repo uses `record_type` everywhere in the synthetic JSONL examples and schemas. It includes 10,000 synthetic `note` records that cover every current vault-schema `vault_type/category` pair.

The generated note schema is strict for the public vault-schema matrix:

- unknown `vault_type` values fail validation;
- categories that do not belong to a `vault_type` fail validation;
- areas that do not belong to a `vault_type/category` pair fail validation.

Generated Markdown views prove that Markdown can be rebuilt from JSONL rather than hand-authored as the only source of truth.

Boundary: the repo does not invent strict fields that the public vault-schema does not expose. Deeper extraction contracts such as person-specific fields, purchase amounts, health measurements, or project lifecycle fields should become separate typed record schemas or future generated constraints once those properties are modeled explicitly in the source schema.
