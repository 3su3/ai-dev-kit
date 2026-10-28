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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vocabulary import confidential_pattern   # noqa: E402

# **語の一覧は tests/vocabulary.py が持つ。** ここで打ち直さない。
# 打ち直した結果、1語入れ忘れて「要注意語なし」と誤報告した（2026-10-28）。
# **語の一覧を持つファイルは対象から外す。** 穴ではあるが見える穴。
# 履歴も見るので、**過去に一覧を持っていたファイル**も外す必要がある。
EXCLUDE = ("tests/vocabulary.py", "tests/verify-confidential.py")


def main():
    files = subprocess.run(["git", "ls-files"], cwd=REPO, check=True,
                           capture_output=True, text=True).stdout.split()
    pat = confidential_pattern()
    hits = []
    for rel in files:
        if rel in EXCLUDE:
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
    # **一覧が正本なので、上位に照合先が無い。** 中身は検査できないが、
    # **うっかり減らした**ことは件数で捕まえられる（歯止め。測った数ではない）。
    from vocabulary import WORK_TERMS, UNDECIDED_TERMS
    n = len(WORK_TERMS) + len(UNDECIDED_TERMS)
    MIN_TERMS = 6
    if n < MIN_TERMS:
        sys.exit(f"要注意語が {n} 語。{MIN_TERMS} 語を下回った。"
                 "減らすなら、この下限も一緒に下げる（意図した削除かを示す）")

    print(f"  追跡ファイル {len(files)} 件を見た（{', '.join(EXCLUDE)} を除く）")

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
             "--", *[f":(exclude){e}" for e in EXCLUDE]],
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
