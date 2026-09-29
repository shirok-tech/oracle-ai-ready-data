# Changelog

## 0.4.0 - 2026-09-29

- Fixed inherited SQLcl ECHO ON corrupting the base collector's spool by disabling
  echo before SPOOL. Reject echoed SQL, missing/malformed mandatory sections and
  inconsistent inventories before scoring, while retaining valid empty scopes.
- Removed the unnecessary SQLCASE command from the supplementary collector to
  avoid the Obsolete warning observed in SQLcl 25.4.
- Added an optional, read-only annotation/domain collector generated locally with
  validated scope, bind parameters, capability probes, and JSON-safe output.
- Added `--semantics-input` and a shared bilingual AI Semantics Readiness
  (Advisory) section to Markdown and self-contained HTML reports.
- Distinguished successful empty collection, not collected, confirmed unsupported,
  confirmed permission denial, undetermined unavailability, and collection errors.
- Added distinct-column coverage, table annotation presence, direct/domain/unknown
  provenance, domain associations, and independent runtime evidence guidance.
- Added part 3 reproduction SQL generation, manual evidence records, fixtures,
  regression tests, and sample reports. Prior user results are explicitly labeled.
- Preserved all score formulas, weights, COMMENT gates, valid existing collector
  inputs, profile defaults, and RAG behavior.
- Recorded user-completed Database revalidation on 2026-09-23 (Oracle AI Database
  26ai 23.26.3.3.0, SQLcl 25.4), including Japanese/English HTML visual checks.
  The final report distinguishes these results from local tests, historical Select
  AI trials, and the generated DDL package that was not rerun in a new environment.

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
