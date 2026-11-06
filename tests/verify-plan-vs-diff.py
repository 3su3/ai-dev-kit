#!/usr/bin/env python3
"""`plan-vs-diff` が、**不完全な材料で確信を持った嘘をつかない**か検める。

この道具は「計画と実装がずれていないか」を出す。ずれていないと言い切れることが
価値なので、**材料が揃っていないのに本文を出すのが一番まずい**。

実際にそうなっていた。未コミットの変更があるとき、警告は出すのに比較は続けており、
**実装済みのものが「計画にあって未実装」として並んだ**。警告は上、本文は下なので、
本文のほうが信じられる。

見るのは4つ。

  1. 未コミットの変更があるとき、既定では**本文を出さずに止まる**
  2. `--include-uncommitted` を付けたときだけ、作業ツリーの変更を数える
  3. **計画そのものは差分から外す**（計画を書けば必ず変わる。毎回並ぶと本物が埋もれる）
  4. 3点比較で取る（`base..HEAD` だと base 側へ入った他人の変更まで数える）
"""
import os
import pathlib
import subprocess
import sys
import tempfile

TOOL = pathlib.Path(__file__).resolve().parent.parent / "bin" / "plan-vs-diff"


def git(args, cwd):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)


def build(d):
    """使い捨てのリポジトリ。base に1コミット、枝に1コミット、作業ツリーに1つ。"""
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e"}
    os.environ.update(env)
    git(["init", "-q", "-b", "main"], d)
    for p in ("a.css", "b.css", "c.css"):
        (pathlib.Path(d) / p).write_text("x\n")
    (pathlib.Path(d) / "plan.md").write_text(
        "# 計画\n\n## 修正対象\n\n- `a.css`\n- `b.css`\n")
    git(["add", "-A"], d); git(["commit", "-qm", "init"], d)
    git(["branch", "-q", "base"], d)
    # 枝でコミット済みの変更を1つ
    (pathlib.Path(d) / "a.css").write_text("y\n")
    git(["commit", "-qam", "a"], d)
    return env


def run(d, *args):
    r = subprocess.run([sys.executable, str(TOOL)] + list(args),
                       cwd=d, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main() -> int:
    if not TOOL.exists():
        print(f"SKIP: {TOOL} が無い")
        return 0
    ok = True
    with tempfile.TemporaryDirectory() as d:
        build(d)
        # 作業ツリーに未コミットの変更（b.css は計画にある / c.css は無い）
        (pathlib.Path(d) / "b.css").write_text("z\n")
        (pathlib.Path(d) / "c.css").write_text("z\n")
        (pathlib.Path(d) / "plan.md").write_text(
            "# 計画\n\n## 修正対象\n\n- `a.css`\n- `b.css`\n\n変更\n")

        print("== 未コミットがあるとき、既定では本文を出さない ==")
        rc, out = run(d, "plan.md", "--base", "base")
        # **本文だけに出る印で測る。** 「計画にあって未実装」は断り文の説明にも
        # 出てくるので、それで測ると自分の警告文に引っかかる。
        no_body = "# 計画 " not in out
        hit = rc != 0 and no_body
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} exit={rc} / 本文を出さない={no_body}")
        if not hit:
            print("   ", out.strip().splitlines()[:3])

        print("\n== --include-uncommitted で作業ツリーを数える ==")
        rc, out = run(d, "plan.md", "--base", "base", "--include-uncommitted")
        has_body = "計画にあって未実装 0 件" in out
        counts_c = "+ c.css" in out
        ok &= has_body and counts_c
        print(f"  {'ok  ' if has_body else 'FAIL'} 未実装 0 件（a も b も済んでいる）")
        print(f"  {'ok  ' if counts_c else 'FAIL'} 計画に無い c.css を出す")

        print("\n== 計画そのものを差分に数えない ==")
        no_plan = "+ plan.md" not in out
        ok &= no_plan
        print(f"  {'ok  ' if no_plan else 'FAIL'} plan.md が『計画に無い変更』に出ない")

        print("\n== 見出しが無い計画も読めるか ==")
        # 雛形（`## 修正対象`）が Kiro に届いていなかった時期の計画は、タスクごとに
        # `**対象**:` を書いている。**読む側を広げた。** 計画側に節を足すと
        # タスクごとの記述と二重持ちになり、古い方が生き残る。
        (pathlib.Path(d) / "plan2.md").write_text(
            "# 計画\n\n## タスク分解\n\n### Task 1\n- **対象**: `a.css`\n\n"
            "### Task 2\n- **対象**: `c.css`\n")
        rc, out = run(d, "plan2.md", "--base", "base", "--include-uncommitted")
        for label, cond in [("対象行から読む", "**対象**: の行 2 本" in out),
                            ("読み方を出力に出す", "計画の読み方" in out),
                            ("a.css を計画に数える", "計画にあって未実装 0 件" in out),
                            ("b.css を巻き込みとして出す", "+ b.css" in out)]:
            ok &= bool(cond)
            print(f"  {'ok  ' if cond else 'FAIL'} {label}")

        print("\n== 名前だけの行を、差分のパスへ結ぶか ==")
        # 結ばないと**同じものが両側に出る**。片方は「未実装」、片方は「巻き込み」で、
        # どちらも嘘になる。
        (pathlib.Path(d) / "sub").mkdir(exist_ok=True)
        (pathlib.Path(d) / "sub" / "deep.css").write_text("z\n")
        (pathlib.Path(d) / "plan3.md").write_text(
            "# 計画\n\n## 修正対象\n\n- `deep.css`\n")
        rc, out = run(d, "plan3.md", "--base", "base", "--include-uncommitted")
        for label, cond in [("両側に出さない",
                             not ("- deep.css" in out and "+ sub/deep.css" in out)),
                            ("結んで未実装にしない", "- deep.css" not in out)]:
            ok &= bool(cond)
            print(f"  {'ok  ' if cond else 'FAIL'} {label}")

        print("\n== 同名が複数あるときは結ばない ==")
        (pathlib.Path(d) / "sub2").mkdir(exist_ok=True)
        (pathlib.Path(d) / "sub2" / "deep.css").write_text("z\n")
        rc, out = run(d, "plan3.md", "--base", "base", "--include-uncommitted")
        cond = "同名が 2 件ある" in out
        ok &= bool(cond)
        print(f"  {'ok  ' if cond else 'FAIL'} 曖昧だったことを出す")

        print("\n== 3点比較か（base 側の変更を数えない）==")
        # base を進めても、こちらの差分件数は変わらないこと
        git(["checkout", "-q", "base"], d)
        (pathlib.Path(d) / "other.css").write_text("q\n")
        git(["add", "-A"], d); git(["commit", "-qm", "base side"], d)
        git(["checkout", "-q", "main"], d)
        rc2, out2 = run(d, "plan.md", "--base", "base", "--include-uncommitted")
        no_other = "other.css" not in out2
        ok &= no_other
        print(f"  {'ok  ' if no_other else 'FAIL'} base 側だけの other.css を数えない")

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: ファイルの集合だけを見る。中身が計画どおりかは見ない")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
