# Usage

## Assessment only

Run the data or feature collector with SQLcl, then run the matching scorer.

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
