#!/usr/bin/env python3
"""harness-ticket-of の判定を検査する。

**この道具は「引けなかった」を返すのが仕事**なので、失敗が正常系に紛れやすい。
見るのは4つ。

  1. 実在した穴が塞がっている（`feature/20001` のように要約を付けない形）
  2. 番号が無いのが正しい分（`chore/`）と、引けない分が**混ざらない**
  3. 番号に見えるが番号でないもの（日付・桁数の外）を**推測で通さない**
  4. 道具自身の失敗（引数が壊れている）が unknown と**違う終了コード**になる

4 が無いと、呼ぶ側から「引けなかった」と「道具が動かなかった」が同じ顔になる。
"""
import importlib.machinery
import importlib.util
import pathlib
import subprocess
import types
import sys

BIN = pathlib.Path(__file__).resolve().parent.parent / "bin" / "harness-ticket-of"


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


CASES = [
    # (ブランチ, 期待 verdict, 期待 番号, なぜ見るか)
    ("feature/20001",                     "ticket",  20001, "要約なし。2026-11-06 に実際に落ちていた形"),
    ("feature/20002-order-sync",      "ticket",  20002, "規約どおりの形"),
    ("feature/20002-contract_to_alpha",   "ticket",  20002, "検証環境向けの枝も同じチケット"),
    ("origin/feature/20003-cache-expiry", "ticket",  20003, "リモート名が付いていても引く"),
    ("claude/redmine-20004-front",        "ticket",  20004, "エージェントが切る形"),
    ("chore/findings-note",               "none",    None,  "起票しない変更。番号が無いのが正しい"),
    ("chore/20005-grid-tailwind",         "ticket",  20005, "chore でも番号があれば番号が勝つ"),
    ("someone/weekly-retro-draft",           "unknown", None,  "Orca の既定名。規約外"),
    ("crew/mate/example-app",    "unknown", None,  "他ツールが切る枝"),
    ("feature/123_r1-2_member_id",       "unknown", None,  "3桁は番号帯の外。推測しない"),
    ("feature/2026-11-06-notes",          "unknown", None,  "日付の 2026 を番号と読まない"),
    ("",                                  "unknown", None,  "空は引けない"),
]


def main() -> int:
    if not BIN.exists():
        print(f"SKIP: {BIN} が無い")
        return 0
    mod = _load()
    ok = True

    print("== 判定 ==")
    for branch, want_v, want_n, why in CASES:
        got_v, got_n = mod.resolve(branch)
        hit = (got_v == want_v and got_n == want_n)
        ok &= hit
        mark = "ok  " if hit else "FAIL"
        shown = branch or "(空)"
        print(f"  {mark} {shown:38s} -> {got_v} {got_n if got_n is not None else '-'}")
        if not hit:
            print(f"       期待 {want_v} {want_n} / {why}")

    print("\n== 終了コード（呼ぶ側が3値で分岐できるか）==")
    for branch, want_code, label in [
        ("feature/20002-x", 0, "ticket"),
        ("chore/x",         2, "none"),
        ("someone/x",          3, "unknown"),
    ]:
        r = subprocess.run([sys.executable, str(BIN), branch], capture_output=True, text=True)
        hit = r.returncode == want_code
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} {label:8s} exit={r.returncode} (期待 {want_code})")

    print("\n== 道具自身の失敗が unknown と区別できるか ==")
    r = subprocess.run([sys.executable, str(BIN), "feature/20002-x", "--digits", "abc"],
                       capture_output=True, text=True)
    hit = r.returncode == 1
    ok &= hit
    print(f"  {'ok  ' if hit else 'FAIL'} 壊れた引数 exit={r.returncode} (期待 1 / unknown の 3 ではない)")

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: ブランチ名からの判定だけを見る。その番号のチケットが実在するかは見ない")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
