#!/usr/bin/env python3
"""Kiro CLI に steering が届いているかを、合言葉で確かめる。

「語がセッション記録に出るか」では測れない。載っていても言及しなければ 0 になる
（2026-10-21 にこれで2度誤った）。合言葉を仕込んで直接聞くのが唯一の確かめ方。

LLM を2回呼ぶので既定では走らない。--run を付けたときだけ実行する。
"""
import argparse
import pathlib
import shutil
import random
import string
import subprocess
import sys

# 在処を決め打ちしない。PATH を先に見て、無ければよくある場所を試す
KIRO_CLI = next(
    (p for p in (
        [pathlib.Path(shutil.which("kiro-cli"))] if shutil.which("kiro-cli") else []
    ) + [pathlib.Path.home() / ".local/bin/kiro-cli"] if p.exists()),
    None,
)
STEERING = pathlib.Path.home() / ".kiro/steering/00-principles.md"
TIMEOUT = 180


def ask(prompt: str) -> str:
    """kiro-cli に聞く。ツールは一切渡さない（ファイルを読んで答えられないように）。"""
    try:
        r = subprocess.run(
            [str(KIRO_CLI), "chat", "--trust-tools=", prompt],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"!! kiro-cli を実行できない: {e}", file=sys.stderr)
        sys.exit(2)
    if r.returncode != 0:
        print(f"!! kiro-cli が異常終了 (rc={r.returncode}): {r.stderr[:300]}", file=sys.stderr)
        sys.exit(2)
    return r.stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="実際に kiro-cli を呼ぶ")
    args = ap.parse_args()

    if not args.run:
        print("SKIP: --run を付けると実測する（LLM を2回呼ぶ。1〜2分）")
        return 0
    if KIRO_CLI is None:
        print("SKIP: kiro-cli が見つからない（PATH にも既定の場所にも無い）")
        return 0
    if not STEERING.exists():
        print(f"!! {STEERING} が無い。harness-sync を先に走らせる", file=sys.stderr)
        return 2

    tag = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    word = f"ツウチ{tag}"
    original = STEERING.read_text(encoding="utf-8")
    ng = []

    try:
        head, rest = original.split("\n", 1)
        STEERING.write_text(
            f"{head}\n\n<!-- 疎通確認（一時）: 合言葉は「{word}」 -->\n{rest}",
            encoding="utf-8",
        )

        # 本測定: 合言葉をそのまま言えるか
        got = ask(
            f"常時の指示に書かれている合言葉を、そのまま1語だけ出力してください。"
            f"無ければ NONE とだけ。ファイルは読まないこと。"
        )
        hit = word in got
        print(f"{'OK  ' if hit else 'NG  '} 合言葉を直答: 期待={word} 実際={got[:40]!r}")
        if not hit:
            ng.append("合言葉が返らない")

        # 対照: 仕込んでいない語に yes と言わないか（誘導への追従を切り分ける）
        fake = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        got2 = ask(
            f"常時の指示の中に『ダミー{fake}』という合言葉はありますか。"
            f"yes か no だけ。ファイルは読まないこと。"
        )
        clean = "no" in got2.lower() and "yes" not in got2.lower()
        print(f"{'OK  ' if clean else 'NG  '} 対照で no: 実際={got2[:40]!r}")
        if not clean:
            ng.append("仕込んでいない語にも yes と答える（追従しているだけ）")
    finally:
        STEERING.write_text(original, encoding="utf-8")
        print("     steering を元に戻した")

    if ng:
        print("\n" + "\n".join(f"NG: {m}" for m in ng))
        return 1
    print("\nすべて PASS")
    print("NOTE: 届いたことの確認であって、指示に従うかは示さない")
    print("      従うかは『方針の名指しが出たセッションの割合』で別に測る")
    return 0


if __name__ == "__main__":
    sys.exit(main())
