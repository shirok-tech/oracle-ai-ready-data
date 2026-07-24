# Oracle Database AI Ready 評価レポート

## 1. エグゼクティブサマリー
- 総合スコア: **0.97 / 1.00**
- Profile: **scan**
- Mandatory comment gate: **pass**
- Comment quality review: **pass**
- Semantic type warnings: **11件**
- 結論: **AI Ready候補**
- コメント有無チェックは必須条件です。コメント品質とSemantic type mismatchは初期実装では警告であり、既存スコアには影響しません。

## 2. スコープと前提
| 項目 | 値 |
|---|---|
| Schema | BAD_AI_READY |
| Table pattern | % |
| Profile | scan |
| 評価対象テーブル数 | 8 |
| 評価対象カラム数 | 68 |
| SQLcl spool | bad_ai_ready_after.out |
| Scan timestamp | 2026-07-21T05:50:04.843069 +00:00 |
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
| Clean | 20.0% | 1.00 | PK 100.0%, table stats 100.0%, column stats 100.0%, constraints 100.0% |
| Contextual | 25.0% | 1.00 | table comments 100.0%, column comments 100.0%, relationships 100.0% |
| Consumable | 15.0% | 1.00 | text-bearing tables 100.0%, vector tables 0.0%, documentation 100.0%, PK 100.0% |
| Current | 15.0% | 1.00 | freshness columns 100.0%, recent stats 100.0% |
| Correlated | 15.0% | 0.83 | FK 62.5%, source metadata 100.0%, PK 100.0% |
| Compliant | 10.0% | 0.96 | sensitive documented 100.0%, broad data grant absence 100.0% |

## 5. メトリクス詳細
| Metric | Value | Status | 説明 |
|---|---:|---|---|
| Table comment coverage | 100.0% | pass | コメントが設定されている評価対象テーブルの割合です。100%でない場合は必須ゲートがfailです。 |
| Column comment coverage | 100.0% | pass | コメントが設定されている評価対象カラムの割合です。100%でない場合は必須ゲートがfailです。 |
| PK coverage | 100.0% | 良好 | 有効な主キーがあるテーブルの割合です。AI回答の根拠行を安定して参照するために重要です。 |
| FK coverage | 62.5% | 要確認 | 外部キーを持つ、または外部キー関係に参加するテーブルの割合です。表間の関連を安全に扱うための指標です。 |
| Relationship coverage | 100.0% | 良好 | 主キーまたは外部キーのいずれかを持つテーブルの割合です。データモデルの説明可能性を見ます。 |
| Constraint coverage | 100.0% | 良好 | 主キー、一意、外部キー、CHECK制約のいずれかがあるテーブルの割合です。構造的な品質管理の指標です。 |
| Table stats coverage | 100.0% | 良好 | LAST_ANALYZEDが入っているテーブルの割合です。統計情報が未取得だとデータ状態の確認が弱くなります。 |
| Column stats coverage | 100.0% | 良好 | LAST_ANALYZEDが入っているカラムの割合です。列分布やNULL傾向の評価に使います。 |
| Recent stats coverage | 100.0% | 良好 | 統計情報が最近取得されているテーブルの割合です。既定では90日以内をrecentと見なします。 |
| Freshness coverage | 100.0% | 良好 | UPDATED_ATやLAST_UPDATE_DATEなど、鮮度を示す列があるテーブルの割合です。 |
| Source metadata coverage | 100.0% | 良好 | SOURCE_SYSTEM、BATCH_ID、CREATED_BYなど、出所や更新者を示す列があるテーブルの割合です。 |
| Text-bearing table coverage | 100.0% | 参考 | RAG候補となるテキスト列を持つテーブルの割合です。検索対象テキストの有無を確認します。 |
| Vector table coverage | 0.0% | 参考 | VECTOR型またはembedding候補を持つテーブルの割合です。embeddingを外部管理している場合は設計書で補足してください。 |
| Sensitive candidate documentation | 100.0% | 良好 | 機微情報候補列のうちコメントがある列の割合です。列名ベース推定なので人間の分類が必要です。 |
| Broad data grant absence | 100.0% | 良好 | PUBLICなど広い相手へのデータアクセス権限が検出されなかった割合です。高いほどリスクが低い見立てです。 |
| Table comment quality coverage | 100.0% | pass | コメント本文がplaceholder、短すぎる説明、汎用文ではない割合です。初期実装では警告のみです。 |
| Column comment quality coverage | 100.0% | pass | コメント本文がplaceholder、短すぎる説明、汎用文ではない割合です。初期実装では警告のみです。 |

## 6. Mandatory comment gate
| Check | Coverage | Result | Required action |
|---|---:|---|---|
| Table comments | 100.0% | pass | Missing 0 table comments |
| Column comments | 100.0% | pass | Missing 0 column comments |

## 7. 主要な発見事項
### High priority
- High priority の自動検出事項はありません。

### Medium priority
- 機微情報候補列が 10 件あります。列名ベースの推定のため、業務オーナーによる分類が必要です。

### Low priority / manual review
- VECTOR型カラムは未検出です。embeddingを別スキーマや外部サービスで管理している場合は設計書に明記してください。

## 8. コメント品質
| 項目 | 値 |
|---|---:|
| Table comment quality coverage | 100.0% |
| Column comment quality coverage | 100.0% |
| Placeholder comments | 0 |
| Too-short comments | 0 |
| Generic/name-only comments | 0 |
| Repeated generic groups | 0 |

- コメント品質の自動レビュー対象はありません。

## 9. Semantic type mismatch
文字列型ですが、列名またはコメントから数値・日付として扱われる可能性がある列です。推定結果のため、自動的な型変更は行いません。

| Column | DB type | 推定される意味 | 根拠 | 推奨対応 |
|---|---|---|---|---|
| BAD_AI_READY.CUSTOMER_FEATURES.CHURN_SCORE_TXT | VARCHAR2 | NUMBER | name: SCORE; comment: 小数文字列 | NUMBER列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.CUSTOMER_FEATURES.LIFETIME_VALUE_TXT | VARCHAR2 | NUMBER | name: VALUE; comment: 小数文字列, 数値変換 | NUMBER列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.RAW_CUSTOMERS.BIRTHDATE_TXT | VARCHAR2 | DATE/TIMESTAMP | name: BIRTHDATE; comment: yyyy-mm-dd | DATE/TIMESTAMP列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.RAW_CUSTOMERS.LAST_PURCHASE_AMT | VARCHAR2 | NUMBER | name: AMT; comment: to_number, 数値変換, 数値文字列 | NUMBER列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.RAW_CUSTOMERS.SIGNUP_WHEN_TXT | VARCHAR2 | DATE/TIMESTAMP | name: WHEN; comment: hh24:mi:ss, yyyy-mm-dd, 日時を | DATE/TIMESTAMP列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.RAW_ORDERS.AMOUNT_TXT | VARCHAR2 | NUMBER | name: AMOUNT; comment: 数値変換, 数値文字列 | NUMBER列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.RAW_ORDERS.ORDER_TIME_TXT | VARCHAR2 | DATE/TIMESTAMP | name: TIME; comment: to_date, yyyy-mm-dd | DATE/TIMESTAMP列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.RAW_ORDER_LINES.DISCOUNT_TXT | VARCHAR2 | NUMBER | name: DISCOUNT; comment: 数値文字列 | NUMBER列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.RAW_ORDER_LINES.QUANTITY_TXT | VARCHAR2 | NUMBER | name: QUANTITY; comment: to_number, 数値変換, 整数文字列 | NUMBER列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.RAW_ORDER_LINES.UNIT_PRICE_TXT | VARCHAR2 | NUMBER | name: PRICE; comment: 数値文字列 | NUMBER列、仮想列、または型付きAI用Viewを検討してください。 |
| BAD_AI_READY.SUPPORT_TICKETS.SEVERITY_TXT | VARCHAR2 | NUMBER | name: SEVERITY; comment: 整数文字列 | NUMBER列、仮想列、または型付きAI用Viewを検討してください。 |

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
-- No executable improvement SQL generated from the available metadata.
```

## 11. 手動レビューが必要な項目
- 機微情報候補列: 10件。業務オーナーによる分類が必要です。
- 広いデータ権限候補: 0件。DBA確認が必要です。
- Semantic type mismatch候補: 11件。推定のため業務・アプリ仕様と照合してください。
- 主キー、外部キー、更新日時、データ粒度、保持期間はアプリケーション仕様と照合してください。

## 12. 次のアクション
1. 文字列型に保存された数値・日付候補11列を確認し、型付き列、仮想列、またはAI用Viewを検討します。
2. DBA・業務オーナーがセキュリティとプライバシーを確認します: 機微情報候補10列。
