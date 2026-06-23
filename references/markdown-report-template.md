# Markdown report template

Use this structure unless the user requests a different format.

```markdown
# Oracle Database AI Ready 評価レポート

## 1. エグゼクティブサマリー
- 総合スコア: X.XX / 1.00
- Profile: scan または rag
- Mandatory comment gate: pass/fail
- 結論: ready / usable with remediation / pilot only / not ready

## 2. スコープと前提
| 項目 | 値 |
|---|---|
| Schema | ... |
| Table pattern | ... |
| 評価対象テーブル数 | ... |
| 評価対象カラム数 | ... |
| SQLcl spool | ... |
| 注意事項 | ... |

## 3. スコアカード
| Dimension | Score | 主な根拠 |
|---|---:|---|
| Clean | 0.00 | ... |
| Contextual | 0.00 | ... |
| Consumable | 0.00 | ... |
| Current | 0.00 | ... |
| Correlated | 0.00 | ... |
| Compliant | 0.00 | ... |

## 4. Mandatory comment gate
| Check | Coverage | Result | Required action |
|---|---:|---|---|
| Table comments | ... | pass/fail | ... |
| Column comments | ... | pass/fail | ... |

## 5. 主要な発見事項
### High priority
- ...

### Medium priority
- ...

### Low priority
- ...

## 6. 改善 SQL
> 実行前に DBA / アプリケーションオーナーがレビューしてください。

```sql
-- generated SQL here
```

## 7. 手動レビューが必要な項目
- 機微情報候補列
- PUBLIC など広い権限付与
- 業務キー、データ粒度、更新頻度、保持期間

## 8. 次のアクション
1. ...
2. ...
3. ...
```

Keep the report concise, but include enough evidence to explain every score. If there are more than 100 missing comments, show a representative sample and mention that the full generated SQL file or parser output contains additional statements.
