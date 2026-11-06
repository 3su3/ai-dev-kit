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


def _load():
    loader = importlib.machinery.SourceFileLoader("dispatch", str(TOOL))
    spec = importlib.util.spec_from_loader("dispatch", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


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
