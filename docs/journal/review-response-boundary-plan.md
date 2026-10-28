# `review-response` の GitHub 固有部分を分ける Plan (v1)

> **状態: 完了** — PR [#16](https://github.com/3su3/ai-dev-kit/pull/16) でマージ済み。成果物は `claude/skills/review-response/github.md`。

> この行は実装・撤退のたびに更新する。更新されていない状態行は、書いた時点で凍っているだけで現状を表さない。

関連: [#15](https://github.com/3su3/ai-dev-kit/pull/15)（`review-discipline` で同じことをした）

# 1. 概要

## 背景

`review-discipline` で GitHub 固有部分を `github.md` へ分けた（#15）。
`review-response` にも**同じ問題がある**。3面すべてに配られているのに、
`gh api`、GraphQL の `resolveReviewThread`、`in_reply_to`、`databaseId` が本文に入っている。

## 目的

**指摘への向き合い方**（どこでも通じる）と、**GitHub での返信・resolve の手順**（GitHub 限定）を分ける。

# 3. 現状調査

節ごとに GitHub 固有の語を数えた（`SKILL.md` 107行）。

| 節 | GitHub 依存 | 性格 |
|---|---|---|
| 立場 | 0/5 | **普遍** |
| 裏どりの手順 | 0/5 | **普遍** |
| 3つに振り分ける | 0/11 | **普遍** |
| 同じ指摘が3回続いたら | 0/2 | **普遍** |
| 返信 | 1/8 | ほぼ普遍 |
| resolve | 3/7 | 判断は普遍、操作は GitHub |
| **投稿のしかた** | **10/20** | **GitHub 固有** |
| 依頼者本人からの指摘 | 2/2 | 普遍（「PR」の語だけ） |

**#15 と同じ形。** 判断の節は1語も GitHub に触れておらず、「投稿のしかた」に集中している。

# 4. 実装方針

**Minimal。** #15 と同じ切り方をする。同梱ファイル `github.md` を足し、
「投稿のしかた」を移す。`SKILL.md` には「GitHub なら `github.md` を読む」の1行を残す。

**resolve の判断**（対応したものだけ閉じる、まとめて閉じない、質問中は開けておく）は
**普遍**なので `SKILL.md` に残し、**操作**（GraphQL の mutation、REST との口の違い）だけ移す。

**文面承認の規則は `SKILL.md` に残す。** #15 で、移送中に両方へ残して重複を作った。
今回は先に決めておく。

| 代替案 | 退けた理由 |
|---|---|
| スキルを分ける | 発火条件が同じ |
| そのまま | GitHub 以外で使えない手順を読ませ続ける |

# 5. 修正対象

- `claude/skills/review-response/SKILL.md` — 1節を移し、参照を1行置く
- `claude/skills/review-response/github.md` — 新規

対象外: `review-discipline`、`dev-flow`、`bin/harness-sync`（変更不要）。

# 6. 影響範囲

- 3面の配布物が変わる。`harness-sync` の再実行が要る
- Kiro の steering が縮む。`github.md` は**配られない**（在処を案内するだけ）

# 7. テスト計画

| 検証 | 方法 |
|---|---|
| 普遍の節が残っている | `tests/verify-harness-sync.py` が PASS |
| **重複が無い** | `SKILL.md` と `github.md` で25字超の一致行が0であること（#15 で2件作った） |
| GitHub 固有部分へ辿れる | Kiro で「resolve は取り消せるか」と質問 |
| 判断が残っている | Kiro で「返信していないスレッドを resolve してよいか」と質問 |

3つ目は `github.md` にしか無い内容（`unresolveReviewThread`）、4つ目は `SKILL.md` に残す内容。
**片方が失敗して片方が成功すれば、原因まで切り分かる。**

照合は**そのファイルにしか無い文字列**で行う。話題が合うだけでは到達の証拠にならない。

# 9. レビューで確認してほしいこと

- 「resolve の判断は普遍、操作は GitHub 固有」の切り方が妥当か

# 10. 承認

- [ ] Human の実装承認（この版に対して）

# 11. 完了条件

- `SKILL.md` から GitHub 固有の手順が消え、`github.md` へ移っている
- **重複0**を機械で確認
- `tests/verify-harness-sync.py` が PASS
- 3面へ配り直し、Kiro で2問の切り分けを実測
- 到達しなければ撤退（`SKILL.md` へ戻す）
