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

## 口が2つに分かれている

**返信は REST、resolve は GraphQL。** `resolve` に REST の口は無い。

## 取り消せるもの・取り消せないもの

| 操作 | 取り消し |
|---|---|
| `resolve` | **できる**（`unresolveReviewThread`） |
| 返信 | **できない。** API で削除はできるが、相手には既に通知が届いている |

文面の承認が要るのは返信のほう。`resolve` は後から戻せる。
