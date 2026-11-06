#!/usr/bin/env python3
"""harness-dispatch が、立ててはいけない場面で立てないか検める。

投入は**取り消しにくい**。ワークツリーができ、エージェントが走り出し、枝が切られる。
この道具の危険は「立たないこと」ではなく、**立ててはいけない場面で立つこと**。

見るのは4つ。

  1. 枝の名前が規約どおりに組まれる（要約が無ければ番号だけ）
  2. 要約を推測しない（渡された文字列だけを使い、形が違えば断る）
  3. **同じチケットのワークツリーが既にあれば止める**
     実測で1チケットが3つのワークツリーに乗っていた。段の持ち主が決まらなくなる
  4. **確認できなかったときに「無い」と同じ扱いにしない**
     Orca に繋がらないだけで二重に立てると、気づく手がかりが無い

番号を引く規則をここに持たないことも見る。実際に2箇所で古い式が生き残った。
"""
import importlib.machinery
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import types

TOOL = pathlib.Path(__file__).resolve().parent.parent / "local" / "harness-dispatch"


def _load_source(path, name="tool"):
    """**バイトコードのキャッシュを通さずに読む。**

    macOS の system Python は `sys.pycache_prefix` を持ち、`~/Library/Caches` 配下へ
    バイトコードを溜める。ツリーの中に `__pycache__` が出ないので気づけない。
    `SourceFileLoader` で読むと**古いコードが読まれることがあり**、変異を当てたのに
    緑のまま、ソースと違う結果、という形で出る（2026-11-06 に実際に数時間溶かした）。

    ソースを読んで `exec` すれば、キャッシュの経路を一切通らない。
    """
    ns = types.ModuleType(name)
    ns.__file__ = str(path)
    exec(compile(pathlib.Path(path).read_text(encoding="utf-8"), str(path), "exec"),
         ns.__dict__)
    return ns


def _load():
    return _load_source(TOOL)


def main() -> int:
    if not TOOL.exists():
        print(f"SKIP: {TOOL} が無い（個人層の道具）")
        return 0
    m = _load()
    ok = True

    print("== 要約の形 ==")
    for slug, want, why in [("s3-lifecycle", True,  "英小文字とハイフン"),
                            ("a1-b2",        True,  "数字が混じってよい"),
                            ("S3-Lifecycle", False, "大文字は断る"),
                            ("s3_lifecycle", False, "下線は断る"),
                            ("ライフサイクル",  False, "**日本語は断る。推測して英字にしない**"),
                            ("-x",           False, "先頭のハイフン")]:
        got = bool(m.SLUG_OK.match(slug))
        hit = got == want
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} {slug:14s} -> {got} ({why})")

    print("\n== 既に立っているワークツリーを見つけるか ==")
    ws = [{"branch": "refs/heads/feature/20001-foo", "path": "/w/a"},
          {"branch": "refs/heads/feature/20002", "path": "/w/b"},
          {"branch": "refs/heads/someone/日本語", "path": "/w/c"},
          {"branch": "refs/heads/chore/no-number", "path": "/w/d"}]
    real_run = m.run
    m.run = lambda cmd, **k: types.SimpleNamespace(
        returncode=0, stdout=json.dumps({"result": {"worktrees": ws}}), stderr="")
    try:
        for num, want, why in [(20001, 1, "要約つきの枝"),
                               (20002, 1, "**要約なしの枝も見つける**"),
                               (20003, 0, "立っていない")]:
            got = m.existing_worktrees(num)
            hit = got is not None and len(got) == want
            ok &= hit
            print(f"  {'ok  ' if hit else 'FAIL'} #{num} -> {len(got) if got is not None else None} 件"
                  f" (期待 {want}) — {why}")
    finally:
        m.run = real_run

    print("\n== 確認できなかったときに「無い」と言わないか ==")
    for rc, out, why in [(1, "", "Orca が落ちている"),
                         (0, "これはJSONではない", "返事が壊れている")]:
        m.run = lambda cmd, _rc=rc, _o=out, **k: types.SimpleNamespace(
            returncode=_rc, stdout=_o, stderr="")
        try:
            got = m.existing_worktrees(20001)
        finally:
            m.run = real_run
        hit = got is None
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} {why:20s} -> {got!r} (期待 None。空リストではない)")

    print("\n== 送り先の端末が1つに決まるときだけ送るか ==")
    # 決められないのに送ると、**無関係の端末へ本文を流し込む**。
    for before, after, want, why in [
        ({"a"},      {"a", "b"},      "b",  "1つ増えた"),
        ({"a"},      {"a"},           None, "増えていない＝端末ができていない"),
        ({"a"},      {"a", "b", "c"}, None, "**2つ増えた。どれか決められない**"),
        (None,       {"a", "b"},      None, "**前が取れていない**"),
        ({"a"},      None,            None, "**後が取れていない**"),
    ]:
        got = m.new_handle(before, after)
        hit = got == want
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} {str(before):16s}->{str(after):18s} -> {got!r} ({why})")

    print("\n== 端末一覧が取れないときに「空」と言わないか ==")
    for rc, out, why in [(1, "", "Orca が落ちている"), (0, "壊れた", "返事が壊れている")]:
        m.run = lambda cmd, _rc=rc, _o=out, **k: types.SimpleNamespace(
            returncode=_rc, stdout=_o, stderr="")
        try:
            got = m.terminal_handles()
        finally:
            m.run = real_run
        hit = got is None
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} {why:18s} -> {got!r} (期待 None。set() ではない)")

    print("\n== 送り先が無ければ送らないか ==")
    called = []
    m.run = lambda cmd, **k: (called.append(cmd) or
                              types.SimpleNamespace(returncode=0, stdout="", stderr=""))
    try:
        sent = m.deliver(None, "本文")
    finally:
        m.run = real_run
    hit = (sent is False) and not called
    ok &= hit
    print(f"  {'ok  ' if hit else 'FAIL'} handle=None -> 送った回数 {len(called)} (期待 0)")

    print("\n== 投入プロンプトの形 ==")
    # **届け方の制約がそのまま仕様になっている。** 改行があると途中で送信され、
    # マーカーが先頭に無いと段が付かない。どちらも成功を返して静かに失敗する。
    prompt = m.build_prompt("plan", 20001, "https://例.invalid")
    checks = [
        ("改行が無い",            "\n" not in prompt,
         "**改行で途中送信され、残りが次の発話になる**"),
        ("マーカーが先頭",        prompt.startswith("#plan "),
         "sq-time は先頭か末尾しか見ない"),
        ("番号が入る",            " 20001 " in prompt,
         "段をチケットに紐づけるため"),
        ("URL が入る",            "/issues/20001" in prompt,
         "エージェントがチケットを読めるように"),
        ("修正対象を要求する",     "修正対象" in prompt,
         "**常時読みへ足さずに、ここで要求する**"),
        ("道具の名を添える",       "plan-vs-diff" in prompt,
         "何のために要るかを書く。直し方の無い指示にしない"),
    ]
    for label, got, why in checks:
        ok_ = bool(got)
        ok &= ok_
        print(f"  {'ok  ' if ok_ else 'FAIL'} {label}")
        if not ok_:
            print(f"       {why}")

    print("\n== 待ちの判定そのもの（落ち着いたと言い切ってよいか）==")
    # **ケースごとにモジュールを読み直す。** 偽物を節をまたいで使い回すと、
    # 前の節の差し替えが残って「同じコードなのに結果が変わる」ように見える。
    # 実際にそれで長く詰まった。読み直しは安いので、毎回まっさらから始める。
    import types as _t1
    SAT = json.dumps({"result": {"wait": {"satisfied": True}}})
    NOT = json.dumps({"result": {"wait": {"satisfied": False}}})

    def _fake(seq):
        calls = []
        def f(cmd, **k):
            rc, body = seq[min(len(calls), len(seq) - 1)]
            calls.append(cmd)
            return _t1.SimpleNamespace(returncode=rc, stdout=body, stderr="")
        f.calls = calls
        return f

    for seq, want, why in [
        ([(0, SAT), (0, SAT)], True,  "2回とも落ち着いた"),
        ([(0, SAT), (0, NOT)], False, "**1回目だけ落ち着き、2回目は働いていた**"),
        ([(0, NOT), (0, NOT)], False, "時間切れ"),
        ([(1, ""), (1, "")],   None,  "**呼べなかった。落ち着いた扱いにしない**"),
        ([(0, "こわれ"), (0, "こわれ")], None, "**返事が壊れている。同上**"),
    ]:
        mm = _load()
        f = _fake(seq)
        mm.run = f
        got = mm.wait_idle("term_x", settle=0)
        hit = got is want
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} {why:38s} -> {got!r} "
              f"(期待 {want!r}, 尋ねた回数 {len(f.calls)})")

    print("\n== 連鎖: 待てなかったら次を送らない ==")
    # **働いている最中へ送ると、前の段の途中に割り込む。** 待てなかったとき
    # （取得失敗・時間切れ）に次を送らないことが、この仕組みの安全弁。
    import types as _t2
    real_wait = m.wait_idle
    for verdict, want_sent, why in [
        (True,  2, "落ち着いた → 2本とも送る"),
        (False, 1, "**時間切れ → 2本目を送らない**"),
        (None,  1, "**測れない → 2本目を送らない**"),
    ]:
        calls = []
        m.wait_idle = lambda h, settle=None, _v=verdict: _v
        m.run = lambda cmd, **k: (calls.append(cmd) or
                                  _t2.SimpleNamespace(returncode=0, stdout="", stderr=""))
        try:
            got = m.deliver_chain("term_x", ["ひとつめ", "ふたつめ"])
        finally:
            m.wait_idle = real_wait
            m.run = real_run
        hit = got == want_sent
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} 待ちの結果={verdict!r} -> 送った {got} 本 "
              f"(期待 {want_sent}) — {why}")

    print("\n== 連鎖: 送れなかったらそこで止まる ==")
    m.wait_idle = lambda h, settle=None: True
    m.run = lambda cmd, **k: _t2.SimpleNamespace(returncode=1, stdout="", stderr="だめ")
    try:
        got = m.deliver_chain("term_x", ["ひとつめ", "ふたつめ"])
    finally:
        m.wait_idle = real_wait
        m.run = real_run
    hit = got == 0
    ok &= hit
    print(f"  {'ok  ' if hit else 'FAIL'} 1本目が送れない -> 送った {got} 本 (期待 0)")

    print("\n== レビューのプロンプトが実装を止めているか ==")
    rp = m.build_review_prompt(20001)
    for label, cond in [("1行である", "\n" not in rp),
                        ("マーカーが先頭", rp.startswith("#plan-self ")),
                        ("[issue] が無くなるまで繰り返す", "繰り返す" in rp),
                        ("**候補を絞らない**", "全部出す" in rp),
                        ("対応要否は実装側", "実装側が決める" in rp),
                        ("**実装させない**", "実装はしない" in rp),
                        ("人の承認で止まる", "人の承認を待つ" in rp)]:
        ok &= bool(cond)
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")

    print("\n== 番号を引く規則を自前で持っていないか ==")
    bad = [l for l in TOOL.read_text().splitlines()
           if re.search(r"""r["'][^"']*\\d\{[0-9]""", l)]
    hit = not bad
    ok &= hit
    print(f"  {'ok  ' if hit else 'FAIL'} 自前の番号正規表現 {len(bad)} 件")
    for l in bad[:2]:
        print(f"       {l.strip()[:74]}")

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: 立てる前の判断だけを見る。Orca が実際に作る中身は見ない")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
