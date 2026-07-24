# Report Template

## Executive summary

- Scope
- Readiness state
- Blocking gaps
- Recommended next action

## Evidence

- Database and session context
- Package and procedure visibility
- Schema metadata coverage
- Profile attributes
- Vector-index attributes

## Findings

| Priority | Finding | Evidence | Risk | Action |
|---|---|---|---|---|

## Comment quality

- Review advisory findings separately from the mandatory comment-presence gate.
- Include placeholders, short or generic text, name-only comments, and repeated generic comments.

## Semantic type mismatch

- List string columns that appear to store numeric or date/timestamp values.
- Mark candidates as manual review only; do not prescribe automatic type changes.

## Next actions

- Generate actions dynamically from unresolved findings, manual-review items, and profile-specific requirements.
- Omit actions for findings that are already resolved.

## HTML output

The same report model can also generate an optional self-contained HTML report.

## Runtime validation

- SHOWPROMPT result
- SHOWSQL review
- Optional RUNSQL result
- RAG known-answer test
- Source/citation test
- Stateless GENERATE test

## Safety and review

- Credential handling
- Metadata and data sent to provider
- Object scope
- Production change approval
