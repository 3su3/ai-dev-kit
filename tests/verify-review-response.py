#!/usr/bin/env python3
"""指摘を受けた側が、**決められないものを黙って振り分けない**か検める。

セルフレビューは候補を絞らず全部出す（`review-discipline/judgement.md`）。出す側が
絞らないぶん、**受ける側に「対応するか」の判断が集まる。** そこで迷ったものを
①②③のどれかへ寄せると、**判断したように見えて実は決めていない**状態が残る。
読む人からは③（決めた理由がある）と区別できない。

見るのは3つ。

  1. 振り分けが4つある（直す / 範囲外 / 別案 / **決められない**）
  2. 4つ目の行き先が**人**である
  3. スキルの説明（description）にも出ている。**出ていないと発火しない**

3 が落ちると、規約は在るのに読まれない。Claude のスキルは description の一致で
載るので、本文だけ直しても届かない。
"""
import pathlib
import re
import sys

SKILL = (pathlib.Path(__file__).resolve().parent.parent
         / "claude" / "skills" / "review-response" / "SKILL.md")


def main() -> int:
    if not SKILL.exists():
        print(f"SKIP: {SKILL} が無い")
        return 0
    body = SKILL.read_text(encoding="utf-8")
    desc = re.search(r'^description:\s*"?(.*?)"?\s*$', body, re.M)
    desc = desc.group(1) if desc else ""
    ok = True

    print("== 振り分け ==")
    rows = re.findall(r"^\|\s*\*\*(①|②|③|④)[^|]*\|", body, re.M)
    hit = len(rows) == 4
    ok &= hit
    print(f"  {'ok  ' if hit else 'FAIL'} 4つある（実際 {len(rows)} 件 {rows}）")

    print("\n== 決められないものの行き先 ==")
    m = re.search(r"^\|\s*\*\*④[^|]*\|([^|]*)\|([^|]*)\|", body, re.M)
    cell = (m.group(2) if m else "")
    for label, cond, why in [
        ("④ が在る", bool(m), "迷ったものの置き場が無い"),
        ("**人に聞く**", "人に聞く" in cell, "行き先が人でないと、黙って振り分けられる"),
        ("その場で聞く", "その場" in cell or "その場" in body,
         "最後にまとめて聞くと、その間の作業が決まっていない前提に積まれる"),
    ]:
        ok &= bool(cond)
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        if not cond:
            print(f"       {why}")

    print("\n== 説明（description）に出ているか ==")
    for must in ("決められない", "人に聞く"):
        cond = must in desc
        ok &= cond
        print(f"  {'ok  ' if cond else 'FAIL'} description に「{must}」"
              f"{'' if cond else '  ← 出ていないと発火しない'}")

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: 書いてあるかだけを見る。実際にそう振る舞うかは出力で測る")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
