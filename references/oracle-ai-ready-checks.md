# Oracle AI-ready checks

## Profiles

Use one of these MVP profiles:

- `scan`: general metadata readiness scan for Oracle Database schemas/tables.
- `rag`: retrieval-augmented generation readiness. Prefer this when the user mentions RAG, vector search, embeddings, retrieval, chat over tables, semantic search, or agents that answer from database content.

## Dimensions

Score each dimension from 0.00 to 1.00.

| Dimension | Meaning for Oracle Database metadata |
|---|---|
| Clean | Stable keys, constraints, usable optimizer statistics, and basic nullability metadata. |
| Contextual | Tables and columns are documented and relationships are declared. |
| Consumable | Data can be used by AI pipelines, especially text/vector retrieval for the `rag` profile. |
| Current | Data has freshness indicators and recent statistics. |
| Correlated | Tables can be joined or traced to source/update context. |
| Compliant | Sensitive-looking columns and broad grants are visible for review. |

## Mandatory comment gate

Always evaluate this gate separately from numeric scoring:

- Table comments: pass only when 100% of in-scope tables have non-empty comments.
- Column comments: pass only when 100% of in-scope columns have non-empty comments.

If either coverage value is below 100%, overall readiness gate is `fail`. Explain that numeric scoring may still show relative progress, but the user's mandatory metadata requirement is not met.

## Metric definitions

### Clean

Inputs: `table_inventory`, `column_inventory`, `constraints`.

Useful metrics:

- Primary-key coverage: tables with an enabled primary key / total tables.
- Statistics coverage: tables with `LAST_ANALYZED` populated / total tables.
- Column-statistics coverage: columns with `LAST_ANALYZED` populated / total columns.
- Constraint coverage: tables with at least one primary, unique, foreign-key, or check constraint / total tables.

Default score: average primary-key coverage, table-statistics coverage, column-statistics coverage, and constraint coverage.

### Contextual

Inputs: `table_comments`, `column_comments`, `constraints`.

Useful metrics:

- Table-comment coverage.
- Column-comment coverage.
- Relationship metadata: tables with primary or foreign-key constraints / total tables.

Default score: 40% table-comment coverage, 40% column-comment coverage, 20% relationship metadata.

### Consumable

Inputs: `column_inventory`, `rag_candidate_columns`, `table_comments`, `column_comments`.

For `scan` profile, score general AI consumption:

- Documented metadata coverage: average of table and column comment coverage.
- Text-bearing table coverage: tables with at least one character or LOB text column / total tables.
- Stable identifier coverage: primary-key coverage.

For `rag` profile, emphasize retrieval:

- Text-bearing table coverage.
- Vector-column coverage, where `DATA_TYPE = VECTOR` appears.
- Documentation coverage.
- Stable identifier coverage.

Do not require vector columns for every RAG workload. A zero vector-column score is a finding, not always a blocker, because embeddings may live outside the scanned schema.

### Current

Inputs: `table_inventory`, `freshness_columns`.

Useful metrics:

- Freshness-column coverage: tables with columns such as `UPDATED_AT`, `LAST_UPDATE_DATE`, `MODIFIED_DATE`, `EFFECTIVE_DATE`, `CREATED_AT`, or similar / total tables.
- Recent-statistics coverage: tables with `LAST_ANALYZED` populated and not obviously stale if the date is available.

Treat missing freshness columns as a higher risk for RAG and agents because answers may be stale or hard to explain.

### Correlated

Inputs: `constraints`, `column_inventory`.

Useful metrics:

- Foreign-key coverage: tables participating in foreign-key relationships / total tables.
- Source/update metadata columns: tables with columns such as `SOURCE_SYSTEM`, `SOURCE_ID`, `BATCH_ID`, `LOAD_ID`, `ETL_JOB`, `CREATED_BY`, `UPDATED_BY`, or similar / total tables.
- Primary-key coverage.

### Compliant

Inputs: `sensitive_candidate_columns`, `object_grants`, comments.

Useful metrics:

- Sensitive-name candidate coverage: sensitive-looking columns with comments / total sensitive-looking columns.
- Broad-grant risk: tables granted to `PUBLIC` or other broad users/roles should be flagged.
- Manual-review status: if sensitive-looking columns exist, mark compliance as requiring owner/DBA review even when comments are present.

The skill should not claim legal, privacy, or regulatory compliance. It should identify metadata signals and review items.

## Profile weights

### scan

- Clean: 20%
- Contextual: 25%
- Consumable: 15%
- Current: 15%
- Correlated: 15%
- Compliant: 10%

### rag

- Clean: 10%
- Contextual: 30%
- Consumable: 30%
- Current: 10%
- Correlated: 10%
- Compliant: 10%

## Recommended interpretation

| Overall score | Interpretation |
|---:|---|
| 0.85 - 1.00 | Strong numeric readiness; still enforce mandatory gates. |
| 0.70 - 0.84 | Usable with remediation plan. |
| 0.50 - 0.69 | Significant gaps; pilot only. |
| 0.00 - 0.49 | Not ready for AI consumption without remediation. |

When mandatory comments are incomplete, use this phrasing: "Numeric score indicates relative readiness, but the mandatory comment gate failed, so this dataset is not ready under the requested policy."

## Improvement SQL guidance

Safe generated SQL:

- `COMMENT ON TABLE` for missing table comments.
- `COMMENT ON COLUMN` for missing column comments.
- `DBMS_STATS.GATHER_TABLE_STATS` suggestions for missing table statistics, labeled DBA-review.

Template-only SQL:

- `ALTER TABLE ... ADD CONSTRAINT` for primary/foreign keys.
- `ALTER TABLE ... ADD UPDATED_AT` or similar freshness columns.
- Vector columns, vector indexes, materialized views, masking/redaction, audit-policy, or privilege changes.

Always present generated SQL as review-before-run. Do not execute it automatically.
