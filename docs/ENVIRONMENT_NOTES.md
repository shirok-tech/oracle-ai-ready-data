# Environment Notes

- Exact provider and model attributes vary by provider and database service.
- Use the current Oracle service documentation and the provider capability matrix.
- Oracle Database 19c and Oracle AI Database 26ai do not expose identical profile behavior.
- Annotations are a 26ai metadata-enrichment option; keep comments for portability when appropriate.
- Dictionary visibility, annotation registration and Select AI prompt enrichment
  are independent. The optional v0.4 collector probes required dictionary columns
  at runtime rather than inferring availability from a version number. ORA-00942
  alone does not prove that a feature is unsupported.
- SQLcl supports the `SELECT AI` keyword workflow.
- Stateless applications can call `DBMS_CLOUD_AI.GENERATE` with an explicit profile name.
- RAG document loading can be asynchronous; check index and pipeline status before testing retrieval.
