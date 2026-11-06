#!/usr/bin/env python3
"""harness-branch-check が、**切り直してよい場面でだけ**切り直しを勧めるか検める。

この警告の危険は「出ないこと」ではなく「**出してはいけない場面で出ること**」。
PR を作った後にブランチ名を変えると、旧名の ref が消えた時点でその PR は閉じる。
`git branch -m` を勧めてしまうと取り返しがつかない。

見るのは3つ。

  1. 番号が引ける枝・引けなくてよい枝では**黙る**（黙らないと警告が無視される）
  2. PR が無いときだけ `git branch -m` を出す
  3. **PR の有無を確かめられなかったときは勧めない**（取得失敗を「無い」と同じ扱いにしない）

3 が無いと、`gh` が落ちているだけで「PR は無い」と読み、PR を閉じさせる。
"""
import importlib.machinery
import importlib.util
import pathlib
import types
import sys

BIN = pathlib.Path(__file__).resolve().parent.parent / "bin" / "harness-branch-check"
RENAME = "git branch -m"


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
    return _load_source(BIN)


# (枝, verdict, PRの有無, 出すか, 切り直しを勧めてよいか, なぜ見るか)
CASES = [
    ("feature/20002-x",  "ticket",  False, False, False, "番号が引ける。言うことは無い"),
    ("chore/findings",   "none",    False, False, False, "番号が無いのが正しい。黙る"),
    ("main",             "unknown", False, False, False, "既定の枝に番号は要らない"),
    ("qa/alpha",         "unknown", False, False, False, "検証環境の枝に番号は要らない"),
    ("someone/weekly",      "unknown", False, True,  True,  "規約外・PR なし。切り直せる"),
    ("someone/weekly",      "unknown", True,  True,  False, "**PR がある。勧めたら PR が閉じる**"),
    ("someone/weekly",      "unknown", None,  True,  False, "**取得失敗。無いと同じ扱いにしない**"),
]


def main() -> int:
    if not BIN.exists():
        print(f"SKIP: {BIN} が無い")
        return 0
    mod = _load()
    ok = True
    for branch, verdict, has_pr, want_show, may_rename, why in CASES:
        show, msg = mod.advise(branch, verdict, has_pr)
        hit = (show == want_show)
        if show:
            hit &= ((RENAME in msg) == may_rename)
        ok &= hit
        pr = {True: "PRあり", False: "PRなし", None: "PR不明"}[has_pr]
        said = "勧める" if (show and RENAME in msg) else ("言うだけ" if show else "黙る")
        print(f"  {'ok  ' if hit else 'FAIL'} {branch:16s} {verdict:8s} {pr:6s} -> {said}")
        if not hit:
            print(f"       期待: {'出す' if want_show else '黙る'}"
                  f" / 切り直し {'可' if may_rename else '不可'}  — {why}")
            print(f"       実際: {msg!r}")
    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: 文面の判定だけを見る。git や gh から実際にどう取れるかは見ない")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
