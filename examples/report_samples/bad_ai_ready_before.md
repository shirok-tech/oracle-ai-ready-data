# Oracle Database AI Ready 評価レポート

## 1. エグゼクティブサマリー
- 総合スコア: **0.22 / 1.00**
- Profile: **scan**
- Mandatory comment gate: **fail**
- Comment quality review: **fail**
- Semantic type warnings: **11件**
- 結論: **必須コメントゲート未達のため、要求ポリシー上は未Ready**
- コメント有無チェックは必須条件です。コメント品質とSemantic type mismatchは初期実装では警告であり、既存スコアには影響しません。

## 2. スコープと前提
| 項目 | 値 |
|---|---|
| Schema | BAD_AI_READY |
| Table pattern | % |
| Profile | scan |
| 評価対象テーブル数 | 8 |
| 評価対象カラム数 | 52 |
| SQLcl spool | bad_ai_ready_before.out |
| Scan timestamp | 2026-07-21T04:45:57.267992 +00:00 |
| 注意事項 | ALL_* dictionary viewsで見えるメタデータを評価します。実データ値、業務上の正しさ、法令遵守は別途レビューが必要です。 |

## 3. 評価項目の説明
| Dimension | Weight | 何を評価しているか | なぜ重要か |
|---|---:|---|---|
| Clean | 20.0% | 主キー、制約、統計情報があり、AI処理の前提となる構造的な信頼性を確認します。 | キーや統計情報が不足すると、根拠行の特定、結合、品質確認が不安定になります。 |
| Contextual | 25.0% | テーブル/カラムコメントとリレーション定義により、データの意味が説明できるかを確認します。 | AIが列名だけから意味を推測すると誤解しやすいため、コメントを必須ゲートにしています。 |
| Consumable | 15.0% | AIやRAGパイプラインが利用しやすいテキスト列、VECTOR列、安定ID、ドキュメントを確認します。 | 検索対象、根拠、embedding管理方法が曖昧だと、RAG/agentの回答品質が安定しません。 |
| Current | 15.0% | 更新日時などの鮮度列と最近の統計情報があり、データの新しさを説明できるかを確認します。 | 古いデータや更新時点不明のデータは、AI回答の鮮度リスクになります。 |
| Correlated | 15.0% | 外部キー、主キー、source/update系メタデータにより、他テーブルや元データと関連付けられるかを確認します。 | 関連が宣言されていないと、AIが表間のつながりを誤解したり、根拠追跡が弱くなります。 |
| Compliant | 10.0% | 機微情報らしい列名、コメント有無、広い権限付与候補を検出し、レビュー可能性を確認します。 | この評価は法令遵守を保証しませんが、AI利用前のセキュリティ/プライバシーレビュー対象を明確にします。 |

## 4. スコアカード
| Dimension | Weight | Score | 主な根拠 |
|---|---:|---:|---|
| Clean | 20.0% | 0.45 | PK 0.0%, table stats 87.5%, column stats 94.2%, constraints 0.0% |
| Contextual | 25.0% | 0.00 | table comments 0.0%, column comments 0.0%, relationships 0.0% |
| Consumable | 15.0% | 0.35 | text-bearing tables 100.0%, vector tables 0.0%, documentation 0.0%, PK 0.0% |
| Current | 15.0% | 0.35 | freshness columns 0.0%, recent stats 87.5% |
| Correlated | 15.0% | 0.00 | FK 0.0%, source metadata 0.0%, PK 0.0% |
| Compliant | 10.0% | 0.28 | sensitive documented 0.0%, broad data grant absence 62.5% |

## 5. メトリクス詳細
| Metric | Value | Status | 説明 |
|---|---:|---|---|
| Table comment coverage | 0.0% | fail | コメントが設定されている評価対象テーブルの割合です。100%でない場合は必須ゲートがfailです。 |
| Column comment coverage | 0.0% | fail | コメントが設定されている評価対象カラムの割合です。100%でない場合は必須ゲートがfailです。 |
| PK coverage | 0.0% | 要改善 | 有効な主キーがあるテーブルの割合です。AI回答の根拠行を安定して参照するために重要です。 |
| FK coverage | 0.0% | 要改善 | 外部キーを持つ、または外部キー関係に参加するテーブルの割合です。表間の関連を安全に扱うための指標です。 |
| Relationship coverage | 0.0% | 要改善 | 主キーまたは外部キーのいずれかを持つテーブルの割合です。データモデルの説明可能性を見ます。 |
| Constraint coverage | 0.0% | 要改善 | 主キー、一意、外部キー、CHECK制約のいずれかがあるテーブルの割合です。構造的な品質管理の指標です。 |
| Table stats coverage | 87.5% | 良好 | LAST_ANALYZEDが入っているテーブルの割合です。統計情報が未取得だとデータ状態の確認が弱くなります。 |
| Column stats coverage | 94.2% | 良好 | LAST_ANALYZEDが入っているカラムの割合です。列分布やNULL傾向の評価に使います。 |
| Recent stats coverage | 87.5% | 良好 | 統計情報が最近取得されているテーブルの割合です。既定では90日以内をrecentと見なします。 |
| Freshness coverage | 0.0% | 要改善 | UPDATED_ATやLAST_UPDATE_DATEなど、鮮度を示す列があるテーブルの割合です。 |
| Source metadata coverage | 0.0% | 要改善 | SOURCE_SYSTEM、BATCH_ID、CREATED_BYなど、出所や更新者を示す列があるテーブルの割合です。 |
| Text-bearing table coverage | 100.0% | 参考 | RAG候補となるテキスト列を持つテーブルの割合です。検索対象テキストの有無を確認します。 |
| Vector table coverage | 0.0% | 参考 | VECTOR型またはembedding候補を持つテーブルの割合です。embeddingを外部管理している場合は設計書で補足してください。 |
| Sensitive candidate documentation | 0.0% | 要改善 | 機微情報候補列のうちコメントがある列の割合です。列名ベース推定なので人間の分類が必要です。 |
| Broad data grant absence | 62.5% | 要改善 | PUBLICなど広い相手へのデータアクセス権限が検出されなかった割合です。高いほどリスクが低い見立てです。 |
| Table comment quality coverage | 0.0% | fail | コメント本文がplaceholder、短すぎる説明、汎用文ではない割合です。初期実装では警告のみです。 |
| Column comment quality coverage | 0.0% | fail | コメント本文がplaceholder、短すぎる説明、汎用文ではない割合です。初期実装では警告のみです。 |

## 6. Mandatory comment gate
| Check | Coverage | Result | Required action |
|---|---:|---|---|
| Table comments | 0.0% | fail | Missing 8 table comments |
| Column comments | 0.0% | fail | Missing 52 column comments |

## 7. 主要な発見事項
### High priority
- Mandatory comment gate が fail です。table comment 欠落 8 件、column comment 欠落 52 件があります。
- 主キー未検出のテーブルが 8 件あります。RAG/agent応答の根拠行を安定して参照しづらくなります。
- PUBLICなど広いデータアクセス権限候補が 3 件あります。AI利用前に公開範囲を確認してください。

### Medium priority
- 統計情報が未取得または古いテーブルが 1 件あります。Clean/Current score の主な減点要因です。
- 鮮度を示す日時列が未検出のテーブルが 8 件あります。データの新しさを説明しづらくなります。
- 機微情報候補列が 10 件あります。列名ベースの推定のため、業務オーナーによる分類が必要です。

### Low priority / manual review
- VECTOR型カラムは未検出です。embeddingを別スキーマや外部サービスで管理している場合は設計書に明記してください。

## 8. コメント品質
| 項目 | 値 |
|---|---:|
| Table comment quality coverage | 0.0% |
| Column comment quality coverage | 0.0% |
| Placeholder comments | 0 |
| Too-short comments | 0 |
| Generic/name-only comments | 0 |
| Repeated generic groups | 0 |

| Object | Issue | Current comment |
|---|---|---|
| BAD_AI_READY.AI_DOCUMENTS | missing | - |
| BAD_AI_READY.CUSTOMER_FEATURES | missing | - |
| BAD_AI_READY.EMPTY_EXPORT | missing | - |
| BAD_AI_READY.ORPHAN_REGIONS | missing | - |
| BAD_AI_READY.RAW_CUSTOMERS | missing | - |
| BAD_AI_READY.RAW_ORDERS | missing | - |
| BAD_AI_READY.RAW_ORDER_LINES | missing | - |
| BAD_AI_READY.SUPPORT_TICKETS | missing | - |
| BAD_AI_READY.AI_DOCUMENTS.BODY_TEXT | missing | - |
| BAD_AI_READY.AI_DOCUMENTS.CHUNK_NUMBER | missing | - |
| BAD_AI_READY.AI_DOCUMENTS.DOC_ID | missing | - |
| BAD_AI_READY.AI_DOCUMENTS.EMBEDDING_BLOB_TXT | missing | - |
| BAD_AI_READY.AI_DOCUMENTS.LIFECYCLE_STATE | missing | - |
| BAD_AI_READY.AI_DOCUMENTS.ORIGIN_URI | missing | - |
| BAD_AI_READY.AI_DOCUMENTS.TITLE_TXT | missing | - |
| BAD_AI_READY.CUSTOMER_FEATURES.CHURN_SCORE_TXT | missing | - |
| BAD_AI_READY.CUSTOMER_FEATURES.CUSTOMER_ID | missing | - |
| BAD_AI_READY.CUSTOMER_FEATURES.FEATURE_NOTES | missing | - |
| BAD_AI_READY.CUSTOMER_FEATURES.LIFETIME_VALUE_TXT | missing | - |
| BAD_AI_READY.CUSTOMER_FEATURES.SEGMENT_CODE | missing | - |
| BAD_AI_READY.EMPTY_EXPORT.EXPORT_ID | missing | - |
| BAD_AI_READY.EMPTY_EXPORT.EXPORT_NAME | missing | - |
| BAD_AI_READY.EMPTY_EXPORT.PAYLOAD | missing | - |
| BAD_AI_READY.ORPHAN_REGIONS.COUNTRY_CODE | missing | - |
| BAD_AI_READY.ORPHAN_REGIONS.REGION_NAME | missing | - |
| BAD_AI_READY.ORPHAN_REGIONS.RISK_TIER_TXT | missing | - |
| BAD_AI_READY.RAW_CUSTOMERS.BIRTHDATE_TXT | missing | - |
| BAD_AI_READY.RAW_CUSTOMERS.COUNTRY_CODE | missing | - |
| BAD_AI_READY.RAW_CUSTOMERS.CUSTOMER_ID | missing | - |
| BAD_AI_READY.RAW_CUSTOMERS.EMAIL | missing | - |
| BAD_AI_READY.RAW_CUSTOMERS.FULL_NAME | missing | - |
| BAD_AI_READY.RAW_CUSTOMERS.LAST_PURCHASE_AMT | missing | - |
| BAD_AI_READY.RAW_CUSTOMERS.NOTES | missing | - |
| BAD_AI_READY.RAW_CUSTOMERS.PHONE | missing | - |
| BAD_AI_READY.RAW_CUSTOMERS.SIGNUP_WHEN_TXT | missing | - |
| BAD_AI_READY.RAW_CUSTOMERS.SSN | missing | - |
| BAD_AI_READY.RAW_CUSTOMERS.STATUS_TXT | missing | - |
| BAD_AI_READY.RAW_ORDERS.AMOUNT_TXT | missing | - |
| BAD_AI_READY.RAW_ORDERS.CURRENCY_CODE | missing | - |
| BAD_AI_READY.RAW_ORDERS.CUSTOMER_ID | missing | - |
| BAD_AI_READY.RAW_ORDERS.ORDER_ID | missing | - |
| BAD_AI_READY.RAW_ORDERS.ORDER_PAYLOAD | missing | - |
| BAD_AI_READY.RAW_ORDERS.ORDER_TIME_TXT | missing | - |
| BAD_AI_READY.RAW_ORDERS.PAYMENT_CARD_HINT | missing | - |
| BAD_AI_READY.RAW_ORDERS.SHIPPING_POSTAL_CODE | missing | - |
| BAD_AI_READY.RAW_ORDER_LINES.DISCOUNT_TXT | missing | - |
| BAD_AI_READY.RAW_ORDER_LINES.LINE_COMMENT | missing | - |
| BAD_AI_READY.RAW_ORDER_LINES.LINE_NO | missing | - |
| BAD_AI_READY.RAW_ORDER_LINES.ORDER_ID | missing | - |
| BAD_AI_READY.RAW_ORDER_LINES.QUANTITY_TXT | missing | - |
| BAD_AI_READY.RAW_ORDER_LINES.SKU | missing | - |
| BAD_AI_READY.RAW_ORDER_LINES.UNIT_PRICE_TXT | missing | - |
| BAD_AI_READY.SUPPORT_TICKETS.AGENT_EMAIL | missing | - |
| BAD_AI_READY.SUPPORT_TICKETS.CUSTOMER_ID | missing | - |
| BAD_AI_READY.SUPPORT_TICKETS.PROBLEM_DESCRIPTION | missing | - |
| BAD_AI_READY.SUPPORT_TICKETS.REQUESTER_PHONE | missing | - |
| BAD_AI_READY.SUPPORT_TICKETS.RESOLUTION_TEXT | missing | - |
| BAD_AI_READY.SUPPORT_TICKETS.SEVERITY_TXT | missing | - |
| BAD_AI_READY.SUPPORT_TICKETS.TICKET_ID | missing | - |
| BAD_AI_READY.SUPPORT_TICKETS.TICKET_STATUS | missing | - |

## 9. Semantic type mismatch
文字列型ですが、列名またはコメントから数値・日付として扱われる可能性がある列です。推定結果のため、自動的な型変更は行いません。

| Column | DB type | 推定される意味 | 根拠 | 推奨対応 |
|---|---|---|---|---|
| BAD_AI_READY.CUSTOMER_FEATURES.CHURN_SCORE_TXT | VARCHAR2 | NUMBER | name: SCORE | NUMBER列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.CUSTOMER_FEATURES.LIFETIME_VALUE_TXT | VARCHAR2 | NUMBER | name: VALUE | NUMBER列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.RAW_CUSTOMERS.BIRTHDATE_TXT | VARCHAR2 | DATE/TIMESTAMP | name: BIRTHDATE | DATE/TIMESTAMP列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.RAW_CUSTOMERS.LAST_PURCHASE_AMT | VARCHAR2 | NUMBER | name: AMT | NUMBER列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.RAW_CUSTOMERS.SIGNUP_WHEN_TXT | VARCHAR2 | DATE/TIMESTAMP | name: WHEN | DATE/TIMESTAMP列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.RAW_ORDERS.AMOUNT_TXT | VARCHAR2 | NUMBER | name: AMOUNT | NUMBER列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.RAW_ORDERS.ORDER_TIME_TXT | VARCHAR2 | DATE/TIMESTAMP | name: TIME | DATE/TIMESTAMP列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.RAW_ORDER_LINES.DISCOUNT_TXT | VARCHAR2 | NUMBER | name: DISCOUNT | NUMBER列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.RAW_ORDER_LINES.QUANTITY_TXT | VARCHAR2 | NUMBER | name: QUANTITY | NUMBER列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.RAW_ORDER_LINES.UNIT_PRICE_TXT | VARCHAR2 | NUMBER | name: PRICE | NUMBER列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.SUPPORT_TICKETS.SEVERITY_TXT | VARCHAR2 | NUMBER | name: SEVERITY | NUMBER列、仮想列、または型付きAI用Viewを検討してください。 |

## 10. 改善SQLの考え方
| SQLカテゴリ | 理由 | 目的 | 実行前確認 |
|---|---|---|---|
| COMMENT ON TABLE / COLUMN | コメント欠落はmandatory gateとContextual scoreを下げます。 | 業務意味、粒度、単位、NULL意味、機微性を明文化します。 | TODO文を実説明に置換し、業務オーナー承認後に実行します。 |
| Comment quality review | コメントが存在してもplaceholderや汎用文ではAIへ十分な意味を伝えられません。 | 実際の業務説明へ置き換えます。 | 自動上書きはせず、人間がレビューします。 |
| Semantic type review | 文字列型に数値・日付が保存されるとNL2SQLで暗黙変換や文字列比較が発生します。 | 型付き列、仮想列、AI用Viewを検討します。 | 自動ALTERは生成しません。データとアプリ影響を確認します。 |
| DBMS_STATS.GATHER_TABLE_STATS | LAST_ANALYZED未設定/古い統計はClean/Current scoreを下げます。 | 統計情報を収集します。 | 大規模表ではDBA確認が必要です。 |
| PRIMARY KEY / freshness column | キーや鮮度列の不足は根拠追跡や新しさ説明を弱くします。 | 根拠行の特定と鮮度説明を可能にします。 | テンプレートのため設計レビューが必要です。 |
| REVOKE候補 | 広いデータ権限はAI利用前の公開範囲確認が必要です。 | 不要な公開を減らします。 | 依存利用者への影響を確認します。 |

```sql
-- Remediation: missing table comments
-- Reason: テーブルコメントがないため、Contextual score と mandatory comment gate が低下します。
-- Purpose: テーブルの業務目的、粒度、更新頻度、AI利用時の注意点を明文化します。
-- Review: TODOコメントを業務オーナーが実際の説明に置き換えてから実行してください。
COMMENT ON TABLE "BAD_AI_READY"."AI_DOCUMENTS" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.AI_DOCUMENTS.';
COMMENT ON TABLE "BAD_AI_READY"."CUSTOMER_FEATURES" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.CUSTOMER_FEATURES.';
COMMENT ON TABLE "BAD_AI_READY"."EMPTY_EXPORT" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.EMPTY_EXPORT.';
COMMENT ON TABLE "BAD_AI_READY"."ORPHAN_REGIONS" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.ORPHAN_REGIONS.';
COMMENT ON TABLE "BAD_AI_READY"."RAW_CUSTOMERS" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.RAW_CUSTOMERS.';
COMMENT ON TABLE "BAD_AI_READY"."RAW_ORDERS" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.RAW_ORDERS.';
COMMENT ON TABLE "BAD_AI_READY"."RAW_ORDER_LINES" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.RAW_ORDER_LINES.';
COMMENT ON TABLE "BAD_AI_READY"."SUPPORT_TICKETS" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.SUPPORT_TICKETS.';

-- Remediation: missing column comments
-- Reason: カラムコメントがないため、AIが列の意味、単位、NULLの意味、機微性を誤解する可能性があります。
-- Purpose: 各カラムの意味、形式、許容値、NULLの扱い、出所、機微性を明文化します。
-- Review: TODOコメントを業務オーナーが実際の説明に置き換えてから実行してください。
COMMENT ON COLUMN "BAD_AI_READY"."AI_DOCUMENTS"."BODY_TEXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AI_DOCUMENTS.BODY_TEXT.';
COMMENT ON COLUMN "BAD_AI_READY"."AI_DOCUMENTS"."CHUNK_NUMBER" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AI_DOCUMENTS.CHUNK_NUMBER.';
COMMENT ON COLUMN "BAD_AI_READY"."AI_DOCUMENTS"."DOC_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AI_DOCUMENTS.DOC_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."AI_DOCUMENTS"."EMBEDDING_BLOB_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AI_DOCUMENTS.EMBEDDING_BLOB_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."AI_DOCUMENTS"."LIFECYCLE_STATE" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AI_DOCUMENTS.LIFECYCLE_STATE.';
COMMENT ON COLUMN "BAD_AI_READY"."AI_DOCUMENTS"."ORIGIN_URI" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AI_DOCUMENTS.ORIGIN_URI.';
COMMENT ON COLUMN "BAD_AI_READY"."AI_DOCUMENTS"."TITLE_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AI_DOCUMENTS.TITLE_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."CUSTOMER_FEATURES"."CHURN_SCORE_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.CUSTOMER_FEATURES.CHURN_SCORE_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."CUSTOMER_FEATURES"."CUSTOMER_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.CUSTOMER_FEATURES.CUSTOMER_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."CUSTOMER_FEATURES"."FEATURE_NOTES" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.CUSTOMER_FEATURES.FEATURE_NOTES.';
COMMENT ON COLUMN "BAD_AI_READY"."CUSTOMER_FEATURES"."LIFETIME_VALUE_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.CUSTOMER_FEATURES.LIFETIME_VALUE_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."CUSTOMER_FEATURES"."SEGMENT_CODE" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.CUSTOMER_FEATURES.SEGMENT_CODE.';
COMMENT ON COLUMN "BAD_AI_READY"."EMPTY_EXPORT"."EXPORT_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.EMPTY_EXPORT.EXPORT_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."EMPTY_EXPORT"."EXPORT_NAME" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.EMPTY_EXPORT.EXPORT_NAME.';
COMMENT ON COLUMN "BAD_AI_READY"."EMPTY_EXPORT"."PAYLOAD" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.EMPTY_EXPORT.PAYLOAD.';
COMMENT ON COLUMN "BAD_AI_READY"."ORPHAN_REGIONS"."COUNTRY_CODE" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.ORPHAN_REGIONS.COUNTRY_CODE.';
COMMENT ON COLUMN "BAD_AI_READY"."ORPHAN_REGIONS"."REGION_NAME" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.ORPHAN_REGIONS.REGION_NAME.';
COMMENT ON COLUMN "BAD_AI_READY"."ORPHAN_REGIONS"."RISK_TIER_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.ORPHAN_REGIONS.RISK_TIER_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."BIRTHDATE_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.BIRTHDATE_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."COUNTRY_CODE" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.COUNTRY_CODE.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."CUSTOMER_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.CUSTOMER_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."EMAIL" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.EMAIL.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."FULL_NAME" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.FULL_NAME.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."LAST_PURCHASE_AMT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.LAST_PURCHASE_AMT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."NOTES" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.NOTES.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."PHONE" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.PHONE.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."SIGNUP_WHEN_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.SIGNUP_WHEN_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."SSN" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.SSN.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."STATUS_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.STATUS_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDERS"."AMOUNT_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDERS.AMOUNT_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDERS"."CURRENCY_CODE" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDERS.CURRENCY_CODE.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDERS"."CUSTOMER_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDERS.CUSTOMER_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDERS"."ORDER_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDERS.ORDER_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDERS"."ORDER_PAYLOAD" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDERS.ORDER_PAYLOAD.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDERS"."ORDER_TIME_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDERS.ORDER_TIME_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDERS"."PAYMENT_CARD_HINT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDERS.PAYMENT_CARD_HINT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDERS"."SHIPPING_POSTAL_CODE" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDERS.SHIPPING_POSTAL_CODE.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDER_LINES"."DISCOUNT_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDER_LINES.DISCOUNT_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDER_LINES"."LINE_COMMENT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDER_LINES.LINE_COMMENT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDER_LINES"."LINE_NO" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDER_LINES.LINE_NO.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDER_LINES"."ORDER_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDER_LINES.ORDER_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDER_LINES"."QUANTITY_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDER_LINES.QUANTITY_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDER_LINES"."SKU" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDER_LINES.SKU.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDER_LINES"."UNIT_PRICE_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDER_LINES.UNIT_PRICE_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."SUPPORT_TICKETS"."AGENT_EMAIL" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.SUPPORT_TICKETS.AGENT_EMAIL.';
COMMENT ON COLUMN "BAD_AI_READY"."SUPPORT_TICKETS"."CUSTOMER_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.SUPPORT_TICKETS.CUSTOMER_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."SUPPORT_TICKETS"."PROBLEM_DESCRIPTION" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.SUPPORT_TICKETS.PROBLEM_DESCRIPTION.';
COMMENT ON COLUMN "BAD_AI_READY"."SUPPORT_TICKETS"."REQUESTER_PHONE" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.SUPPORT_TICKETS.REQUESTER_PHONE.';
COMMENT ON COLUMN "BAD_AI_READY"."SUPPORT_TICKETS"."RESOLUTION_TEXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.SUPPORT_TICKETS.RESOLUTION_TEXT.';
COMMENT ON COLUMN "BAD_AI_READY"."SUPPORT_TICKETS"."SEVERITY_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.SUPPORT_TICKETS.SEVERITY_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."SUPPORT_TICKETS"."TICKET_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.SUPPORT_TICKETS.TICKET_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."SUPPORT_TICKETS"."TICKET_STATUS" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.SUPPORT_TICKETS.TICKET_STATUS.';

-- Remediation: missing or stale optimizer statistics
-- Reason: LAST_ANALYZEDが未設定または古いため、Clean/Current score が低下します。
-- Purpose: Oracle optimizer統計を収集し、メタデータ上もデータ状態を確認しやすくします。
-- Review: 大きい表ではメンテナンス時間、DBMS_STATS設定、サンプリング方針をDBAと確認してください。
-- Target: BAD_AI_READY.EMPTY_EXPORT; stats_reason=missing
BEGIN
  DBMS_STATS.GATHER_TABLE_STATS(
    ownname => 'BAD_AI_READY',
    tabname => 'EMPTY_EXPORT',
    cascade => TRUE,
    method_opt => 'FOR ALL COLUMNS SIZE AUTO'
  );
END;
/

-- Template only: primary key candidates
-- Reason: 主キー未検出のため、Clean/Correlated/Consumable score が低下します。
-- Purpose: AI回答の根拠行を安定して参照できる業務キーを明確にします。
-- Review: 重複データ、NULL、既存アプリ影響、制約名、索引方針を確認するまで実行しないでください。
-- ALTER TABLE "BAD_AI_READY"."AI_DOCUMENTS" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);
-- ALTER TABLE "BAD_AI_READY"."CUSTOMER_FEATURES" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);
-- ALTER TABLE "BAD_AI_READY"."EMPTY_EXPORT" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);
-- ALTER TABLE "BAD_AI_READY"."ORPHAN_REGIONS" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);
-- ALTER TABLE "BAD_AI_READY"."RAW_CUSTOMERS" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);
-- ALTER TABLE "BAD_AI_READY"."RAW_ORDERS" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);
-- ALTER TABLE "BAD_AI_READY"."RAW_ORDER_LINES" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);
-- ALTER TABLE "BAD_AI_READY"."SUPPORT_TICKETS" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);

-- Template only: freshness column candidates
-- Reason: 鮮度列が未検出のため、Current score が低下し、AI回答でデータの新しさを説明しづらくなります。
-- Purpose: 更新日時、取込日時、有効期間などを明示し、RAG/agent回答の鮮度説明を可能にします。
-- Review: アプリが別の方法で鮮度を管理していないか確認し、列追加の影響をレビューしてください。
-- ALTER TABLE "BAD_AI_READY"."AI_DOCUMENTS" ADD "UPDATED_AT" TIMESTAMP(6);
-- ALTER TABLE "BAD_AI_READY"."CUSTOMER_FEATURES" ADD "UPDATED_AT" TIMESTAMP(6);
-- ALTER TABLE "BAD_AI_READY"."EMPTY_EXPORT" ADD "UPDATED_AT" TIMESTAMP(6);
-- ALTER TABLE "BAD_AI_READY"."ORPHAN_REGIONS" ADD "UPDATED_AT" TIMESTAMP(6);
-- ALTER TABLE "BAD_AI_READY"."RAW_CUSTOMERS" ADD "UPDATED_AT" TIMESTAMP(6);
-- ALTER TABLE "BAD_AI_READY"."RAW_ORDERS" ADD "UPDATED_AT" TIMESTAMP(6);
-- ALTER TABLE "BAD_AI_READY"."RAW_ORDER_LINES" ADD "UPDATED_AT" TIMESTAMP(6);
-- ALTER TABLE "BAD_AI_READY"."SUPPORT_TICKETS" ADD "UPDATED_AT" TIMESTAMP(6);

-- Review only: broad data grants
-- Reason: PUBLICなど広い相手へのデータアクセス権限があるため、Compliant score が低下します。
-- Purpose: AI利用前に公開範囲が意図通りかを確認し、不要な広い権限を減らします。
-- Review: REVOKEはアプリや利用者に影響するため、DBA/業務オーナー確認後に個別判断してください。
-- Review grant: SELECT on BAD_AI_READY.RAW_CUSTOMERS to PUBLIC
-- REVOKE SELECT ON "BAD_AI_READY"."RAW_CUSTOMERS" FROM "PUBLIC";
-- Review grant: SELECT on BAD_AI_READY.RAW_ORDERS to PUBLIC
-- REVOKE SELECT ON "BAD_AI_READY"."RAW_ORDERS" FROM "PUBLIC";
-- Review grant: SELECT on BAD_AI_READY.SUPPORT_TICKETS to PUBLIC
-- REVOKE SELECT ON "BAD_AI_READY"."SUPPORT_TICKETS" FROM "PUBLIC";
```

## 11. 手動レビューが必要な項目
- 機微情報候補列: 10件。業務オーナーによる分類が必要です。
- 広いデータ権限候補: 3件。DBA確認が必要です。
- Semantic type mismatch候補: 11件。推定のため業務・アプリ仕様と照合してください。
- 主キー、外部キー、更新日時、データ粒度、保持期間はアプリケーション仕様と照合してください。

## 12. 次のアクション
1. 欠落しているテーブルコメント8件、カラムコメント52件を補完し、Mandatory comment gateをpassにします。
2. 構造・運用メタデータを改善します: 主キー未定義8表、未取得または古い統計1表、鮮度列未定義8表、出所列未定義8表。
3. 文字列型に保存された数値・日付候補11列を確認し、型付き列、仮想列、またはAI用Viewを検討します。
4. DBA・業務オーナーがセキュリティとプライバシーを確認します: 広いデータ権限3件、機微情報候補10列。
