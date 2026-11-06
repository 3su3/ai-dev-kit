#!/usr/bin/env python3
"""担当の記録と、起こす相手の決め方を検める。

**ここだけは保存する。** 段・PR・忙しさは観測できるので計算で出せるが、
**「どのチームが持っているか」は観測できない**。リーダーの会話の中にしかなく、
`/clear` で消える。

見るのは4つ。

  1. **道具で進められるものだけ起こす。** 人の判断が要るものは起こしても進まない
  2. **担当が分からないものは起こさない。** どの端末へ送るか決められない
  3. **人が要るものは、起こさずに状態だけ変える**（サイドバーで分かるように）
  4. **黙って奪わない。** 2チームが同じチケットを持つと引き渡しが衝突する

1 と 2 を混ぜると、無関係な端末へ本文を流し込むか、誰にも届かない指示を出す。
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import types

TOOL = pathlib.Path(__file__).resolve().parent.parent / "local" / "harness-team"


def _load(path, name="t"):
    ns = types.ModuleType(name)
    ns.__file__ = str(path)
    exec(compile(pathlib.Path(path).read_text(encoding="utf-8"), str(path), "exec"),
         ns.__dict__)
    return ns


def main() -> int:
    if not TOOL.exists():
        print(f"SKIP: {TOOL} が無い（個人層の道具）")
        return 0
    m = _load(TOOL)
    ok = True

    print("== 起こす相手の決め方 ==")
    owners = {"100": "chore/team-a", "200": "chore/team-b"}
    rows = [("道具", 100),   # 担当あり → 起こす
            ("道具", 999),   # 担当なし → 起こさない
            ("人",   200),   # 人が要る → 状態だけ
            ("待ち", 100),   # 働いている → 何もしない
            ("不明", 100)]   # 測れない → 何もしない
    wake, mark, unknown, clear = m.wake_targets(rows, owners)
    for label, got, want in [("起こす", sorted(i for i, _ in wake), [100]),
                             ("状態だけ", sorted(i for i, _ in mark), [200]),
                             ("担当不明", sorted(i for i, _ in unknown), [999]),
                             ("印を戻す", sorted(i for i, _ in clear), [100, 100, 100])]:
        hit = got == want
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} {label}: {got} (期待 {want})")

    print("\n== 待ち・不明は触らない ==")
    touched = {i for i, _ in wake} | {i for i, _ in mark} | {i for i, _ in unknown}
    hit = 100 in touched and len([r for r in rows if r[0] in ("待ち", "不明")]) == 2
    # 「待ち」「不明」の行が wake にも mark にも入っていないこと
    hit = not any(w == "待ち" or w == "不明" for w, i in rows if i in
                  {i for i, _ in wake} and w in ("待ち", "不明"))
    only_tool = all(any(w == "道具" for w, i2 in rows if i2 == i) for i, _ in wake)
    ok &= only_tool
    print(f"  {'ok  ' if only_tool else 'FAIL'} 起こすのは『道具』の行だけ")

    print("\n== 人待ちを抜けたら印を戻すか ==")
    # 戻すのを「道具で進む行」だけにすると、承認のあと実装が走っている間（待ち）に
    # 戻る機会が無く、印が残り続ける。残ると**次に人が要るときに黙る**。
    for who, want, why in [
        ("待ち", True,  "**働いている。人待ちではない → 戻す**"),
        ("不明", True,  "測れないだけで人待ちではない → 戻す"),
        ("道具", True,  "道具で進む → 戻す"),
        ("人",   False, "人待ちのまま → 残す"),
    ]:
        _, _, _, cl = m.wake_targets([(who, 100)], {"100": "chore/team-a"})
        got = bool(cl)
        hit = got is want
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} {who:4s} -> {'戻す' if got else '残す'}  （{why}）")

    print("\n== 同じことを繰り返し言わないか ==")
    # 15分おきに回るので、状態を見ずに伝えると**同じことを1日に何十回も言う**。
    # in-review を「もう伝えた」の印として使う。新しい記録を持たない。
    for status, want, why in [
        (None,          True,  "**状態が分からない。言い漏らすより重複がまし**"),
        ("in-progress", True,  "まだ伝えていない"),
        ("in-review",   False, "**もう伝えた。黙る**"),
        ("todo",        True,  "別の状態なら伝える"),
    ]:
        got = m.should_tell(status)
        hit = got is want
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} status={status!r:14s} -> {'伝える' if got else '黙る'}"
              f"  （{why}）")

    print("\n== 表示が動きと食い違わないか ==")
    # 「伝える」と出しながら送信を飛ばしていた。表示と動きが食い違うと、ログを
    # 数えても当てにならない。
    for team, status, want, why in [
        (None,           None,          "伝えられない", "**担当がいない。相手がいない**"),
        ("chore/team-a", "in-progress", "伝える",       "伝える"),
        ("chore/team-a", "in-review",   "伝え済み",     "もう伝えた"),
    ]:
        got = m.tell_label(team, status)
        hit = got.startswith(want)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} team={str(team):14s} status={str(status):12s}"
              f" -> {got}  （{why}）")

    print("\n== 担当の記録 ==")
    with tempfile.TemporaryDirectory() as d:
        env = dict(os.environ, HARNESS_TEAMS=str(pathlib.Path(d) / "teams.json"))
        # **コミットを1つ作る。** 空のリポジトリだと枝を引けず、実物と形が違う。
        env2 = dict(env, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e",
                    GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e")
        subprocess.run(["git", "init", "-q", "-b", "chore/team-x"], cwd=d,
                       capture_output=True)
        (pathlib.Path(d) / "x.txt").write_text("x\n")
        subprocess.run(["git", "add", "-A"], cwd=d, capture_output=True, env=env2)
        subprocess.run(["git", "commit", "-qm", "i"], cwd=d, capture_output=True, env=env2)

        def run(args):
            return subprocess.run([sys.executable, str(TOOL)] + args, cwd=d,
                                  capture_output=True, text=True, env=env)

        run(["take", "100"])
        got = json.loads((pathlib.Path(d) / "teams.json").read_text())
        hit = got.get("100") == "chore/team-x"
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} take で記録される -> {got}")

        # 別のチームが同じ番号を取ろうとする
        subprocess.run(["git", "checkout", "-q", "-b", "chore/team-y"], cwd=d,
                       capture_output=True)
        r = run(["take", "100"])
        still = json.loads((pathlib.Path(d) / "teams.json").read_text())
        hit = r.returncode != 0 and still.get("100") == "chore/team-x"
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} **黙って奪わない** -> {still}")

        run(["drop", "100"])
        after = json.loads((pathlib.Path(d) / "teams.json").read_text())
        hit = "100" not in after
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} drop で外れる -> {after}")

    print("\n== 読み方を自前で持っていないか ==")
    src = TOOL.read_text(encoding="utf-8")
    for label, cond, why in [
        ("次の判断は harness-next に委ねる", 'nx.next_step(' in src,
         "自前で決めると判定が2箇所になる"),
        ("送りは harness-dispatch に委ねる", "d.deliver(" in src,
         "逐語＋改行の順が2箇所になる"),
        ("待ちの読みも委ねる", "d.read_wait(" in src,
         "時間切れの扱いが2箇所になる"),
    ]:
        ok &= bool(cond)
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        if not cond:
            print(f"       {why}")

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: 決め方と記録だけを見る。実際に起こせるかは見ない")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
