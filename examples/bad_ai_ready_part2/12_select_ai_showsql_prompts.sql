-- Run as the Select AI profile owner after 11_create_select_ai_profile.sql.
-- SHOWSQL is used first so the generated SQL can be reviewed before execution.
-- Run this same file before and after 07_apply_ai_ready_improvements.sql when
-- you want a strict Before/After comparison.

set long 1000000
set longchunksize 1000000
set linesize 250
set pagesize 1000
set trimspool on
set feedback on

spool select_ai_bad_ai_ready_showsql.log

prompt ============================================================================
prompt T01: Basic object selection
prompt ============================================================================
SELECT AI SHOWSQL 顧客は全部で何人ですか？;

prompt ============================================================================
prompt T02: Business term, code value, and customer-to-region relationship
prompt ============================================================================
SELECT AI SHOWSQL 有効な顧客数を国名別に集計し、人数の多い順、同数の場合は国名の昇順で表示してください。;

prompt ============================================================================
prompt T03: Customer-to-order relationship, text amount conversion, and PII control
prompt ============================================================================
SELECT AI SHOWSQL 日本の有効な顧客について、顧客ID、顧客名、注文金額合計、通貨コードを表示してください。注文金額は文字列ではなく数値として変換して集計してください。注文金額合計の大きい順、同額の場合は顧客IDの昇順で上位10件を表示してください。異なる通貨は合算せず、メールアドレス、電話番号、SSN、カード情報は表示しないでください。;

prompt ============================================================================
prompt T04: Text date conversion, text amount conversion, and currency separation
prompt ============================================================================
SELECT AI SHOWSQL 2025年の注文金額を月別、通貨別に集計し、月の昇順、通貨コードの昇順で表示してください。異なる通貨は合算しないでください。;

prompt ============================================================================
prompt T05: Relationship-aware anti join
prompt ============================================================================
SELECT AI SHOWSQL 注文を一度もしていない顧客は何人ですか？;

prompt ============================================================================
prompt T06: Ticket codes, severity conversion, and customer relationship
prompt ============================================================================
SELECT AI SHOWSQL OPENまたはIN_PROGRESSの問い合わせのうち、重大度4以上のものを顧客ごとに集計し、顧客ID、顧客名、問い合わせ件数を表示してください。件数の多い順、同数の場合は顧客IDの昇順で表示してください。メールアドレスと電話番号は表示しないでください。;

prompt ============================================================================
prompt T07: Feature semantics and numeric conversion without personal data
prompt ============================================================================
SELECT AI SHOWSQL 離反傾向スコアが0.80以上の顧客をセグメント別に集計し、顧客数と平均顧客生涯価値を表示してください。離反傾向スコアと顧客生涯価値は数値として変換して計算してください。セグメントコードの昇順で表示し、顧客名や連絡先は表示しないでください。;

prompt ============================================================================
prompt T08: Three-table relationship and quantity conversion
prompt ============================================================================
SELECT AI SHOWSQL 顧客状態がACTIVEで、国コードがJPの顧客が購入した商品の総数量をSKU別に集計してください。数量は文字列ではなく数値として変換して集計し、総数量の多い順、同数の場合はSKUの昇順で上位10件を表示してください。;

prompt ============================================================================
prompt T09: Freshness and source metadata added by the remediation SQL
prompt ============================================================================
SELECT AI SHOWSQL 注文データについて、提供元システムごとの行数と最終更新日時を表示し、提供元システムの昇順で表示してください。;

prompt ============================================================================
prompt T10: Empty but documented table
prompt ============================================================================
SELECT AI SHOWSQL 外部出力データは何件ありますか？;

spool off

prompt Generated SQL was written to select_ai_bad_ai_ready_showsql.log.
prompt Compare each query with SELECT_AI_TEST_CASES.md before RUNSQL.
