# ユーザー提供の過去実測

出典はユーザー提供のブログ原稿第3回v0.7、v0.4.0実装依頼、および修正済みRUNSQLログです。原本ログはリポジトリへ取り込んでいません。以下はユーザー環境での観測であり、この実装作業でDatabaseやLLMを呼び出した結果ではありません。再現時の合格率を固定するfixtureでもありません。

| 項目 | 提供された環境 |
|---|---|
| Database | Oracle AI Database 26ai、23.26.3.3.0 |
| Provider / model | OpenAI / gpt-5.4-nano |
| データ所有者 / Select AI実行User | BAD_AI_READY / ADB_USER |
| 最小実験 | comments=false、constraints=false。Off/On間でannotationsのみ変更 |
| 表と由来 | AIRD_T02.C03: 直接、AIRD_T03.C03: AIRD_D01由来 |
| 意味と参照値 | Q7=有効、X9=取消。有効合計2000、全件合計2500 |

このモデル名をSkillや生成器の既定値にはしていません。

| 条件 | SHOWSQLの意味が正しい回数 | 保存SQLの結果が正しい回数 | 別試行RUNSQL r01 / r02 / r03 |
|---|---:|---:|---|
| Direct-Off | 0/3 | 0/3 | 2500 / 2500 / 2500 |
| Direct-On | 3/3 | 3/3 | 2000 / 2000 / 2000 |
| Domain-Off | 0/3 | 0/3 | NULL / NULL / NULL |
| Domain-On | 3/3 | 3/3 | 2000 / 2000 / 2000 |

辞書上のDomain継承と、OnのSHOWPROMPTへのマーカー・値対応の取り込みを確認した、と報告されています。修正済みRUNSQLログ本文のDomain-Off r01〜r03には`(NULL)`があり、12試行はDatabaseエラーなく完了したとされています。末尾のgrep一覧だけではNULL行が表示されていないため、本文も参照しました。

保存したSHOWSQLのSQLを確認した事実と、別試行RUNSQLの結果を分けます。RUNSQLの2500から条件の欠落を、NULLから内部SQLの特定条件や対象行数を断定しません。

後半は既存の3表`RAW_CUSTOMERS`・`RAW_ORDERS`・`RAW_ORDER_LINES`を使い、comments=true、constraints=trueのOff/Onで比較した観測です。

| 質問 | Off | On |
|---|---|---|
| 日本の有効な顧客数 | 3/3、結果6 | 3/3、結果6 |
| 日本の有効な顧客が購入した商品のSKU別総数量上位10件 | 3/3、参照結果と一致 | 3/3、参照結果と一致 |

OnのSHOWPROMPTへの追加Annotation取り込みは報告されていますが、この2問では正答率差は観測されていません。このリポジトリの最小再現例は2表とDomainの比較までを扱い、後半の3表にはAnnotationを追加しません。

3回ずつの小規模検証であり、一般的な精度保証ではありません。AnnotationやDomainの有無・coverageだけで適格性や業務的な正しさを判定せず、既存スコアとCOMMENT必須ゲートを維持します。View継承や高度なDomain機能まで検証済みとは扱いません。
