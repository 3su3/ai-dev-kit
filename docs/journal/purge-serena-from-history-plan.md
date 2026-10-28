# `.serena/` を履歴から除去する Plan (v1)

> **状態: 実施済み（残件あり）** — PR [#13](https://github.com/3su3/ai-dev-kit/pull/13) で履歴から除去した。ブランチと通常の `git clone` からは到達しない。**GitHub が保持する `refs/pull/*` には残っている**（こちらからは消せない）。GC 依頼は [公開前チェックリスト](publication-checklist.md) のブロッカー。

> この行は実装・撤退のたびに更新する。更新されていない状態行は、書いた時点で凍っているだけで現状を表さない。

関連: 止血コミット `7ebf0c5`（追跡解除・ローテーション済み）

# 1. 概要

## 背景

`d7e6ed7` で `git add -A` により `.serena/` を巻き込み、`serena_config.yml` の
`auth_secret`（ファイル自身が `Keep this value private` と記す値）を `origin/main` へ
push した。[Public-ready 原則](principles/public-ready.md) の「パスワード、トークン、
秘密鍵などの秘密情報」に該当する。

止血は済んでいる（`.gitignore` 追加・追跡解除・ローカル設定削除によるローテーション）。
**履歴には残っている。**

## 目的

公開に向けて、秘密情報を履歴から除去する。

# 3. 現状調査

| 観測 | 結果 |
|---|---|
| 混入したコミット | **`d7e6ed7` の1つだけ** |
| `.serena` を含むコミット数 | 1 |
| 他の秘密情報（全履歴走査） | **検出なし** |
| 到達範囲 | `origin/main` に push 済み。private リポジトリ |
| クローンしている人 | **作成者のみ**（複数人運用の前）|
| 実害 | 低い。ダッシュボード認証用で `listen_address` / `trusted_hosts` ともに localhost のみ。ローテーション済み |

**いまが最も安い。** 複数人が入ってから、あるいは公開直前にやると、全員の再クローンが要る。

# 4. 実装方針

**Minimal。** `git filter-repo --path .serena --invert-paths` で `.serena/` を全履歴から
除去し、force push する。履歴の書き換えは1ファイルのパス指定のみで、他の内容には触れない。

| 代替案 | 退けた理由 |
|---|---|
| 公開時に履歴を捨てて新リポジトリへ | Decision Traceability と衝突。今日までの判断の経緯が失われる |
| 残す（ローテーション済みなので実害なしとする） | 原則が「履歴も対象」と明記しており、公開時に説明が要る |
| `BFG` を使う | `filter-repo` で足りる。道具を増やさない |

# 5. 修正対象

- Git 履歴から `.serena/` のパスを除去（全コミット）
- `origin/main` へ force push

対象外: ファイルの内容変更、他のパス、タグ（無し）、他リポジトリ。

# 6. 影響範囲

- **全コミットの SHA が変わる。** `d7e6ed7` 以降だけでなく、`filter-repo` の仕様により
  全履歴が書き換わる
- Issue・PR 本文に書いた SHA（`30451f3`、`0a20d1d`、`d7e6ed7` 等）が**到達不能になる**
- マージ済み PR の差分表示が壊れる可能性がある
- `origin/main` への force push が要る

### SHA 参照の扱い

Issue #2、#10、PR #1、#9、#12 の本文に SHA が書かれている。**書き換えない**
（当時の記録であり、過去の記録を現在の状態に合わせて改変しない）。
代わりに、本 Plan が「この時点で履歴を書き換えたため、それ以前の SHA は到達しない」
ことの参照先になる。

# 7. テスト計画

| 検証 | 方法 |
|---|---|
| 秘密が履歴から消えた | `git log --all -S "auth_secret"` が空 |
| `.serena` が履歴から消えた | `git log --all -- .serena` が空 |
| **内容が変わっていない** | 書き換え前後で `git cat-file -p HEAD^{tree}` を比較 |
| テストが通る | `verify-harness-sync` / `verify-dev-flow-risk` / `verify-harness-status` |
| コミット数が一致 | 書き換え前後で `git rev-list --count --all` を比較 |

# 8. 失敗時の停止条件と復旧

- **作業前に `git clone --mirror` でバックアップを取る。** 取れなければ中止
- 書き換え後の検証で**ツリーの内容に差分が出たら force push しない**
- force push が拒否された場合、強制解除せず報告する
- 復旧: バックアップから `git push --mirror` で戻す

# 10. 承認

- [ ] **Human の実装承認。** 高リスク（秘密情報・履歴の書き換え・force push）

# 11. 完了条件

- `auth_secret` が全履歴から消えている（実測）
- 最新ツリーの内容が書き換え前と**完全一致**
- テスト3種が PASS
- 結果と、SHA が到達不能になった旨を Issue #2 へ記録
