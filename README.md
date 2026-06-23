# Oracle AI Ready Data Skill

Oracle Database schemas and Oracle AI feature readiness can be evaluated from SQLcl output and converted into Markdown reports with review-before-run improvement SQL.

This repository is packaged as a ChatGPT Skill, but the scripts can also be used directly from a shell.

## What this evaluates

### 1. Data readiness

Use `scan` and `rag` profiles to evaluate whether a schema has enough metadata and structure for AI use cases.

Key checks include:

- Mandatory table comment coverage
- Mandatory column comment coverage
- Primary key, foreign key, relationship, and constraint coverage
- Optimizer statistics coverage
- Freshness columns such as `UPDATED_AT` or `LAST_UPDATE_DATE`
- RAG candidate text columns
- VECTOR / embedding candidate columns
- Sensitive column candidates and broad grants

### 2. Oracle AI feature readiness

Use feature readiness to determine whether the current database environment exposes and has configured Oracle AI features.

Priority features:

- Select AI / NL2SQL
- Select AI RAG
- Oracle AI Vector Search / Vector Index
- Select AI Agent SQL tool
- Select AI Agent RAG tool
- Synthetic Data Generation (SDG)
- NL2SQL Feedback
- Auto Object Selection

Translation and generic Chat are intentionally out of the default priority scope.

## Requirements

- SQLcl for collection
- Python 3.6 or later for report generation
- Oracle Database user with dictionary visibility for the target schema
- Optional: DBA/SYSDBA or AI-enabled ADMIN user for feature readiness confirmation

The Python scripts use only the standard library.

## Quick start: scan profile

```bash
sql -s ai_audit/****@dbhost:1521/service @scripts/oracle_ai_ready_collect.sql HR % scan

python3 scripts/score_oracle_ai_ready_scan.py \
  oracle_ai_ready_scan_HR_scan.out \
  --profile scan \
  --language ja \
  --output hr_scan_report.md \
  --sql-output hr_scan_improvement.sql
```

## Quick start: RAG profile

```bash
sql -s ai_audit/****@dbhost:1521/service @scripts/oracle_ai_ready_collect.sql HR % rag

python3 scripts/score_oracle_ai_ready_scan.py \
  oracle_ai_ready_scan_HR_rag.out \
  --profile rag \
  --language ja \
  --output hr_rag_report.md \
  --sql-output hr_rag_improvement.sql
```

## Quick start: Oracle AI feature readiness

```bash
sql -s admin/****@adb @scripts/oracle_ai_feature_collect.sql HR %

python3 scripts/score_oracle_ai_feature_readiness.py \
  oracle_ai_feature_readiness_HR.out \
  --language ja \
  --output oracle_ai_feature_readiness_HR.md \
  --sql-output oracle_ai_feature_setup_HR.sql
```

## How to read feature readiness

A common confusion is the difference between “feature not present” and “feature present but not configured”.

| Result pattern | Meaning |
|---|---|
| `DBMS_CLOUD_AI visible = yes`, no AI profile | Select AI exists, but AI profile/credential/model setup is still needed. |
| `DBMS_CLOUD_AI visible = no`, `DBMS_VECTOR visible = yes` | Native Vector Search may be available, but Select AI is not visible. Use native vector or application-managed RAG. |
| `DBMS_CLOUD_AI visible = no`, `DBMS_VECTOR visible = no` | Current user cannot confirm major Oracle AI capabilities. Check service type, release, component installation, and privileges. |

## Repository layout

```text
.
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── docs/
│   ├── USAGE.md
│   └── ENVIRONMENT_NOTES.md
├── examples/
│   └── bad_ai_ready_schema.sql
├── profiles/
│   ├── scan.yaml
│   ├── rag.yaml
│   └── feature-readiness.yaml
├── references/
│   ├── markdown-report-template.md
│   ├── oracle-ai-ready-checks.md
│   └── oracle-ai-feature-checks.md
└── scripts/
    ├── oracle_ai_ready_collect.sql
    ├── oracle_ai_feature_collect.sql
    ├── score_oracle_ai_ready_scan.py
    └── score_oracle_ai_feature_readiness.py
```

## Safety notes

Collectors are read-only. Generated improvement/setup SQL is for review. Do not run DDL, grants, revokes, DBMS_STATS, Select AI profile setup, vector index creation, or agent setup in production without DBA, security, and application-owner review.

Do not commit real `.out` files, logs, credentials, connection strings, API keys, or generated reports that contain sensitive metadata unless they have been reviewed and sanitized.
