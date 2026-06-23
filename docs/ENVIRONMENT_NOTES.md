# Environment Notes

These notes summarize observed interpretation patterns for Oracle AI feature readiness.

## Autonomous AI Database / Autonomous AI Lakehouse

If `DBMS_CLOUD_AI`, `DBMS_CLOUD_AI_AGENT`, and `DBMS_VECTOR` are visible, but no AI profile exists, report this as:

```text
AI features exist, but setup is incomplete.
```

The next action is usually:

1. Create or confirm provider credential.
2. Create Select AI profile.
3. Test `SELECT AI showsql`.
4. Add RAG vector index configuration if needed.
5. Add agent/tool setup only after profile and privilege review.

## OCI Base Database Service

If `DBMS_VECTOR` is visible but `DBMS_CLOUD_AI` is not, Select AI is not visible to the current user/PDB. Native Vector Search may still be usable.

Recommended direction:

- Use native `VECTOR` columns and `VECTOR_DISTANCE` smoke tests.
- Build application-managed RAG where the application calls embedding/LLM services and Oracle Database stores vectors.
- Use Autonomous AI Database or another Select AI-enabled environment for `DBMS_CLOUD_AI` / `SELECT AI` testing.

## 19c / non-AI environments

If neither `DBMS_CLOUD_AI` nor `DBMS_VECTOR` is visible, treat major Oracle AI capabilities as not confirmed. Ask a DBA or environment owner to verify service type, installed components, PDB visibility, and privileges.
