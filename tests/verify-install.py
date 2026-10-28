#!/usr/bin/env python3
"""導入が AI に伝わる状態かを、**実際に隔離した HOME へ入れて**確かめる。

`tests/` の他の検査は「配る内容」が正しいかを見る静的な検査で、
**まっさらな HOME・未導入でも全部 PASS する**（2026-10-28 に実測）。
ここだけは使い捨ての HOME を作って `install.sh` を流し、
ディスクに何が届いたかを見る。

本物の `~/.claude` `~/.kiro` `~/.codex` には触らない。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

ok = True


def check(name, cond, detail=""):
    global ok
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{('  ' + detail) if detail and not cond else ''}")
    ok &= bool(cond)


def run(cmd, home, cwd):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)


def main():
    global ok

    print("\n## 1. AI の入口がある")
    # 入口が無いと、エージェントはこのリポジトリに入った時点で読むものが無い。
    # **配布の仕組みを持つキット自身が、自分には配っていない**状態だった。
    for f in ("AGENTS.md", "CLAUDE.md", "README.md"):
        check(f"{f} がある", (REPO / f).is_file())
    entry = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    check("入口が install.sh を指している", "./install.sh" in entry)
    check("入口が --verify を指している", "--verify" in entry)
    # **本文を複製しない。** 複製すると必ず古い方が生き残る。
    claude_md = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    check("CLAUDE.md は参照だけ（本文を複製していない）",
          len(claude_md) < 400 and "AGENTS.md" in claude_md,
          f"{len(claude_md)} 字")

    print("\n## 1b. README の検証一覧が実態と合っている")
    # **一覧を手で保たない。** #53 と #54 で足した2本が載っていなかった
    # （2026-10-28 に発見）。足した本人が気づけない形は、検査で止める。
    listed = {m.group(1) for m in re.finditer(r"python3 tests/([\w.-]+)",
                                              (REPO / "README.md").read_text(encoding="utf-8"))}
    actual = {f.name for f in (REPO / "tests").iterdir()
              if f.is_file() and f.name.startswith(("verify-", "probe-"))}
    check("README の一覧 = tests/ の実体", listed == actual,
          f"README だけ={sorted(listed - actual)} / 実体だけ={sorted(actual - listed)}")

    print("\n## 2. 壊れた行を作る手順が残っていない")
    # 非 git のコピーで `git rev-parse --show-toplevel` は空になり、
    # `@/claude/principles.md` を終了コード 0 で出す。
    # 取得失敗と正常が同じ顔になる出力。
    for rel in ("README.md", "local/example.md"):
        # **コードブロックの中だけを見る。** 散文で「これを使うな」と書いた行まで
        # 咎めると、禁止を明記するほど赤くなる（2026-10-28 に自分で踏んだ）
        hits, infence = [], False
        for ln in (REPO / rel).read_text(encoding="utf-8").splitlines():
            if ln.lstrip().startswith("```"):
                infence = not infence
                continue
            if infence and "git rev-parse --show-toplevel" in ln:
                hits.append(ln)
        check(f"{rel}: 手順としてパスを組み立てさせていない", not hits,
              f"{len(hits)} 行: {hits[:1]}")

    tmp = Path(tempfile.mkdtemp(prefix="kit-install-"))
    try:
        kit = tmp / "kit"
        kit.mkdir()
        # **作業ツリーの中身で試す。** `git archive HEAD` だと未コミットの変更が
        # 試されず、直した直後に古いコードを測ることになる（2026-10-28 に踏んだ）。
        # 追跡対象だけを写すので、gitignore された local/ terms/ は入らない
        # ＝新規利用者の手元と同じ状態になる。`.git` も写らない。
        tracked = subprocess.run(["git", "ls-files", "-z"], cwd=REPO,
                                 check=True, capture_output=True).stdout.split(b"\0")
        for rel in (x.decode() for x in tracked if x):
            src = REPO / rel
            if not src.is_file():
                continue
            dst = kit / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        check("非 git のコピーを作れた", not (kit / ".git").exists())
        check("gitignore された層は入っていない（新規利用者と同じ）",
              not (kit / "local" / "preferences.md").exists())

        print("\n## 3. まっさらな HOME へ入れる")
        home = tmp / "home"
        home.mkdir()
        r = run(["./install.sh"], home, kit)
        check("install.sh が成功する", r.returncode == 0, r.stderr[-300:])
        out = r.stdout + r.stderr
        check("~/.claude/skills が張られた", (home / ".claude" / "skills").is_symlink())
        check("張り先がキットを指している",
              (home / ".claude" / "skills").resolve() == (kit / "claude" / "skills").resolve())
        # **import 行を表示している。** 自分で組み立てさせない
        line = [ln for ln in out.splitlines() if "claude/principles.md" in ln]
        check("import 行を表示している", bool(line), out[-300:])
        # **壊れた行を出していない。** repo_root が空だと `@/claude/...` になる
        check("表示された行が壊れていない",
              all("@/claude/" not in ln for ln in line), str(line))
        check("表示された行のファイルが実在する",
              bool(line) and Path(line[0].strip().lstrip("@").replace("\\ ", " ")).is_file(),
              str(line))
        # **導入が1本道になっている。** 面ごとの配布が別の節に分かれていると
        # 片方しかやらずに終わる
        check("install.sh が他の面にも配っている（harness-sync を呼ぶ）",
              "他の面へ配る" in out)
        check("install.sh が届いたかを見ている（--verify）", "届いたかを見る" in out)

        print("\n## 4. 受け口が無い面は作らない")
        for d in (".kiro", ".codex"):
            check(f"{d} を勝手に作っていない", not (home / d).exists())

        print("\n## 5. dry-run と本番が一致する")
        # 判定より前で分岐していたため、受け口の無い環境で
        # 「7件書く」と言って本番は 7 件とも飛ばしていた
        d = run(["python3", "bin/harness-sync", "--dry-run"], home, kit).stdout
        a = run(["python3", "bin/harness-sync"], home, kit).stdout
        check("dry-run が書くと言う数 = 本番が書く数",
              d.count("[dry-run]") == a.count("[write]"),
              f"dry-run {d.count('[dry-run]')} 件 / 本番 {a.count('[write]')} 件")

        print("\n## 6. 一部だけ入った状態を警告する")
        # ~/.kiro だけあって steering/ が無いと、原則もレビュー規約も届かないのに
        # 実装スキルだけが入る。規約なしで実装が走る形が警告なく成立していた。
        h2 = tmp / "home2"
        (h2 / ".kiro").mkdir(parents=True)
        r2 = run(["python3", "bin/harness-sync"], h2, kit)
        both = r2.stdout.count("[write]") and r2.stdout.count("[skip]")
        check("その状態が本当に起きる（検査の前提）", bool(both),
              f"write {r2.stdout.count('[write]')} / skip {r2.stdout.count('[skip]')}")
        check("一部だけ入ったことを警告する", "一部だけ入っている" in r2.stderr,
              r2.stderr[-300:])
        check("届かなかった原則を名指しする", "原則（①層）" in r2.stderr)
        check("直し方を出す（mkdir の行）", "mkdir -p" in r2.stderr)
        check("「その面は未導入」と言っていない", "その面は未導入" not in r2.stdout,
              "判定はファイル単位。面単位の言い方は嘘になる")

        print("\n## 7. --verify はディスクを見る")
        v2 = run(["python3", "bin/harness-sync", "--verify"], h2, kit)
        check("未導入を検出して落ちる", v2.returncode != 0)
        check("原則が届いていないことを言う",
              "原則（①層）が届いていない" in v2.stderr, v2.stderr[-300:])
        # **Kiro が書き換えた後でも、偽の赤を出さないか。**
        # Kiro は agent 定義に kiroUpgrade（revision・フィンガープリント）と
        # permissions を足し、ツール名も書き換える。全文で比べると、流した直後から
        # 毎回「ずれている」と言い続けて警告が意味を失う。
        # こちらが持っているのは resources だけ。
        h3 = tmp / "home3"
        for d in ("steering", "harness-parts", "agents"):
            (h3 / ".kiro" / d).mkdir(parents=True)
        (h3 / ".codex").mkdir()
        run(["python3", "bin/harness-sync"], h3, kit)
        clean = run(["python3", "bin/harness-sync", "--verify"], h3, kit)
        check("全部入った直後は緑（検査の前提）", clean.returncode == 0,
              clean.stdout[-300:])
        j = next((h3 / ".kiro" / "agents").glob("harness-*.json"))
        d = json.loads(j.read_text(encoding="utf-8"))
        d["kiroUpgrade"] = {"revision": 2, "fingerprint": "sha256:" + "0" * 64}
        d["permissions"] = {"rules": [{"capability": "fs_read", "effect": "allow"}]}
        d["tools"] = sorted(d.get("tools", []), reverse=True) + ["todo_list"]
        j.write_text(json.dumps(d, indent=2), encoding="utf-8")
        after = run(["python3", "bin/harness-sync", "--verify"], h3, kit)
        check("Kiro が書き換えた後も緑（偽の赤を出さない）", after.returncode == 0,
              after.stdout[-400:])
        # **指す先が変わったら赤になること。** 上が緩すぎないかの対照
        d["resources"] = ["file://~/.kiro/harness-parts/存在しないもの.md"]
        j.write_text(json.dumps(d, indent=2), encoding="utf-8")
        broken = run(["python3", "bin/harness-sync", "--verify"], h3, kit)
        check("指す先が変わったら赤（上が緩すぎないか）", broken.returncode != 0,
              broken.stdout[-300:])

        # **静的な検査は未導入でも緑になる。** それが --verify を足した理由
        st = run(["python3", "tests/verify-harness-sync.py"], h2, kit)
        check("静的な検査は未導入でも緑（だから --verify が要る）", st.returncode == 0,
              "ここが赤なら、この検査の前提が変わっている")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: 使い捨ての HOME で見ている。本物の環境へ届いたかは "
          "`bin/harness-sync --verify` で見る")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
