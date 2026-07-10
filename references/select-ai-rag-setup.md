# Select AI NL2SQL and RAG Setup Reference

## Table of contents

1. Readiness levels
2. NL2SQL profile design
3. RAG profile design
4. Vector-index design
5. Smoke tests
6. Common failure modes

## 1. Readiness levels

Use these states consistently:

- **Feature detected**: the package or procedure is visible.
- **Configured**: profiles, credentials, and indexes are present with required attributes.
- **Runtime verified**: provider calls succeed and representative tests produce acceptable results.
- **Production ready**: security, cost, quality, monitoring, and change-management reviews are complete.

Do not collapse these states into one score or one label.

## 2. NL2SQL profile design

A bounded NL2SQL profile should normally include:

- provider and existing credential object name
- provider-specific model, deployment, endpoint, or region attributes
- object list or automated object selection
- `comments=true`
- `annotations=true` when 26ai annotations are used
- `constraints=true`
- `enforce_object_list=true` for constrained use cases
- role and additional instructions

Use a dedicated view when a business rule must always be applied. Examples include revenue recognition filters, security predicates, effective-date rules, and status-code normalization.

`SHOWPROMPT` is the most useful evidence that metadata enrichment is actually included. `SHOWSQL` is the safest first runtime test.

## 3. RAG profile design

Use a separate RAG profile unless there is a reviewed reason to combine responsibilities. Include:

- provider and existing credential object name
- answer-generation model or provider deployment
- embedding model
- optional custom source-URL setting
- vector-index name after the index is created

RAG needs a real source corpus. A normalized application schema with short attributes is not a substitute for policy documents, manuals, tickets, reports, or other retrieval content.

## 4. Vector-index design

A managed Select AI vector index normally requires:

- `vector_db_provider`
- `profile_name`
- `location`
- `object_storage_credential_name`
- chunk size and overlap
- refresh rate
- optional match limit and similarity threshold
- `enable_sources` when citation output is required

`enable_sources` belongs to the vector index. `enable_custom_source_uri` belongs to the profile.

Treat the document URI, filename, business key, effective date, source system, and access classification as source metadata. Validate that citations resolve to useful locations.

## 5. Smoke tests

Run in this order:

1. Inspect stored profile attributes.
2. Run `SHOWPROMPT` for a representative NL2SQL question.
3. Run `SHOWSQL` and manually review tables, joins, filters, grouping, date semantics, and read-only behavior.
4. Run `RUNSQL` only after review.
5. Run RAG `SHOWPROMPT` to inspect retrieval augmentation.
6. Run RAG `NARRATE` against questions with known answers.
7. Check sources, filenames, missing citations, stale documents, and retrieval of intentionally irrelevant documents.
8. Repeat through `DBMS_CLOUD_AI.GENERATE` for stateless clients.

## 6. Common failure modes

- The profile exists but the credential cannot call the provider.
- A provider-specific model or deployment attribute is missing.
- Object scope is too broad and irrelevant tables dominate the prompt.
- Comments contain technical names but no business meaning.
- Annotations exist but `annotations=true` is absent.
- `SHOWPROMPT` does not contain expected metadata.
- A business rule is written only in instructions and is omitted by generated SQL.
- RAG uses a different embedding model for indexing and querying.
- The vector-index pipeline has not completed or refreshed.
- Documents lack stable source metadata or useful citations.
- `enable_sources` is incorrectly placed on the AI profile.
