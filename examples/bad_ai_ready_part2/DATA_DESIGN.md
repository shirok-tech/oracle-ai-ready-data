
# BAD_AI_READY v2 のテストデータ設計

## 方針

第2回では、行データの修復ではなく、Skillが生成した改善SQLをレビューして実行するとAI Ready評価が改善する流れに集中します。

そのため、CSVは最初から次を満たします。

- 主キー候補はすべてNULLなし・重複なし
- 外部キー候補はすべて参照先が存在
- 日付、金額、状態コードなどの文字列値は統一形式
- 実在する個人情報を含まない合成データ

改善前に意図的に欠落させるのは、テーブル/カラムコメント、PK/FK定義、鮮度列、出所列、統計情報、および任意のPUBLIC権限整理です。

## PK候補

| 表 | 主キー |
|---|---|
| `RAW_CUSTOMERS` | `CUSTOMER_ID` |
| `RAW_ORDERS` | `ORDER_ID` |
| `RAW_ORDER_LINES` | `ORDER_ID, LINE_NO` |
| `AI_DOCUMENTS` | `DOC_ID, CHUNK_NUMBER` |
| `CUSTOMER_FEATURES` | `CUSTOMER_ID` |
| `SUPPORT_TICKETS` | `TICKET_ID` |
| `ORPHAN_REGIONS` | `COUNTRY_CODE` |
| `EMPTY_EXPORT` | `EXPORT_ID` |

## FK候補

| 子表.列 | 親表.列 |
|---|---|
| `RAW_CUSTOMERS.COUNTRY_CODE` | `ORPHAN_REGIONS.COUNTRY_CODE` |
| `RAW_ORDERS.CUSTOMER_ID` | `RAW_CUSTOMERS.CUSTOMER_ID` |
| `RAW_ORDER_LINES.ORDER_ID` | `RAW_ORDERS.ORDER_ID` |
| `CUSTOMER_FEATURES.CUSTOMER_ID` | `RAW_CUSTOMERS.CUSTOMER_ID` |
| `SUPPORT_TICKETS.CUSTOMER_ID` | `RAW_CUSTOMERS.CUSTOMER_ID` |

`05_verify_badness.sql`のPK/FK候補違反はすべて0になる想定です。したがって、`07_apply_ai_ready_improvements.sql`の制約はデータ修復なしで`ENABLE VALIDATE`として追加できます。
