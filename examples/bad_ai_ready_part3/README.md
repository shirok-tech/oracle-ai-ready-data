# 第3回: Annotation / Domain の最小比較

> **2026-09-29追記：** 利用者による2026-09-23の実DB再検証と日英HTML目視確認は
> 完了しました。[最終検証報告](../../docs/v0.4-validation-complete.md)と
> [第3回記事原稿](../../docs/articles/oracle-ai-ready-data-part3.md)を参照してください。
> 再検証は既存ラボを使用しており、この生成器のDDL一式を新規環境で再実行したものではありません。
> 以下の実装時点の記録と、初回作成用の手順はそのまま残しています。

3行・3列の表を2つ作り、直接AnnotationとDomain由来Annotationを比較する手順です。既存の第2回の8表、行データ、Profileを変更しません。`AIRD_D01`、`AIRD_T02`、`AIRD_T03`と4つの`AIRD_P_*` Profileだけを追加し、同名オブジェクトがあれば停止します。

このリポジトリのv0.4.0実装作業では、SQL生成とローカルテストのみ実施しています。以下のDatabase接続・DDL/DML・外部LLM呼び出しは、利用者が対象環境と生成ファイルを確認した後に実施する手順です。[RESULTS.md](RESULTS.md)にはユーザーから提供された過去の実測と限界を記録しています。

## 前提とファイル生成

- Python 3.10以上、SQLcl、Annotation / Domain / Select AIに対応する検証用Database。
- データ所有者とSelect AI実行User。所有者には検証用表・Domain作成権限、実行Userには`DBMS_CLOUD_AI`の利用権限とproviderへの接続設定が必要です。
- 実行Userが所有する**既存Credentialのオブジェクト名**と、利用環境で動作確認済みの**OpenAIモデル名**を別々に指定します。`SELECT credential_name FROM user_credentials`で名前を確認してください。パスワードやAPIキーを入力しません。

リポジトリのルートで実行します。`YOUR_EXISTING_CREDENTIAL`、`YOUR_VERIFIED_MODEL`を実際の名前に置き換えます。モデルの既定値はありません。

```bash
python3 examples/bad_ai_ready_part3/generate_part3.py \
  --output-dir examples/bad_ai_ready_part3/generated_run01 \
  --owner BAD_AI_READY --select-ai-user ADB_USER \
  --credential-name YOUR_EXISTING_CREDENTIAL \
  --model YOUR_VERIFIED_MODEL
```

生成処理は標準ライブラリのみを使い、DatabaseにもLLMにも接続しません。既存の`generate_select_ai_setup.py`の識別子検証・Profile属性生成・Profile作成処理を再利用します。OpenAIの最小構成が対象です。別providerや独自endpointが必要な場合は、既存の汎用Profile生成器を使って必要な接続属性を揃えてください。`domains=true`のような追加属性は使いません。

出力ディレクトリの再利用を拒否します。`manifest.json`には所有者、実行User、Credential名、モデル、表、属性、質問、試行数を記録します。`--trials 3`が既定値で、固定のSQL文字列や正答率を期待する設定ではありません。

| 生成ファイル | 実施内容 |
|---|---|
| `01_create_lab.sql` | 所有者でDomain、2表、6行、2表のSELECT権限を追加 |
| `02_dictionary_reference.sql` | 所有者で辞書と参照値を保存 |
| `03_create_profiles.sql` | 実行Userで既存Credentialを確認して4 Profileを作成 |
| `04_*_probe.sql` | Profile属性、SHOWPROMPT、SHOWSQLを別ファイルに保存 |
| `reviews/*.sql` | SHOWSQL出力を保存する場所。未記入なら実行を停止 |
| `05_*_reviewed.sql` | レビュー後に保存したSQLそのものを実行 |
| `06_*_runsql.sql` | 既定では無効。明示opt-in時のみ別の生成・実行 |
| `99_cleanup_template.sql` | コメント化された手動の後片付け |

## 1. 辞書と参照結果

生成したSQLを読んでから、出力ディレクトリへ移動します。接続文字列は環境に合わせて変更し、パスワードはSQLclの対話入力に任せます。各スクリプトは終了時に接続を閉じます。DDLには暗黙のcommitがあるため、途中の失敗をROLLBACKで一括復元できません。

```bash
cd examples/bad_ai_ready_part3/generated_run01
sql BAD_AI_READY@adb_high @01_create_lab.sql
sql BAD_AI_READY@adb_high @02_dictionary_reference.sql
```

`logs/02_dictionary.csv`で`AIRD_T02.C03`の直接Annotation、`AIRD_T03.C03`の`DOMAIN_OWNER` / `DOMAIN_NAME`、`AIRD_D01`の定義を別々に確認します。Domain定義の行を表の列coverageに足しません。データ所有者で見える辞書とSelect AI実行Userで見えるメタデータは同一とは限りません。

`logs/02_reference.log`の両表で全件合計2500、有効な注文（`Q7`）の合計2000を確認します。コメント、CHECK、PK/FKは追加していません。

一般の収集には`scripts/generate_semantics_collector.py`で生成する読み取り専用Collectorを使用します。リポジトリのルートからの生成例は次のとおりです。`AIRD_T0_`の最初のアンダースコアは文字そのもの、末尾は1文字のワイルドカードとして指定しています。

```bash
python3 scripts/generate_semantics_collector.py \
  --owner BAD_AI_READY --table-like 'AIRD\_T0_' \
  --output examples/bad_ai_ready_part3/generated_run01/collect_lab_semantics.sql \
  --spool-file lab_semantics_owner_r01.json
```

生成ファイルをレビューし、出力ディレクトリで所有者のSQLclセッションから`@collect_lab_semantics.sql`を実行します。Select AI実行Userでの収集も比較する場合は、別のspool名へ生成して実行します。可視性と対象範囲を記録し、元のスキャンと照合できるようにします。JSONをScorerへ渡す方法は[利用手順](../../docs/USAGE.md)を参照してください。辞書機能のない環境で、この必須前提のラボSQLが成功することは要求しません。旧環境の互換性は一般Collector側で扱います。

## 2. Profile属性 → SHOWPROMPT → SHOWSQL

```bash
sql ADB_USER@adb_high @03_create_profiles.sql
sql ADB_USER@adb_high @04_AIRD_P_D_OFF_r01_probe.sql
sql ADB_USER@adb_high @04_AIRD_P_D_ON_r01_probe.sql
sql ADB_USER@adb_high @04_AIRD_P_M_OFF_r01_probe.sql
sql ADB_USER@adb_high @04_AIRD_P_M_ON_r01_probe.sql
```

`r02`、`r03`も同様に新しいSQLclセッションで実施します。ログオンスクリプトで会話を自動作成しないでください。実験中にFeedbackを登録しません。共通属性は`comments=false`、`constraints=false`、`conversation=false`、`enforce_object_list=true`です。同じ表のOff/Onペアは`annotations`以外を一致させ、モデル・Credential・object_listも各試行の`*_attributes.csv`で確認します。`temperature`や`seed`を新たに固定しません。同じ設定でも生成結果が変わる可能性があります。

| 条件 | 表 | annotations |
|---|---|---|
| Direct-Off / Direct-On | AIRD_T02 | false / true |
| Domain-Off / Domain-On | AIRD_T03 | false / true |

質問は「有効な注文について、C02の合計を教えてください。」です。`*_showprompt.txt`で`MAP_PROOF_V1`と`Q7 = active`の値対応を確認します。DDLログに同じマーカーがあってもプロンプト取り込みの証拠にはしません。

```bash
grep -HnE 'MAP_PROOF_V1|Q7 = active' logs/*_showprompt.txt
grep -HnE 'ORA-[0-9]+|SP2-|SQLcl' logs/*
```

grepは補助確認です。結果が長い場合はファイル全体を読み、切れていないことも確認します。`SHOWPROMPT`と`SHOWSQL`は別呼び出しであり、個々の辞書情報・生成SQLの意味を独立して判定します。

## 3. 保存した生成SQLのレビューと実行

`*_showsql.txt`のSQL本体を、対応する`reviews/AIRD_P_D_ON_r01.sql`等へコピーします。テンプレートの停止用PL/SQLをすべて置き換え、説明やコードフェンスだけを取り除いて、SQLの終端にセミコロンを付けます。条件を書き直した場合は修正版として別記録にし、生成成功に数えません。

次をレビューします。

- 指定Profileの`AIRD_T02`または`AIRD_T03`だけを読むSELECTであること。PL/SQL、SQLclコマンド、複数文、DML/DDL等を含む応答は実行しません。
- `SUM(C02)`相当を計算し、`C03 = 'Q7'`相当で有効な注文を特定していること。
- 偶然同じ数値になるだけの条件を正解としないこと。例えば`C03 <> 'X9'`は未知のコードを有効と扱い得るため要レビューです。

レビュー済みファイルを実行する例です。

```bash
sql ADB_USER@adb_high @05_AIRD_P_D_ON_r01_reviewed.sql
```

`*_reviewed_result.log`にSQL本体と結果が残ります。LLMは呼び出しません。安全なSQLでも意味が誤っていれば不正解として記録します。非SQL応答、範囲外参照等は失敗として記録し、実行しません。Offが正解しても異常ではありません。登録数や結果だけでプロンプトへの取り込みを断定しないでください。

## 4. RUNSQLは任意の別試行

`06_*_runsql.sql`は既定で何も生成・実行しません。必要な場合のみ、別の新規出力ディレクトリへ同じ設定で`--enable-runsql`を指定して生成します。新しいディレクトリでは`01`〜`03`を再実行せず、既存Profile属性が同じことを確認したうえで`06`を実行します。

リポジトリのルートで生成する例です。

```bash
python3 examples/bad_ai_ready_part3/generate_part3.py \
  --output-dir examples/bad_ai_ready_part3/generated_runsql01 \
  --owner BAD_AI_READY --select-ai-user ADB_USER \
  --credential-name YOUR_EXISTING_CREDENTIAL \
  --model YOUR_VERIFIED_MODEL --enable-runsql
cd examples/bad_ai_ready_part3/generated_runsql01
sql ADB_USER@adb_high @06_AIRD_P_D_OFF_r01_runsql.sql
```

各`06`は`*_runsql_attributes.csv`も保存します。元のプローブの属性と比較して設定変更がないことを確認し、4条件×3回を別々のセッションで記録します。

RUNSQLは自然言語から**新たにSQLを生成して実行**します。SHOWSQLでレビューしたSQLそのものの実行には使いません。RUNSQLの2500やNULLだけから内部のWHERE条件や対象行数を断定しません。

`SET NULL '(NULL)'`でNULLを可視化し、SQL表示・結果表示は`LINESIZE 220`、長いプロンプトのみ`PAGESIZE 0`と`LINESIZE 32767`を使います。大量の見出し埋めやパディングを避けます。ファイル名にはProfile・試行番号が入り、`SPOOL ... CREATE`を使います。既存ログがある試行を繰り返さず、新しい出力ディレクトリまたは新しい試行番号を使ってください。SPOOLエラー時は以降の実験を中止し、ファイルが作成されたことを確認してください。

```bash
grep -HnE '2000|2500|\(NULL\)|ORA-[0-9]+' logs/*_runsql.log
```

保存SQL実行と別試行RUNSQLの判定は[EVIDENCE_TEMPLATE.md](EVIDENCE_TEMPLATE.md)で分けて記録します。

## 5. 証跡と片付け

`manifest.json`、辞書、Profile属性、プロンプト、生成SQL、レビューしたSQL、結果、手動判定を保存します。接続パスワード、APIキー、トークンをログへ残さず、共有時には業務メタデータも確認します。

`99_cleanup_template.sql`は手動確認後に必要な行だけコメントを外します。データ所有者とProfile所有者の接続を分け、検証用2表・Domain・4 Profileだけを削除します。既存の第2回の表・Profileは削除しません。ラボ表を残して通常Collectorの`%`を再収集すると分母が増えるため、以前のスコアと比較する際は同じ対象8表に範囲を揃えてください。

## 公式仕様

- [CREATE DOMAIN](https://docs.oracle.com/en/database/oracle/oracle-database/26/sqlrf/create-domain.html) / [CREATE TABLE](https://docs.oracle.com/en/database/oracle/oracle-database/26/sqlrf/CREATE-TABLE.html): Domainと列の関連付け。
- [annotations_clause](https://docs.oracle.com/en/database/oracle/oracle-database/26/sqlrf/annotations_clause.html): Annotationの定義。
- [DBMS_CLOUD_AI](https://docs.oracle.com/en/cloud/paas/autonomous-database/serverless/adbsb/dbms-cloud-ai-package.html): Profile属性。生成器の既存のannotations対応を利用します。
- [Use AI Keyword to Enter Prompts](https://docs.oracle.com/en/database/oracle/oracle-database/26/selai/use-ai-keyword-enter-prompts.html): SHOWPROMPT、SHOWSQL、RUNSQL。
- [SPOOL](https://docs.oracle.com/en/database/oracle/oracle-database/26/sqpug/SPOOL.html): CREATEによる新規ログ保存。

View由来の継承、高度なDomain機能、実環境での権限・provider互換性は、この最小例の検証範囲に含みません。
