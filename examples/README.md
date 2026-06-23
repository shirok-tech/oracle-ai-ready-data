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
