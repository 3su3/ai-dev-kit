#!/usr/bin/env bash
# 既存ファイルを壊さない。symlink でないものがあれば退避してから張る。
set -euo pipefail
cd "$(dirname "$0")"
SRC="$PWD"

link() {
  local from="$SRC/$1" to="$2"
  if [ -L "$to" ]; then rm "$to"
  elif [ -e "$to" ]; then
    local bak="$to.bak-$(date +%Y%m%d-%H%M%S)"
    echo "退避: $to -> $bak"; mv "$to" "$bak"
  fi
  mkdir -p "$(dirname "$to")"
  ln -s "$from" "$to"
  echo "link : $to -> $from"
}

link claude/skills "$HOME/.claude/skills"

# ~/.claude/CLAUDE.md は symlink にしない。
#   - 同じファイル内の相対 import（`@CLAUDE.ndf.md` 等）の解決先が変わりうる
#   - プラグインが生成・追記する場合があり、上書き合戦になる
# 実ファイルのまま import 行を1行足す。行は README の「導入」に表示方法がある。
echo
echo "次を ~/.claude/CLAUDE.md に追記すると、原則（①層）が常時読まれる:"
printf '  @%s/claude/principles.md\n' "$(printf '%s' "$SRC" | sed 's/ /\\ /g')"
[ -f "local/preferences.md" ] && \
  printf '  @%s/local/preferences.md\n' "$(printf '%s' "$SRC" | sed 's/ /\\ /g')"
echo

case ":$PATH:" in
  *":$SRC/bin:"*) ;;
  *) echo "PATH に $SRC/bin を追加してください" ;;
esac

# **ここまでで入るのは Claude Code の面だけ。** 他の面（Codex / Kiro）は
# harness-sync が配る。導入の手順を2箇所に分けると、片方しかやらずに終わる。
# 受け口が無い面は飛ばすだけなので、入れていないツールがあっても害は無い。
echo
echo "== 他の面へ配る =="
python3 "$SRC/bin/harness-sync" || true

echo
echo "== 届いたかを見る =="
python3 "$SRC/bin/harness-sync" --verify || true
