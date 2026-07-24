# Oracle AI Ready Data Checks

## Data readiness dimensions

- **Clean**: keys, constraints, and optimizer evidence.
- **Contextual**: table comments, column comments, and documented relationships.
- **Consumable**: stable identifiers, useful text, vector candidates, and bounded semantic views.
- **Current**: freshness columns and recent statistics.
- **Correlated**: foreign keys, source metadata, and traceability.
- **Compliant**: sensitive-data documentation and review of broad grants.

## Mandatory project gates

This skill applies a project policy that every in-scope table and column must have a comment. Missing comments fail the gate even when the weighted score is acceptable.

## Comment quality review

- The mandatory gate remains based on 100 percent comment presence.
- Comment quality is reviewed as a separate indicator and does not change the score in v0.3.0.
- Warn on `TODO`, `TBD`, and `FIXME`; overly short or generic text; name-only descriptions; and repeated short generic comments.
- This automated review does not replace review by the business owner.

## Semantic type mismatch

- Infer NUMBER or DATE/TIMESTAMP candidates from string-column names and comments.
- Treat inferred candidates as review-only warnings; they do not change the score in v0.3.0.
- Do not automatically generate `ALTER TABLE ... MODIFY` statements from these warnings.
- Consider typed columns, virtual columns, or AI-oriented views after manual review.

## Dynamic next actions

- Output actions only for unresolved findings, manual-review items, and profile-specific requirements.
- Do not request remediation again for already-resolved findings.

## Interpretation

- A high scan score supports metadata quality but does not prove Select AI runtime connectivity.
- A high RAG score supports source-data design but does not prove document ingestion or retrieval quality.
- A VECTOR column is not required when Select AI manages a separate document vector table.
- A document corpus still needs source, chunking, embedding, refresh, and citation design.
