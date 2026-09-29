# Usage

## Assessment only

Run the data or feature collector with SQLcl, then run the matching scorer.

The data-readiness scorer can optionally produce a self-contained HTML report:

```bash
python3 scripts/score_oracle_ai_ready_scan.py \
  oracle_ai_ready_scan_HR_scan.out \
  --profile scan \
  --language ja \
  --output oracle_ai_ready_scan_HR.md \
  --html-output oracle_ai_ready_scan_HR.html \
  --sql-output oracle_ai_ready_improvement_HR.sql
```

`--html-output` is optional. The HTML has embedded CSS, contains no JavaScript
or external CDN resources, and is generated from the same assessment model as
the Markdown report. Comment-quality and semantic-type mismatch findings are
warnings only; they do not change readiness scores.

### Input validation and SQLcl ECHO

The base collector sets `ECHO OFF` before starting SPOOL, even when its calling
SQLcl session has `ECHO ON`. Leave echo disabled during collection.

The scorer rejects `SQL>` prompt/echo lines outside quoted CSV values. It also
requires closed `run_context`, `table_inventory`, and `column_inventory` sections,
valid required headers/values, and consistent table/column inventories.
`run_context` must have one row with `TARGET_OWNER` and `PROFILE` (`scan` or `rag`).
CSV records must have the expected number of fields. These are input checks;
the CLI options, score formulas, weights, and COMMENT gates are unchanged.

A valid empty scope still works: the two inventory sections must be present,
but may contain only headers, no content, or SQLcl's `no rows selected` message.
The existing scoring behavior for an empty scope is retained; that result must
not be interpreted as evidence of populated tables or a successful SQL query.
Quoted multiline comment values containing literal `SQL>` or section-marker
text remain valid data.

On invalid input the CLI exits with code 1, prints an error to stderr, and writes
no report or SQL output (existing output files remain untouched). Preserve the
corrupt scan for diagnosis and recollect in a fresh output directory using the
updated collector. Do not remove echo lines by hand and assume the remaining
metadata is complete. See the [fix and Database retest procedure](v0.4-echo-fix.md).

## Optional Annotation/Domain assessment (v0.4.0)

The original collector and CLI still work without semantic evidence. The report
then labels the new advisory section `not_collected`, with N/A instead of 0%.

Generate a supplementary collector locally (Python 3.10+, standard library only):

```bash
python3 scripts/generate_semantics_collector.py \
  --owner HR --table-like '%' \
  --output collect_ai_semantics.sql \
  --spool-file hr_semantics_r01.json
```

Review the SQL, then run `@collect_ai_semantics.sql` in an already connected SQLcl
session when Database access is authorized. This is a **read-only metadata**
collector; it creates no domains, annotations, profiles or credentials and calls
no LLM. The generator itself never connects. The evidence filename must be a
simple filename in SQLcl's current directory. `SPOOL ... CREATE` prevents replacing
an earlier trial; choose a fresh name for each run (SQLcl's `OFF`/`OUT` names are
rejected). The collector sets UTF-8, disables timing/autotrace/error logging and
autocommit, and leaves those SQLcl settings in effect. It issues no commit or
rollback and keeps the session connected. Prefer a dedicated collection session.
Check the SQLcl terminal for errors and verify `collected_at` in the JSON before
scoring. If `SPOOL CREATE` fails, an existing file is left intact; it is not fresh
evidence. The script uses `WHENEVER ... CONTINUE NONE` to avoid committing or
rolling back an existing transaction, so a client error does not guarantee exit.
Owner accepts an unquoted
Oracle identifier. Table patterns accept letters, digits, `_`, `$`, `#`, `%`, and
backslash escapes for `%`, `_`, or backslash. Other inputs are rejected.

Regenerate supplementary collector SQL after updating the template. It no longer
emits `SET SQLCASE MIXED`, which produced an Obsolete warning in the reported
SQLcl 25.4 environment. Existing generated SQL files are not rewritten by the
update; the collection queries and JSON construction are unchanged.

Use the same schema/table scope and, preferably, the same session user as the
original scan. Collect separately as the data owner and Select AI user if you
need to compare their visibility. Check both session contexts and timestamps.

```bash
python3 scripts/score_oracle_ai_ready_scan.py oracle_ai_ready_scan_HR_scan.out \
  --semantics-input hr_semantics_r01.json --language ja \
  --output hr_scan_report.md --html-output hr_scan_report.html
```

Coverage is computed over the distinct collected columns that are also in the
original scan. A narrower supplementary scope is shown explicitly and does not
claim coverage of the whole scan. Empty scope, failed collection, and missing
collection yield N/A; successfully collected annotations with zero matches over
a nonempty scope yield 0.00%. Table annotations and domain definitions never add
to the column numerator. Counts have no score or COMMENT-gate effect.

JSON fields retain Unicode, quotes, commas, newlines, and valueless annotations.
Malformed/truncated JSON or invalid states stop scoring with an error instead of
silently treating the input as empty. Component-level collection failures in a
valid JSON envelope appear in the report; partial rows are not used as complete
coverage. A file with missing component statuses is treated as not collected.

See [format/states/provenance](../references/annotation-guidance.md),
[manual runtime evidence](../references/semantics-evidence-template.md), and
[part 3](../examples/bad_ai_ready_part3/README.md). The scorer does not ingest
runtime logs or run generated SQL. Attach the completed evidence template to the
report; stages without evidence remain unverified.

## Assessment plus setup generation

Use the feature scorer with `--config-output`, edit the generated JSON, and pass it to `generate_select_ai_setup.py`.

The feature scorer can also generate the setup package in one command when a reviewed config already exists:

```bash
python3 scripts/score_oracle_ai_feature_readiness.py \
  oracle_ai_feature_readiness_HR.out \
  --output feature.md \
  --sql-output compatibility_template.sql \
  --setup-config reviewed_config.json \
  --setup-dir generated_select_ai_setup
```

## Replace mode

The setup generator does not modify existing profiles or indexes by default. `--replace-existing` emits destructive drop/create blocks. Use it only after a deliberate review of profile consumers, vector data, and rollback requirements.
