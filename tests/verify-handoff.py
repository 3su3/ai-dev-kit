#!/usr/bin/env python3
"""渡し先を取り違えないか、言い切れないときに止まるか検める。

渡すのは**取り消しにくい操作**。いまのエージェントを閉じ、別のエージェントを立て、
本文を送る。間違えると、働いている最中の変更が消えるか、無関係な端末へ本文が入る。

見るのは4つ。

  1. 段ごとに**誰を立てるか**が決まっている（plan-self/self は Kiro、impl は Claude）
  2. **承認を記録するのは impl へ渡すときだけ**（他の2つは承認ではない）
  3. 端末が**1つに決まらなければ渡さない**（0個でも2個以上でも）
  4. 送る本文が**1行**で、マーカーが先頭にある（どちらも静かに失敗する形）

3 が効く場面を実際に踏んだ。`/quit` しただけの抜け殻が残っていて、同じ枝に端末が
2個あった（2026-11-06）。**どちらへ送るかを決められない。**
"""
import pathlib
import sys
import types

TOOL = pathlib.Path(__file__).resolve().parent.parent / "local" / "harness-handoff"


def _load(path, name="t"):
    """**バイトコードのキャッシュを通さずに読む**（macOS は ~/Library/Caches へ溜める）。"""
    ns = types.ModuleType(name)
    ns.__file__ = str(path)
    exec(compile(pathlib.Path(path).read_text(encoding="utf-8"), str(path), "exec"),
         ns.__dict__)
    return ns


def term(handle, branch, orphaned=False, title="x", agent=None):
    return {"handle": handle, "branch": f"refs/heads/{branch}",
            "orphaned": orphaned, "title": title, "agentIdentity": agent}


def main() -> int:
    if not TOOL.exists():
        print(f"SKIP: {TOOL} が無い（個人層の道具）")
        return 0
    m = _load(TOOL)
    ok = True
    B = "feature/20001-x"

    print("== 段ごとの渡し先 ==")
    for step, agent, approval in [("plan-self", "kiro", False),
                                  ("impl", "claude", True),
                                  ("self", "kiro", False),
                                  ("pr", "claude", False)]:
        s = m.STEPS[step]
        hit = s["agent"] == agent and s["approval"] is approval
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} {step:10s} -> {s['agent']:6s} "
              f"承認の記録={s['approval']}")

    print("\n== 承認を記録するのは1つだけ ==")
    n = sum(1 for s in m.STEPS.values() if s["approval"])
    hit = n == 1
    ok &= hit
    print(f"  {'ok  ' if hit else 'FAIL'} 記録する段 {n} 件（期待 1。渡すこと自体は承認ではない）")

    print("\n== 端末が1つに決まるときだけ渡す ==")
    for rows, want_ok, why in [
        ([term("a", B)],                               True,  "1つ。渡す"),
        ([term("a", B), term("b", B)],                 False, "**2つ。どちらか決められない**"),
        ([],                                           False, "0個"),
        ([term("a", B, orphaned=True)],                False, "**抜け殻だけ**"),
        ([term("a", "feature/29999-y")],               False, "別の枝しか無い"),
        ([term("a", B), term("b", B, orphaned=True)],  True,  "抜け殻は数えない"),
        ([term("a", B, agent="claude"), term("b", B)], True,
         "**素のシェルが残っていても、動いている方を選ぶ**"),
        ([term("a", B, agent="claude"), term("b", B, agent="kiro")], False,
         "**2つ動いている。閉じ忘れ。渡さない**"),
        (None,                                         False, "**一覧を取れなかった**"),
    ]:
        got, reason = m.pick(rows, B)
        hit = (got is not None) == want_ok
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} {why:34s} -> "
              f"{'渡す' if got else '止まる'}")
        if not hit:
            print(f"       {reason}")

    print("\n== セルフレビューの後、PR まで行けるか ==")
    d = types.SimpleNamespace(build_review_prompt=lambda t: f"#plan-self {t} …")
    # **ここで止めると次が回らない。** codex レビューは PR に対して走るので、
    # PR が無いと止まる。Kiro はコミットしないし、実装した端末は閉じている。
    pr = m.prompt_for(d, "pr", 20001)
    for label, cond, why in [
        ("コミットする", "コミット" in pr, "PR の中身が無いと codex が見るものが無い"),
        ("Ready で PR を作る", "**Ready で** PR を作る" in pr,
         "**Draft で止めると codex が走らず、次の段が回らない**"),
        ("Draft で止めない", "Draft" not in pr,
         "セルフレビューが先に終わっているので、Draft が守るものが無い"),
        ("レビュワーを指名しない", "指名しない" in pr, "通知が飛ぶ"),
        ("4つに振り分ける", "4つに振り分ける" in pr,
         "セルフレビューの指摘は全部来る。対応要否は実装側が決める"),
        ("決められないものは聞く", "その場で聞いて" in pr, "黙って振り分けない"),
    ]:
        ok &= bool(cond)
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        if not cond:
            print(f"       {why}")

    print("\n== 動いているエージェントを名前で出すか ==")
    # `agentIdentity` は動いているエージェントの名前を返し、/quit 済みの端末では
    # None になる。**当初「Kiro は None」と読み違えた**（観測したのが /quit 済みの
    # 端末だったため）。名前が出れば、閉じ忘れがどちらかすぐ分かる。
    _, why2 = m.pick([term("a", B, agent="claude"), term("b", B, agent="kiro")], B)
    for label, cond in [("claude を名指しする", "claude" in why2),
                        ("kiro を名指しする", "kiro" in why2)]:
        ok &= bool(cond)
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")

    print("\n== 止まる理由を取り違えないか ==")
    # 一覧を取れなかったのと、端末が無いのは**別のこと**。どちらも止まるので判断は
    # 同じだが、「端末が無い」と出ると、在る端末を探しに行くことになる。
    _, r_none = m.pick(None, B)
    _, r_empty = m.pick([], B)
    for label, cond in [("取れなかったと言う", "取れなかった" in r_none),
                        ("無いときは無いと言う", "端末が無い" in r_empty),
                        ("2つを混ぜない", r_none != r_empty)]:
        ok &= bool(cond)
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")

    print("\n== 送る本文の形 ==")
    d = types.SimpleNamespace(build_review_prompt=lambda t: f"#plan-self {t} …")
    for step, head in [("plan-self", "#plan-self "), ("impl", "#impl "),
                       ("self", "#self "), ("pr", "#self ")]:
        text = m.prompt_for(d, step, 20001)
        for label, cond in [(f"{step}: 1行である", "\n" not in text),
                            (f"{step}: マーカーが先頭", text.startswith(head))]:
            ok &= bool(cond)
            print(f"  {'ok  ' if cond else 'FAIL'} {label}")

    print("\n== 待ち方・送り方を harness-dispatch に委ねているか ==")
    # **否定で測らない。** 「写していない」を文字列の不在で見ると、説明文に書いた
    # 語まで拾って偽の赤になる（実際にそうなった）。**呼んでいることを肯定で測る。**
    src = TOOL.read_text(encoding="utf-8")
    for label, cond, why in [
        ("待ちは d.wait_idle に委ねる", "d.wait_idle(" in src,
         "自前で待つと、落ち着きの判定が2箇所になる"),
        ("送りは d.deliver に委ねる", "d.deliver(" in src,
         "自前で送ると、逐語＋改行の順が2箇所になる"),
        ("tui-idle を自前で叩かない", '"tui-idle"' not in src.replace("`tui-idle`", ""),
         "叩いていたら委ねていない"),
    ]:
        ok &= bool(cond)
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        if not cond:
            print(f"       {why}")

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: 渡す前の判断だけを見る。Orca が実際に立てる中身は見ない")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
