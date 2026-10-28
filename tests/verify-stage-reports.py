#!/usr/bin/env python3
"""各段の報告が「成果物から」作られる形になっているか。

**自分の記憶から書いた報告は、ずれを構造的に見逃す。**
実装が計画からずれたときほど「計画どおりにやったつもり」で書くので、
読む人が一番気づきたいものだけが落ちる。

以前は実装報告の「計画記録との差異」の既定が `- なし` だった。
"""
import re
import sys
from pathlib import Path

DEV = Path(__file__).resolve().parent.parent / "claude" / "skills" / "dev-flow"
ok = True


def check(name, cond, detail=""):
    global ok
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{('  ' + detail) if detail and not cond else ''}")
    ok &= bool(cond)


def section(path, head="# チャットでの報告"):
    body = (DEV / path).read_text(encoding="utf-8")
    return body[body.index(head):] if head in body else ""


def items(text):
    """` 1. ラベル  説明` の形の項目名を拾う"""
    return re.findall(r"^\s*(\d+)\.\s+(\S+)", text, re.M)


def main():
    print("\n## 3つの段すべてに報告の形がある")
    stages = {
        "計画後（leader.md）": section("leader.md"),
        "実装後（implementer.md）": section("implementer.md"),
        "実機確認後（verification-report.md）":
            (DEV / "verification-report.md").read_text(encoding="utf-8")
            if (DEV / "verification-report.md").is_file() else "",
    }
    for n, body in stages.items():
        check(n, bool(body), "節が見つからない")

    print("\n## 5つ以内に絞ってある")
    # **読む側が全部読まないと「おかしい」に気づけない形にしない。**
    for n, body in stages.items():
        nums = [int(i) for i, _ in items(body)]
        check(f"{n}: {len(nums)} 項目", 0 < len(nums) <= 5, f"{len(nums)} 項目")

    print("\n## 記憶からではなく成果物から作らせている")
    check("計画後: plan.md を読み直すと書いてある",
          "読み直して" in stages["計画後（leader.md）"])
    impl = stages["実装後（implementer.md）"]
    check("実装後: git diff を使うと書いてある", "git diff" in impl)
    check("実装後: 集合で突き合わせるコマンドがある", "comm -3" in impl)
    check("実装後: 記憶から書くなと言っている", "記憶から書かない" in impl)
    # **「なし」を既定にしない。** 以前の形がそれで、一番見たいものを落としていた
    check("実装後: 「なし」と書く前に実行させる", "と書く前に" in impl)

    print("\n## 実機確認は結論を先に言う")
    v = stages["実機確認後（verification-report.md）"]
    check("問題なし / 懸念あり のどちらかを必ず書く",
          "問題なし" in v and "懸念あり" in v and "必ず書く" in v)
    # **反映されていないと「何も変わっていない」が正しい見た目になる**
    check("反映の確認を頭に書かせる", "反映" in v and "書けないなら" in v)
    check("確かめていない範囲を黙らせない", "確かめていないこと" in v)
    check("止めるかどうかは人が決める", "人が決める" in v)

    print("\n## 入口から辿れる")
    skill = (DEV / "SKILL.md").read_text(encoding="utf-8")
    check("SKILL.md が verification-report.md を指している",
          "verification-report.md" in skill)

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: 書いてあるかだけを見る。実際にそう報告するかは出力で測る")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
