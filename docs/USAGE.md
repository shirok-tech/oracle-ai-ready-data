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
warnings only in v0.3.0; they do not change readiness scores.

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
