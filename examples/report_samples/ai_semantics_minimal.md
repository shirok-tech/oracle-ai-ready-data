# Oracle Database AI Ready 評価レポート

## 1. エグゼクティブサマリー
- 総合スコア: **0.10 / 1.00**
- Profile: **scan**
- Mandatory comment gate: **fail**
- Comment quality review: **fail**
- Semantic type warnings: **0件**
- 結論: **必須コメントゲート未達のため、要求ポリシー上は未Ready**
- コメント有無チェックは必須条件です。コメント品質とSemantic type mismatchは初期実装では警告であり、既存スコアには影響しません。

## 2. スコープと前提
| 項目 | 値 |
|---|---|
| Schema | BAD_AI_READY |
| Table pattern | - |
| Profile | scan |
| 評価対象テーブル数 | 2 |
| 評価対象カラム数 | 6 |
| SQLcl spool | minimal_scan.csv |
| Scan timestamp | - |
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
| Clean | 20.0% | 0.00 | PK 0.0%, table stats 0.0%, column stats 0.0%, constraints 0.0% |
| Contextual | 25.0% | 0.00 | table comments 0.0%, column comments 0.0%, relationships 0.0% |
| Consumable | 15.0% | 0.00 | text-bearing tables 0.0%, vector tables 0.0%, documentation 0.0%, PK 0.0% |
| Current | 15.0% | 0.00 | freshness columns 0.0%, recent stats 0.0% |
| Correlated | 15.0% | 0.00 | FK 0.0%, source metadata 0.0%, PK 0.0% |
| Compliant | 10.0% | 1.00 | sensitive documented 100.0%, broad data grant absence 100.0% |

## 5. メトリクス詳細
| Metric | Value | Status | 説明 |
|---|---:|---|---|
| Table comment coverage | 0.0% | fail | コメントが設定されている評価対象テーブルの割合です。100%でない場合は必須ゲートがfailです。 |
| Column comment coverage | 0.0% | fail | コメントが設定されている評価対象カラムの割合です。100%でない場合は必須ゲートがfailです。 |
| PK coverage | 0.0% | 要改善 | 有効な主キーがあるテーブルの割合です。AI回答の根拠行を安定して参照するために重要です。 |
| FK coverage | 0.0% | 要改善 | 外部キーを持つ、または外部キー関係に参加するテーブルの割合です。表間の関連を安全に扱うための指標です。 |
| Relationship coverage | 0.0% | 要改善 | 主キーまたは外部キーのいずれかを持つテーブルの割合です。データモデルの説明可能性を見ます。 |
| Constraint coverage | 0.0% | 要改善 | 主キー、一意、外部キー、CHECK制約のいずれかがあるテーブルの割合です。構造的な品質管理の指標です。 |
| Table stats coverage | 0.0% | 要改善 | LAST_ANALYZEDが入っているテーブルの割合です。統計情報が未取得だとデータ状態の確認が弱くなります。 |
| Column stats coverage | 0.0% | 要改善 | LAST_ANALYZEDが入っているカラムの割合です。列分布やNULL傾向の評価に使います。 |
| Recent stats coverage | 0.0% | 要改善 | 統計情報が最近取得されているテーブルの割合です。既定では90日以内をrecentと見なします。 |
| Freshness coverage | 0.0% | 要改善 | UPDATED_ATやLAST_UPDATE_DATEなど、鮮度を示す列があるテーブルの割合です。 |
| Source metadata coverage | 0.0% | 要改善 | SOURCE_SYSTEM、BATCH_ID、CREATED_BYなど、出所や更新者を示す列があるテーブルの割合です。 |
| Text-bearing table coverage | 0.0% | 参考 | RAG候補となるテキスト列を持つテーブルの割合です。検索対象テキストの有無を確認します。 |
| Vector table coverage | 0.0% | 参考 | VECTOR型またはembedding候補を持つテーブルの割合です。embeddingを外部管理している場合は設計書で補足してください。 |
| Sensitive candidate documentation | 100.0% | 良好 | 機微情報候補列のうちコメントがある列の割合です。列名ベース推定なので人間の分類が必要です。 |
| Broad data grant absence | 100.0% | 良好 | PUBLICなど広い相手へのデータアクセス権限が検出されなかった割合です。高いほどリスクが低い見立てです。 |
| Table comment quality coverage | 0.0% | fail | コメント本文がplaceholder、短すぎる説明、汎用文ではない割合です。初期実装では警告のみです。 |
| Column comment quality coverage | 0.0% | fail | コメント本文がplaceholder、短すぎる説明、汎用文ではない割合です。初期実装では警告のみです。 |

## 6. Mandatory comment gate
| Check | Coverage | Result | Required action |
|---|---:|---|---|
| Table comments | 0.0% | fail | Missing 2 table comments |
| Column comments | 0.0% | fail | Missing 6 column comments |

## 7. 主要な発見事項
### High priority
- Mandatory comment gate が fail です。table comment 欠落 2 件、column comment 欠落 6 件があります。
- 主キー未検出のテーブルが 2 件あります。RAG/agent応答の根拠行を安定して参照しづらくなります。

### Medium priority
- 統計情報が未取得または古いテーブルが 2 件あります。Clean/Current score の主な減点要因です。
- 鮮度を示す日時列が未検出のテーブルが 2 件あります。データの新しさを説明しづらくなります。
- テキスト候補列を持つテーブルは 0.0% です。RAG対象テーブルを明確化してください。

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
| BAD_AI_READY.AIRD_T02 | missing | - |
| BAD_AI_READY.AIRD_T03 | missing | - |
| BAD_AI_READY.AIRD_T02.C01 | missing | - |
| BAD_AI_READY.AIRD_T02.C02 | missing | - |
| BAD_AI_READY.AIRD_T02.C03 | missing | - |
| BAD_AI_READY.AIRD_T03.C01 | missing | - |
| BAD_AI_READY.AIRD_T03.C02 | missing | - |
| BAD_AI_READY.AIRD_T03.C03 | missing | - |

## 9. Semantic type mismatch
- Semantic type mismatch候補はありません。

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
COMMENT ON TABLE "BAD_AI_READY"."AIRD_T02" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.AIRD_T02.';
COMMENT ON TABLE "BAD_AI_READY"."AIRD_T03" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.AIRD_T03.';

-- Remediation: missing column comments
-- Reason: カラムコメントがないため、AIが列の意味、単位、NULLの意味、機微性を誤解する可能性があります。
-- Purpose: 各カラムの意味、形式、許容値、NULLの扱い、出所、機微性を明文化します。
-- Review: TODOコメントを業務オーナーが実際の説明に置き換えてから実行してください。
COMMENT ON COLUMN "BAD_AI_READY"."AIRD_T02"."C01" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AIRD_T02.C01.';
COMMENT ON COLUMN "BAD_AI_READY"."AIRD_T02"."C02" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AIRD_T02.C02.';
COMMENT ON COLUMN "BAD_AI_READY"."AIRD_T02"."C03" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AIRD_T02.C03.';
COMMENT ON COLUMN "BAD_AI_READY"."AIRD_T03"."C01" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AIRD_T03.C01.';
COMMENT ON COLUMN "BAD_AI_READY"."AIRD_T03"."C02" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AIRD_T03.C02.';
COMMENT ON COLUMN "BAD_AI_READY"."AIRD_T03"."C03" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AIRD_T03.C03.';

-- Remediation: missing or stale optimizer statistics
-- Reason: LAST_ANALYZEDが未設定または古いため、Clean/Current score が低下します。
-- Purpose: Oracle optimizer統計を収集し、メタデータ上もデータ状態を確認しやすくします。
-- Review: 大きい表ではメンテナンス時間、DBMS_STATS設定、サンプリング方針をDBAと確認してください。
-- Target: BAD_AI_READY.AIRD_T02; stats_reason=missing
BEGIN
  DBMS_STATS.GATHER_TABLE_STATS(
    ownname => 'BAD_AI_READY',
    tabname => 'AIRD_T02',
    cascade => TRUE,
    method_opt => 'FOR ALL COLUMNS SIZE AUTO'
  );
END;
/
-- Target: BAD_AI_READY.AIRD_T03; stats_reason=missing
BEGIN
  DBMS_STATS.GATHER_TABLE_STATS(
    ownname => 'BAD_AI_READY',
    tabname => 'AIRD_T03',
    cascade => TRUE,
    method_opt => 'FOR ALL COLUMNS SIZE AUTO'
  );
END;
/

-- Template only: primary key candidates
-- Reason: 主キー未検出のため、Clean/Correlated/Consumable score が低下します。
-- Purpose: AI回答の根拠行を安定して参照できる業務キーを明確にします。
-- Review: 重複データ、NULL、既存アプリ影響、制約名、索引方針を確認するまで実行しないでください。
-- ALTER TABLE "BAD_AI_READY"."AIRD_T02" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);
-- ALTER TABLE "BAD_AI_READY"."AIRD_T03" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);

-- Template only: freshness column candidates
-- Reason: 鮮度列が未検出のため、Current score が低下し、AI回答でデータの新しさを説明しづらくなります。
-- Purpose: 更新日時、取込日時、有効期間などを明示し、RAG/agent回答の鮮度説明を可能にします。
-- Review: アプリが別の方法で鮮度を管理していないか確認し、列追加の影響をレビューしてください。
-- ALTER TABLE "BAD_AI_READY"."AIRD_T02" ADD "UPDATED_AT" TIMESTAMP(6);
-- ALTER TABLE "BAD_AI_READY"."AIRD_T03" ADD "UPDATED_AT" TIMESTAMP(6);
```

## 11. 手動レビューが必要な項目
- 機微情報候補列: 0件。業務オーナーによる分類が必要です。
- 広いデータ権限候補: 0件。DBA確認が必要です。
- Semantic type mismatch候補: 0件。推定のため業務・アプリ仕様と照合してください。
- 主キー、外部キー、更新日時、データ粒度、保持期間はアプリケーション仕様と照合してください。

## 12. 次のアクション
1. 欠落しているテーブルコメント2件、カラムコメント6件を補完し、Mandatory comment gateをpassにします。
2. 構造・運用メタデータを改善します: 主キー未定義2表、未取得または古い統計2表、鮮度列未定義2表、出所列未定義2表。

## 13. AI Semantics Readiness (Advisory)

Annotation／Domainは任意のAdvisoryです。件数・coverageでスコアやCOMMENT必須ゲートは変わりません。
coverageの母数は、補助Collectorの収集対象と元の評価対象が重なるdistinct列です。直接登録と継承が同じ列にある場合も全体では1列です。未収集・失敗・対象列0件はN/Aです。
値なしAnnotationや任意ラベルも有効です。登録数は意味の正しさを保証しません。DESCRIPTION／ALIASES／VALUESを含む内容は業務担当者が確認してください。Domain名の ? は由来情報の不足です。
ALL_*で現セッションに見える範囲のみです。データ所有者と実行Userの可視性、収集日時、対象範囲を照合してください。View経由の継承や高度なDomain機能は未対応です。
ランタイム証跡は references/semantics-evidence-template.md に独立して記録してください。RUNSQLは別の生成試行であり、レビューした保存SQLの実行ではありません。

### 収集状態

| Component | State | Diagnostic |
| --- | --- | --- |
| scope | collected / 収集成功 | Normalized from displayed successful dictionary query output in the user-provided draft. |
| annotations | collected / 収集成功 | Normalized from displayed successful dictionary query output in the user-provided draft. |
| domains | collected / 収集成功 | Normalized from displayed successful dictionary query output in the user-provided draft. |

### 集計

| Metric | Value |
| --- | --- |
| 収集対象の表数 | 2 |
| 収集対象の列数（重複排除） | 6 |
| 元の評価対象列数 | 6 |
| 表Annotationがある表数 | 0 |
| Annotated columns | 2 |
| Direct columns | 1 |
| Domain-inherited columns | 1 |
| 由来不明の列数 | 0 |
| Domain-linked columns | 1 |
| Column annotation coverage | 33.33% |
| 対象外の意味情報レコード（除外） | 3 |

### 収集コンテキスト

| Field | Value |
| --- | --- |
| session&#95;user | ADB&#95;USER |
| current&#95;schema | N/A |
| target&#95;owner | BAD&#95;AI&#95;READY |
| table&#95;like&#95;pattern | N/A |
| db&#95;name | N/A |
| con&#95;name | N/A |
| collected&#95;at | N/A |

### Annotationと由来

| Object | Level | Category | Name | Value | Origin | Domain |
| --- | --- | --- | --- | --- | --- | --- |
| BAD&#95;AI&#95;READY.AIRD&#95;T02.C03 | COLUMN | ALIASES | ALIASES | Order status, 注文状態, 注文ステータス | DIRECT | — |
| BAD&#95;AI&#95;READY.AIRD&#95;T02.C03 | COLUMN | DESCRIPTION | DESCRIPTION | MAP&#95;PROOF&#95;V1: Order status code. 有効な注文 means active orders. | DIRECT | — |
| BAD&#95;AI&#95;READY.AIRD&#95;T02.C03 | COLUMN | VALUES | VALUES | Q7 = active &#40;有効な注文&#41;; X9 = cancelled &#40;取消済みの注文&#41; | DIRECT | — |
| BAD&#95;AI&#95;READY.AIRD&#95;T03.C03 | COLUMN | ALIASES | ALIASES | Order status, 注文状態, 注文ステータス | DOMAIN&#95;INHERITED | BAD&#95;AI&#95;READY.AIRD&#95;D01 |
| BAD&#95;AI&#95;READY.AIRD&#95;T03.C03 | COLUMN | DESCRIPTION | DESCRIPTION | MAP&#95;PROOF&#95;V1: Order status code. 有効な注文 means active orders. | DOMAIN&#95;INHERITED | BAD&#95;AI&#95;READY.AIRD&#95;D01 |
| BAD&#95;AI&#95;READY.AIRD&#95;T03.C03 | COLUMN | VALUES | VALUES | Q7 = active &#40;有効な注文&#41;; X9 = cancelled &#40;取消済みの注文&#41; | DOMAIN&#95;INHERITED | BAD&#95;AI&#95;READY.AIRD&#95;D01 |

### 列のDomain関連付け

| Column | Domain | Domain column |
| --- | --- | --- |
| BAD&#95;AI&#95;READY.AIRD&#95;T03.C03 | BAD&#95;AI&#95;READY.AIRD&#95;D01 | — |

### 独立した検証事項

| Stage | Evidence |
| --- | --- |
| 辞書登録（観測） | 収集値を参照。業務上の正しさは未確認 |
| Profile設定 | 未確認 |
| SHOWPROMPT確認 | 未確認 |
| 生成SQLレビュー | 未確認 |
| 保存SQLの実行 | 未確認 |
| 別試行RUNSQL | 未確認 |
