# Oracle AI Feature Readiness Checks

## Purpose

Use these checks to determine which Oracle AI features are visible and how close the current environment is to using them. The checks intentionally separate **feature presence** from **feature configured and ready to use**.

## Priority features

| Feature | Primary evidence | Ready evidence | Notes |
|---|---|---|---|
| Select AI / NL2SQL | `DBMS_CLOUD_AI`, `CREATE_PROFILE`, `GENERATE`, `GENERATE_SQL`, `SET_PROFILE` | enabled AI profile with provider, credential, and model/endpoint | Core feature for natural-language SQL. |
| Select AI RAG | `DBMS_CLOUD_AI.CREATE_VECTOR_INDEX` | enabled vector index plus profile attributes `embedding_model` and `vector_index_name` | Do not mark ready just because the procedure is visible. |
| Oracle AI Vector Search / Vector Index | `DBMS_VECTOR`, `DBMS_VECTOR_CHAIN`, `VECTOR` columns, vector indexes | target VECTOR columns or vector index evidence | Native vector search can exist without Select AI. |
| Select AI Agent - SQL tool | `DBMS_CLOUD_AI_AGENT`, `CREATE_AGENT`, `CREATE_TOOL`, `RUN_TOOL`, `SQL_TOOL` | Agent package plus usable NL2SQL profile | SQL tool rollout needs least-privilege review. |
| Select AI Agent - RAG tool | `DBMS_CLOUD_AI_AGENT.RAG_TOOL` plus RAG readiness | Agent package plus usable RAG/vector setup | Requires both agent and RAG readiness. |
| Synthetic Data Generation | `DBMS_CLOUD_AI.GENERATE_SYNTHETIC_DATA` | usable AI profile plus schema comments/constraints | Treat as non-production until reviewed. |
| NL2SQL Feedback | `DBMS_CLOUD_AI.FEEDBACK` | usable AI profile and feedback governance | Collect after generated SQL review process exists. |
| Auto Object Selection | `object_list_mode=automated`, vector index support | automated profile and vector/object metadata support | Use manual `object_list` until validated. |

Translation and generic Chat are not part of the default priority list.

## Status meanings

| Status | Meaning |
|---|---|
| `利用可能そう` | Required package/procedure evidence and minimal configuration evidence are present. Still validate with a smoke test. |
| `対応あり・設定必要` | Required packages/procedures are visible, but AI profile, credential, vector index, or agent configuration is missing. |
| `機能は見えるが前提不足` | Some evidence is visible, but a blocking prerequisite is missing or ambiguous. |
| `現ユーザーから未検出` | Current user cannot see the package/procedure/view. This may mean unsupported environment, missing component, PDB not enabled, or insufficient privileges. |
| `不明・手動確認` | Collector evidence is incomplete or probe sections errored in a way that prevents confident classification. |

## Environment interpretation patterns

### Autonomous AI Database / Autonomous AI Lakehouse

If `DBMS_CLOUD_AI`, `DBMS_CLOUD_AI_AGENT`, and `DBMS_VECTOR` are visible but `USER_CLOUD_AI_PROFILES` is empty, report **AI機能あり・未設定**. The next step is credential and AI profile setup, not an upgrade.

### OCI Base Database Service

If `DBMS_VECTOR` / `DBMS_VECTOR_CHAIN` is visible but `DBMS_CLOUD_AI` is not, report native vector capability separately. Recommend native vector smoke tests or application-managed RAG. Do not output Select AI `CREATE_PROFILE` SQL as if it can run.

### 19c or non-vector environments

If neither `DBMS_CLOUD_AI` nor `DBMS_VECTOR` is visible, report major AI features as not detected from the current user. Recommend DBA/SYSDBA component and privilege checks.

## Setup SQL policy

- Output `DBMS_CLOUD_AI.CREATE_PROFILE` only when `DBMS_CLOUD_AI` is visible.
- Output `DBMS_CLOUD_AI.CREATE_VECTOR_INDEX` only when `CREATE_VECTOR_INDEX` is visible.
- Output `DBMS_CLOUD_AI_AGENT` placeholders only when `DBMS_CLOUD_AI_AGENT` is visible.
- Output native vector smoke tests when vector packages are visible but Select AI is not.
- Never output credential secrets; use placeholders.
