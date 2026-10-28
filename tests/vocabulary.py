#!/usr/bin/env python3
"""**語彙は正本から取り出す。手で並べない。**

2026-10-28、同じ形の誤りを1日に3回やった。

1. 要注意語の一覧に1語入れ忘れ、公開前の確認で「要注意語なし」と**誤って報告**した
2. 実機の測定で接頭辞を `issue:` の形で探した。正しい形はコロン無しで、
   **出ている挙動を「出ていない」と誤判定**した
3. 実機の測定で出どころを特定の言い回しで探した。別の言い回しで書かれており
   **取りこぼした**

いずれも「**一致とみなす文字列を手で打ち直した**」ことが原因。
ここが一致判定の正本で、検査も測定もここから取る。
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEW = ROOT / "claude" / "skills" / "review-discipline"

# **職場・取引先に紐づく語。** 公開リポジトリに入ってはいけない。
WORK_TERMS = ("carmo", "volareinc", "redmine" + r"\.system", "kintone", "nyle")

# **判断を避けた語。** 機密ではないが、公開してよいかの判断はしていない。
UNDECIDED_TERMS = (r"[Ww]aymark",)


def confidential_pattern():
    """要注意語。**この関数が正本。** 呼ぶ側で打ち直さない。"""
    return re.compile("|".join(WORK_TERMS + UNDECIDED_TERMS))


def prefixes():
    """指摘の接頭辞を `SKILL.md` の表から読む。**打ち直さない。**"""
    body = (REVIEW / "SKILL.md").read_text(encoding="utf-8")
    found = re.findall(r"^\| `\[(\w+)\]` \|", body, re.M)
    if not found:
        raise RuntimeError("SKILL.md の接頭辞の表が読めない。表の形が変わった")
    return tuple(found)


def prefix_pattern(strict=True):
    """出力中の指摘を拾う。

    `strict` が偽のときは**表記ゆれを許す**（`[issue]` / `issue:` / 行頭の `issue`）。
    実機の出力を数えるときはこちら。**規約どおりの形だけを探すと、
    守られている出力を「守られていない」と読む。**
    """
    w = "|".join(prefixes())
    if strict:
        return re.compile(rf"\[({w})\]")
    return re.compile(rf"(?:\[({w})\]|(?<![\w\[])({w}):|^\s*\d+\.\s+({w})\b)", re.M)


def summary_source_pattern():
    """要約の「出どころ」を**構造で**拾う。

    `この PR（...）:` の括弧の中身。**言い回しを列挙しない。**
    「本文から」「私の読み」「コードから読み取り」…と無限に書ける。
    """
    return re.compile(r"この\s*(?:PR|変更|ファイル|コード)\s*[（(]([^）)]{1,40})[）)]\s*[:：]")
