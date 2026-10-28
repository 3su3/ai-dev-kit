#!/usr/bin/env python3
"""review-discipline の静的な整合。接頭辞の綴りと、取り違えやすい記述を見る。

指摘の接頭辞が `[issue]` 形式で1つに揃っているか。

**`issue:` 形式はふつうの文章と衝突する。** あるリポジトリの .md 全体で、
レビュー指摘が1件も無いのに 22 件が誤検出された（「GitHub issue:」「親 issue:」
「対象 issue:」等）。行頭に縛っても `- issue: path` の形で素通りする。
`[issue]` 形式は同じ母集団で 0 件だった（2026-10-28 に測定）。

**綴りがぶれると、遵守を測る判別子が弱くなる。** 分子に誤検出が混じり、
接頭辞を忘れた回と区別がつかなくなる。
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vocabulary import prefixes   # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent / "claude" / "skills" / "review-discipline"
# **接頭辞は SKILL.md の表が正本。** ここで打ち直さない（2026-10-28 に3回外した）
WORDS = prefixes()

ok = True


def check(name, cond, detail=""):
    global ok
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{('  ' + detail) if detail and not cond else ''}")
    ok &= bool(cond)


def main():
    files = sorted(SKILL_DIR.glob("*.md"))
    if not files:
        sys.exit(f"スキルが読めない: {SKILL_DIR}。検査が成立しない")

    print("\n## コロン形式が残っていない")
    for f in files:
        body = f.read_text(encoding="utf-8")
        hits = re.findall(r"(?<![\w\[])(" + "|".join(WORDS) + r"):(?=\s|`|$)", body)
        check(f"{f.name}", not hits, f"{len(hits)} 件: {hits[:3]}")

    print("\n## markdown のリンクに化ける形が無い")
    # `[issue](...)` はリンクとして描画される。直後に `(` を置かない
    for f in files:
        body = f.read_text(encoding="utf-8")
        hits = re.findall(r"\[(" + "|".join(WORDS) + r")\]\(", body)
        check(f"{f.name}", not hits, f"{hits[:3]}")

    print("\n## 語彙は4語ちょうど")
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    found = re.findall(r"^\| `\[(\w+)\]` \|", skill, re.M)
    check("接頭辞の表が読める", found == list(WORDS) and len(found) >= 3, f"{found}")
    # **複合を作らない。** 実使用で `nit/ask:` が出たことがある（2026-10-28）
    comp = re.findall(r"\[(?:" + "|".join(WORDS) + r")/(?:" + "|".join(WORDS) + r")\]", skill)
    check("複合の接頭辞が定義されていない", not comp, f"{comp[:3]}")

    print("\n## 禁じた見出し語が指示として残っていない")
    # `SKILL.md` は Critical / Warning / Suggestion を禁じている。
    # **「〜とする」「〜を使う」のような指示の形だけを見る。**
    # 語そのものを咎めると、禁止を明記した文（この検査の説明を含む）まで赤くなる。
    for f in files:
        body = f.read_text(encoding="utf-8")
        hits = []
        for ln in body.splitlines():
            m = re.search(r"(Critical|Warning|Suggestion)\s*(とする|にする|を使う|で書く)", ln)
            if not m or "使わない" in ln:
                continue
            # **引用「」の中は指示ではない。** 禁止を説明する文が自分で赤くなる
            # （2026-10-28、この検査を書いた回に踏んだ）
            before, after = ln[:m.start()], ln[m.end():]
            if before.count("「") > before.count("」") and "」" in after:
                continue
            hits.append(ln)
        check(f"{f.name}", not hits, f"{hits[:1]}")

    print("\n## 他のファイルが表に無い語を使っていない")
    for f in files:
        used = {m for m in re.findall(r"`?\[(\w+)\]`?", f.read_text(encoding="utf-8"))}
        # 番号参照（[1] 等）や他の括弧表記は数字で弾く
        unknown = {u for u in used if u.isalpha() and u.islower() and u.isascii()} - set(WORDS)
        check(f"{f.name}", not unknown, f"表に無い: {sorted(unknown)}")

    print("\n## 計画をレビューするときの観点がある")
    # **コードの観点は計画に当たらない。** Null も Transaction も N+1 も、
    # まだ書かれていないものには問えない。2026-10-28 まで、観点の正本が
    # どこにも無かった（checklist.md はコード前提、plan-review.md は運用だけ）。
    pc = SKILL_DIR / "plan-checklist.md"
    check("plan-checklist.md がある", pc.is_file())
    if pc.is_file():
        body = pc.read_text(encoding="utf-8")
        for must in ("比較した案", "どこから来たか", "完了条件", "やらないこと",
                     "取り消す", "釣り合い"):
            check(f"観点がある: {must}", must in body)
        # **運用は dev-flow が持つ。** 両方が相手に投げていた状態へ戻さない
        check("運用は plan-review.md が持つと書いてある", "plan-review.md" in body)
        check("[issue] の線が計画用に定義されている",
              "手戻りが確定" in body)
        check("テストは「未実行」で閉じると書いてある", "未実行" in body)

    # **Kiro は同梱ファイルを開かない。** 観点の名前は常時読みに無いと届かない。
    # **観点の一覧は手で並べない。** 常時読みの行から取って、詳細側と突き合わせる
    # （2026-10-28、手で並べた語が片方にしか無く偽の赤になった）。
    skill_body = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    check("常時読みに計画の観点の行がある", "**計画だけのとき**" in skill_body)
    m = re.search(r"\*\*計画だけのとき\*\*[:：](.+?)（`plan-checklist\.md`）",
                  skill_body, re.S)
    check("観点の一覧を取り出せる", bool(m), "行の形が変わった")
    if m and pc.is_file():
        names = [x.strip() for x in m.group(1).replace("\n", "").split("/") if x.strip()]
        check("観点が 1 つ以上ある", len(names) >= 1, f"{names}")
        for n in names:
            check(f"詳細側にもある: {n}", n in pc.read_text(encoding="utf-8"))
    # **要約の出どころは常時読みに要る。** 要約を書くのもレビューと同じ
    # エージェントで、読み違えると「自信のある誤った要約」が出る。読む人は
    # 不慣れな分野でそれを読むので気づけない。**誤った要約は無いより悪い。**
    check("常時読みに要約がある", "「この PR」の3行から始める" in skill_body)
    check("出どころを書けと言っている", "出どころを書く" in skill_body)
    sel = (SKILL_DIR / "selection.md").read_text(encoding="utf-8")
    check("詳細側に出どころの説明がある", "無いより悪い" in sel)
    check("影響範囲が3行目だと両方に書いてある",
          "影響範囲" in skill_body and "影響範囲" in sel)

    # **要約は件数と関係なく出す。** 候補一覧を飛ばすと要約ごと消えていた
    # （2026-10-28 の実測。4 件を「少ない」と判断して一覧ごと飛ばした）。
    check("要約が候補一覧の外にある", "候補一覧を出さない回も書く" in skill_body)
    check("詳細側にも理由がある", "一覧の外へ出した" in sel)

    for must in ("手戻りが確定", "未実行"):
        check(f"常時読みに届いている: {must}", must in skill_body)

    print("\n## 語彙を正本から取っている")
    # **一致とみなす文字列を手で打ち直さない。** 2026-10-28 に3回外した。
    # 検査も測定も tests/vocabulary.py から取る。
    import vocabulary as voc
    check("接頭辞を SKILL.md から取れる", len(voc.prefixes()) >= 3, f"{voc.prefixes()}")
    # **表記ゆれを許す側も要る。** 実機の出力は規約どおりの形とは限らず、
    # 厳密に探すと「守られている出力」を守られていないと読む
    loose = voc.prefix_pattern(strict=False)
    for sample in ("[issue] a", "issue: a", " 1. issue  a"):
        check(f"ゆれ許容で拾える: {sample!r}", bool(loose.search(sample)))
    # **出どころは構造で拾う。** 言い回しは無限に書ける
    for sample in ("この PR（本文から）: x", "この PR（コードから読み取り): x",
                   "この変更（差分を読んだ私の読み）: x"):
        check(f"出どころを構造で拾える: {sample[:16]!r}",
              bool(voc.summary_source_pattern().search(sample)))

    print("\n## クロスの相手をサブエージェントと取り違えない")
    # **相手は別プロセスの CLI。** 実使用で、Claude が「サブエージェントの起動が
    # 既定で止めてある」を理由にクロスを辞退した（2026-10-28）。禁じられているのは
    # Agent ツールで、シェルから CLI を叩くことではない。止まり方（理由を書く）は
    # 正しかったので、直すのは読みの方。
    cr = (SKILL_DIR / "cross-review.md").read_text(encoding="utf-8")
    check("別プロセスの CLI だと書いてある", "別プロセスの CLI" in cr)
    check("サブエージェントではないと書いてある", "サブエージェントではない" in cr)
    check("制限が当てはまらないと書いてある", "当てはまらない" in cr)

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: 綴りだけを見る。実際にエージェントが付けるかは出力で測る")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
