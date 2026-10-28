#!/usr/bin/env python3
"""普遍の層が、他の環境でもそのまま成立するかを見る。

ai-dev-kit は **公開前提**で、**リポジトリを跨いで使える**ことが前提。
`docs/principles/public-ready.md` は**機密性**（公開してよい情報か）を扱うが、
**可搬性**（他の人の環境で成立するか）は誰も見ていなかった。

2026-10-26 までに4回すり抜けた。どれも社内用語でも秘密でもなく、
**その環境でしか成り立たない事実**だった。

  1. 使えるモデルの一覧と可用性（契約と時期で変わる）
  2. 道具の絶対パス（`~/.local/bin/...` を決め打ち）
  3. 別リポジトリの道具と履歴への依存（テストが FileNotFoundError で落ちていた）
  4. ひとつのチームの作業順序を普遍として記述

ここで見るのは機械で判定できる 1〜3。4 は `verify-dev-flow-risk.py` が見ている。

**`docs/journal/verification-log.md` は対象外。** あれは測定の**証拠**であって規約ではないので、
環境固有の値が入っているのが正しい。
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# 普遍の層。local/ と terms/ は gitignore 済みなので最初から対象外
SCAN = ["claude", "bin", "tests", "docs", "README.md", "CONTRIBUTING.md", "install.sh"]
# 測定の証拠と、過去の経緯の記録。**規約ではないので環境固有でよい。**
# ただし**機密性は免除されない**（秘密・個人情報は別の基準で見る）。
EXEMPT = set()
EXEMPT_GLOB = ("docs/journal/*",)   # 測定の証拠と、何をどう決めたかの記録

ABS_PATH = re.compile(r'(?<![\w.])(/Users/[\w.-]+|/home/[\w.-]+|[A-Z]:\\\\Users\\\\[\w.-]+)')
MODEL = re.compile(r'\b(claude|gpt|gemini|llama)-[a-z]*-?\d+(\.\d+)*(-[a-z]+)?\b', re.I)
# 本文中のファイル参照。**このリポジトリに実在するディレクトリ直下**だけを見る。
# 導入先リポジトリの文書を指す記述（`docs/development/...` 等）は正しい書き方なので、
# 第1階層が実在するかで切り分ける（`docs/development/` はここに無い → 外部の話）。
# `bin/` と `tests/` の道具は**拡張子が無い**ものがある。それも対象にする
REPO_PATH = re.compile(
    r'`((?:claude|docs)/[\w./-]+\.(?:md|py|sh)|(?:bin|tests)/[\w.-]+)`')
# ディレクトリを伴わない裸のファイル名も見る。他の製品の内部ファイルがここに
# 書かれていても、第1階層が無いので上の正規表現は拾えない（実際に1件すり抜けた）
BARE_FILE = re.compile(r'`([\w-]+\.(?:js|ts|py|sh|rb|go|rs|json|toml|ya?ml))`')


def files():
    for name in SCAN:
        p = ROOT / name
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix in (".md", ".py", ".sh", "") and f.stat().st_size:
                    yield f


def main():
    errors = []
    for f in files():
        rel = f.relative_to(ROOT).as_posix()
        if rel in EXEMPT or any(f.match(g) for g in EXEMPT_GLOB):
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        # 1. 絶対パス。**このマシンに実在するもの**だけを咎める。
        #    架空の例（/Users/me/... など）は存在しないので通る
        for m in ABS_PATH.finditer(text):
            if pathlib.Path(m.group(1)).exists():
                errors.append(f"{rel}: 実在する絶対パス {m.group(1)}  "
                              f"→ PATH を見るか、無ければ SKIP にする")

        # 2. 版つきのモデル名。使えるかは契約と時期で変わる
        if rel != "tests/verify-portable.py":
            for m in MODEL.finditer(text):
                errors.append(f"{rel}: 版つきモデル名 {m.group(0)}  "
                              f"→ 確かめ方を書く（指定して not available が返るか）")

        # 3b. 裸のファイル名。このリポジトリのどこにも無ければ、外部の製品のもの
        for m in BARE_FILE.finditer(text):
            name = m.group(1)
            if not any(ROOT.rglob(name)):
                errors.append(f"{rel}: どこにも無いファイル名 {name}  "
                              f"→ 他の製品の内部に触れている。確かめ方を書く")

        # 3. このリポジトリに無いファイルへの参照
        for m in REPO_PATH.finditer(text):
            target = m.group(1).split("#")[0].rstrip("/")
            if "*" in target or "<" in target:
                continue
            if (ROOT / target).exists():
                continue
            # 第1・第2階層が実在しないなら、外部リポジトリの話。咎めない
            parts = target.split("/")
            if len(parts) > 2 and not (ROOT / parts[0] / parts[1]).exists():
                continue
            # 「以前は〜だった」のような経緯の記述は咎めない。
            # **語ではなく位置で切る。** 語で切ると「以前は」を足すだけで
            # 現役の依存が素通りする（2026-10-26 に実際にそうなった）。
            # 冒頭の docstring / コメント block の中だけを経緯とみなす。
            # 拡張子で判定しない。**shebang 始まりの拡張子なし**が漏れる
            # （`tests/verify-at-rev` がまさにそれで、1回素通りした）
            body_start = 0
            m2 = re.search(r'"""', text[:2000])
            if m2:
                m3 = text.find('"""', m2.end())
                body_start = m3 + 3 if m3 > 0 else 0
            if m.start() < body_start:
                continue
            errors.append(f"{rel}: 存在しないファイルを参照 {target}  "
                          f"→ このリポジトリの中で完結させる")

    n_exempt = sum(1 for f in files()
                   if f.relative_to(ROOT).as_posix() in EXEMPT
                   or any(f.match(g) for g in EXEMPT_GLOB))
    print(f"## 可搬性の検査（対象 {len(list(files())) - n_exempt} ファイル / "
          f"除外 {n_exempt}：測定の証拠と経緯の記録）")
    if errors:
        for e in sorted(set(errors)):
            print(f"  [FAIL] {e}")
        print(f"\nFAIL {len(set(errors))} 件")
        print("\nここは**公開前提で、リポジトリを跨いで使える**層。")
        print("その環境でしか成り立たない事実は、`local/`（gitignore 済み）へ置くか、")
        print("事実ではなく**確かめ方**を書く。")
        return 1
    print("  [PASS] 実在する絶対パスなし")
    print("  [PASS] 版つきモデル名なし")
    print("  [PASS] 存在しないファイルへの参照なし")
    print("\nすべて PASS")
    print("NOTE: 機械で見える範囲だけ。『他の人の運用でも成立するか』は人が見る")
    return 0


if __name__ == "__main__":
    sys.exit(main())
