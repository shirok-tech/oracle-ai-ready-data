# Oracle AI Ready Data Skill

This project evaluates Oracle Database metadata and Oracle AI feature readiness, generates Markdown reports and optional self-contained HTML reports, then creates a reviewable Select AI NL2SQL and Select AI RAG setup package.

## What changed in v0.4.0

Version 0.4.0 adds **AI Semantics Readiness (Advisory)**: optional collection of
table/column annotations and column domain associations, distinct-column coverage,
and dictionary-based provenance in Japanese/English Markdown and self-contained
HTML. Collection success with zero rows is distinguished from missing evidence,
confirmed unsupported/denied access, undetermined unavailability, and errors.
Existing score formulas, weights, COMMENT gates, and RAG behavior are unchanged.

The existing profile generator already supports `annotations=true` and SHOWPROMPT;
no new profile attribute or model default is introduced. Annotation counts do not
prove business meaning or SQL correctness. Runtime evidence remains a separate
human review, with a [recording template](references/semantics-evidence-template.md).

See [optional collection and reporting](docs/USAGE.md#optional-annotationdomain-assessment-v040),
[format and limitations](references/annotation-guidance.md), and the
[part 3 reproduction package](examples/bad_ai_ready_part3/README.md).
The part 3 results describe prior user observations, not executions by this update.
The user completed Database revalidation on Oracle AI Database 26ai 23.26.3.3.0
with SQLcl 25.4 on **2026-09-23**, including Japanese/English HTML visual checks.
See the [final validation report](docs/v0.4-validation-complete.md),
[v0.4.0 release notes](docs/releases/v0.4.0.md), and the
[part 3 article manuscript](docs/articles/oracle-ai-ready-data-part3.md).
The article is prepared for Qiita; no Qiita publication is claimed here.

Generate the optional read-only collector locally, then review and execute it in
an authorized SQLcl session using the same scope as the normal scan:

```bash
python3 scripts/generate_semantics_collector.py \
  --owner HR --table-like '%' \
  --output collect_semantics.sql --spool-file hr_semantics_r01.json

python3 scripts/score_oracle_ai_ready_scan.py oracle_ai_ready_scan_HR_scan.out \
  --semantics-input hr_semantics_r01.json --language ja \
  --output hr_scan_report.md --html-output hr_scan_report.html
```

**After updating, regenerate previously generated semantics SQL.** The normal
collector disables ECHO before SPOOL, and the scorer rejects malformed scans
instead of treating them as empty inventories. Preserve old evidence and
recollect rejected scans in a fresh output directory.

A valid zero-object scope retains the legacy score/gate behavior, including
0.97/pass; it is **not evidence that any data is AI Ready**. Runtime SQL
correctness remains a separate verification step. Revalidation used the existing
lab; the complete newly generated DDL package was not rerun in a new environment.

## What changed in v0.3

Version 0.3 improves the data-readiness report workflow without changing the
existing readiness score formulas:

1. Generate next actions only from unresolved findings.
2. Review comment quality separately from comment presence.
3. Flag numeric/date-like values stored in text columns for manual review.
4. Generate an optional self-contained HTML report with `--html-output`.
5. Add BAD_AI_READY before/after regression tests and report samples.

Comment-quality and semantic-type findings are advisory in v0.3 and do not
change the existing dimension or overall scores.

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

### 1. Assess data readiness

```bash
sql -s admin/****@adb \
  @scripts/oracle_ai_ready_collect.sql HR % scan

python3 scripts/score_oracle_ai_ready_scan.py \
  oracle_ai_ready_scan_HR_scan.out \
  --profile scan \
  --language ja \
  --output oracle_ai_ready_scan_HR.md \
  --html-output oracle_ai_ready_scan_HR.html \
  --sql-output oracle_ai_ready_improvement_HR.sql
```

### 2. Assess feature readiness

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

### 3. Review the config

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

### 4. Generate setup SQL

```bash
python3 scripts/generate_select_ai_setup.py \
  hr_select_ai_config.json \
  --output-dir generated_select_ai_setup
```

### 5. Run preflight, setup, and smoke tests

Review every file before running it. Start with `01_preflight.sql`. Save and review
the `SHOWSQL` output, then execute that saved SQL to validate it. Optional `RUNSQL`
is a separate generation trial; keep it commented by default.

### 6. Verify stored configuration

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
    ├── generate_semantics_collector.py
    ├── oracle_ai_semantics_collect.sql.in
    ├── oracle_ai_feature_collect.sql
    ├── score_oracle_ai_ready_scan.py
    ├── score_oracle_ai_feature_readiness.py
    ├── generate_select_ai_setup.py
    └── score_select_ai_verification.py
```

## Safety

Collectors are read-only. Setup files create or modify AI profiles and vector indexes and can invoke external providers. Review with the DBA, security team, data owner, and application owner before production use.
