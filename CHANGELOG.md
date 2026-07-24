# Changelog

## 0.3.0 - 2026-07-25

- Added optional self-contained HTML reports with `--html-output`.
- Added dynamic next actions based on unresolved findings.
- Added advisory comment-quality checks for placeholders, short/generic text,
  name-only comments, and repeated generic comments.
- Added advisory semantic-type warnings for numeric/date-like text columns.
- Added BAD_AI_READY before/after regression fixtures and report samples.
- Preserved existing score formulas, mandatory comment gate behavior, and CLI
  compatibility.

## 0.2.0 - 2026-07-10

- Added JSON-driven Select AI setup generation.
- Added separate NL2SQL and RAG profiles.
- Added comments, annotations, and constraints to NL2SQL profile generation.
- Added managed vector-index generation with document source and citation settings.
- Added preflight, smoke-test, verification, and rollback SQL generation.
- Added post-setup configuration scoring.
- Corrected `enable_sources` placement to vector-index attributes.
- Preserved readiness assessment workflows.

## 0.1.0 - 2026-06-25

- Initial readiness assessment release.
