# AI Semantics 実行証跡 / Runtime evidence

これは人が記入する記録です。未確認欄を推測で埋めず、関連するレポートと
一緒に共有してください。v0.4 Scorerはこの文書を自動採点・取り込みしません。
接続パスワード、APIキー、トークン、Credentialの秘密値は記載しません。

## 実行条件 / Context

| 項目 / Field | 記録 / Record |
|---|---|
| 実施者・実施日時 / Operator and time | 未記入 / Unspecified |
| Database製品・サービス・完全なバージョン / Database and full version | 未記入 |
| データ所有者 / Data owner | 未記入 |
| 実行User・current schema / Execution user and schema | 未記入 |
| 対象表・列 / Scoped objects | 未記入 |
| Profile名 / Profile | 未記入 |
| Provider・モデル / Provider and model | 未記入 |
| 実行User所有の既存Credential名 / Existing user-owned credential name | 未記入（秘密値不可） |
| comments / constraints / annotations | 未記入 |
| その他Profile属性・object_list / Other attributes and scope | 未記入 |
| Off/On条件・試行番号 / Condition and trial ID | 未記入 |
| 自然言語の質問 / Exact prompt | 未記入 |
| 参照SQL・期待する意味と結果 / Reference SQL, expected meaning and result | 未記入 |

## 独立した確認 / Independent checks

各行に状態（未確認・確認済み・問題あり）と、ファイル名・該当箇所・観察内容を
記載します。成功した段階から他の段階の成功を推定しません。

| 段階 / Stage | 状態 / State | 証跡と観察 / Evidence and observation |
|---|---|---|
| 辞書登録：表/列Annotation、Domain関連付け、継承元 | 未確認 / Unverified | |
| Profile設定：Credential名、モデル、対象表、属性 | 未確認 / Unverified | |
| SHOWPROMPT：対象列に結び付いた値対応・マーカー | 未確認 / Unverified | |
| SHOWSQLの保存と意味のレビュー：対象表・結合・条件・集計 | 未確認 / Unverified | |
| レビューした保存SQLそのものの実行結果 | 未確認 / Unverified | |
| 任意の別試行RUNSQL：試行番号・結果・エラー | 未確認 / Unverified | |

## 結果と限界 / Result and limitations

- SQL文字列の完全一致ではなく、業務上の意味と参照結果を比較する。
- 同じ数値が偶然返る誤ったSQLを正答としない。
- RUNSQLは新しい生成呼び出し。レビュー済みSHOWSQLと同一と仮定しない。
- RUNSQLの2500やNULLだけから、WHERE条件や対象行の有無を断定しない。
- 試行回数、モデル、質問、データの制限を記録し、一般的な精度保証としない。
- 未実施項目と次の確認事項：未記入。
