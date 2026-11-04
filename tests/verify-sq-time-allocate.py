#!/usr/bin/env python3
"""sq-time の `post --total` を検める。**本物の ~/.local/state は触らない。**

勤務として申告する合計と、段ごとの実測は別物。実測（`days`）は触らず、
Redmine へ出す直前だけ比率のまま割り当て直す。**合計は必ず指定値に一致する。**

いちばん効くのは「母集団が欠けたまま配らない」こと。post は登録を終えた
チケットの内訳をローカルから消すため、`days` だけを見ると**その日の残り1件を
合計いっぱいまで膨らませる**。欠けを見るのは `posted` 側。

道具は gitignore された個人層（`local/sq-time`）にある。無ければ飛ばす。
"""
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQ = os.path.join(ROOT, "local", "sq-time")
ok = True

# **道具が無い環境では飛ばす。** `local/*` は gitignore なので CI には存在しない。
# 無いまま走らせると全項目が FAIL になり、**偽の赤**で本物の失敗が埋もれる。
if not os.path.exists(SQ):
    print("SKIP: local/sq-time が無い（個人層。gitignore 配下）。"
          "道具のある環境で走らせること")
    sys.exit(0)

DAY = "2026-01-05"      # 架空の日。実データと重ならない
ISSUES = [90001, 90002, 90003, 90004]
MINUTES = [200, 100, 40, 5]


def check(label, cond, detail=""):
    global ok
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f"  {detail}" if detail else ""))
    ok = ok and cond


def state(days=None, posted=None):
    # **`min` は見られない。** 道具は `until - since` から取り直すので、
    # ここを手で書くと期待値だけが合う**偽の緑**になる（実際に一度やった）
    d = {}
    base = datetime.datetime.fromisoformat(f"{DAY}T10:00:00")
    for issue, mins in zip(ISSUES, MINUTES):
        d[str(issue)] = [{"phase": "実装:作成", "min": mins,
                          "since": base.isoformat(),
                          "until": (base + datetime.timedelta(minutes=mins)).isoformat()}]
    return {"open": {}, "current": {}, "posted": posted or [],
            "days": {DAY: days if days is not None else d}}


def run(st, *args):
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "state.json")
        json.dump(st, open(p, "w"), ensure_ascii=False)
        r = subprocess.run([sys.executable, SQ, "post", "--date", DAY, *args],
                           capture_output=True, text=True,
                           env=dict(os.environ, SQ_TIME_STATE=p,
                                    SQ_TIME_LOG=os.path.join(tmp, "log.jsonl")))
        return r.returncode, r.stdout + r.stderr


def hours(out):
    return [(m.group(1), float(m.group(2)))
            for m in re.finditer(r"#(\d+)\s+([\d.]+)h\s+\[", out)]


print("## 1. 合計は指定値にちょうど一致する")
for total in (8, 7.5, 4, 1.0):
    rc, out = run(state(), "--total", str(total))
    got = hours(out)
    s = sum(h for _, h in got)
    check(f"--total {total} → 合計 {s}h", rc == 0 and abs(s - total) < 1e-9,
          f"{len(got)} 件")

print("\n## 2. 実測の比率を保つ（大きい段が小さい段を下回らない）")
rc, out = run(state(), "--total", "8")
got = dict(hours(out))
order = [got[str(i)] for i in ISSUES]
check("実測の多い順に並ぶ", all(a >= b for a, b in zip(order, order[1:])), str(order))
check("実測 0 分でないチケットが落ちない", all(h > 0 for h in order))

print("\n## 3. 配りきれない合計は失敗させる（黙って合計をずらさない）")
rc, out = run(state(), "--total", "0.5")   # 4件 × 最低 0.25h = 1.0h 要る
check("rc != 0", rc != 0, f"rc={rc}")
check("要る合計を示す", "1.0h" in out and "配れない" in out)

print("\n## 4. 母集団が欠けたまま配らない")
# 4-a 登録済みが混じる。**`days` からは消えているので `posted` を見ないと気づけない**
part = {str(ISSUES[0]): state()["days"][DAY][str(ISSUES[0])]}
rc, out = run(state(days=part, posted=[f"{DAY}:{ISSUES[1]}"]), "--total", "8")
check("登録済みがある日は止まる", rc != 0, f"rc={rc}")
check("どれが欠けたか名指しする", f"#{ISSUES[1]}" in out and "母集団" in out)
check("残り1件を合計いっぱいへ膨らませない", "8.0h  [" not in out)

# 4-b 実測の裏が無い段（手で足した値）が混じる
d = state()["days"][DAY]
d[str(ISSUES[0])].append({"phase": "手で足した段", "min": 30})   # since/until 無し
rc, out = run(state(days=d), "--total", "8")
check("裏の無い段がある日は止まる", rc != 0, f"rc={rc}")
check("どの段かを名指しする", "手で足した段" in out)

print("\n## 5. --total を付けなければ従来どおり（実測の丸め）")
rc, out = run(state())
got = hours(out)
check("rc == 0", rc == 0)
check("按分の注記が付かない", "按分" not in out)
check("丸めた実測が出る", [h for _, h in got] == [3.25, 1.75, 0.75, 0.25],
      str([h for _, h in got]))

print("\n## 6. 按分したことが Redmine 側に残る")
rc, out = run(state(), "--total", "8")
check("実測と合計をコメントに書く",
      "実測 200分を当日合計 8.0h へ按分" in out)

print("\n## 7. 日をまたげば同じチケットでも登録できる（印は日付つき）")
rc, out = run(state(posted=[f"2025-12-31:{i}" for i in ISSUES]))
check("前日の印では飛ばさない", len(hours(out)) == len(ISSUES),
      f"{len(hours(out))} 件")

print("\nすべて PASS" if ok else "\nFAIL あり")
sys.exit(0 if ok else 1)
