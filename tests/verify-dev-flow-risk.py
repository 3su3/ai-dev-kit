#!/usr/bin/env python3
"""Static dev-flow policy regression checks. Run: python3 tests/verify-dev-flow-risk.py"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "claude/skills/dev-flow"
NAMES = ("SKILL.md", "leader.md", "implementer.md", "workflow.md", "risk-policy.md", "plan-template.md", "plan-review.md")

def validate(docs):
    errors = []
    for name in NAMES:
        if name not in docs:
            errors.append(f"missing {name}")
    if errors:
        return errors
    referenced = {
        name
        for line in docs["SKILL.md"].splitlines() if line.startswith("|")
        for name in re.findall(r"`([\w-]+\.md)`", line)
    }
    for name in referenced:
        if name not in docs:
            errors.append(f"missing {name}")
    if errors:
        return errors
    if "- plan.md\n" in docs["leader.md"] or "必ずテンプレートから成果物を作成してください" in docs["leader.md"]:
        errors.append("leader requires full plan for every change")
    if "軽微" not in docs["leader.md"] or "通常・高リスク" not in docs["leader.md"]:
        errors.append("leader lacks risk-based plan")
    if "## plan.md の再読" in docs["implementer.md"] or "plan.md に従ってテスト" in docs["implementer.md"]:
        errors.append("implementer has stale unconditional plan")
    if "テスト成功 / Lint 成功 / 静的解析成功" in docs["SKILL.md"]:
        errors.append("skill has contradictory completion rule")
    for name in ("SKILL.md", "implementer.md", "workflow.md"):
        if "risk-policy.md" not in docs[name]:
            errors.append(f"{name} does not reference policy")
    # 実機での確認が段として存在すること。段が無いと「順番を飛ばした」と判断できない
    # （2026-10-26 に実際に飛ばされた）。**どの順かは決めない** — 対象リポジトリの
    # 規約と計画で決まる流儀であって、普遍ではない（反映してからレビューする運用もある）。
    if "実機での確認" not in docs["SKILL.md"]:
        errors.append("SKILL.md lacks a stage for real-environment checks")
    # 順序を勝手に前後させないこと。ここが普遍の部分
    if "決まっている順番を、自分の判断で前後させない" not in docs["SKILL.md"]:
        errors.append("SKILL.md lacks stop line for reordering stages")
    # 「聞かない」だけだと、選択肢として出す形で回避される
    for name in ("SKILL.md", "implementer.md"):
        if "選べる形で提案しない" not in docs[name] and "選択肢としても出さない" not in docs[name]:
            errors.append(f"{name} allows offering later stages as a choice")
    # 順番が決まっていないときに、自分で決めて進めないこと
    if "順番が決まっていないなら、決めてもらう" not in docs["implementer.md"]:
        errors.append("implementer may invent the order itself")
    # **「出すのは N つだけ」と、他の文書が「出せ」と言うものが食い違わないこと。**
    # 2026-10-27 に2回続けて食い違った（判定が割れた根拠 / 何人で見たか）。
    # 別の回に別の文書へ足すと、矛盾が見えない。
    rd = ROOT.parent / "review-discipline"
    sel = (rd / "selection.md").read_text(encoding="utf-8")
    cross = (rd / "cross-review.md").read_text(encoding="utf-8")
    import re as _re
    m = _re.search(r"出すのはこの(\d+)つだけ", sel)
    if not m:
        errors.append("selection.md lacks the fixed-section count")
    else:
        rows = _re.findall(r"^\| \d+ \| ", sel, _re.M)
        if len(rows) != int(m.group(1)):
            errors.append(f"selection.md says {m.group(1)} sections but lists {len(rows)}")
    # cross-review が「書け」と言うものは、selection の一覧か例外に現れること
    for phrase, where in (("判定した理由を書く", "何人で見たか"),
                          ("判定が割れたら", "判定が割れた")):
        if phrase in cross and where not in sel:
            errors.append(f"cross-review says '{phrase}' but selection.md has no slot for it")

    # **①層と②層で同じ主張を2箇所に持たないこと。** 原則「主張・観点・規約は1箇所に置く」
    # に自分で違反していた（2026-10-26 に発見）。2箇所にあると古い方が生き残る。
    principles = (ROOT.parents[1] / "principles.md").read_text(encoding="utf-8")
    rd = (ROOT.parent / "review-discipline" / "SKILL.md").read_text(encoding="utf-8")
    if "ケースを足さず主張を狭めるか解き方を変える" in principles \
            and "判定の根拠そのものを差し替える" in rd:
        errors.append("principles and review-discipline both state the 3-strikes rule")
    # ai-dev-kit 自体の貢献規則は、常時読みの①層へ置かない（採用した人には無意味）
    if "ai-dev-kit" in principles:
        errors.append("principles references this repo's own contribution rules")

    # **順序そのものを普遍として書いていないこと。** 流儀は local/preferences.md へ
    if "レビューを経てから" in docs["SKILL.md"] or "5 が通ってから" in docs["SKILL.md"]:
        errors.append("SKILL.md hardcodes one team's ordering as universal")
    for phrase in ("承認権限を付与・省略するものではない", "リポジトリが要求する承認は省略不可",
                   "実装前のHuman承認", "停止してHumanに確認"):
        if phrase not in docs["risk-policy.md"]:
            errors.append(f"policy missing invariant: {phrase}")
    if "必要な計画または承認を確認できない場合は作業を開始してはいけません" not in docs["implementer.md"]:
        errors.append("implementer missing approval stop")
    template = docs["plan-template.md"]
    if "- [ ] テストが追加されている" in template or "- [ ] Lint が成功している" in template:
        errors.append("plan template has unconditional verification checklist")
    if "未実行・利用不可" not in template or "承認欄への記入だけでは承認とみなさない" not in template:
        errors.append("plan template lacks verification and approval safeguards")
    for name in ("SKILL.md", "leader.md", "implementer.md", "workflow.md", "risk-policy.md"):
        if "リポジトリ" not in docs[name]:
            errors.append(f"{name} lacks repository-specific rules")
    if "勝手に規約やディレクトリを新設しない" not in docs["risk-policy.md"]:
        errors.append("policy allows invented project conventions")
    if "Journalを共通ハーネスだけの判断で一律に必須化しない" not in docs["risk-policy.md"]:
        errors.append("policy forces journal universally")
    for name in ("SKILL.md", "leader.md", "implementer.md", "workflow.md", "risk-policy.md", "plan-template.md"):
        if "plan-review.md" not in docs[name]:
            errors.append(f"{name} does not link Plan review procedure")
    review = docs["plan-review.md"]
    for phrase in (
        "Human 自身が Plan をレビューする場合",
        "Draft PR は推奨候補であり必須ではない",
        "Plan レビュー用の Draft PR がある場合は、原則として同じ PR で実装と実装レビューを続ける",
        "対象リポジトリの規則や Human の指示が優先される",
        "別の PR が必要な場合は、作成前に理由と PR の関係を明示する",
        "Draft PR を作ること自体は必須ではない",
        "安全な共有先がない場合",
        "commit SHA など変更されない版識別子",
        "旧版への LGTM を新版へ流用しない",
        "レビュー AI が該当版と対応を再確認",
        "実装 AI の対応済み申告だけでは完了しない",
        "再確認できない場合は未確認",
        "Human の判断は AI レビュー完了と別に記録",
        "AI の LGTM は Human の実装承認ではない",
    ):
        if phrase not in review:
            errors.append(f"Plan review procedure missing: {phrase}")
    return errors

def main():
    docs = {path.name: path.read_text(encoding="utf-8") for path in ROOT.glob("*.md")}
    errors = validate(docs)
    assert not errors, "\n".join(errors)
    mutations = (
        ("risk-policy.md", "リポジトリが要求する承認は省略不可"),
        ("risk-policy.md", "実装前のHuman承認"),
        ("implementer.md", "必要な計画または承認を確認できない場合は作業を開始してはいけません"),
        ("plan-template.md", "承認欄への記入だけでは承認とみなさない"),
        ("risk-policy.md", "勝手に規約やディレクトリを新設しない"),
        ("plan-review.md", "旧版への LGTM を新版へ流用しない"),
        ("plan-review.md", "Human の判断は AI レビュー完了と別に記録"),
        ("plan-review.md", "原則として同じ PR で実装と実装レビューを続ける"),
        ("implementer.md", "plan-review.md"),
    )
    for name, phrase in mutations:
        assert phrase in docs[name], f"mutation target missing: {name}"
        mutated = dict(docs)
        mutated[name] = mutated[name].replace(phrase, "")
        assert validate(mutated), f"false green: {name} / {phrase}"
    for name in NAMES:
        mutated = dict(docs)
        del mutated[name]
        if name != "SKILL.md":
            mutated["SKILL.md"] = mutated["SKILL.md"].replace(f"`{name}`", "")
        assert validate(mutated) == [f"missing {name}"], f"missing-file check failed: {name}"
    print(f"PASS: dev-flow static consistency and {len(mutations) + len(NAMES)} negative controls")
    print("NOTE: does not verify real agent behavior")

if __name__ == "__main__":
    main()
