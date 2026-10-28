# `review-discipline` の GitHub 固有部分を分ける Plan (v1)

> **状態: 完了** — PR [#15](https://github.com/3su3/ai-dev-kit/pull/15) でマージ済み。成果物は `claude/skills/review-discipline/github.md`。

> この行は実装・撤退のたびに更新する。更新されていない状態行は、書いた時点で凍っているだけで現状を表さない。

関連 Issue: [#2](https://github.com/3su3/ai-dev-kit/issues/2)（残件の1つ）

# 1. 概要

## 背景

`review-discipline` は3面（Claude Code / Codex / Kiro）すべてに配られている。しかし本文には
**GitHub でしか成立しない手順**が混ざっている。`gh api` のコマンド、`start_line` / `side`、
差分外での `422`、`REQUEST_CHANGES` / `APPROVE` の `event`。

GitHub を使わないプロジェクトへ導入すると、**使えない手順を毎回読まされる**。
②層でも「読まれる量を小さく保つ」が効く。

## 目的

**レビューの原則**（どこでも通じる）と、**GitHub への出し方**（GitHub 限定）を分ける。

# 3. 現状調査

節ごとに GitHub 固有の語を数えた（`SKILL.md` 131行）。

| 節 | GitHub 依存 | 性格 |
|---|---|---|
| 立場 | 0/5 | **普遍** |
| 観点 | 0/8 | **普遍** |
| 接頭辞 | 0/9 | **普遍** |
| 同じ指摘が3回続いたら | 0/2 | **普遍** |
| テスト | 2/9 | ほぼ普遍 |
| 本文（総評）の形 | 2/9 | ほぼ普遍 |
| **判定** | **9/16** | **GitHub 固有**（`event` 名、自分の PR での 422） |
| **投稿のしかた** | **9/23** | **GitHub 固有**（`gh api`、`start_line`、422） |

**境界は明確。** 上4節は1語も GitHub に触れていない。下2節が集中している。

`checklist.md`（137行）は 2/137 でほぼ普遍。触らない。

# 4. 実装方針

**Minimal。** `SKILL.md` に同梱ファイル `github.md` を足し、「判定」「投稿のしかた」を移す。
`SKILL.md` 側には「GitHub なら `github.md` を読む」の1行を残す。

| 代替案 | 退けた理由 |
|---|---|
| スキルを2つに分ける | 発火条件が同じ（「レビューして」）。2つ出て取り違えの元 |
| GitHub 固有部分を消す | いま使っているのは GitHub。消すと実用性が落ちる |
| そのまま | GitHub 以外の導入先で、使えない手順を読ませ続ける |

**判定の考え方（ブロッカーの有無で決める）は普遍**なので `SKILL.md` に残し、
**`event` 名への対応づけ**だけを `github.md` へ移す。

# 5. 修正対象

- `claude/skills/review-discipline/SKILL.md` — 2節を移し、参照を1行置く
- `claude/skills/review-discipline/github.md` — 新規
- `bin/harness-sync` — **変更しない**（同梱ファイルは Kiro へ在処を案内済み、Codex は絶対パス）

対象外: `checklist.md`、`review-response`（後述）、`dev-flow`。

## `review-response` について

同じ問題がある（107行中12行が GitHub 固有。`gh api`、GraphQL の `resolveReviewThread`、
`in_reply_to`）。ただし **Issue #2 が挙げているのは `review-discipline`** であり、
本 Plan のスコープ外とする。やるなら別 PR。

# 6. 影響範囲

- 3面の配布物が変わる。`harness-sync` の再実行が要る
- **Kiro は本文を埋め込む方式**なので、`SKILL.md` が短くなった分 steering も縮む。
  移した `github.md` は**配られない**（同梱ファイルは在処を案内するだけ）
- **これは意図した結果。** GitHub を使うときだけ読めばよい

# 7. テスト計画

| 検証 | 方法 | 示すこと |
|---|---|---|
| 普遍の節が残っている | `tests/verify-harness-sync.py` が引き続き PASS | 本文の配布が壊れていない |
| GitHub 固有部分へ辿れる | **Kiro で「自分の PR に APPROVE を出せるか」と質問** | 同梱ファイルへの到達 |
| 判定の考え方が残っている | 「issue が0件で suggestion だけのとき、承認するか」と質問 | 普遍部分が `SKILL.md` に残っている |

2つ目は `github.md` にしか無い内容。**話題が合うだけでは到達の証拠にならない**ので、
`Can not approve your own pull request` という**そのファイルにしか無い文字列**で照合する。

# 9. レビューで確認してほしいこと

- 「判定の考え方は普遍、`event` 名は GitHub 固有」の切り方が妥当か
- `github.md` が Kiro へ配られないことを許容してよいか（GitHub を使うときだけ読む前提）

# 10. 承認

- [ ] Human の実装承認（この版に対して）

# 11. 完了条件

- `SKILL.md` から GitHub 固有の手順が消え、`github.md` へ移っている
- `tests/verify-harness-sync.py` が PASS
- 3面へ配り直し、**Kiro で到達を実測**（そのファイルにしか無い文字列で照合）
- 到達しなければ撤退（`SKILL.md` へ戻す）
