# 公開前チェックリスト

公開の時期は決めていない。**公開する価値が出てきたと感じた時点**で、ここを上から順に確認する。

このリストは「公開してよいか」を機械的に判定するものではない。**判断を忘れないための入口**。
各項目には、確認に使えるコマンドを添えてある。手で目視する項目はそう書いてある。

関連: [Public-ready 原則](principles/public-ready.md) / [CONTRIBUTING](../CONTRIBUTING.md)

---

## 1. 秘密情報（**ブロッカー**）

### 1-1. `refs/pull/*` に残る秘密の除去を GitHub へ依頼する

**2026-10-19 時点で未了。公開する前に必ず実施する。**

`.serena/serena_config.yml` の `auth_secret` を 1 コミットで混入させ、push した
（`d7e6ed7`、混入後 46 コミットが継承）。履歴の書き換えは完了しており、
**ブランチからは除去済み**。通常の `git clone` では到達しない。

残っているのは GitHub が保持する PR の ref（`refs/pull/N/head`）で、**こちらからは消せない**。
GitHub Support に GC を依頼する必要がある。

| 経路 | 到達 |
|---|---|
| `refs/heads/*`、通常の `git clone` | **しない**（除去済み） |
| `refs/pull/*`（アクセス権のある人が明示的に fetch） | **する** |

値はローテーション済みで、元々 `127.0.0.1` 待受のダッシュボード認証用。
**private である間は実害がほぼ無いため延期している。公開するとこの前提が消える。**

確認:

```bash
# ブランチ側がクリーンであること（0 件であるべき）
git clone --quiet <repo> /tmp/pubcheck && cd /tmp/pubcheck
git rev-list --all | while read c; do git ls-tree -r --name-only $c | grep -q "^\.serena" && echo $c; done | wc -l

# PR ref 側（GC 依頼が済むまでは 0 にならない）
git clone --quiet --mirror <repo> /tmp/pubcheck-mirror && cd /tmp/pubcheck-mirror
git for-each-ref --format='%(refname)' refs/pull/ | while read r; do
  git rev-list "$r" | while read c; do git ls-tree -r --name-only $c | grep -q "^\.serena" && echo x; done
done | wc -l
```

### 1-2. 全履歴を秘密情報で走査し直す

混入は1件とは限らない。**公開の直前にもう一度走らせる**（それまでにコミットが増えるため）。

```bash
git log --all -p --diff-filter=AM | grep -nE "auth_secret:|api[_-]?key|password|BEGIN .*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_|github_pat_|sk-[A-Za-z0-9]{20,}|xox[baprs]-"
```

**検出ゼロを無条件に信じない。** 検査が壊れていないことを、既知の値で陽性になるか確かめてから使う。

---

## 2. Public-ready（**ブロッカー**）

### 2-1. 内部を示す語の除去

**語の一覧の正本は `tests/verify-confidential.py`。** ここには書かない
（2箇所に持つと、必ず片方が古くなる。実際にこの節は、既に直った2ファイルを
「残存」と言い続けていた）。

```bash
python3 tests/verify-confidential.py
```

**書いてあるだけの検査は、無いのと同じ。** 以前はここに `git grep` のコマンドが
あっただけで、誰も走らせていなかった（2026-10-28 に装置化）。

**機械的な置換で済ませない。** 名前を伏せても、構成の記述から特定できることがある。
判断がつかなければ止めて確認する（Public-ready 原則「判断できない場合」）。

### 2-2. Issue と PR の本文

本文は**リポジトリのファイルとは別に**公開される。同じ基準で確認する。
ローカルパス、内部の固有名、業務の文脈が入っていないか。

**過去の記録は書き換えない**のが原則だが、公開は別の判断。
消すか、伏せるか、公開しないかを項目ごとに決める。

### 2-3. 著者のメールアドレス

**2026-10-19 時点で 4 種類が履歴に入っている**（会社のアドレスを含む）。

```bash
git log --format='%ae' | sort -u
```

公開するかどうかを決める。変えるなら履歴の書き換えが要るので、**1-1 の GC 依頼と同じ回にまとめる**。

---

## 3. 公開物として成立しているか

### 3-1. LICENSE

**無い。** 公開には要る。ライセンスの無いリポジトリは利用条件が不明で、読む人が使えない。

### 3-2. 導入手順が、このリポジトリを知らない人に通じるか

`README.md` の導入手順を、**何も知らない状態で**たどれるか確認する。目視。
`~/work/dotfiles` のような、作成者の環境に依存した記述が残っていないか。

```bash
git grep -nE "/Users/|~/work/" -- $(git ls-files)
```

### 3-3. `terms/` と `local/` が gitignore されているか

固有の情報を分ける仕組みが効いているか。

```bash
git ls-files terms/ local/     # example 以外が出たら NG
```

---

## 4. 公開した後に効くこと

- **公開後は履歴を消せない。** 1 と 2 は公開前にしか実施できない
- Issue と PR も公開される。以後に書くものは公開前提になる
- fork されると、こちらの削除は相手に及ばない

**判断に迷ったら公開しない。** 公開は後からでもできるが、取り消しはできない。
