#!/usr/bin/env python3
"""`docs/journal/*plan*.md` が状態行を持っているかを見る。

**状態行は凍る。** 実際、3本が書いた時点の状態（「承認待ち」）のまま、
対応する PR がマージされた後も残っていた。採用されていない方針が
Plan という正本の顔で残ると、次に読む人がそれを現行だと思う。

この検査が見るのは**存在と形だけ**。中身が現状と合っているかは見ない
（機械で判定するには PR の状態を引く必要があり、テストでネットワークに
触れたくない）。**形が整っていても古いことはある。**
"""
import pathlib
import re
import sys

DOCS = pathlib.Path(__file__).resolve().parent.parent / "docs"
STATES = ["完了", "撤退", "実施済み", "実装済み", "検討中", "承認待ち", "保留"]
LINE = re.compile(r"^> \*\*状態:\s*([^*]+?)\*\*(.*)$", re.M)
CITE = re.compile(r"#\d+|`[0-9a-f]{7,}`|\.md")


def main():
    plans = sorted(DOCS.glob("journal/*plan*.md"))
    if not plans:
        sys.exit("docs/ に Plan 文書が無い。検査が成立しない")

    ok = True
    for p in plans:
        m = LINE.search(p.read_text(encoding="utf-8"))
        if not m:
            print(f"  [FAIL] {p.name}: 状態行が無い（`> **状態: ...**` の形で書く）")
            ok = False
            continue
        state, rest = m.group(1).strip(), m.group(2)
        if not any(s in state for s in STATES):
            print(f"  [FAIL] {p.name}: 状態『{state}』が既知の語でない（{' / '.join(STATES)}）")
            ok = False
        elif not CITE.search(rest):
            print(f"  [FAIL] {p.name}: 状態『{state}』に根拠（PR 番号・コミット・文書）が無い")
            ok = False
        else:
            print(f"  [PASS] {p.name}: {state}")

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: 存在と形だけを見ている。中身が現状と合っているかは見ていない")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
