#!/usr/bin/env python3
"""harness-reach が、**既定 agent 経由で載るもの**を見分けるか検める。

既定 agent にした部品は、**agent を選ばなくても載る**。これを「選んだときだけ載る」と
報告し続けると、逆向きの嘘になる。嘘の向きが悪い: 設定が戻って実際には載らなくなっても
**表示が変わらない**ので、規約なしで走っていることに気づけない。

見るのは3つ。

  1. 既定 agent が指している部品は `既定:` になる
  2. 既定でない agent しか指していなければ `agent:` のまま
  3. **既定を読めなかったときは `既定:` と言わない**（読めない＝無い、にしない）

3 が無いと、設定ファイルが壊れているだけで「載っている」と報告する。
"""
import importlib.machinery
import importlib.util
import json
import pathlib
import sys
import tempfile

BIN = pathlib.Path(__file__).resolve().parent.parent / "bin" / "harness-reach"


def _load():
    loader = importlib.machinery.SourceFileLoader("harness_reach", str(BIN))
    spec = importlib.util.spec_from_loader("harness_reach", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


# (その部品を指す agent, 既定 agent, 期待, なぜ見るか)
STATUS_CASES = [
    (["harness-impl", "other"], "harness-impl", "既定:harness-impl", "既定が指している。選ばなくても載る"),
    (["harness-impl"],          "other",        "agent:harness-impl", "既定は別。選んだときだけ"),
    (["harness-impl"],          None,           "agent:harness-impl", "**既定を読めない。載ると言わない**"),
    ([],                        "harness-impl", "agent:無し",         "誰も指していない"),
    ([],                        None,           "agent:無し",         "どちらも無い"),
]


def main() -> int:
    if not BIN.exists():
        print(f"SKIP: {BIN} が無い")
        return 0
    mod = _load()
    ok = True

    print("== 載り方の判定 ==")
    for who, default, want, why in STATUS_CASES:
        got = mod.part_status(who, default)
        hit = got == want
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} 指す={who or '[]'} 既定={default!r} -> {got}")
        if not hit:
            print(f"       期待 {want} — {why}")

    print("\n== 既定の読み取り（取れないときに None を返すか）==")
    with tempfile.TemporaryDirectory() as d:
        base = pathlib.Path(d)
        cases = [
            ("正しい設定", json.dumps({mod.DEFAULT_AGENT_KEY: "harness-impl"}), "harness-impl"),
            ("鍵が無い",   json.dumps({"chat.agentEngine": "v3"}),              None),
            ("値が空",     json.dumps({mod.DEFAULT_AGENT_KEY: ""}),             None),
            ("壊れたJSON", "{これはJSONではない",                                None),
        ]
        for label, body, want in cases:
            f = base / f"{label}.json"
            f.write_text(body, encoding="utf-8")
            got = mod.read_default_agent(f)
            hit = got == want
            ok &= hit
            print(f"  {'ok  ' if hit else 'FAIL'} {label:10s} -> {got!r} (期待 {want!r})")
        missing = base / "ここには無い.json"
        got = mod.read_default_agent(missing)
        hit = got is None
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'} ファイル無し -> {got!r} (期待 None)")

    print("\n" + ("すべて PASS" if ok else "FAIL あり"))
    print("NOTE: 載る経路があるかまで。実際に読まれたかは verify-kiro-reach.py --run が測る")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
