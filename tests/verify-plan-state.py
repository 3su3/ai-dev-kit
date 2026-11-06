#!/usr/bin/env python3
"""harness-plan-state が、plan の状態を取り違えないか検める。

**この道具の危険は「無い」と「分からない」の取り違え。** `gh` が落ちている・認証が
切れている・ファイル一覧が返らない、を「plan が無い」と同じに扱うと、**済んでいる
plan を未着手として数える**。数が静かに減るだけなので、出力からは気づけない。

見るのは4つ。

  1. 変更パスが plan の置き場だけ → plan PR、ほかが混じれば実装 PR
  2. Draft と Ready を分ける（Ready が人の承認の合図）
  3. 複数あるときは**一番進んだもの**を採る
  4. **取れていないものが1本でもあれば unknown へ倒す**（none にしない）
"""
import importlib.machinery
import importlib.util
import json as _j
import pathlib
import sys

BIN = pathlib.Path(__file__).resolve().parent.parent / "bin" / "harness-plan-state"
PP = ["issues/"]


def _load():
    loader = importlib.machinery.SourceFileLoader("plan_state", str(BIN))
    spec = importlib.util.spec_from_loader("plan_state", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def pr(paths, state="OPEN", draft=False):
    return {"state": state, "isDraft": draft, "files": [{"path": p} for p in paths]}


CLASSIFY = [
    (["issues/me/1_plan.md"],                    "plan",    "plan の置き場だけ"),
    (["issues/me/a.md", "issues/me/b.md"],       "plan",    "複数でも置き場の中なら plan"),
    (["issues/me/1_plan.md", "app/Foo.php"],     "impl",    "コードが混じれば実装"),
    (["app/Foo.php"],                            "impl",    "コードだけ"),
    ([],                                         "unknown", "**一覧が空。取れていない**"),
]

STATE = [
    ([pr(["issues/a.md"], "MERGED")],                         "merged", "マージ済み＝plan 完了"),
    ([pr(["issues/a.md"], "OPEN", draft=False)],              "ready",  "Ready＝人の承認が要る"),
    ([pr(["issues/a.md"], "OPEN", draft=True)],               "draft",  "Draft＝まだレビュー前"),
    ([pr(["issues/a.md"], "CLOSED")],                         "closed", "閉じられた"),
    ([pr(["app/Foo.php"], "MERGED")],                         "none",   "実装 PR しか無い"),
    ([],                                                      "none",   "PR が無い"),
    ([pr(["issues/a.md"], "OPEN", True), pr(["issues/b.md"], "MERGED")],
                                                              "merged", "一番進んだものを採る"),
    ([pr(["app/Foo.php"], "MERGED"), pr([], "OPEN")],         "unknown","**取れていないのが混じる**"),
    ([pr([], "MERGED")],                                      "unknown","一覧が空のものだけ"),
]


def main() -> int:
    if not BIN.exists():
        print(f"SKIP: {BIN} が無い")
        return 0
    m = _load()
    ok = True

    print("== plan PR か実装 PR か ==")
    for paths, want, why in CLASSIFY:
        got = m.classify(paths, PP)
        hit = got == want
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} {str(paths)[:44]:46s} -> {got}")
        if not hit:
            print(f"       期待 {want} — {why}")

    print("\n== チケットの plan 状態 ==")
    for prs, want, why in STATE:
        got = m.plan_state(prs, PP)
        hit = got == want
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} {why:34s} -> {got}")
        if not hit:
            print(f"       期待 {want}")

    print("\n== 上限で打ち切られたとき「無い」と言わないか ==")
    # **subprocess で測らない。** gh が無い環境では取得失敗でも unknown になり、
    # 打ち切りを見ていなくても通ってしまう（偽の緑）。純粋な関数で測る。
    for prs, trunc, want, why in [
        ([],                             True,  "unknown", "**打ち切り。見ていないだけかも**"),
        ([],                             False, "none",    "全部見た上で無い"),
        ([pr(["issues/a.md"], "MERGED")], True, "merged",  "在ったほうは打ち切りでも言える"),
        ([pr(["app/Foo.php"], "MERGED")], True, "unknown", "実装しか無い＋打ち切り"),
    ]:
        got = m.resolve_state(prs, PP, trunc)
        hit = got == want
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} 打ち切り={str(trunc):5s} {why:34s} -> {got}")
        if not hit:
            print(f"       期待 {want}")

    print("\n== fetch が打ち切りを呼び出し側へ渡すか（配線）==")
    # 純粋な関数のテストは部品しか守らない。`len(rows) >= limit` から truncated へ
    # 渡る配線が死ぬと、上の守りが丸ごと効かなくなる。**gh の応答だけを偽装**して、
    # fetch 自身の返し方を測る。
    import subprocess as _sp
    import types as _t
    real_run = _sp.run
    for n, limit, want, why in [(3, 3, True, "上限ちょうど＝打ち切られたかもしれない"),
                                (2, 3, False, "上限未満＝全部見た"),
                                (0, 3, False, "0 件でも上限未満なら全部見た")]:
        body = _j.dumps([{"number": i, "state": "OPEN", "isDraft": False,
                          "headRefName": f"feature/2000{i}-x", "files": []}
                         for i in range(n)])
        _sp.run = lambda *a, **k: _t.SimpleNamespace(returncode=0, stdout=body, stderr="")
        try:
            got = m.fetch([], limit)
        finally:
            _sp.run = real_run
        hit = got is not None and got[1] == want
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} {n}件/上限{limit} -> truncated={got[1] if got else None}"
              f" (期待 {want}) — {why}")

    print("\n== 取得失敗が none と区別できるか ==")
    fail_rows = m.fetch(["--repo", "存在しない/リポジトリ"], 1)
    hit = fail_rows is None
    ok &= hit
    print(f"  {'ok  ' if hit else 'FAIL'} 引けないリポジトリ -> {fail_rows!r} (期待 None)")

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: PR の形からの判定だけを見る。plan の中身が妥当かは見ない")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
