#!/usr/bin/env python3
"""board が「生きているワークツリー」だけを出し、state を勝手に消さないか検める。

board は終わった作業の段を抱え続ける。実測で 27 行中 23 行が、もう存在しない
ワークツリーだった。**「いまどこに居るか」が読めなくなる**ので表示から外す。

ただし**表示から外すことと、記録を消すことは別**。一時的に見えないだけのワークツリー
（外付けを外した・別マシンのパスなど）を、表示のついでに消してはいけない。

見るのは4つ。

  1. 生きている / 消えた の判定
  2. **`prune-board` は `--yes` が無ければ state を変えない**
  3. `--yes` を付けたときだけ落ちる
  4. **番号を引く正規表現を自前で持っていない**（規則を2箇所に置かない）

4 は構造の検査。以前ここだけ `(\\d{4,5})[-_]` を持っていて、要約を付けない枝と
6桁の番号を取りこぼしていた。**同じ規則が2つあると、必ず古い方が生き残る。**
"""
import importlib.machinery
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

TOOL = pathlib.Path(__file__).resolve().parent.parent / "local" / "sq-time"


def _load():
    loader = importlib.machinery.SourceFileLoader("sq_time", str(TOOL))
    spec = importlib.util.spec_from_loader("sq_time", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def main() -> int:
    if not TOOL.exists():
        print(f"SKIP: {TOOL} が無い（個人層の道具。kit だけでは動かない）")
        return 0
    m = _load()
    ok = True

    print("== ワークツリーが生きているか ==")
    with tempfile.TemporaryDirectory() as d:
        base = pathlib.Path(d)
        live = base / "live"; (live / ".git").mkdir(parents=True)
        nogit = base / "nogit"; nogit.mkdir()
        gone = base / "gone"
        for path, want, why in [(live, True, "ディレクトリと .git がある"),
                                (nogit, False, ".git が無い＝ワークツリーではない"),
                                (gone, False, "そもそも無い")]:
            got = m.worktree_alive(str(path))
            hit = got == want
            ok &= hit
            print(f"  {'ok  ' if hit else 'FAIL'} {path.name:6s} -> {got} ({why})")

    print("\n== prune-board は --yes が無ければ消さない ==")
    with tempfile.TemporaryDirectory() as d:
        base = pathlib.Path(d)
        live = base / "live"; (live / ".git").mkdir(parents=True)
        state = base / "state.json"
        seed = {"current": {str(live): {"issue": 20001, "phase": "実装:作成"},
                            str(base / "消えた"): {"issue": 20002, "phase": "plan:作成"}},
                "days": {}, "posted": []}
        env = dict(os.environ, SQ_TIME_STATE=str(state), SQ_TIME_LOG=str(base / "log.jsonl"))

        def run(args):
            return subprocess.run([sys.executable, str(TOOL)] + args,
                                  capture_output=True, text=True, env=env, cwd=str(base))

        def count():
            return len(json.loads(state.read_text())["current"])

        state.write_text(json.dumps(seed))
        run(["prune-board"])
        hit = count() == 2
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} --yes 無し -> {count()} 件 (期待 2。消えていない)")

        run(["prune-board", "--yes"])
        left = json.loads(state.read_text())["current"]
        hit = len(left) == 1 and str(live) in left
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} --yes あり -> {len(left)} 件 "
              f"(期待 1。生きている方だけ残る)")

    print("\n== 番号を引く規則を自前で持っていないか ==")
    src = TOOL.read_text()
    # 「4〜6桁の数字を捕まえる正規表現」が board 側に残っていないこと
    bad = [l for l in src.splitlines()
           if re.search(r"re\.(search|match|compile)\(.*\\d\{4", l)
           and "_M" not in l and "REDMINE_URL" not in l]
    hit = not bad
    ok &= hit
    print(f"  {'ok  ' if hit else 'FAIL'} 自前の番号正規表現 {len(bad)} 件")
    for l in bad[:3]:
        print(f"       {l.strip()[:76]}")

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: 表示と state の扱いだけを見る。Redmine や GitHub の中身は見ない")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
