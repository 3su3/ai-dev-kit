"""スキルが発火するかを1プロンプトで探る探針。テストではない。

使い方: python3 tests/probe-skill-firing.py "<プロンプト>" [秒]
引数なしで走らせた場合は SKIP（tests/*.py の一括実行で NG に見えないように）。
"""
import json, subprocess, sys

if len(sys.argv) < 2:
    print("SKIP: 探針。プロンプトを引数で渡す  例: probe-skill-firing.py \'実装して\'")
    sys.exit(0)

prompt = sys.argv[1]
TIMEOUT = int(sys.argv[2]) if len(sys.argv) > 2 else 900
try:
    r = subprocess.run(
    ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
     "--allowed-tools", "Skill", "--disallowed-tools", "Bash,Edit,Write,Agent"],
        capture_output=True, text=True, timeout=TIMEOUT)
except subprocess.TimeoutExpired:
    print(f"発火したツール: !! タイムアウト（{TIMEOUT}秒）。測定は成立していない")
    sys.exit(2)
except OSError as e:
    # claude が PATH に無い等。ここで落とさないと「発火なし」と区別が付かない
    print(f"発火したツール: !! claude を起動できない: {e}")
    sys.exit(2)
lines = [l for l in r.stdout.splitlines() if l.strip()]
if r.returncode != 0 or not lines:
    # 失敗を「発火なし」と同じ顔で出さない。必ずこの行を出して落ちる。
    print(f"発火したツール: !! 測定が成立していない rc={r.returncode} lines={len(lines)}")
    print(f"  stderr: {r.stderr[:600]}")
    sys.exit(2)
fired, sawinit, text = [], False, []
for l in lines:
    try: ev = json.loads(l)
    except Exception: continue
    if ev.get("type") == "system" and ev.get("subtype") == "init":
        sawinit = True
    msg = ev.get("message") or {}
    if not isinstance(msg, dict): msg = {}
    cont = msg.get("content") or []
    if not isinstance(cont, list): cont = []
    for b in cont:
        if isinstance(b, dict):
            if b.get("type") == "tool_use":
                fired.append((b.get("name"), (b.get("input") or {}).get("skill")))
            if b.get("type") == "text":
                text.append(b["text"])
if not sawinit:
    sys.exit("!! init イベントが無い。セッションが立ち上がっていない")
print(f"  セッション成立: yes (イベント {len(lines)} 件)")
print(f"  発火したツール: {fired or '—'}")
print(f"  応答冒頭      : {(' '.join(text))[:160]!r}")
