#!/usr/bin/env python3
"""harness-sync が配る内容を検査する。

見るのは5つ。

  1. Kiro の steering には**常時要るものだけ**が入る（それ以外は入らない）
  2. 頼んだときだけ要るものは `harness-parts/` に本文ごと置かれ、agent の
     `resources` から指される
  3. Kiro へ渡す本文は**埋め込まれ**、同梱ファイルの在処が添えられている
  4. 原則（①層）は埋め込まれている
  5. Kiro 向けに frontmatter が混じらない（付くと規約が届かない）

**1 が一番効く。** 常時読みを増やすと、無関係な指示まで守られなくなることを
2026-10-21 に実測した（詳細は docs/journal/verification-log.md）。steering が太るのを
ここで止める。

**Kiro には本文を埋め込む。** ポインタだけにしたところ Kiro は辿らず一般知識で
答えた（2026-10-19 実測、PR #9）。もっともらしい答えが返るため、到達の有無が
見た目では判別できない。

Codex は AGENTS.md がポインタ方式のまま。**ただし Codex が実際に辿るかは未検証**
なので、ここでは「ポインタが書かれている」ことしか見ていない。
"""
import pathlib
import json
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SYNC = ROOT / "bin" / "harness-sync"
HOME = pathlib.Path.home()
SKILLS = pathlib.Path(__file__).resolve().parent.parent / "claude" / "skills"

# **テスト側が期待を持つ。** harness-sync の KIRO_AGENTS を読むと、設定を変えたとき
# 期待も一緒に変わり、何も検査しなくなる（2026-10-21 に変異を当てて確認済み）。
# 置き場所を変えるときは、ここも手で変える。
EXPECT_ALWAYS = {"review-discipline"}            # steering に置く（使用が最多）
EXPECT_ON_DEMAND = {"dev-flow", "review-response"}  # harness-parts に置く
EXPECT_AGENTS = {"harness-impl": {"dev-flow"},
                 "harness-response": {"review-response"}}

# **既定が「随時」であること。** ここが逆だと、スキルを足した人が何もしなくても
# 常時読みが太る。足した人は自分が枠を使ったことに気づかない。
EXPECT_DEFAULT_ON_DEMAND = True

# 常時読みの上限。**測った崖ではなく、増やさないための歯止め。**
#
# **2026-10-28 に 3850 → 3920 へ上げた。** 初めて上げた。
# それまでは毎回「増やす前に1つ落とす」で払っていた（同日だけで 566 字）。
# 払えるものが尽きたのが理由で、枠が足りないことが分かったからではない。
#
# 上げた分で入れたのは、計画をレビューするときの観点。**Kiro は同梱ファイルを
# 開かないので、常時読みに置かないと届かない**（同日に合言葉で測定済み）。
#
# **次に同じ要求が来たら、上げずに主張を狭める。** 2回上げたら歯止めではない。
STEERING_BUDGET = 3920


def load():
    ns = {"__name__": "_b", "__file__": str(SYNC)}
    exec(compile(SYNC.read_text(encoding="utf-8").split("def main(")[0], str(SYNC), "exec"), ns)
    return ns


def main():
    ns = load()
    skills = ns["skills"]()
    if not skills:
        sys.exit("スキルが1つも読めない。検査が成立しない")
    names = {n for n, _, _ in skills}
    missing = (EXPECT_ALWAYS | EXPECT_ON_DEMAND) - names
    if missing:
        sys.exit(f"期待しているスキルが存在しない: {sorted(missing)}  "
                 f"（スキルを増減したら、このテストの期待も手で直す）")

    ok = True
    def check(name, cond, detail=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}{('  ' + detail) if detail and not cond else ''}")
        ok &= cond

    kiro = ns["targets"]("kiro")
    codex_body = next(iter(ns["targets"]("codex").values()))
    ST = HOME / ".kiro" / "steering"
    HP = HOME / ".kiro" / "harness-parts"
    AG = HOME / ".kiro" / "agents"

    print("\n## 1. steering には常時要るものだけ")
    in_steering = {p.stem for p in kiro if p.parent == ST} - {"00-principles"}
    check("steering の中身が期待どおり", in_steering == EXPECT_ALWAYS,
          f"期待={sorted(EXPECT_ALWAYS)} 実際={sorted(in_steering)}")
    for n in EXPECT_ON_DEMAND:
        check(f"steering に {n} が居ない", (ST / f"{n}.md") not in kiro,
              "常時読みに戻っている")
    # **実際に置かれる中身で数える。** 本文だけだと包みのコメント分が落ちて、
    # 上限の判定が甘くなる（2026-10-21 に 180 字ぶん甘く出ていた）。
    total = sum(len(ns["wrap"](b)) for p, b in kiro.items() if p.parent == ST)
    check(f"常時読みが {STEERING_BUDGET} 字以内", total <= STEERING_BUDGET,
          f"実際 {total} 字。増やす前に1つ落とす（①層）")
    print(f"       常時読み {total} 字 / 上限 {STEERING_BUDGET} 字")

    # **常時読みに「いつ読むか」を入れない。** 発火させる対象が無い
    # （steering は必ず読まれる）。随時のものには要る。
    for q, b in kiro.items():
        if q.parent == ST and q.stem != "00-principles":
            check(f"steering の {q.stem} に「いつ読むか」が無い",
                  "**いつ読むか:**" not in b, "発火用の文は常時読みでは枠の無駄")
    for n in EXPECT_ON_DEMAND:
        b = kiro.get(HP / f"{n}.md", "")
        check(f"harness-parts の {n} には「いつ読むか」がある", "**いつ読むか:**" in b)

    # **出す形は常時読みに置く。** 同梱ファイルは Kiro では開かれない。
    # ポインタ（1周目）でも「読む」という命令（2周目）でも開かなかった
    # （2026-10-28、合言葉＋陰性対照で測定）。3周目は解き方を変えて畳んだ。
    rd = next((b for q, b in kiro.items()
               if q.parent == ST and q.stem == "review-discipline"), "")
    for must in ("何人で見たか", "1件1行", "裏どり済み・問題なし", "未実行も書く",
                 "レビュー: 単独", "3件以下"):
        check(f"steering に出す形がある: {must}", must in rd)

    # **同じ表が2箇所になった。** 片方が古くなるのを止める。
    def items(text, pat):
        # **re.M が要る。** 無いと両方が空集合になり、「空 == 空」で緑になる
        # （2026-10-28 に書いた。件数も見ているのでそこで止まった）
        return [m.group(1) for m in re.finditer(pat, text, re.M)]
    # **6つの節だけを見る。** 出し方の 1./2. を拾うと数が合わなくなる
    sec = rd.split("出すのはこの6つだけ", 1)[-1].split("```", 1)[0]
    inline = items(sec, r"^\d\. \*\*(.+?)\*\*")
    sel = (SKILLS / "review-discipline" / "selection.md").read_text(encoding="utf-8")
    table = items(sel, r"^\| \d \| \*\*(.+?)\*\*")
    check("steering の6項目 = selection.md の6項目", inline == table and len(table) == 6,
          f"steering={inline} / selection.md={table}")

    print("\n## 2. 頼んだときだけのものは harness-parts と agent 定義にある")
    for n in EXPECT_ON_DEMAND:
        check(f"harness-parts に {n} がある", (HP / f"{n}.md") in kiro)
    for agent, members in EXPECT_AGENTS.items():
        path = AG / f"{agent}.json"
        if path not in kiro:
            check(f"agent {agent} が生成される", False, "定義が無い")
            continue
        cfg = json.loads(kiro[path])
        res = set(cfg.get("resources") or [])
        want = {f"file://~/.kiro/harness-parts/{n}.md" for n in members}
        check(f"agent {agent} の resources が期待どおり", res == want,
              f"期待={sorted(want)} 実際={sorted(res)}")
        # steering は無条件に載るので、指しても無意味。指していたら設計の取り違え
        check(f"agent {agent} が steering を指していない",
              not any("steering" in r for r in res))

    print("\n## 3. Kiro へ渡す本文は埋め込まれ、同梱ファイルの在処が添えられている")
    for name, desc, body in skills:
        marker = next((l.strip() for l in body.splitlines()
                       if len(l.strip()) > 25 and not l.startswith("#")), None)
        if marker is None:
            continue
        path = (HP if name in EXPECT_ON_DEMAND else ST) / f"{name}.md"
        f = kiro.get(path)
        if f is None:
            check(f"kiro/{name}: 配られている", False, f"{path} が無い")
            continue
        check(f"kiro/{name}: 本文が埋め込まれている", marker in f,
              "本文が消えている（ポインタだけでは Kiro は辿らない）")
        check(f"kiro/{name}: 同梱ファイルの在処が添えられている",
              str(ROOT / "claude" / "skills" / name) in f)
        check(f"codex: {name} のポインタが書かれている",
              str(ROOT / "claude" / "skills" / name / "SKILL.md") in codex_body)

    print("\n## 4. 原則（①層）は埋め込まれている")
    principles = (ROOT / "claude" / "principles.md").read_text(encoding="utf-8")
    pm = next(l.strip() for l in principles.splitlines()
              if len(l.strip()) > 25 and not l.startswith("#"))
    check("kiro: 原則の本文が入っている", pm in kiro[ST / "00-principles.md"])
    check("codex: 原則の本文が入っている", pm in codex_body)

    print("\n## 5. Kiro へ frontmatter が混じらない")
    for path, body in kiro.items():
        if path.suffix != ".md":
            continue
        check(f"kiro/{path.name}: 先頭が frontmatter でない",
              not body.lstrip().startswith("---"))

    print("\n## 6. 新しいスキルは既定で随時へ行く")
    # 実在しない名前を1つ足して、どこへ配られるかを見る。
    # **既定を文章で確かめない。** 実際に足して置き場所を測る
    import types
    probe = "zz-probe-skill"
    orig = ns["skills"]
    ns["skills"] = lambda: orig() + [(probe, "探針", "本文。" + "x" * 40)]
    try:
        k2 = ns["targets"]("kiro")
        in_st = (ST / f"{probe}.md") in k2
        in_hp = (HP / f"{probe}.md") in k2
        has_agent = any(p.name == f"harness-{probe}.json" for p in k2)
        check("足したスキルは steering へ行かない", not in_st,
              "既定が常時になっている。足した人が気づかずに枠を使う")
        check("足したスキルは harness-parts へ行く", in_hp)
        check("足したスキルは自分の agent を持つ", has_agent,
              "どの agent からも指されず、載らないまま気づけない")
    finally:
        ns["skills"] = orig

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: 配る内容の検査であって、各エージェントが実際に読むかは示さない")
    print("      読むかは tests/verify-kiro-reach.py --run で測る")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
