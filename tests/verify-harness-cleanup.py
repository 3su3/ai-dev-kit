#!/usr/bin/env python3
"""配り先を変えたとき、古い配布物が消えるかを見る。

**消えないと、steering から外したはずのものが載り続ける。** 画面にも出力にも
出ないので、気づけない。置き場所を変えた 2026-10-21 に実際に残った。

手書きのファイルは消さない。区別は自動生成の印（`harness-sync:begin`）だけ。

偽物の HOME を作って harness-sync をそこへ配らせる。本物の `~/.kiro` は触らない。
"""
import os
import pathlib
import runpy
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SYNC = ROOT / "bin" / "harness-sync"
MARK = "<!-- harness-sync:begin 自動生成。直接編集しない。正本は ~/work/dotfiles -->"


def snapshot(directory):
    if not directory.exists():
        return None
    return tuple((str(p.relative_to(directory)), p.is_dir(),
                  p.read_bytes() if p.is_file() else None, p.stat().st_mtime_ns)
                 for p in sorted(directory.rglob("*")))


def main():
    ok = True
    def check(name, cond, detail=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}{('  ' + detail) if detail and not cond else ''}")
        ok &= cond

    with tempfile.TemporaryDirectory() as tmp:
        home = pathlib.Path(tmp)
        st = home / ".kiro" / "steering"
        st.mkdir(parents=True)

        # (a) 自動生成の印があり、今は配り先でないもの → 消えるべき。
        #     **実在しないスキル名を使う。** 実在するスキル名にすると、どちらを
        #     steering に置くかを変えたときに雛形が合わなくなる（2026-10-21 に起きた）
        stale = st / "zz-retired-skill.md"
        stale.write_text(f"{MARK}\n\n# 配り先から外れた古い配布物\n", encoding="utf-8")
        # (b) 印が無い手書きのもの → 残るべき
        mine = st / "my-own-note.md"
        mine.write_text("# 手で書いたメモ\n\n消えてはいけない。\n", encoding="utf-8")
        # (c) 印があり、今も配り先であるもの → 残る（上書きされる）。
        #     原則は常に steering なので、置き場所を変えても壊れない
        live = st / "00-principles.md"
        live.write_text(f"{MARK}\n\n# 古い中身\n", encoding="utf-8")

        # (d) 自分が作った形の古い agent 定義 → 消えるべき
        ag0 = home / ".kiro" / "agents"
        ag0.mkdir(parents=True)
        (ag0 / "harness-zz-retired.json").write_text('{"name":"harness-zz-retired"}', encoding="utf-8")
        # (e) 他人のもの → 残るべき
        (ag0 / "kirocrew-sample.json").write_text('{"name":"kirocrew-sample"}', encoding="utf-8")

        env = dict(os.environ, HOME=str(home))
        r = subprocess.run([sys.executable, str(SYNC), "--only", "kiro"],
                           capture_output=True, text=True, env=env, timeout=60)
        if r.returncode != 0:
            print(f"!! harness-sync が落ちた: {r.stderr[:400]}", file=sys.stderr)
            return 2

        check("配り先から外れた自動生成物は消える", not stale.exists(),
              "残っている。外したはずのものが載り続ける")
        check("手書きのファイルは消さない", mine.exists(),
              "消えた。印の無いものに触っている")
        check("今も配り先のものは残る", live.exists())
        check("今も配り先のものは中身が更新される",
              live.exists() and "古い中身" not in live.read_text(encoding="utf-8"))
        # 何が harness-parts へ行くかは設定次第なので、**1つ以上あること**を見る
        hp = home / ".kiro" / "harness-parts"
        check("harness-parts へ配られている",
              hp.is_dir() and any(hp.glob("*.md")),
              "1本も無い。常時読みに全部入っている可能性がある")
        # `or not ...is_dir()` のような逃げ道を置かない。無ければ FAIL でよい
        # （置き場が無いなら作るのが harness-sync の仕事）
        ag = home / ".kiro" / "agents"
        check("配り先から外れた agent 定義も消える",
              not (ag / "harness-zz-retired.json").exists(),
              "残っている。存在しないファイルを指す agent が生き続ける")
        check("自分のものでない agent は消さない",
              (ag / "kirocrew-sample.json").exists(),
              "harness-* 以外に触っている")
        check("agent 定義が配られている",
              ag.is_dir() and any(ag.glob("harness-*.json")),
              "~/.kiro/agents が無いと黙って飛ばされる")

        # (f) 指されていない harness-parts を警告するか。**警告が出ることを確かめる。**
        #     出ない方向だけ見ると、検査が壊れていても気づけない
        orphan = home / ".kiro" / "harness-parts" / "zz-orphan-probe.md"
        orphan.write_text("# 孤児\n", encoding="utf-8")
        r2 = subprocess.run([sys.executable, str(SYNC), "--only", "kiro"],
                            capture_output=True, text=True, env=env, timeout=60)
        check("指されていない harness-parts を警告する",
              "zz-orphan-probe.md" in r2.stderr,
              "警告が出ない。載らないものが黙って残る")
        orphan.unlink()
        r3 = subprocess.run([sys.executable, str(SYNC), "--only", "kiro"],
                            capture_output=True, text=True, env=env, timeout=60)
        check("指されているものは警告しない", "警告" not in r3.stderr,
              "常に警告している。無視されるようになる")

    with tempfile.TemporaryDirectory() as tmp:
        home = pathlib.Path(tmp)
        codex = home / ".codex"
        codex.mkdir()
        agents = codex / "AGENTS.md"
        agents.write_text(f"手書き前\n{MARK}\n\n# 古い生成物\n"
                          "<!-- harness-sync:end -->\n手書き後\n", encoding="utf-8")
        kiro = home / ".kiro"
        kiro.mkdir()
        ns = runpy.run_path(str(SYNC))
        ns["targets"].__globals__["HOME"] = home
        kiro_targets = tuple(ns["targets"]("kiro"))
        for p in kiro_targets:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('{"name":"generated"}' if p.suffix == ".json"
                         else f"{MARK}\n\n# 古い生成物\n", encoding="utf-8")
        for parent in {p.parent for p in kiro_targets}:
            is_json = any(p.parent == parent and p.suffix == ".json"
                          for p in kiro_targets)
            stale = parent / ("harness-zz-retired.json" if is_json else "zz-retired.md")
            stale.write_text('{"name":"retired"}' if is_json
                             else f"{MARK}\n\n# 古い配布物\n", encoding="utf-8")
        (kiro / "steering" / "my-own-note.md").write_text("# 手書き\n", encoding="utf-8")
        before = snapshot(kiro)
        env = dict(os.environ, HOME=str(home))
        r = subprocess.run([sys.executable, str(SYNC), "--only", "codex"],
                           capture_output=True, text=True, env=env, timeout=60)
        check("--only codex が成功する", r.returncode == 0, r.stderr[:400])
        check("Kiro の対象外ファイルは存在・内容・更新時刻が不変",
              bool(kiro_targets) and before == snapshot(kiro))
        check("--only codex で Kiro orphan 警告が出ない",
              "警告:" not in r.stderr)
        content = agents.read_text(encoding="utf-8")
        check("Codex の生成ブロックは更新され、手書き部分は残る",
              content.startswith("手書き前\n") and content.endswith("手書き後\n")
              and "# 古い生成物" not in content)

    with tempfile.TemporaryDirectory() as tmp:
        home = pathlib.Path(tmp)
        codex = home / ".codex"
        codex.mkdir()
        agents = codex / "AGENTS.md"
        agents.write_text(f"手書き前\n{MARK}\n\n# 古い生成物\n"
                          "<!-- harness-sync:end -->\n手書き後\n", encoding="utf-8")
        (home / ".kiro" / "steering").mkdir(parents=True)
        before = snapshot(codex)
        env = dict(os.environ, HOME=str(home))
        r = subprocess.run([sys.executable, str(SYNC), "--only", "kiro"],
                           capture_output=True, text=True, env=env, timeout=60)
        check("--only kiro が成功する", r.returncode == 0, r.stderr[:400])
        check("手書き部分を含む Codex AGENTS.md は存在・内容・更新時刻が不変",
              before == snapshot(codex))
        check("Kiro の配布は行われる",
              (home / ".kiro" / "steering" / "00-principles.md").is_file())

    for only, target, outside in (
            ("codex", ".codex/AGENTS.md", ".kiro"),
            ("kiro", ".kiro/steering/00-principles.md", ".codex")):
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            (home / (".codex" if only == "codex" else ".kiro/steering")).mkdir(
                parents=True)
            env = dict(os.environ, HOME=str(home))
            r = subprocess.run([sys.executable, str(SYNC), "--only", only],
                               capture_output=True, text=True, env=env, timeout=60)
            check(f"--only {only}: 対象外ディレクトリが無くても成功する",
                  r.returncode == 0 and (home / target).is_file()
                  and not (home / outside).exists(), r.stderr[:400])

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: 偽物の HOME で見ている。本物の ~/.kiro は触っていない")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
