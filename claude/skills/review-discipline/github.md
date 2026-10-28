# GitHub への出し方

`review-discipline` の指摘を GitHub のレビューとして出すときの手順。
**GitHub を使わないリポジトリでは読まなくてよい。** 判断の原則は `SKILL.md` にある。

## 判定を `event` へ対応づける

| 判定（`SKILL.md` で決めたもの） | `event` |
|---|---|
| Request changes | `REQUEST_CHANGES` |
| Comment | `COMMENT` |
| Approve | `APPROVE` |

本文に「判定」節を作らない。`event` が判定を表す。

**自分が作成した PR には `APPROVE` も `REQUEST_CHANGES` も出せない。** どちらも 422 で落ちる
（`Can not approve your own pull request` / `Can not request changes on your own pull request`）。
自分の PR をレビューするときは `COMMENT` を使い、**本来の判定を本文の冒頭に書く**。

> 本来の判定: Request changes（`[issue]` 2件）。自分の PR のため `COMMENT` で出している。

## 投稿のしかた

文面の承認を得たら（`SKILL.md` の「出し方」）、1回の API 呼び出しで本文とインラインを
同時に出す。

```bash
cat > /tmp/review.json <<'JSON'
{
  "event": "COMMENT",
  "body": "（総評）",
  "comments": [
    {"path": "app/Services/Foo.php", "line": 42, "side": "RIGHT",
     "body": "[issue] $estimate が null のとき後続が落ちる。..."},
    {"path": "app/Services/Foo.php", "start_line": 60, "line": 64, "side": "RIGHT",
     "body": "[nit] この4行はヘルパーに寄せられる。"}
  ]
}
JSON
gh api repos/{owner}/{repo}/pulls/{number}/reviews --input /tmp/review.json
```

- `line` は**差分の行番号ではなくファイルの行番号**。`side` は追加行なら `RIGHT`、削除行なら `LEFT`
- 複数行にまたがる指摘は `start_line`（始まり）と `line`（終わり）を両方指定する
- **差分に無い行を1つでも混ぜると、レビュー全体が投稿されない。** `422 Line could not be resolved`
  が返り、同じ呼び出しに入れた**妥当な指摘も1件も残らない**（実測済み）。
  行番号に自信が無い指摘は、インラインに入れず本文へ回す
