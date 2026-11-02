# GitHub での返信と resolve

`review-response` の判断を GitHub のレビューコメントへ反映するときの操作。
**GitHub を使わないリポジトリでは読まなくてよい。** 何を返すか・いつ閉じるかは `SKILL.md` にある。

文面の承認を得たら（`SKILL.md` の「返信」）、次の3つで出す。**いずれも実測済み。**

```bash
# スレッド一覧（threadId と、返信先になるコメントの databaseId を引く）
gh api graphql -f query='
query($owner:String!,$repo:String!,$num:Int!){
  repository(owner:$owner,name:$repo){ pullRequest(number:$num){
    reviewThreads(first:50){ nodes{ id isResolved
      comments(first:5){ nodes{ databaseId path line body } } } } } }
}' -F owner=OWNER -F repo=REPO -F num=N \
  --jq '.data.repository.pullRequest.reviewThreads.nodes[]
        | {threadId:.id, resolved:.isResolved, c:(.comments.nodes[0]|{databaseId,path,line})}'

# 返信（REST。in_reply_to はスレッド先頭コメントの databaseId）
gh api repos/OWNER/REPO/pulls/N/comments -f body='（返信）' -F in_reply_to=DATABASE_ID

# resolve（GraphQL。threadId は上で引いたもの）
gh api graphql -f query='mutation($id:ID!){ resolveReviewThread(input:{threadId:$id}){ thread{ isResolved } } }' -F id=THREAD_ID
```

## 返信・resolve 後の確認

> **この手順が効くのは Claude と Codex。** Kiro には同梱ファイルが届かない
> （`bin/harness-reach` で確認できる）。Kiro で投稿する経路があるなら、そこでは効かない。

後続の判断が返信内容やスレッド状態に依存する場合は、書き込み応答の ID を使って
保存後の状態を再取得する。返信は `body` と `in_reply_to_id` を承認済みの文面・返信先と
照合する。resolve は対象 `threadId` の `isResolved` を確認する。

```bash
gh api repos/OWNER/REPO/pulls/comments/COMMENT_ID \
  --jq '{body,in_reply_to_id,pull_request_url}'
gh api graphql -f query='
query($id:ID!){ node(id:$id){ ... on PullRequestReviewThread{ id isResolved } } }
' -F id=THREAD_ID --jq '.data.node | {id,isResolved}'
```

取得不能、空・欠落・`null`、不一致を成功と扱わず、確認できた範囲を報告して
依存する後続処理を止める。
返信・resolve を状態不明のまま繰り返さない。返信と resolve の間で返信の確認が
必要なら、確認を済ませてから resolve へ進む。

## 読み戻す口（書き込みの口とは別）

**書き込みの種類ごとに、読み戻す口が違う。** PR への総評コメントだけ `issues/` 側にある。
書き込み側の口の分かれ方は、下の「口が2つに分かれている」。

| 書き込み | 読み戻す口 |
|---|---|
| レビュー投稿 | `repos/O/R/pulls/N/reviews/REVIEW_ID` |
| インライン・返信 | `repos/O/R/pulls/comments/COMMENT_ID` |
| resolve | GraphQL `node(id: THREAD_ID)` |
| PR への総評コメント | `repos/O/R/issues/comments/COMMENT_ID` |

**`gh` は ID をそのまま返さない。** `gh pr comment` の応答は URL なので、末尾から切り出す。

```bash
url=$(gh pr comment N --body-file /tmp/body.md)
id=${url##*-}
gh api repos/O/R/issues/comments/"$id" --jq '.body' > /tmp/readback.md
```

## 口が2つに分かれている

**返信は REST、resolve は GraphQL。** `resolve` に REST の口は無い。

## 取り消せるもの・取り消せないもの

| 操作 | 取り消し |
|---|---|
| `resolve` | **できる**（`unresolveReviewThread`） |
| 返信 | **できない。** API で削除はできるが、相手には既に通知が届いている |

文面の承認が要るのは返信のほう。`resolve` は後から戻せる。
