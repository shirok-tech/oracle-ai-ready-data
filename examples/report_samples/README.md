# Data readiness report samples

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
