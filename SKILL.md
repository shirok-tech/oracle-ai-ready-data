---
name: oracle-ai-ready-data
description: assess oracle database schemas and turn readiness findings into reviewable select ai nl2sql and select ai rag setup packages. use when chatgpt needs to inspect sqlcl metadata, score ai-ready comments and relationships, check dbms_cloud_ai or vector capabilities, generate ai profiles that include comments annotations and constraints, create managed vector-index configuration for document rag, produce smoke tests, or verify an existing select ai setup.
---

# Oracle AI Ready Data

## Goal

Evaluate Oracle Database metadata, distinguish feature presence from usable configuration, and generate reviewable SQL that takes a schema from assessment to tested Select AI NL2SQL or Select AI RAG configuration.

Use the user's language in reports. Never request or store provider secrets. Accept only names of existing Oracle credential objects.

## Choose the workflow

1. Use **data assessment** when the request is about comments, constraints, relationships, schema quality, scan readiness, or RAG data candidates.
2. Use **feature assessment** when the request is about DBMS_CLOUD_AI, Select AI, Vector Search, AI Agent, SDG, Feedback, or available procedures.
3. Use **setup generation** when the user wants to create or improve Select AI profiles, connect annotations and comments to NL2SQL, configure Select AI RAG, or produce executable setup SQL.
4. Use **verification** when profiles or vector indexes already exist and the user wants evidence that the stored configuration is complete.

Do not describe an environment as ready merely because packages, profiles, or indexes exist. Runtime smoke tests are required.

## Data assessment

Collect metadata:

```bash
sql -s <user>/<password>@<connect_identifier> \
  @scripts/oracle_ai_ready_collect.sql <schema_owner> <table_like_pattern> <profile>
```

Score it:

```bash
python3 scripts/score_oracle_ai_ready_scan.py \
  oracle_ai_ready_scan_HR_scan.out \
  --profile scan \
  --language ja \
  --output hr_scan_report.md \
  --sql-output hr_scan_improvement.sql
```

Use `rag` instead of `scan` when the user asks about document retrieval, embeddings, vector search, or agent RAG.

Always enforce these gates:

- Table comment coverage must be 100 percent.
- Column comment coverage must be 100 percent.

Treat these gates as the project's chosen policy, not as a universal Oracle product prerequisite.

## Feature assessment

Collect evidence:

```bash
sql -s <user>/<password>@<connect_identifier> \
  @scripts/oracle_ai_feature_collect.sql <schema_owner> <table_like_pattern>
```

Create a report, compatibility SQL template, and editable setup config:

```bash
python3 scripts/score_oracle_ai_feature_readiness.py \
  oracle_ai_feature_readiness_HR.out \
  --language ja \
  --output oracle_ai_feature_readiness_HR.md \
  --sql-output oracle_ai_feature_setup_HR.sql \
  --config-output hr_select_ai_config.json
```

Interpret results precisely:

- Package visible and profile absent means supported-looking but not configured.
- Profile present does not prove provider connectivity or SQL quality.
- Vector capability present does not mean a document corpus exists.
- A relational schema with no suitable long-form documents is not automatically RAG ready.

## Select AI setup generation

Start from `examples/select_ai_rag_config.json` or a config emitted by the feature scorer. Require these inputs:

- Target schema owner.
- Existing AI provider credential object name.
- Supported chat model or provider-specific deployment/endpoint attributes.
- Bounded object list or `object_list_mode=automated` for NL2SQL.
- For RAG: a real document location, an object-storage credential object, an embedding model, and a vector index name.
- Representative NL2SQL and RAG smoke-test prompts.

Generate the package:

```bash
python3 scripts/generate_select_ai_setup.py \
  examples/select_ai_rag_config.json \
  --output-dir generated_select_ai_setup
```

The generator creates:

- `01_preflight.sql`
- `02_create_nl2sql_profile.sql`
- `03_create_rag_profile.sql`
- `04_create_vector_index.sql`
- `05_attach_vector_index.sql`
- `06_smoke_test.sql`
- `07_collect_verification.sql`
- `99_rollback_template.sql`

Run only after reviewing provider, model, region, credential names, object scope, document source, data-governance implications, and generated SQL.

### NL2SQL metadata rules

For the NL2SQL profile, prefer:

- `comments=true`
- `annotations=true` on Oracle AI Database 26ai when annotations are used
- `constraints=true`
- `enforce_object_list=true` for bounded profiles
- Accurate `role` and `additional_instructions`

Use comments or annotations for definitions, aliases, units, and semantic context. Put logic that must never be omitted into reviewed database views rather than relying only on prompt text.

Use `SHOWPROMPT` to confirm that the expected metadata actually reaches prompt construction. This is more reliable than checking only that annotations exist in DDL.

### RAG rules

Use separate profiles for NL2SQL and RAG by default. This keeps SQL metadata scope and document-retrieval configuration independently testable.

Require the RAG profile to contain an embedding model. Require the managed vector index to contain:

- `profile_name`
- `location`
- `object_storage_credential_name`
- `vector_db_provider`
- chunk settings
- refresh settings
- source settings

Place `enable_sources` in the vector-index attributes. Do not set it as an AI-profile attribute. Use `enable_custom_source_uri` on the profile only when custom source URLs are intentionally configured.

The embedding model used for indexing and query embeddings must be compatible. Validate retrieved chunks and citations against known documents.

## Setup verification

Run the generated evidence collector:

```bash
sql -s <user>/<password>@<connect_identifier> \
  @generated_select_ai_setup/07_collect_verification.sql
```

Score stored configuration:

```bash
python3 scripts/score_select_ai_verification.py \
  select_ai_setup_verification.out \
  --nl2sql-profile HR_NL2SQL \
  --rag-profile HR_RAG \
  --vector-index HR_DOCS_VECIDX \
  --output select_ai_setup_verification.md
```

Then run `06_smoke_test.sql` and inspect:

1. Profile and vector-index status.
2. `SHOWPROMPT` metadata enrichment.
3. `SHOWSQL` table selection, joins, filters, and read-only behavior.
4. Optional `RUNSQL` only after reviewing generated SQL.
5. RAG answer grounding, source links, filenames, and known-answer accuracy.
6. Stateless `DBMS_CLOUD_AI.GENERATE` calls for Database Actions, APEX, or connection pools.

## Safety

- Collectors are read-only.
- Setup SQL changes database objects and can invoke external AI providers.
- Do not embed passwords, API keys, tokens, or private keys in configs, SQL, reports, or logs.
- Do not run generated DDL in production without DBA, security, data-owner, and application-owner review.
- Object names, column names, comments, annotations, prompts, retrieved document content, and query results may be sent to an AI provider depending on the action and configuration.
- Keep `RUNSQL` disabled until `SHOWSQL` output has been reviewed.
- Keep rollback statements commented until deletion scope and retained data are understood.

## References

Read these only when needed:

- `references/oracle-ai-ready-checks.md` for schema metrics.
- `references/oracle-ai-feature-checks.md` for feature-state interpretation.
- `references/select-ai-rag-setup.md` for profile, vector-index, and smoke-test design.
- `references/annotation-guidance.md` for comments, annotations, aliases, units, and semantic views.
- `references/markdown-report-template.md` for report structure.
