
# oracle-ai-ready-data 第2回用 BAD_AI_READY v4

この版は、**改善SQLをそのまま適用してAI Ready評価を改善する**ことに焦点を合わせたデモです。

初期状態ではコメント、PK/FK、鮮度・出所メタデータ、統計情報を意図的に欠落させます。一方、CSVの行データは最初から一意性と参照整合性を満たすため、前処理なしで改善SQLを実行できます。

> 注意: `BAD_AI_READY`ユーザーを削除・再作成します。必ず検証用データベースで実行してください。

## 0. 前提環境と実行場所

- Oracle Database（`DBMS_CLOUD_AI`を利用するSelect AI確認では、対応するAutonomous Database環境）
- SQLcl（CSVロードで`LOAD`コマンドを使用）
- Python 3.10以降（`oracle-ai-ready-data`の評価スクリプトとローカル検証用）
- スキーマ作成用の管理者アカウント、`BAD_AI_READY`、およびSelect AI用の読取り専用ユーザー
- Select AI確認時のみ、DBAが事前作成したCredentialオブジェクト名`OPENAI_CRED`。Credential値、APIキー、トークンはこのパッケージに含めない

SQLclはこのパッケージのルートで起動してください。これにより`02_load_csv.sql`内の`data/*.csv`と、以下の`@`による相対パスが一致します。

```bash
cd examples/bad_ai_ready_part2
sql BAD_AI_READY/"<password>"@"<connect-identifier>"
```

実環境では、機微情報、コメントに含める業務説明、接続先、権限、および外部AIプロバイダへの送信対象を、業務オーナーとDBAが必ず確認してください。

## 1. 変更点

旧版にあった重複ID、NULLキー、孤児レコード、不正形式値は削除しました。

- 8表、元の52列、合計448行は維持
- PK候補はすべてNULLなし・一意
- FK候補はすべて参照先あり
- `07_apply_ai_ready_improvements.sql`にレビュー済みコメント、PK/FK、`UPDATED_AT`、`SOURCE_SYSTEM`、統計収集、PUBLIC権限削除を収録
- 改善後は8表、68列になり、全列にコメントが設定される
- Select AI実行ログを踏まえ、T03・T07は数値変換を明示し、T08は`ACTIVE`と`JP`のコード条件を明示

## 2. 収録ファイル

```text
bad_ai_ready_part2/
├── 00_admin_create_schema.sql ... 14_select_ai_reference_sql.sql
├── 90_drop_schema.sql
├── data/
├── tools/
├── DATA_DESIGN.md
├── RESULTS.md
└── SELECT_AI_TEST_CASES.md
```

| ファイル | 内容 |
|---|---|
| `00_admin_create_schema.sql` | `BAD_AI_READY`ユーザーを再作成 |
| `01_create_bad_tables.sql` | コメント・制約・鮮度/出所列なしの8表を作成 |
| `02_load_csv.sql` | SQLclで整合済みCSVをロード |
| `03_optional_public_grants.sql` | 任意で3件のPUBLIC SELECTを付与 |
| `04_delete_stats_before_scan.sql` | 初回評価前に統計を削除 |
| `05_verify_badness.sql` | メタデータ不足とPK/FK候補が有効であることを確認 |
| `06_part3_reference_queries.sql` | 第3回のSelect AI比較用正解SQL |
| `07_apply_ai_ready_improvements.sql` | 今回用に整形した実行可能な改善SQL |
| `08_verify_after_improvement.sql` | 改善後のコメント、PK/FK、鮮度、出所、統計、権限を検証 |
| `09_optional_prepare_ai_documents_rag.sql` | 任意。AI_DOCUMENTSへVECTOR列を追加するスキーマ準備 |
| `10_grant_select_ai_access.sql` | 専用Select AIユーザーへ8表のSELECT権限を付与 |
| `11_create_select_ai_profile.sql` | コメントとPK/FKを有効にしたOpenAI Profileを作成 |
| `12_select_ai_showsql_prompts.sql` | 10件の日本語プロンプトで生成SQLをレビュー |
| `13_select_ai_runsql_prompts.sql` | レビュー後に同じ10件を実行 |
| `14_select_ai_reference_sql.sql` | 生成SQLと結果を比較する決定的な参照SQL |
| `SELECT_AI_TEST_CASES.md` | 自然言語、合格基準、期待結果の一覧 |
| `DATA_DESIGN.md` | PK/FK候補とデータ設計 |
| `RESULTS.md` | 改善前後の実測結果とSelect AI確認時の注意点 |
| `GITHUB_PUBLISHING.md` | GitHubリポジトリとReleaseへの公開手順 |

## 3. 行数

| CSV | 行数 |
|---|---:|
| `raw_customers.csv` | 50 |
| `raw_orders.csv` | 100 |
| `raw_order_lines.csv` | 200 |
| `ai_documents.csv` | 12 |
| `customer_features.csv` | 50 |
| `support_tickets.csv` | 30 |
| `orphan_regions.csv` | 6 |
| `empty_export.csv` | 0 |
| **合計** | **448** |

## 4. 改善前の評価

```sql
@00_admin_create_schema.sql        -- ADMINで実行
@01_create_bad_tables.sql          -- BAD_AI_READYで実行
@02_load_csv.sql
@03_optional_public_grants.sql     -- 任意
@04_delete_stats_before_scan.sql
@05_verify_badness.sql
```

その後、Skillを`scan` profileで実行します。コメントが0件のためMandatory comment gateはfailになります。

## 5. 改善SQLの実行

```sql
@07_apply_ai_ready_improvements.sql
@08_verify_after_improvement.sql
```

`07`は、Skillが生成した改善カテゴリを今回のデモに合わせて確定したものです。

- 8件の`COMMENT ON TABLE`
- 改善後68列すべての`COMMENT ON COLUMN`
- 8件のPKと5件のFKを`ENABLE VALIDATE`で追加
- 全8表へ`UPDATED_AT`と`SOURCE_SYSTEM`を追加
- 任意に付与したPUBLIC SELECT/READを削除
- 全8表のオプティマイザ統計を収集

## 6. 改善後にSkillを再実行

```bash
sql -s 'admin/<password>@<connect-identifier>' \
  @../../scripts/oracle_ai_ready_collect.sql BAD_AI_READY % scan

python3 ../../scripts/score_oracle_ai_ready_scan.py \
  oracle_ai_ready_scan_BAD_AI_READY_scan.out \
  --profile scan \
  --language ja \
  --output bad_ai_ready_scan_after_report.md \
  --sql-output bad_ai_ready_scan_after_improvement.sql
```

期待する変化は次のとおりです。

| 指標 | 改善前 | 改善後の期待値 |
|---|---:|---:|
| Table comment coverage | 0% | 100% |
| Column comment coverage | 0% | 100% |
| Mandatory comment gate | fail | pass |
| PK coverage | 0% | 100% |
| Relationship coverage | 0% | 100% |
| Constraint coverage | 0% | 100% |
| Freshness coverage | 0% | 100% |
| Source metadata coverage | 0% | 100% |
| Recent statistics coverage | 0%または環境依存 | 100% |
| Sensitive candidate documentation | 0% | 100% |
| Broad data grant absence | 62.5%または100% | 100% |

総合スコアはSkillのバージョンとprofile重みにより変動するため、記事では固定値ではなく、Mandatory gateのpassと各coverageの改善を示してください。

今回の実測では、`scan`は**0.08 / fail**から**0.97 / pass**へ、`rag`は**0.21 / fail**から**0.93 / pass**へ改善しました。RAG側はVECTOR列が未作成のため、Vector Searchを含む完全なRAG Readyを意味しません。詳細は`RESULTS.md`を参照してください。

### 再実行時の挙動

最初からやり直す場合は、管理者で`00_admin_create_schema.sql`を実行してから、`01`〜`08`を順に実行してください。`01_create_bad_tables.sql`は対象8表を削除して作り直します。`07_apply_ai_ready_improvements.sql`は、鮮度・出所列と制約を存在確認して追加するため、同一のロード済みデータに対して再実行できます。再実行時もコメントを再適用し、統計を再収集します。`11_create_select_ai_profile.sql`は同名Profileを作り直すため、実行前に対象ユーザーの既存Profileへの影響を確認してください。

## 7. 記事にそのまま使える説明

> 初回評価では、テーブルコメント8件とカラムコメント52件が欠落し、主キー、外部キー、鮮度列、出所メタデータも未定義だったため、Mandatory comment gateはfailとなった。そこで、Skillが示した改善カテゴリを今回のデータモデルに合う説明へ具体化し、PK/FK候補を確定して実行した。テストデータは最初から一意性と参照整合性を満たすため、データ修復を挟まずに制約をENABLE VALIDATEで追加できた。再評価ではコメントcoverageが100%となりMandatory comment gateがpassし、Clean、Contextual、Current、Correlated、Compliantの各指標も改善した。

## 8. RAG profileについて

第2回で「AI Readyになった」と述べる対象は、全8表を対象にした`scan` profileです。RAGを扱う場合は、検索対象である`AI_DOCUMENTS`だけにscopeを絞り、必要に応じて`09_optional_prepare_ai_documents_rag.sql`を実行してください。

この任意スクリプトはVECTOR列を追加するだけで、embedding生成や検索品質を保証しません。実際のRAG Ready評価は、embeddingを投入して検索精度を確認する回で扱うのが適切です。

## 9. ローカル再生成・検証

```bash
python3 tools/generate_csv.py
python3 tools/validate_package.py
```

すべてのメール、電話番号、識別番号、文書URIは合成値です。


## 10. Select AIでNL2SQLの機能確認

改善後のAI Ready評価に加えて、整備したコメントとPK/FKがSelect AIのSQL生成で使われることを確認できます。

### 10.1 専用ユーザーへ読取り権限を付与

`07_apply_ai_ready_improvements.sql`の後、`BAD_AI_READY`で実行します。Qiita記事と異なるSelect AIユーザーを使う場合は、スクリプト先頭の`SELECT_AI_USER`を変更します。

```sql
@10_grant_select_ai_access.sql
```

### 10.2 AI Profileを作成

Qiita記事の手順でACL、`DBMS_CLOUD_AI`権限、`OPENAI_CRED`を準備した`ADB_USER`へ接続して実行します。

```sql
@11_create_select_ai_profile.sql
```

このProfileでは、改善SQLで整備したメタデータをLLMへ渡すため、次を明示しています。

```json
"comments": true,
"constraints": true,
"object_list_mode": "all",
"enforce_object_list": true
```

`comments=true`により表・列コメントを、`constraints=true`によりPK/FKなどの参照制約をNL2SQL生成用メタデータへ含めます。

### 10.3 生成SQLを先に確認

```sql
@12_select_ai_showsql_prompts.sql
```

次を確認します。

- 顧客、注文、明細、問い合わせ、特徴量、国マスタから正しい表を選ぶ
- PK/FKと同じ列で2表または3表をJOINする
- 日付・金額・数量・スコアを保持する`*_TXT`列を必要に応じて変換する
- 通貨を混在させずに集計する
- メール、電話番号、SSN、カード情報を出力しない

生成SQLの書式はモデルにより変わるため、`14_select_ai_reference_sql.sql`との文字列一致ではなく、意味と結果を比較します。

### 10.4 レビュー後に実行

```sql
@13_select_ai_runsql_prompts.sql
```

期待値と詳細は`SELECT_AI_TEST_CASES.md`にあります。主な期待値は次のとおりです。

| テスト | 期待値 |
|---|---|
| 全顧客数 | 50 |
| 国名別の有効顧客 | 6か国、合計40人 |
| 日本の有効顧客の注文上位 | 6人、1位は顧客31のJPY 141.95 |
| 2025年月別・通貨別注文額 | 60行 |
| 注文なし顧客 | 0 |
| OPEN/IN_PROGRESSかつ重大度4以上 | 7顧客 |
| 離反スコア0.80以上 | S1=2、S2=5、S3=3 |
| 日本のACTIVE顧客が購入したSKU上位 | 指定10SKU、各総数量2 |
| 注文データの出所 | PART2_CSV、100行 |
| 外部出力データ | 0 |

### 10.5 記事での位置づけ

Select AIが正しいSQLと結果を返したことは、AI Ready評価そのものの代替ではありません。記事では次の3段階で示します。

1. Skill再評価でMandatory comment gateが`pass`になり、コメント、PK/FK、鮮度、出所、統計などのcoverageが改善した。
2. `SELECT AI SHOWSQL`で、表選択、JOIN条件、コード条件、型変換、機微情報の非表示をレビューした。
3. `SELECT AI RUNSQL`の結果を`14_select_ai_reference_sql.sql`と比較し、意味と結果が一致することを確認した。

LLMは同じメタデータでも条件や型変換を省略する場合があります。そのため、AI ReadyはSQLの無条件な正しさを保証するものではなく、`SHOWSQL`によるレビューを含めた運用が必要です。

> 注意: Select AIのNL2SQLでは、オブジェクト名、列名、データ型、コメントなどのスキーマメタデータがAIプロバイダへ送信されます。このパッケージはすべて合成データですが、実データベースではobject_listとコメント内容を事前に確認してください。
