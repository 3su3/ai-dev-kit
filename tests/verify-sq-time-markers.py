#!/usr/bin/env python3
"""マーカーが**別の段に黙って落ちない**か検める。

段の名前は `<対象>:<段>` で、plan 側にも実装側にもレビューの段がある。ところが
マーカーの対応表は長く plan 側のレビューを持っておらず、**段としては在るのに
マーカーから届かなかった**。実測で plan のレビューが `実装:セルフレビュー` に積まれた。

さらに悪いのは**ハイフンの扱い**だった。マーカーの式が `-` を通さないため、
`#plan-self` は `plan` だけ拾って **`plan:作成` になる**。知らない語なら段が
変わらないだけで済むが、これは**別の段へ黙って入る**。出力を見ても分からない。

見るのは3つ。

  1. plan 側・実装側のそれぞれのレビューに、マーカーから届く
  2. ハイフン付きの語が**前半だけ拾われない**
  3. 知らない語は None（段を変えない）。**別の段にしない**
"""
import importlib.machinery
import importlib.util
import pathlib
import sys

TOOL = pathlib.Path(__file__).resolve().parent.parent / "local" / "sq-time"

CASES = [
    ("#plan 20001 ふりだし",      "plan:作成",            "plan の作成"),
    ("#plan-self 20001 見直す",   "plan:セルフレビュー",   "**plan のレビュー。届かなかった分**"),
    ("#plan-fix 20001 直す",      "plan:レビュー反映",     "**plan の反映。届かなかった分**"),
    ("#計画自己 20001",           "plan:セルフレビュー",   "日本語でも届く"),
    ("#self 書き直す",            "実装:セルフレビュー",   "実装側は従来どおり"),
    ("#impl つくる",              "実装:作成",            "実装の作成"),
    ("#codex 反映",               "実装:codex反映",       "codex 反映"),
    ("直した #検証",              "実装:実機検証",        "末尾でも拾う"),
    ("#tw-p-4 を足す",            None,                   "**ハイフン語の前半を拾わない**"),
    ("#plan-zzz 知らない語",       None,                   "**plan に落とさない**"),
    ("途中に #plan があっても",    None,                   "先頭か末尾だけ見る"),
]


def main() -> int:
    if not TOOL.exists():
        print(f"SKIP: {TOOL} が無い（個人層の道具）")
        return 0
    loader = importlib.machinery.SourceFileLoader("sq_time", str(TOOL))
    spec = importlib.util.spec_from_loader("sq_time", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)

    ok = True
    print("== マーカーから段へ ==")
    for text, want, why in CASES:
        got = mod.marker_phase(text)
        if isinstance(got, tuple):
            got = got[0]
        hit = got == want
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} {text!r:26s} -> {got!r}")
        if not hit:
            print(f"       期待 {want!r} — {why}")

    print("\n== 段の名前が対応表と食い違っていないか ==")
    known = set()
    for _, phases in mod.BUCKETS:
        known |= set(phases)
    bad = sorted(v for v in mod.MARKERS.values() if v not in known)
    hit = not bad
    ok &= hit
    print(f"  {'ok  ' if hit else 'FAIL'} 括りに無い段を指すマーカー {len(bad)} 件 {bad}")

    print("\n== 段のうち、マーカーから届かないもの ==")
    unreachable = sorted(known - set(mod.MARKERS.values()))
    print(f"  届かない段 {len(unreachable)} 件: {unreachable}")
    print("  （これは FAIL にしない。手で名乗る段もあってよい）")

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: 語から段への対応だけを見る。実際に hook が刻むかは見ない")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
