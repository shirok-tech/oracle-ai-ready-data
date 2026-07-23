# BAD_AI_READY Part 2 v1.0.0

Oracle DatabaseのAI Ready評価を、意図的に未整備な`BAD_AI_READY`スキーマで失敗させ、改善SQLの適用後に再評価するための再現可能なデモパッケージです。

## 主な内容

- 8表、52列、448行の合成テストデータ
- コメント、PK/FK、鮮度列、出所メタデータ、統計を欠落させた初期DDL
- 8件のPK、5件のFK、68列分のコメント、`UPDATED_AT`、`SOURCE_SYSTEM`、統計収集を適用する改善SQL
- 改善前後の検証SQL
- Select AI用AI Profile、10件の日本語SHOWSQL/RUNSQLプロンプト、参照SQL
- RAG準備用の任意VECTOR列追加SQL

## 実測結果

- scan: 0.08 / fail → 0.97 / pass
- rag: 0.21 / fail → 0.93 / pass

RAG評価ではVECTOR coverageが0%のため、Vector Searchを含む完全なRAG Readyを意味しません。

## v4でのSelect AIプロンプト改善

- T03: 注文金額の明示的な数値変換を要求
- T07: 離反スコアと生涯価値の明示的な数値変換を要求
- T08: `ACTIVE`と`JP`のコード条件を明示

すべてのメール、電話番号、識別番号、文書URIは合成値です。実APIキー、トークン、credential値は含みません。
