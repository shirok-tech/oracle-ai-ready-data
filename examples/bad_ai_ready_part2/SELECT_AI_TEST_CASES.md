# BAD_AI_READY Select AI 機能確認ケース

このテストは、`07_apply_ai_ready_improvements.sql`適用後のスキーマについて、コメントとPK/FKをSelect AIのNL2SQL生成に利用できることを確認するためのものです。

Select AIが実行できたことだけでAI Ready全体を証明するものではありません。Skillの再評価でMandatory comment gateと各coverageを確認したうえで、このテストを**機能確認**として併記します。

## 実行順

1. `BAD_AI_READY`で`07_apply_ai_ready_improvements.sql`を実行
2. Skillを再実行し、Mandatory comment gateが`pass`であることを確認
3. `BAD_AI_READY`で`10_grant_select_ai_access.sql`を実行
4. `ADB_USER`でQiita記事どおりOpenAI credential、ACL、`DBMS_CLOUD_AI`権限を準備
5. `ADB_USER`で`11_create_select_ai_profile.sql`を実行
6. `12_select_ai_showsql_prompts.sql`で生成SQLをレビュー
7. `14_select_ai_reference_sql.sql`と意味が一致することを確認
8. `13_select_ai_runsql_prompts.sql`で結果を確認

AI Profileでは、整備したメタデータを使わせるために次を明示しています。

```json
"comments": true,
"constraints": true,
"object_list_mode": "all",
"enforce_object_list": true
```

## 合格基準

生成SQLは参照SQLと文字単位で同じである必要はありません。次を満たせば合格とします。

- 対象業務に合う表を使用している
- FKと同じ列で正しくJOINしている
- `*_TXT`の日付・金額・数量・スコアを必要に応じて数値または日付へ変換している
- 通貨をまたいで金額を合算していない
- 許容値として定義した`ACTIVE`、`OPEN`、`IN_PROGRESS`などを正しく使用している
- 指示していない`EMAIL`、`PHONE`、`SSN`、カード情報などを出力していない
- 結果が下記の期待値と一致する

## テストケース

### T01 基本的な表選択

自然言語:

> 顧客は全部で何人ですか？

期待値: **50**

確認点: `RAW_CUSTOMERS`を選び、`COUNT(*)`または同等の集計を行う。

### T02 コメントと国マスタの関係

自然言語:

> 有効な顧客数を国名別に集計し、人数の多い順、同数の場合は国名の昇順で表示してください。

期待値:

| REGION_NAME | ACTIVE_CUSTOMER_COUNT |
|---|---:|
| Australia | 7 |
| Germany | 7 |
| Singapore | 7 |
| United States | 7 |
| Japan | 6 |
| United Kingdom | 6 |

確認点: `RAW_CUSTOMERS.COUNTRY_CODE`と`ORPHAN_REGIONS.COUNTRY_CODE`をJOINし、`STATUS_TXT='ACTIVE'`を使用する。

### T03 顧客・注文JOIN、文字列金額、機微情報

自然言語:

> 日本の有効な顧客について、顧客ID、顧客名、注文金額合計、通貨コードを表示してください。注文金額は文字列ではなく数値として変換して集計してください。注文金額合計の大きい順、同額の場合は顧客IDの昇順で上位10件を表示してください。異なる通貨は合算せず、メールアドレス、電話番号、SSN、カード情報は表示しないでください。

期待値:

| CUSTOMER_ID | FULL_NAME | TOTAL_ORDER_AMOUNT | CURRENCY_CODE |
|---:|---|---:|---|
| 31 | Demo Customer 031 | 141.95 | JPY |
| 43 | Demo Customer 043 | 127.00 | JPY |
| 25 | Demo Customer 025 | 117.55 | JPY |
| 37 | Demo Customer 037 | 102.60 | JPY |
| 19 | Demo Customer 019 | 93.15 | JPY |
| 1 | Demo Customer 001 | 83.70 | JPY |

確認点: 顧客と注文を`CUSTOMER_ID`でJOINし、`AMOUNT_TXT`を数値変換する。PII候補列をSELECTしない。

### T04 文字列日付、文字列金額、通貨

自然言語:

> 2025年の注文金額を月別、通貨別に集計し、月の昇順、通貨コードの昇順で表示してください。異なる通貨は合算しないでください。

期待値: **60行**。月は`2025-01`から`2025-10`、各月にAUD、EUR、GBP、JPY、SGD、USDの6通貨。

先頭月の期待値:

| ORDER_MONTH | CURRENCY_CODE | TOTAL_ORDER_AMOUNT |
|---|---|---:|
| 2025-01 | AUD | 31.38 |
| 2025-01 | EUR | 109.60 |
| 2025-01 | GBP | 91.80 |
| 2025-01 | JPY | 113.20 |
| 2025-01 | SGD | 79.25 |
| 2025-01 | USD | 130.70 |

確認点: `ORDER_TIME_TXT`を日付として、`AMOUNT_TXT`を数値として扱う。`CURRENCY_CODE`をGROUP BYに含める。

### T05 参照関係を使ったNOT EXISTS

自然言語:

> 注文を一度もしていない顧客は何人ですか？

期待値: **0**

確認点: 顧客と注文の関係を`CUSTOMER_ID`で判断し、`NOT EXISTS`、外部結合、または同等のSQLを生成する。

### T06 問い合わせ状態、重大度、顧客JOIN

自然言語:

> OPENまたはIN_PROGRESSの問い合わせのうち、重大度4以上のものを顧客ごとに集計し、顧客ID、顧客名、問い合わせ件数を表示してください。件数の多い順、同数の場合は顧客IDの昇順で表示してください。メールアドレスと電話番号は表示しないでください。

期待値: 顧客ID **3、10、13、20、25、35、48**の7行で、各件数は1。

確認点: `SUPPORT_TICKETS`と`RAW_CUSTOMERS`を`CUSTOMER_ID`でJOINし、`SEVERITY_TXT`を数値として比較する。

### T07 特徴量の意味と数値変換

自然言語:

> 離反傾向スコアが0.80以上の顧客をセグメント別に集計し、顧客数と平均顧客生涯価値を表示してください。離反傾向スコアと顧客生涯価値は数値として変換して計算してください。セグメントコードの昇順で表示し、顧客名や連絡先は表示しないでください。

期待値:

| SEGMENT_CODE | CUSTOMER_COUNT | AVERAGE_LIFETIME_VALUE |
|---|---:|---:|
| S1 | 2 | 3503.25 |
| S2 | 5 | 2697.50 |
| S3 | 3 | 1598.75 |

確認点: `CHURN_SCORE_TXT`と`LIFETIME_VALUE_TXT`を数値変換し、スコアが高いほど離反傾向が高いというコメントの意味を利用する。

### T08 3表JOINと数量変換

自然言語:

> 顧客状態がACTIVEで、国コードがJPの顧客が購入した商品の総数量をSKU別に集計してください。数量は文字列ではなく数値として変換して集計し、総数量の多い順、同数の場合はSKUの昇順で上位10件を表示してください。

期待値: 上位10件の総数量はいずれも2。SKUは次の順。

`SKU-0001`, `SKU-0002`, `SKU-0037`, `SKU-0038`, `SKU-0049`, `SKU-0050`, `SKU-0061`, `SKU-0062`, `SKU-0073`, `SKU-0074`

確認点: `RAW_CUSTOMERS`→`RAW_ORDERS`→`RAW_ORDER_LINES`をPK/FKと同じ列でJOINし、`QUANTITY_TXT`を数値変換する。

### T09 鮮度と出所

自然言語:

> 注文データについて、提供元システムごとの行数と最終更新日時を表示し、提供元システムの昇順で表示してください。

期待値: `SOURCE_SYSTEM='PART2_CSV'`、行数100。日時は改善SQLを実行した時刻に依存する。

確認点: 改善SQLで追加した`SOURCE_SYSTEM`と`UPDATED_AT`を使用する。

### T10 空表の意味

自然言語:

> 外部出力データは何件ありますか？

期待値: **0**

確認点: コメントから`EMPTY_EXPORT`を対象と判断する。

## 記事での表現例

> AI Ready評価の改善後、AI Profileで`comments=true`と`constraints=true`を有効にし、同じスキーマをSelect AIから問い合わせた。各ケースでは`SHOWSQL`で表選択、JOIN、コード条件、型変換をレビューした後、`RUNSQL`の結果を参照SQLと比較する。これにより、Mandatory comment gateのpassとメタデータcoverageの改善に加え、整備したメタデータがNL2SQLで実際に利用できるかを機能面から確認する。

LLMとモデルの更新により生成SQLの書き方は変わり得るため、記事にはSQL文字列の完全一致ではなく、JOIN、変換、フィルタ、機微情報除外、結果値の一致を確認したと記載します。
