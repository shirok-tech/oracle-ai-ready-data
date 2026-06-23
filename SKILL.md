---
name: oracle-ai-ready-data
description: assess oracle database schemas for ai-ready data and oracle ai feature readiness using sqlcl output. use when the user asks to evaluate oracle database schemas, scan/rag readiness, mandatory table and column comments, metadata quality, select ai/nl2sql readiness, select ai rag, oracle ai vector search, dbms_cloud_ai, dbms_cloud_ai_agent, synthetic data generation, auto object selection, or improvement/setup sql for oracle ai use cases.
---

# Oracle AI Ready Data

## Purpose

Use this skill to evaluate Oracle Database schemas and Oracle AI feature readiness from SQLcl-collected metadata. Produce Markdown reports with scores, mandatory comment-gate results, prioritized gaps, and improvement/setup SQL.

The skill supports two complementary workflows:

1. **Data readiness**: `scan` and `rag` profiles for schema/table metadata quality.
2. **Feature readiness**: checks whether Oracle AI capabilities such as Select AI / NL2SQL, Select AI RAG, Oracle AI Vector Search, AI Agent, SDG, Feedback, and Auto Object Selection are visible and configured.

Translation and generic chat are intentionally low priority and are not primary readiness targets.

## Default workflow

1. Determine the request type.
   - **Schema quality / comments / constraints / HR vs BAD_AI_READY / scan / rag** → use the data readiness workflow.
   - **Which Oracle AI features are available / Select AI / NL2SQL / DBMS_CLOUD_AI / RAG / Vector Search / AI Agent / SDG** → use the feature readiness workflow.
2. Determine scope.
   - Required: schema owner.
   - Optional: table name pattern, profile, existing SQLcl spool file.
   - Default table pattern: `%`.
   - Default data readiness profile: `scan` unless the user mentions RAG, vector search, embeddings, retrieval, chatbot, or agents over table data; then use `rag`.
3. Collect metadata when the user has not provided a SQLcl spool file.
4. Parse and score with the bundled Python scorer when a spool file is available.
5. Produce a Markdown report and review-before-run improvement/setup SQL.

Use Japanese when the user writes in Japanese; otherwise use the user's language.

## Data readiness workflow: scan / rag

Use this for evaluating whether tables and columns are ready for AI/RAG usage from a metadata-quality perspective.

Collection command:

```bash
sql -s <user>/<password>@<connect_identifier> @scripts/oracle_ai_ready_collect.sql <schema_owner> <table_like_pattern> <profile>
```

Examples:

```bash
sql -s ai_audit/****@dbhost:1521/service @scripts/oracle_ai_ready_collect.sql HR % scan
sql -s ai_audit/****@dbhost:1521/service @scripts/oracle_ai_ready_collect.sql HR EMP% rag
```

The collector spools `oracle_ai_ready_scan_<schema>_<profile>.out`.

Scoring command:

```bash
python3 scripts/score_oracle_ai_ready_scan.py \
  oracle_ai_ready_scan_HR_scan.out \
  --profile scan \
  --language ja \
  --output hr_scan_report.md \
  --sql-output hr_scan_improvement.sql
```

For RAG:

```bash
python3 scripts/score_oracle_ai_ready_scan.py \
  oracle_ai_ready_scan_HR_rag.out \
  --profile rag \
  --language ja \
  --output hr_rag_report.md \
  --sql-output hr_rag_improvement.sql
```

### Required scoring behavior

Always evaluate these mandatory gates:

- Table comment coverage: target 100% of in-scope tables.
- Column comment coverage: target 100% of in-scope columns.

If either mandatory gate is below 100%, mark the readiness gate as `fail`, even when the numeric score is otherwise acceptable. This reflects the user's explicit requirement that table and column comments are mandatory.

Use the profile weights and metric definitions in `references/oracle-ai-ready-checks.md`. For most tasks, do not load the reference until scoring or explaining a metric is needed.

## Feature readiness workflow: Oracle AI capabilities

Use this for evaluating whether the current Oracle Database environment can use Oracle AI features and what setup is still missing.

Collection command:

```bash
sql -s <user>/<password>@<connect_identifier> @scripts/oracle_ai_feature_collect.sql <schema_owner> <table_like_pattern>
```

Example:

```bash
sql -s admin/****@adb @scripts/oracle_ai_feature_collect.sql HR %
```

The collector spools `oracle_ai_feature_readiness_<schema>.out`.

Scoring command:

```bash
python3 scripts/score_oracle_ai_feature_readiness.py \
  oracle_ai_feature_readiness_HR.out \
  --language ja \
  --output oracle_ai_feature_readiness_HR.md \
  --sql-output oracle_ai_feature_setup_HR.sql
```

### Feature readiness interpretation

Distinguish these cases clearly:

- **AI feature exists but setup is missing**: `DBMS_CLOUD_AI`, `DBMS_CLOUD_AI_AGENT`, or vector procedures are visible, but AI profiles, credentials, vector indexes, or agent definitions are missing.
- **Select AI blocked**: `DBMS_CLOUD_AI` is not visible. Do not imply that `CREATE_PROFILE` can work. Provide environment/support/privilege checks instead.
- **Native Vector Search available without Select AI**: `DBMS_VECTOR` or `DBMS_VECTOR_CHAIN` is visible but `DBMS_CLOUD_AI` is not. Recommend native vector smoke tests or application-managed RAG rather than Select AI setup SQL.
- **Autonomous AI Database / Autonomous AI Lakehouse pattern**: `DBMS_CLOUD_AI` and `DBMS_CLOUD_AI_AGENT` may be visible even when no AI profile exists. Report this as “AI機能あり・未設定”, not “AI機能なし”.

Prioritize these features:

1. Select AI / NL2SQL
2. Select AI RAG
3. Oracle AI Vector Search / Vector Index
4. Select AI Agent SQL tool
5. Select AI Agent RAG tool
6. Synthetic Data Generation (SDG)
7. NL2SQL Feedback
8. Auto Object Selection

Do not prioritize Translation / generic Chat unless the user explicitly asks.

## Report requirements

Data readiness reports must include:

- Executive summary.
- Scope and assumptions.
- Explanation of each AI-ready dimension.
- Scorecard by AI-ready dimension.
- Metrics detail with explanations.
- Mandatory comment gate result.
- Prioritized findings.
- Improvement SQL with reason, purpose, and review notes.
- Manual review items.

Feature readiness reports must include:

- Executive summary that separates “feature exists” from “ready to use”.
- Environment evidence: DB/PDB, session user, version evidence, compatible parameter when available.
- Feature-by-feature status table.
- Package/procedure evidence.
- AI profile and vector/RAG detection results.
- Key gaps.
- Setup SQL templates only when the required package is visible.
- Next actions tailored to Select AI, native vector search, or missing-feature cases.

## Improvement and setup SQL rules

Generate executable SQL only for safe, reviewable changes. Use quoted identifiers for owner, table, and column names. Keep statements idempotence-aware by including comments that the user must review existing metadata before running.

Preferred data readiness improvement SQL examples:

```sql
COMMENT ON TABLE "OWNER"."TABLE_NAME" IS 'TODO: describe business meaning, grain, refresh cadence, and AI usage notes.';
COMMENT ON COLUMN "OWNER"."TABLE_NAME"."COLUMN_NAME" IS 'TODO: define meaning, units, null semantics, allowed values, and sensitivity.';
```

For potentially disruptive changes such as adding primary keys, adding timestamp columns, creating vector columns/indexes, masking, redaction, or privilege changes, provide templates only and clearly mark them as candidate SQL requiring DBA/application-owner review.

For feature readiness setup SQL:

- Only output `DBMS_CLOUD_AI.CREATE_PROFILE` templates when `DBMS_CLOUD_AI` is visible.
- Only output `DBMS_CLOUD_AI.CREATE_VECTOR_INDEX` templates when `CREATE_VECTOR_INDEX` is visible.
- Only output `DBMS_CLOUD_AI_AGENT` placeholders when `DBMS_CLOUD_AI_AGENT` is visible.
- If only `DBMS_VECTOR` / `DBMS_VECTOR_CHAIN` is visible, output native vector smoke-test SQL instead.

## Bundled resources

- `scripts/oracle_ai_ready_collect.sql`: SQLcl metadata collector for schema data readiness.
- `scripts/score_oracle_ai_ready_scan.py`: Parser and scorer for scan/rag SQLcl output.
- `scripts/oracle_ai_feature_collect.sql`: SQLcl collector for Select AI, RAG, Vector Search, Agent, SDG, Feedback, and Auto Object Selection feature evidence.
- `scripts/score_oracle_ai_feature_readiness.py`: Parser and scorer for Oracle AI feature readiness output.
- `references/oracle-ai-ready-checks.md`: profiles, dimensions, metrics, and interpretation guidance.
- `references/oracle-ai-feature-checks.md`: feature readiness checks and status interpretation.
- `references/markdown-report-template.md`: default report structure.
- `profiles/scan.yaml`: scan profile weights.
- `profiles/rag.yaml`: rag profile weights.
- `profiles/feature-readiness.yaml`: feature readiness priority weights.
