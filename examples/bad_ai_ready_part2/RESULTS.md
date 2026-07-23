# 実測結果と確認事項

## AI Ready評価のBefore / After

| Profile | 改善前 | 改善後 | Mandatory comment gate |
|---|---:|---:|---|
| scan | 0.08 | 0.97 | fail → pass |
| rag | 0.21 | 0.93 | fail → pass |

改善後の`scan`では、テーブルコメント、カラムコメント、PK、Relationship、Constraint、統計、鮮度列、出所メタデータ、機微情報候補のドキュメント、Broad data grant absenceが100%になりました。FK coverageは、FKを所有する子表が8表中5表のため62.5%です。独立表へスコア目的の不自然なFKは追加していません。

改善後の`rag`もMandatory comment gateはpassしました。ただしVECTOR列は0%です。この結果は、テキスト、ID、コメント、鮮度、出所などのメタデータ整備を示すもので、embedding生成、Vector Index、検索品質までを保証しません。

## Select AIの確認方針

1. `12_select_ai_showsql_prompts.sql`で生成SQLをレビューします。
2. 表選択、JOIN、コード条件、明示的な型変換、機微情報の非表示を確認します。
3. 問題がなければ`13_select_ai_runsql_prompts.sql`を実行します。
4. `14_select_ai_reference_sql.sql`の結果と比較します。

初回ログでは、T03の金額集計とT07のスコア比較で暗黙変換が使われ、T08では「有効な顧客」の`STATUS_TXT='ACTIVE'`条件が省略されました。v4では自然言語を次のように明確化しています。

- T03: 注文金額を数値へ変換して集計することを明示
- T07: 離反スコアと顧客生涯価値を数値へ変換することを明示
- T08: `STATUS_TXT='ACTIVE'`と`COUNTRY_CODE='JP'`に相当するコード条件を明示

LLMの出力はモデルや時点で変わるため、参照SQLとの文字列一致ではなく、意味と結果を比較してください。AI ReadyはLLM生成SQLの無条件な正しさを保証しません。
