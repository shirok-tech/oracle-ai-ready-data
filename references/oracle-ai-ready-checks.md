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

## Interpretation

- A high scan score supports metadata quality but does not prove Select AI runtime connectivity.
- A high RAG score supports source-data design but does not prove document ingestion or retrieval quality.
- A VECTOR column is not required when Select AI manages a separate document vector table.
- A document corpus still needs source, chunking, embedding, refresh, and citation design.
