#!/usr/bin/env python3
"""「次にやること」を、観測が足りないのに決めつけないか検める。

次にやることは**保存しない**。段・エージェントの忙しさ・PR の状態から計算する。
保存すると正本が2つになり、古い方が生き残る。計算なら `/clear` しても壊れない。

見るのは4つ。

  1. 段ごとに、次が**人か道具か**で分かれる
  2. **働いている最中は次を出さない**
  3. **測れないときは「不明」**。働いていないことにしない
  4. **PR の状態を引けないときは、PR に関わる判断を出さない**

4 を落とすと、実際には PR 待ちのものへ「検証の結果を見て」のような別の答えを確信を
持って返す。同じ瞬間に2回叩いて答えが食い違った（2026-11-06）。

**`terminal wait` の時間切れは観測であって失敗ではない。** `ok:false` に
`code: timeout` で返るので、終了コードだけ見ると「測れない」と混ざる。混ぜると
働いていることが「分からない」になり、届いた送信を「届いていない」と読む。
"""
import json
import pathlib
import sys
import types

TOOL = pathlib.Path(__file__).resolve().parent.parent / "local" / "harness-next"
DISP = pathlib.Path(__file__).resolve().parent.parent / "local" / "harness-dispatch"


def _load(path, name="t"):
    ns = types.ModuleType(name)
    ns.__file__ = str(path)
    exec(compile(pathlib.Path(path).read_text(encoding="utf-8"), str(path), "exec"),
         ns.__dict__)
    return ns


def main() -> int:
    if not TOOL.exists():
        print(f"SKIP: {TOOL} が無い（個人層の道具）")
        return 0
    m = _load(TOOL)
    ok = True

    print("== 段のあと、誰が動くか ==")
    for phase, want_who, why in [
        ("plan:作成",          "道具", "レビューへ渡す"),
        ("plan:セルフレビュー", "人",   "**plan の承認**"),
        ("実装:作成",          "道具", "レビューへ渡す"),
        ("実装:セルフレビュー", "道具", "**PR まで運ぶ**"),
        ("実装:実機検証",      "人",   "マージの判断"),
        ("実装:チームレビュー", "他",   "こちらから動かさない"),
        ("知らない段",         "不明", "**勝手に決めない**"),
    ]:
        who, _ = m.next_step(phase, busy=False, pr=None)
        hit = who == want_who
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} {phase:<20} -> {who}  （{why}）")

    print("\n== 観測が足りないとき ==")
    for busy, want, why in [
        (True,  "待ち", "働いている最中は次を出さない"),
        (None,  "不明", "**測れない。働いていないことにしない**"),
    ]:
        who, _ = m.next_step("実装:作成", busy=busy, pr=None)
        hit = who == want
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} busy={busy!r} -> {who}  （{why}）")

    print("\n== PR の状態が段より先に効くか ==")
    for pr, want, why in [
        ({"number": 1, "state": "OPEN", "isDraft": True,  "ci": "緑"}, "人",
         "Draft は人が Ready にする"),
        ({"number": 1, "state": "OPEN", "isDraft": False, "ci": "赤"}, "道具",
         "CI が赤なら直す"),
        ({"number": 1, "state": "OPEN", "isDraft": False, "ci": "緑"}, "人",
         "レビュー待ち / マージの判断"),
        ({"number": 1, "state": "OPEN", "isDraft": False, "ci": None}, "不明",
         "**CI を引けない。緑にしない**"),
    ]:
        who, _ = m.next_step("実装:実機検証", busy=False, pr=pr)
        hit = who == want
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} draft={pr['isDraft']} ci={pr['ci']!r} -> {who}"
              f"  （{why}）")

    print("\n== 時間切れを「測れない」と混ぜないか ==")
    d = _load(DISP, "d")
    for body, want, why in [
        (json.dumps({"ok": True, "result": {"wait": {"satisfied": True}}}), True,
         "落ち着いている"),
        (json.dumps({"ok": False, "error": {"code": "timeout"}}), False,
         "**時間切れ＝働いている。これは観測**"),
        (json.dumps({"ok": False, "error": {"code": "invalid_argument"}}), None,
         "別の失敗は測れない"),
        ("こわれた", None, "読めない"),
    ]:
        got = d.read_wait(body)
        hit = got is want
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} {why:34s} -> {got!r}")

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: 観測から次を決める関数だけを見る。実際の段や PR は見ない")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
