-- Run only after reviewing the output from 12_select_ai_showsql_prompts.sql.
-- These prompts are read-only aggregate/select operations over synthetic data.

set long 1000000
set longchunksize 1000000
set linesize 250
set pagesize 1000
set trimspool on
set feedback on

spool select_ai_bad_ai_ready_runsql.log

prompt ============================================================================
prompt T01 expected: 50 customers
prompt ============================================================================
SELECT AI RUNSQL 顧客は全部で何人ですか？;

prompt ============================================================================
prompt T02 expected: six country rows; counts are 7,7,7,7,6,6
prompt ============================================================================
SELECT AI RUNSQL 有効な顧客数を国名別に集計し、人数の多い順、同数の場合は国名の昇順で表示してください。;

prompt ============================================================================
prompt T03 expected: six Japanese active customers; top total is customer 31, JPY 141.95
prompt ============================================================================
SELECT AI RUNSQL 日本の有効な顧客について、顧客ID、顧客名、注文金額合計、通貨コードを表示してください。注文金額は文字列ではなく数値として変換して集計してください。注文金額合計の大きい順、同額の場合は顧客IDの昇順で上位10件を表示してください。異なる通貨は合算せず、メールアドレス、電話番号、SSN、カード情報は表示しないでください。;

prompt ============================================================================
prompt T04 expected: 60 rows covering 2025-01 through 2025-10 and six currencies
prompt ============================================================================
SELECT AI RUNSQL 2025年の注文金額を月別、通貨別に集計し、月の昇順、通貨コードの昇順で表示してください。異なる通貨は合算しないでください。;

prompt ============================================================================
prompt T05 expected: 0 customers without orders
prompt ============================================================================
SELECT AI RUNSQL 注文を一度もしていない顧客は何人ですか？;

prompt ============================================================================
prompt T06 expected: seven customers, each with one qualifying ticket
prompt ============================================================================
SELECT AI RUNSQL OPENまたはIN_PROGRESSの問い合わせのうち、重大度4以上のものを顧客ごとに集計し、顧客ID、顧客名、問い合わせ件数を表示してください。件数の多い順、同数の場合は顧客IDの昇順で表示してください。メールアドレスと電話番号は表示しないでください。;

prompt ============================================================================
prompt T07 expected: S1=2, S2=5, S3=3; no S4 row
prompt ============================================================================
SELECT AI RUNSQL 離反傾向スコアが0.80以上の顧客をセグメント別に集計し、顧客数と平均顧客生涯価値を表示してください。離反傾向スコアと顧客生涯価値は数値として変換して計算してください。セグメントコードの昇順で表示し、顧客名や連絡先は表示しないでください。;

prompt ============================================================================
prompt T08 expected: top ten rows all have total quantity 2
prompt ============================================================================
SELECT AI RUNSQL 顧客状態がACTIVEで、国コードがJPの顧客が購入した商品の総数量をSKU別に集計してください。数量は文字列ではなく数値として変換して集計し、総数量の多い順、同数の場合はSKUの昇順で上位10件を表示してください。;

prompt ============================================================================
prompt T09 expected: PART2_CSV, 100 rows, one maximum UPDATED_AT value
prompt ============================================================================
SELECT AI RUNSQL 注文データについて、提供元システムごとの行数と最終更新日時を表示し、提供元システムの昇順で表示してください。;

prompt ============================================================================
prompt T10 expected: 0 external export rows
prompt ============================================================================
SELECT AI RUNSQL 外部出力データは何件ありますか？;

spool off

prompt Query results were written to select_ai_bad_ai_ready_runsql.log.
