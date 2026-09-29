# Examples

## BAD_AI_READY schema

`bad_ai_ready_schema.sql` creates an intentionally poor schema for comparison testing.

Expected weaknesses:

- Missing table comments
- Missing column comments
- No primary keys
- No foreign keys
- No useful constraints
- Dirty sample data
- Sensitive-looking columns
- Broad grant candidate

Use it to compare against HR or another well-documented schema.

## BAD_AI_READY Part 2 demo

[BAD_AI_READY Part 2](bad_ai_ready_part2/README.md) is a reproducible remediation and Select AI / NL2SQL functional-verification demo. It starts from an intentionally metadata-poor schema, applies reviewed improvements, and verifies the resulting metadata and generated SQL.

## Annotation / Domain comparison (v0.4)

See [bad_ai_ready_part3](bad_ai_ready_part3/README.md) for a locally generated,
reviewable two-table experiment, independent runtime evidence, and prior user
observations. It leaves the part 2 tables unchanged. Generation connects to
neither Database nor LLM; executing the generated lab requires separate access.
