# セキュリティ

## 報告のしかた

**公開の Issue に書かないでください。**

GitHub の **Security → Report a vulnerability**（非公開の脆弱性報告）から連絡してください。
受け取ったら、まず再現できるかを確認して返事します。

## このリポジトリの性質

**ここにあるのは、AI エージェントへ渡す規約と、その検査の道具です。**
利用者の環境で動くのは次の2つだけです。

- `install.sh` — `~/.claude/skills` への symlink を張り、`bin/harness-sync` を呼ぶ
- `bin/*` — 配布と確認のコマンド。**書き込み先は `~/.claude` `~/.codex` `~/.kiro` の配下**

**資格情報は扱いません。** 外部サービスへの通信もしません
（例外は `tests/verify-kiro-reach.py --run` と `tests/probe-skill-firing.py` で、
これらは手元の CLI を呼びます。既定では走りません）。

## 気をつけていること

- **職場・取引先に紐づく語が混ざっていないか** — `tests/verify-confidential.py`
- **この環境にしか無いパスやモデル名が混ざっていないか** — `tests/verify-portable.py`

どちらも**語の一覧に載っているものしか見つけられません。** 載せていない固有名は漏れます。
見つけたら報告してください。
