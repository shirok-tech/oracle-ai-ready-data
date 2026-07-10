# Oracle AI Ready Data Skill

This project evaluates Oracle Database metadata and Oracle AI feature readiness, then generates a reviewable Select AI NL2SQL and Select AI RAG setup package.

## What changed in v0.2

The initial version stopped at readiness reports and setup templates. Version 0.2 adds an assessment-to-runtime workflow:

1. Assess schema metadata and feature visibility.
2. Generate an editable JSON setup configuration.
3. Create separate NL2SQL and RAG profiles.
4. Include comments, annotations, and constraints in NL2SQL metadata enrichment.
5. Create a managed document vector index with chunking, refresh, and source settings.
6. Generate session-based and stateless smoke tests.
7. Collect post-setup evidence and score the stored configuration.

The scripts require Python 3.10 or later and use the standard library only.

## Quick start

### 1. Assess feature readiness

```bash
sql -s admin/****@adb \
  @scripts/oracle_ai_feature_collect.sql HR %

python3 scripts/score_oracle_ai_feature_readiness.py \
  oracle_ai_feature_readiness_HR.out \
  --language ja \
  --output oracle_ai_feature_readiness_HR.md \
  --sql-output oracle_ai_feature_setup_HR.sql \
  --config-output hr_select_ai_config.json
```

### 2. Review the config

Edit `hr_select_ai_config.json` or copy `examples/select_ai_rag_config.json`.

Use existing Oracle credential object names only. Do not place secret values in the file.

For NL2SQL, review:

- provider, model/deployment, and region
- object list
- comments, annotations, and constraints
- business instructions

For RAG, review:

- document location
- embedding model
- object-storage credential object
- chunk size and overlap
- refresh rate
- source/citation settings

### 3. Generate setup SQL

```bash
python3 scripts/generate_select_ai_setup.py \
  hr_select_ai_config.json \
  --output-dir generated_select_ai_setup
```

### 4. Run preflight, setup, and smoke tests

Review every file before running it. Start with `01_preflight.sql`. Keep `RUNSQL` commented until `SHOWSQL` is correct.

### 5. Verify stored configuration

```bash
sql -s admin/****@adb \
  @generated_select_ai_setup/07_collect_verification.sql

python3 scripts/score_select_ai_verification.py \
  select_ai_setup_verification.out \
  --nl2sql-profile HR_NL2SQL \
  --rag-profile HR_RAG \
  --vector-index HR_DOCS_VECIDX \
  --output select_ai_setup_verification.md
```

A passing configuration report still requires runtime testing of provider connectivity, SQL correctness, document ingestion, retrieval quality, and source attribution.

## Important design decisions

- NL2SQL and RAG profiles are separate by default.
- `annotations=true` is included in the NL2SQL profile when Oracle AI Database 26ai annotations are intended for prompt enrichment.
- `enable_sources` is a vector-index attribute.
- `enable_custom_source_uri` is a profile attribute and is optional.
- Relational tables alone do not provide a document corpus for RAG.
- Complex business rules should be implemented in reviewed views when they must be deterministic.

## Repository layout

```text
.
├── SKILL.md
├── README.md
├── agents/openai.yaml
├── docs/
├── examples/
├── profiles/
├── references/
└── scripts/
    ├── oracle_ai_ready_collect.sql
    ├── oracle_ai_feature_collect.sql
    ├── score_oracle_ai_ready_scan.py
    ├── score_oracle_ai_feature_readiness.py
    ├── generate_select_ai_setup.py
    └── score_select_ai_verification.py
```

## Safety

Collectors are read-only. Setup files create or modify AI profiles and vector indexes and can invoke external providers. Review with the DBA, security team, data owner, and application owner before production use.
