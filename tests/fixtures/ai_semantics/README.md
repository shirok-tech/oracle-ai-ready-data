# AI semantics test data

`observed_minimal.json` is a minimal, manually normalized extract of the
dictionary results in the user-provided Japanese article draft
`oracle-ai-ready-data Skill 第3回_v0.7.md` (the `USER_TAB_COLUMNS`,
`USER_ANNOTATIONS_USAGE`, and `ALL_ANNOTATIONS_USAGE` output around lines
562–664). The source describes an Oracle AI Database 26ai 23.26.3.3.0
experiment performed by the user; these are **not** results of a database
connection or model call performed by the test suite.

The fixture retains only two three-column table inventories, six column
annotation records, three domain-definition annotation records, and one
column-to-domain association. The owner context combines the owner's
dictionary output with the cross-user visibility check. Collection status
records and the JSON envelope normalize the displayed successful query
results into the new input format; the source was not produced by the new
collector. No collection timestamp or runtime verification is invented.

The separately supplied `修正Log.log` records RUNSQL trials and is not imported.
Neither the raw log, provider prompts, credentials, nor connection details
are included in these fixtures. Runtime evidence remains unverified by this
metadata-only fixture.

`minimal_scan.csv` is a hand-built, sectioned-CSV companion for rendering the
sample report. It contains only the two known tables, six columns, data types,
and target owner. It is not original collector output and omits statistics,
comments, constraints and other score inputs; its total score must not be used
as a new assessment of the user's Database.

Boundary cases in `tests/test_ai_semantics.py` are explicitly **synthetic**:
empty scope, errors, mixed origins, cross-owner objects, duplicates, unknown
provenance, valueless annotations, and hostile/special text. They should not
be represented as observations from the user's database.
