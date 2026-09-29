# Data readiness report samples

## v0.4 AI semantics

`ai_semantics_minimal.md` and `ai_semantics_minimal.html` demonstrate the new
advisory section: 2 annotated columns out of 6 (33.33%), 1 direct column,
1 domain-inherited column, and 1 domain-linked column. The metadata fixture is a
minimal normalized extract of the user's prior observations; the accompanying
scan is hand-built and lacks most scoring inputs. These files demonstrate
reporting, not a live Database assessment. Runtime stages remain unverified.

```bash
python3 scripts/score_oracle_ai_ready_scan.py \
  tests/fixtures/ai_semantics/minimal_scan.csv \
  --semantics-input tests/fixtures/ai_semantics/observed_minimal.json \
  --language ja \
  --output examples/report_samples/ai_semantics_minimal.md \
  --html-output examples/report_samples/ai_semantics_minimal.html
```

See the [fixture provenance](../../tests/fixtures/ai_semantics/README.md).

## Retained v0.3 samples

These files demonstrate the optional self-contained HTML output added in v0.3.0.
They were generated from the synthetic BAD_AI_READY before/after fixtures under
`tests/fixtures/`.

Generate the reports again with:

```bash
python3 scripts/score_oracle_ai_ready_scan.py \
  tests/fixtures/bad_ai_ready_after.out \
  --profile scan \
  --language ja \
  --output examples/report_samples/bad_ai_ready_after.md \
  --html-output examples/report_samples/bad_ai_ready_after.html \
  --sql-output examples/report_samples/bad_ai_ready_after_improvement.sql
```

The HTML files are self-contained: CSS is embedded, JavaScript is not used, and
no external CDN or network connection is required.
