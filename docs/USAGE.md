# Usage Guide

## Data readiness flow

1. Run the SQLcl collector.
2. Keep the generated `.out` file.
3. Run the Python scorer locally, or upload the `.out` file to ChatGPT and ask for an Oracle AI Ready report.
4. Review the Markdown report and improvement SQL.

### Arguments

```text
@oracle_ai_ready_collect.sql <schema_owner> <table_like_pattern> <profile>
```

| Argument | Example | Description |
|---|---|---|
| `schema_owner` | `HR` | Target schema owner. |
| `table_like_pattern` | `%` or `EMP%` | `LIKE` pattern for target tables. |
| `profile` | `scan` or `rag` | Scoring profile. |

## Feature readiness flow

1. Run the feature collector from the AI-enabled user if possible.
2. Score the output.
3. Use the report to decide whether you are in a Select AI, native vector, or unsupported/privilege-limited environment.

```bash
sql -s admin/****@adb @scripts/oracle_ai_feature_collect.sql HR %
python3 scripts/score_oracle_ai_feature_readiness.py oracle_ai_feature_readiness_HR.out --language ja --output oracle_ai_feature_readiness_HR.md --sql-output oracle_ai_feature_setup_HR.sql
```

## What to upload to ChatGPT

Usually upload the `.out` file. Upload the command log only when SQLcl errors, missing sections, or permission issues need review.

## Expected success markers

Data readiness collector:

```text
@@ORACLE_AI_READY_COLLECTOR_VERSION
@@SECTION:run_context
...
@@END_ORACLE_AI_READY_COLLECTOR
```

Feature readiness collector:

```text
@@ORACLE_AI_FEATURE_COLLECTOR_VERSION
@@SECTION:run_context
...
@@END_ORACLE_AI_FEATURE_COLLECTOR
```
