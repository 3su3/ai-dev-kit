# ai-dev-kit

Claude Code・Codex・Kiro 向けの開発ハーネス。**公開前提で、リポジトリにとらわれない**
部品（kit）の集まり。必要なものだけ選んで使う。

| 入っているもの | 何をするか |
|---|---|
| **kit** | `dev-flow`（実装の流れ）/ `review-discipline`（レビュー）/ `review-response`（指摘への対応） |
| **原則** | 常時効かせる 5〜10 行（`claude/principles.md`） |
| **配る道具** | 1つの正本を Claude / Codex / Kiro の形へ配る（`bin/harness-sync`） |
| **育てる道具** | 観察を kit へ引き上げる合図を出す（`bin/harness-status` ほか） |

**読むところが2つに分かれる。**

| あなたが | 読むもの |
|---|---|
| **kit を使いたい** | [導入](#導入) → [入っているスキル](#入っているスキル) → [配る道具](#配る道具) |
| **ハーネスを育てたい** | [3層](docs/harness-layers.md) → [育てる道具](#育てる道具) → [測り方](docs/measuring-a-harness.md) |

作った過程の記録は `docs/journal/`。**使うだけなら読まなくてよい。**

## 基本原則

このリポジトリへの貢献には、Private 運用中も公開可能な情報だけを扱う **Public-ready** と、変更理由を後から追えるようにする **Decision Traceability** を適用する。人間・AIに共通の規則は [CONTRIBUTING.md](CONTRIBUTING.md)、情報の判断基準は [Public-ready 原則](docs/principles/public-ready.md) を参照する。実際の Public 化は別途 Human の明示承認が必要。

## 何を入れるか

**他プロジェクト・他の人にも普遍的に使えるものだけを入れる。**

固有のものは gitignore された層へ分ける。そうしないと、使う人が自分の流儀と
食い違う記述を読まされ、どれが普遍でどれが好みか判別できなくなる。

| | 置き場 | 例 |
|---|---|---|
| 普遍 | リポジトリ本体 | 検証の道具、レビューの型、網羅性の主張のしかた |
| 固有（プロジェクト） | `terms/<slug>.txt`（gitignore） | 社内用語・環境名 |
| 固有（個人・チーム） | `local/preferences.md`（gitignore） | コミット規約、PR の出し方、進め方 |

雛形は `terms/example.txt` と `local/example.md`。

### 環境で変わる事実を書かない

**社内用語でも個人の流儀でもないのに普遍でないもの**がある。すり抜けやすい。

| 書いてはいけない | 代わりに書く |
|---|---|
| 使えるモデルの一覧・可用性（契約と時期で変わる） | **確かめ方**（名前を指定して `not available` が返るか） |
| 道具の絶対パス（`~/.local/bin/...`） | PATH を先に見て、無ければ `SKIP` |
| 「この面には◯◯が無い」（版と設定で変わる） | 無い場合にどう読み替えるか |
| 自分のアカウントで観測した件数・比率 | 数え方と、数え直すコマンド |

**判定は「他の人の環境でも同じか」。** 同じでないなら、事実ではなく**確かめ方**を書く。

測った値そのものは [検証の記録](docs/journal/verification-log.md) に置く。
あれは**証拠**であって規約ではないので、環境固有でよい。

## 構成

| パス | symlink 先 | 中身 |
|---|---|---|
| `claude/principles.md` | `~/.claude/CLAUDE.md` から `@` で import | 常時効かせたい原則（①層。**普遍のみ**） |
| `local/preferences.md` | 同上 | 個人・チームの既定。**gitignore 済み** |
| `claude/skills/` | `~/.claude/skills/` | 場面で発火する作業の型（②層） |
| `bin/` | PATH へ通す | 棚卸し・検査の道具（③層） |
| `tests/` | — | 上が効いているかの検査 |
| `docs/` | — | **使う人向け**（3層・測り方・公開前チェック） |
| `docs/journal/` | — | **作った過程の記録**。使うだけなら読まなくてよい |
| `terms/` | — | プロジェクト固有語。**.gitignore 済み** |
| `local/` | — | 個人・チームの既定。**.gitignore 済み** |

レビューの指摘が正しく分類されるかを測る fixture は `tests/fixtures/review_target.py`。**仕込んだ内容はファイルに書かない**（書くとレビュアーが仕様と解釈して飛ばす）。答えと測り方は [検証の記録](docs/journal/verification-log.md) にある。

3層の考え方は [3層](docs/harness-layers.md)、**効いているかの測り方**は
[測り方](docs/measuring-a-harness.md)、測った値そのものは [検証の記録](docs/journal/verification-log.md)。

**「書いた」と「届いた」と「守られた」は別物。** 分けて測らないと、どこが壊れているか分からない。
配布物の検査（書いたか）だけでは何も示せない。

## 導入

**この1本道だけでよい。** 面ごとの配布も、届いたかの確認もここに含まれる。

```bash
./install.sh
```

やること:

1. `~/.claude/skills` を張る（既にあるものは退避する）
2. `~/.claude/CLAUDE.md` に足す import 行を**表示する**（下記）
3. 他の面（Codex / Kiro）へ配る — **受け口が無い面は飛ばす**
4. 届いたかを見る（`harness-sync --verify`）

### `~/.claude/CLAUDE.md` への1行

**`install.sh` が表示した行をそのまま使う。** 自分でパスを組み立てない。

```
@<このリポジトリ>/claude/principles.md
```

- **ファイルが無ければ作ってよい。** あるなら**実体のまま1行足す**
- **symlink にしない。** 同じファイルが他の相対 import（`@xxx.md`）を持っている場合、
  解決先がリンク先基準になり得る
- 既に生成・追記する仕組み（プラグイン等）を使っているなら、**上書きするか追記するか**を
  先に確かめる。追記しかしないなら共存できる

> **`git rev-parse --show-toplevel` でパスを作らない。** tarball 等で展開した
> 非 git のコピーでは空文字になり、`@/claude/principles.md` という
> **もっともらしい行を終了コード 0 で出す**（2026-10-28 に実測）。
> 取得失敗と正常が同じ顔になる。

### 入れていないツールの面

**受け口のディレクトリは作らない。** 使っていないツールの設定を生やさないため。
後からそのツールを入れたら、`harness-sync` を流し直せば配られる。

同じ面に入ったものと入らなかったものが混じると**警告が出る**。
`~/.kiro` だけあって `steering/` が無いと、原則もレビュー規約も届かないのに
実装スキルだけが入るため。

### 自分で用意するもの

**導入しただけでは入らない。** どれも無くても動くが、無いなりの動きになる。

| | 何を | 無いとどうなるか |
|---|---|---|
| `local/preferences.md` | 個人の流儀。雛形は [local/example.md](local/example.md) | 流儀が反映されない |
| `local/<スキル名>.md` | スキルごとの個人の既定（クロスの相手など） | そのスキルは kit の既定で動く |
| `terms/<slug>.txt` | プロジェクト固有語 | 固有語の判定をせず、その旨を出す |
| PATH への `bin/` | `install.sh` が警告する | `harness-*` コマンドが引けない |

**`bin/harness-status` と `bin/claude-memory-stocktake` は、Claude Code の
auto-memory が溜まっていないと動かない。** 新規環境では必ず落ちる（候補を列挙して落ちる）。
これは「育てる道具」で、kit を使うだけなら要らない。

### 入ったかを確かめる

```bash
python3 bin/harness-sync --verify
```

**`tests/` の検査は「書いたか」しか見ない。** まっさらな HOME・未導入でも全部 PASS する
（2026-10-28 に実測）。`--verify` は配り先のディスクを見る。

## 入っているスキル

場面で自動的に発火する。本文は `claude/skills/<name>/SKILL.md`。

| スキル | いつ発火するか | 同梱 |
|---|---|---|
| `dev-flow` | 実装・修正・リファクタの依頼（「実装して」「直して」「進めて」） | `risk-policy.md`（軽微/通常/高リスクの分類）、`plan-review.md`、`leader.md`、`implementer.md`、`plan-template.md`、`compare-template.md`、`strategies.md`、`workflow.md` |
| `review-discipline` | レビューの依頼（「レビューして」「指摘して」） | `checklist.md`（観点）、`github.md`（GitHub への出し方） |
| `review-response` | 自分の PR への指摘対応（「指摘対応して」「レビュー返して」） | `github.md`（返信と resolve の操作） |

**判断は `SKILL.md`、GitHub 固有の操作は `github.md`。** GitHub を使わないリポジトリでは
`github.md` を読む必要がない。

同梱ファイルは配布されず、**在処だけが案内される**。必要になったときに読む。
到達することは確認済みだが、**一般知識で答えられる問いでは読まれない**
（[検証の記録](docs/journal/verification-log.md)）。

## 測る道具

**過去の時点を数え直すときに使う。** kit を使う人にも、育てる人にも効く。

### `bin/at-rev`

過去の時点のコードに、今日の道具を持ち込んで走らせる。

`git show <rev>:<path>` で中身だけ引くと、対象ファイルの一覧が今日の作業ツリーで解決されるため、
**その時点に存在したが今は無いファイルが 0 として数えられる**。at-rev は `<rev>` の木を実体化し、
そこへ道具を複製してその中で実行する。走らせる前に今日の木との存在差を出す。

```bash
at-rev <rev> --scope 'src/**' --dry-run        # 存在差だけ見る
at-rev <rev> --bring bin -- ./bin/survey --json
```


## 育てる道具

**kit を使うだけなら要らない。** ハーネス自体を育てるときに使う。

`auto-memory`（まだ型になっていない観察のバッファ）を棚卸しし、
**②型 / ③装置へ引き上げる合図**を出す。考え方は [3層](docs/harness-layers.md)。
**週次で走らせる運用を想定している**（合図が出たときだけ中身を見る）。

### `bin/claude-memory-stocktake`

Claude Code の auto-memory を機械で棚卸しし、①原則 / ②型 / ③装置 のどこへ振るかの材料を出す。
**ファイルから数えられる事実だけ**を列にする。

```bash
claude-memory-stocktake --sort recur --md     # 再発の多い順
claude-memory-stocktake --sort inlinks --md   # 参照の多い順
claude-memory-stocktake --why <name>          # 1件の全列の根拠
```

memory ディレクトリは cwd（または git のトップ階層）から自動で引く。
見つからないときは**黙って別物を選ばず**、候補を並べて落ちる。

### `bin/harness-status`

いま何が引き上げ待ちかを出す。答える問いはこれ1つ。

memory は「**まだ型になっていない観察のバッファ**」で、放っておくと溜まる一方になる。
前回見た時点との差分で、**再発回数が上がったもの**（＝③装置にすべき合図）を出す。

```bash
harness-status          # 前回からの差分
harness-status --all    # 現状の全件
harness-status --mark   # いまの時点を「見た」として記録する
```

基準は `local/snapshot.json`（gitignore 済み）。記録が無い初回は差分ではなく現状を出す。

## 配る道具

**kit を使うならこれ。** 1つの正本を、各エージェントが読む形へ配る。

### `bin/review-outcomes`

**自分のレビュー指摘が、直ったか流れたかを数える。**

```bash
bin/review-outcomes <owner/repo> <レビュアーの login>
```

接頭辞ごとに「直った率」を出す。**対応されない指摘は、相手の注意を取るだけになる。**
どの接頭辞が実際に効いているかを、出した側が測る。

**「直った」はコミット参照の有無だけで数える。** SHA を書かずに直した分は見えない。
未マージの PR は除く（まだ返していないだけのため）。

### `bin/plan-vs-diff`

**計画の「修正対象」と実際の差分を集合で比べる。**

```bash
bin/plan-vs-diff <計画のパス> --base origin/main
```

実装の報告で「計画との差: なし」と書く前に回す。**記憶から書かせないための道具。**
実装したエージェントは計画の方を覚えているので、ずれたときほど
「計画どおりにやったつもり」で書く。未コミットの変更があれば警告する。

### `bin/harness-sync`

**1つの正本を、各エージェントが読む形へ配る。**

| 面 | 受け口 | 方法 |
|---|---|---|
| Claude Code | `~/.claude/skills/` と `~/.claude/CLAUDE.md` の `@` import | symlink（`install.sh`） |
| Codex | `~/.codex/AGENTS.md` | **生成**（原則を本文へ、スキルは一覧で案内） |
| Kiro | `~/.kiro/steering/*.md` + `~/.kiro/harness-parts/` + `~/.kiro/agents/` | **生成**（frontmatter を剥がし、常時と随時に分ける） |

```bash
harness-sync --dry-run    # 何を書くか
harness-sync              # 配る
harness-sync --only codex
```

面ごとに**読み方が違う**ので symlink 1本では済まない。とくに Kiro は
frontmatter（`inclusion:` 等）を付けると規約が届かなくなることが別プロジェクトで
実測されているため、**剥がして渡す**。発火条件は本文の見出しとして残す。

#### Kiro は「常時」と「頼んだときだけ」を分ける

**`~/.kiro/steering/` に置いたものは、どのエージェントでも無条件に全部載る。**
Claude の「description 一致で発火」に当たる仕組みが無い。常時読みを増やすと
**無関係な指示まで守られなくなる**ことを実測した（実装の方針宣言が 6/6 → 2/6。
詳細は `docs/journal/verification-log.md`）。

そこで置き場所を分ける。**既定は「随時」**で、常時にしたいものだけ
`harness-sync` の `KIRO_ALWAYS` に挙げる。

| 置き場所 | 何が入るか | いつ載るか |
|---|---|---|
| `~/.kiro/steering/` | 原則と、**`KIRO_ALWAYS` に挙げたスキル** | **常時** |
| `~/.kiro/harness-parts/` | **それ以外のスキル（既定）** | agent を選んだときだけ |
| `~/.kiro/agents/harness-*.json` | 上を指す `resources` | — |

**スキルを足しても、常時読みは増えない。** 既定で `harness-parts` へ行き、
自分の agent を持つ。使わない kit を入れておいても、Kiro の文脈を食わない。
常時にしたいなら `KIRO_ALWAYS` に挙げる（**枠は有限。上限は検査が見ている**）。

```bash
kiro-cli chat --agent harness-impl      # dev-flow を足す（実装するとき）
kiro-cli chat --agent harness-response  # review-response を足す（指摘に対応するとき）
kiro-cli chat                           # 原則 + review-discipline だけ
```

**代償: 自動で切り替わらない。** 指定を忘れると、その回はスキルが載らない。
とくに **Orca の `--agent` は TUI の種類（claude / kiro / codex）** であって
Kiro の agent 定義名ではないため、**Orca 経由では harness-parts を載せられない**（下記）。

常時読みの量は `tests/verify-harness-sync.py` が見ている。上限は測った崖ではなく
**増やさないための歯止め**で、スキルを1本足すと落ちる。上げるときは何を落としたかを書く。

**現行構成の Orca → Kiro では、実装を開始しない。** この経路では `dev-flow` が載らない。
Orca → Claude など、別の経路にはこの停止条件を適用しない。Kiro で実装する場合は、
worktree の別端末で `kiro-cli chat --agent harness-impl` を直接起動する。

KiroCrew を使う場合は、既存の `~/.kiro/agents/kirocrew.json` を退避し、
現在の `resources` を保持したまま `file://~/.kiro/harness-parts/dev-flow.md` だけを追加する。
新しいセッションで **本文への到達**（description にない `risk-policy.md` の「軽微」など）と
**実装時の遵守**（リスク分類・方針宣言・必要な TDD など）を別々に確認する。
「Minimal」と答えただけでは本文到達の証拠にならない。再起動・更新後の設定保持と
実作業全般での遵守は未検証。実測の範囲は [Issue #25](https://github.com/3su3/ai-dev-kit/issues/25) と
[検証の記録](docs/journal/verification-log.md) を参照する。

受け口のディレクトリが無い面は `[skip]` と出して飛ばす（その面は未導入）。
`harness-parts` と `agents` は自前の置き場なので、`~/.kiro` があれば作る。
**配り先を変えたときは、自動生成の印があり対象から外れたファイルを消す**
（残ると、外したはずのものが載り続ける）。手書きのファイルには触らない。
生成したファイルは `harness-sync:begin/end` で囲まれる。`AGENTS.md` は
そのブロックだけを差し替えるので、手書き部分は残る。

### プロジェクト固有語（`terms/`）

memory が「普遍的な手法」か「そのプロジェクトの運用知識」かを切り分けるための語彙。
`terms/<slug>.txt` に置く（slug = プロジェクトの絶対パスの英数字以外を `-` に置換したもの）。

```
/Users/me/work/myapp  →  terms/-Users-me-work-myapp.txt
```

**`terms/` は .gitignore 済み。** 業務の用語を公開リポジトリへ出さないため。雛形は `terms/example.txt`。
語彙ファイルが無いときは固有語の判定を行わず、その旨を出す（全件 0 を「固有語なし」と誤読させない）。

## 検証

**すべて Python。** 拡張子が無いものもあるので `bash` では流せない。

```bash
python3 tests/verify-portable.py           # 普遍の層が他の環境でも成立するか
python3 tests/verify-confidential.py  # 公開してはいけない語が混ざっていないか
python3 tests/verify-at-rev                # at-rev の3経路比較
python3 tests/verify-harness-status        # harness-status が合図を取りこぼさないか
python3 tests/verify-harness-sync.py       # 配る内容（埋め込み・原則・frontmatter・上限）
python3 tests/verify-harness-cleanup.py    # 配り先を変えたとき古い配布物が消えるか
python3 tests/verify-install.py            # **使い捨ての HOME へ実際に入れて**確かめる
python3 tests/verify-review-discipline.py  # 接頭辞の綴りと、取り違えやすい記述
python3 tests/verify-dev-flow-risk.py      # dev-flow の静的整合性と負例
python3 tests/verify-stage-reports.py  # 各段の報告が成果物から作られる形か
python3 tests/verify-kiro-reach.py --run   # 合言葉で到達を測る（LLM を2回呼ぶ）
python3 tests/verify-plan-status.py        # docs/*plan*.md に状態行があるか
python3 tests/probe-skill-firing.py "レビューして"   # スキルが発火するかの実測（探針）
```

**`verify-portable.py` は入口の検査。** ここが赤なら、他の人の環境では成立しない。
判断の基準は [CONTRIBUTING](CONTRIBUTING.md#このリポジトリが満たすもの)。

`tests/fixtures/review_target.py` はレビューの分類を測る対象。答えと測り方は
[検証の記録](docs/journal/verification-log.md)にある（**ファイル自体には書かない**。
書くとレビュアーが仕様と解釈して飛ばす）。

道具を足したら、**変異を当てて検証が赤になることまで**確かめる。
通ることだけを見ても、その検証が何かを守っている証拠にはならない。
