# ai-dev-kit — エージェント向けの入口

**このリポジトリは、開発ハーネス（原則・スキル・検査の道具）を複数の AI エージェント面へ配るキット。**

## 導入を頼まれたら

```bash
./install.sh
```

**これ1本でよい。** 面ごとの配布も、届いたかの確認も含まれる。
表示された import 行を `~/.claude/CLAUDE.md` に足すところだけ手で行う。

**自分でパスを組み立てない。** `install.sh` が出した行をそのまま使う。
詳細・自分で用意するもの・入ったかの確かめ方は [README の「導入」](README.md#導入)。

## 入ったかを確かめる

```bash
python3 bin/harness-sync --verify
```

**`tests/` の検査は「書いたか」しか見ない。** 未導入でも全部 PASS する。
配り先のディスクを見るのは `--verify` だけ。

## このリポジトリで作業を頼まれたら

**正本は1箇所に置く。** 面ごとのファイル（この `AGENTS.md`、`CLAUDE.md`）は
参照だけを持ち、本文を複製しない。複製すると、必ず古い方が生き残る。

| 読むもの | 何が書いてあるか |
|---|---|
| [README.md](README.md) | 構成・導入・道具の一覧 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | このリポジトリが満たすもの（公開前提・環境非依存） |
| [docs/harness-layers.md](docs/harness-layers.md) | 3層（原則 / スキル / 道具）の分け方 |
| [docs/measuring-a-harness.md](docs/measuring-a-harness.md) | 「書いた」「届いた」「守られた」の分離 |
| [claude/principles.md](claude/principles.md) | 常時読まれる原則（①層） |

**変更したら検査を流す。** 一覧は [README の「検証」](README.md#検証)。
道具を足したときは、**変異を当てて検査が赤になることまで**確かめる。
