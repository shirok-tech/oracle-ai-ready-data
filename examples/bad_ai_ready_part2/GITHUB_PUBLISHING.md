# GitHub公開手順

## 推奨構成

- 展開したソース一式をリポジトリの`examples/bad_ai_ready_part2/`へコミットする
- 配布用ZIPをGitHub Releaseのassetとして添付する

ソースを展開してコミットすると、SQL、Markdown、CSVの差分をレビューできます。ZIPは利用者が一括ダウンロードするための配布物として扱います。

## Gitで追加する例

```bash
git clone <REPOSITORY_URL>
cd <REPOSITORY_NAME>
git switch -c add-bad-ai-ready-part2
mkdir -p examples/bad_ai_ready_part2
cp -R /path/to/bad_ai_ready_part2/. examples/bad_ai_ready_part2/
git add examples/bad_ai_ready_part2
git commit -m "Add BAD_AI_READY Part 2 demo package"
git push -u origin add-bad-ai-ready-part2
```

その後、GitHub上でPull Requestを作成します。

## Release assetとしてZIPを添付する例

GitHub CLIを使用する場合の例です。

```bash
gh auth login
gh release create bad-ai-ready-part2-v1.0.0 \
  /path/to/bad_ai_ready_part2-v1.0.0.zip \
  --title "BAD_AI_READY Part 2 v1.0.0" \
  --notes-file RELEASE_NOTES.md
```

Web画面では、対象リポジトリのReleasesから新しいReleaseを作成し、ZIPをassetとして添付します。

## 公開前チェック

```bash
python3 tools/validate_package.py
sha256sum -c SHA256SUMS
```

- 実APIキー、トークン、パスワード、Walletを含めない
- `OPENAI_CRED`はcredential名であり、credential値は含めない
- 合成データであることをREADMEに明記する
- `SELECT AI SHOWSQL`を先に実行して生成SQLをレビューする
