# Comments, Annotations, and Semantic Views

## Purpose

Comments and annotations translate local business language into metadata that Select AI can place in prompt context. They are not the local dialect itself; they are the mapping from local terms to formal data meaning.

## Recommended placement

| Information | Recommended location |
|---|---|
| Table grain and business purpose | Table comment or description annotation |
| Column meaning and null semantics | Column comment or description annotation |
| Local names, abbreviations, and synonyms | Alias-style annotation |
| Units and currency | Unit-style annotation |
| PK/FK relationships | Database constraints where possible |
| Status-code values that change | Reference table or semantic view |
| Deterministic business calculations | Reviewed view or materialized view |
| Cross-request guidance | `additional_instructions` |
| Long policy or manual content | RAG document corpus |

## Quality checklist

A useful table description states:

- what one row represents
- authoritative source
- refresh cadence or effective-date behavior
- important exclusions
- intended analytical or AI use

A useful column description states:

- business definition
- unit or currency
- null meaning
- allowed values or code-table reference
- sensitivity classification
- which date or amount definition applies

Avoid circular descriptions such as `AMT means amount` or `STATUS is status`.

## Alias example

A business user may ask for `revenue`, `sales`, or a local term. The metadata should map those terms to one reviewed semantic column, such as `AI_SALES_V.REVENUE_AMOUNT`, whose view definition already applies posting, cancellation, and tax rules.

## Verification

Do not assume annotations are used merely because they exist. Enable profile annotation enrichment and inspect `SHOWPROMPT` with a question that should trigger the alias or definition.
