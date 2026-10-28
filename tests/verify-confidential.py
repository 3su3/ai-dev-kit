#!/usr/bin/env python3
"""公開してはいけない語が混ざっていないか。

**これまで `docs/publication-checklist.md` にコマンドが書いてあるだけで、
誰も走らせていなかった。** 書いてあるだけの検査は、無いのと同じ。

**語の一覧はここが正本。** チェックリスト側は、このコマンドを指すだけにする
（2箇所に持つと、必ず片方が古くなる）。
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# **職場・取引先に紐づく語。** 公開リポジトリに入ってはいけない。
WORK = ("carmo", "volareinc", "redmine" + r"\.system", "kintone", "nyle")

# **判断を避けた語。** 2026-10-28 に、この語を含む文書を畳んで 0 件にした。
# 名前自体は本人の個人リポジトリで機密ではないが、**公開してよいかの判断は
# していない**ので、戻ってきたら止める。
UNDECIDED = ("[Ww]aymark",)

# この検査自身は、語の一覧を持っているので対象から外す。
# **穴ではあるが見える穴。** ここへ秘密を書けば素通りする。
SELF = "tests/verify-confidential.py"


def main():
    files = subprocess.run(["git", "ls-files"], cwd=REPO, check=True,
                           capture_output=True, text=True).stdout.split()
    pat = re.compile("|".join(WORK + UNDECIDED))
    hits = []
    for rel in files:
        if rel == SELF:
            continue
        p = REPO / rel
        if not p.is_file():
            continue
        try:
            body = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue          # バイナリは見ない
        for i, line in enumerate(body.splitlines(), 1):
            if pat.search(line):
                hits.append(f"{rel}:{i}: {line.strip()[:80]}")

    if not files:
        sys.exit("git ls-files が空。検査が成立しない")
    print(f"  追跡ファイル {len(files)} 件を見た（{SELF} を除く）")

    # **履歴も見る。** 公開すると過去のコミットも全部読める。
    # 2026-10-28、作業ツリーだけを見ていて、履歴に職場の語が
    # 102/116 コミット分残ったまま公開しかけた。
    revs = subprocess.run(["git", "rev-list", "--all"], cwd=REPO,
                          check=True, capture_output=True, text=True).stdout.split()
    if not revs:
        sys.exit("コミットが1つも無い。履歴の検査が成立しない")
    hist = []
    for i in range(0, len(revs), 200):          # 引数の長さ制限を避ける
        r = subprocess.run(
            ["git", "grep", "-I", "-n", "-E", pat.pattern, *revs[i:i + 200],
             "--", f":(exclude){SELF}"],
            cwd=REPO, capture_output=True, text=True)
        hist += [ln for ln in r.stdout.splitlines() if ln.strip()]
    print(f"  コミット {len(revs)} 件の履歴を見た")
    for h in hits:
        print(f"  [FAIL] 作業ツリー  {h}")
    if hist:
        seen = set()
        for ln in hist:
            # <sha>:<path>:<line>:<本文> → パスだけに畳む
            parts = ln.split(":", 3)
            key = parts[1] if len(parts) > 2 else ln
            if key not in seen:
                seen.add(key)
                print(f"  [FAIL] 履歴  {key}（ほか同一ファイルの版）")
        print(f"  履歴の一致 {len(hist)} 行 / {len(seen)} ファイル")
    hits = hits + hist
    if hits:
        print(f"\n  計 {len(hits)} 件。**履歴の分は作業ツリーを直しても消えない。**\n  公開するなら、履歴を書き換えるか、新しいリポジトリへ現在の tree だけを持っていく")
        sys.exit(1)
    print("  [PASS] 職場・取引先に紐づく語なし（作業ツリー・履歴とも）")
    print("  [PASS] 判断を避けた語なし")
    print("\nすべて PASS")
    print("NOTE: 語の一覧に載っているものだけを見る。載せていない固有名は見つけられない")


if __name__ == "__main__":
    main()
