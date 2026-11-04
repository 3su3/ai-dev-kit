#!/usr/bin/env python3
"""sq-time の取り込みを検める。**本物の ~/.local/state は触らない。**

いちばん効くのは「同じ往復を別経路から二重に入れない」こと。2026-11-04 に
import 対 import しか見ない鍵で重複排除したため、ライブ hook が既に記録した
往復を取り込み、19 分を水増しした。**重なりは source をまたいで見る。**

道具は gitignore された個人層（`local/sq-time`）にある。無ければ飛ばす。
"""
import datetime
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQ = os.path.join(ROOT, "local", "sq-time")
ok = True


def check(label, cond, detail=""):
    global ok
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f"  {detail}" if detail else ""))
    ok = ok and cond


def dash_line(role, ts, content=None, elapsed_ms=None):
    r = {"role": role, "ts": ts, "source_user": "dashboard"}
    if content is not None:
        r["content"] = content
    if elapsed_ms is not None:
        r["meta"] = {"turn_stats": {"elapsed_ms": elapsed_ms}}
    return json.dumps(r, ensure_ascii=False)


def run(tmp, *args, dash=None):
    env = dict(os.environ,
               SQ_TIME_STATE=os.path.join(tmp, "state.json"),
               SQ_TIME_LOG=os.path.join(tmp, "log.jsonl"))
    if dash:
        env["SQ_TIME_DASH_DIR"] = dash
    return subprocess.run([sys.executable, SQ, *args], capture_output=True, text=True, env=env)


def log_rows(tmp):
    p = os.path.join(tmp, "log.jsonl")
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p) if l.strip()]


def fixture(dash, *turns):
    """turns = [(ts, content, [elapsed_ms, ...]), ...] を1タブへ書く。"""
    os.makedirs(dash, exist_ok=True)
    out = []
    for ts, content, elapsed in turns:
        out.append(dash_line("user", ts, content))
        for i, ms in enumerate(elapsed):
            t = (datetime.datetime.fromisoformat(ts) + datetime.timedelta(seconds=i + 1))
            out.append(dash_line("assistant", t.isoformat(), "…", ms))
    with open(os.path.join(dash, "dashboard_chat-1-1.jsonl"), "w") as f:
        f.write("\n".join(out) + "\n")


print("## 1. 重なりは source をまたいで止める")
with tempfile.TemporaryDirectory() as tmp:
    dash = os.path.join(tmp, "dash")
    fixture(dash, ("2026-11-04T01:00:00+00:00", "#plan 15999", [600000]))  # 10分
    # ライブ記録が先にある（同じ時間帯・同じチケット・別 source）
    with open(os.path.join(tmp, "log.jsonl"), "w") as f:
        base = datetime.datetime.fromisoformat("2026-11-04T01:00:00+00:00").astimezone().replace(tzinfo=None)
        f.write(json.dumps({"issue": 15999, "phase": "実装:作成", "min": 10,
                            "since": base.isoformat(),
                            "until": (base + datetime.timedelta(minutes=10)).isoformat(),
                            "cwd": "/x", "branch": "", "source": "claude"}, ensure_ascii=False) + "\n")
    r = run(tmp, "import-kirocrew", dash=dash)
    rows = log_rows(tmp)
    taken = [e for e in rows if e.get("source") == "kirocrew-dash" and not e.get("suppressed")]
    supp = [e for e in rows if e.get("suppressed")]
    check("重なる区間を取り込まない", len(taken) == 0, f"取り込み {len(taken)} 件")
    check("落とした分はログに残る（suppressed）", len(supp) == 1)
    check("見送りが出力に出る", "見送り" in r.stdout)

print("\n## 2. 重ならなければ取り込む（guard が全部落とすのではない）")
with tempfile.TemporaryDirectory() as tmp:
    dash = os.path.join(tmp, "dash")
    fixture(dash, ("2026-11-04T01:00:00+00:00", "#plan 15999", [600000]))
    r = run(tmp, "import-kirocrew", dash=dash)
    taken = [e for e in log_rows(tmp) if e.get("source") == "kirocrew-dash" and not e.get("suppressed")]
    check("取り込まれる", len(taken) == 1)
    check("区間は elapsed と一致（10分）", taken and taken[0]["min"] == 10,
          f"min={taken[0]['min'] if taken else '-'}")

print("\n## 3. 冪等（2回流して2回目は0件）")
with tempfile.TemporaryDirectory() as tmp:
    dash = os.path.join(tmp, "dash")
    fixture(dash, ("2026-11-04T01:00:00+00:00", "#plan 15999", [600000]))
    run(tmp, "import-kirocrew", dash=dash)
    before = len(log_rows(tmp))
    run(tmp, "import-kirocrew", dash=dash)
    check("2回目で増えない", len(log_rows(tmp)) == before, f"{before} → {len(log_rows(tmp))}")

print("\n## 4. carry-over（素の追質問が同じ段・同じチケットに乗る）")
with tempfile.TemporaryDirectory() as tmp:
    dash = os.path.join(tmp, "dash")
    fixture(dash,
            ("2026-11-04T01:00:00+00:00", "#plan 15999", [60000]),
            ("2026-11-04T02:00:00+00:00", "ここも直して", [120000]))
    run(tmp, "import-kirocrew", dash=dash)
    taken = [e for e in log_rows(tmp) if not e.get("suppressed")]
    check("2区間とも plan:作成 / #15999",
          len(taken) == 2 and all(e["phase"] == "plan:作成" and e["issue"] == 15999 for e in taken),
          f"{[(e['phase'], e['issue']) for e in taken]}")

print("\n## 5. マーカーが無いセッションは0件")
with tempfile.TemporaryDirectory() as tmp:
    dash = os.path.join(tmp, "dash")
    fixture(dash, ("2026-11-04T01:00:00+00:00", "ふつうの相談です", [60000]))
    run(tmp, "import-kirocrew", dash=dash)
    check("取り込み0件", len(log_rows(tmp)) == 0)

print("\n## 6. 180分超は suspect が付き、合計から外れる")
with tempfile.TemporaryDirectory() as tmp:
    dash = os.path.join(tmp, "dash")
    fixture(dash, ("2026-11-04T01:00:00+00:00", "#plan 15999", [200 * 60000]))
    run(tmp, "import-kirocrew", dash=dash)
    taken = [e for e in log_rows(tmp) if not e.get("suppressed")]
    check("suspect が付く", taken and taken[0].get("suspect"), f"{taken[0].get('suspect') if taken else '-'}")
    out = run(tmp, "show").stdout
    check("show が登録を止める", "登録を止める段がある" in out)

print("\n## 7. 実ファイルでマーカーが解ける（fixture ではない）")
real = os.path.expanduser("~/.kiro/crew/sessions")
if not os.path.isdir(real):
    print("  [NOTE] ダッシュボードの記録が無いので確かめられない（PASS ではない）")
else:
    with tempfile.TemporaryDirectory() as tmp:
        r = run(tmp, "import-kirocrew")
        taken = [e for e in log_rows(tmp) if not e.get("suppressed")]
        plans = [e for e in taken if e["phase"].startswith("plan")]
        if not taken:
            print("  [NOTE] 実ファイルに解ける回がまだ無い（#付きの運用が始まってから。PASS ではない）")
        else:
            check("実ファイルから区間が取れる", len(taken) > 0, f"{len(taken)} 件")
            check("elapsed_ms を根拠にしている", "elapsed" in r.stdout)
            if plans:
                check("plan:作成 が解ける", all(e["issue"] for e in plans), f"{len(plans)} 件")

print("\nすべて PASS" if ok else "\nFAIL あり")
print("NOTE: 道具は個人層にある。**実データ依存の項目は、記録が無ければ PASS にしない**")
sys.exit(0 if ok else 1)
