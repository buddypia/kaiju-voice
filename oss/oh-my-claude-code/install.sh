#!/bin/bash
set -euo pipefail

# oh-my-claude-code installer
# Usage: curl -fsSL https://raw.githubusercontent.com/yourname/oh-my-claude-code/main/install.sh | bash

REPO_URL="https://github.com/yourname/oh-my-claude-code"
BRANCH="main"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${GREEN}[oh-my-claude-code]${NC} $1"; }
warn() { echo -e "${YELLOW}[oh-my-claude-code]${NC} $1"; }
error() { echo -e "${RED}[oh-my-claude-code]${NC} $1" >&2; }

# 1. プロジェクトルート検出
PROJECT_DIR="${1:-.}"
if [ ! -d "$PROJECT_DIR" ]; then
  error "ディレクトリが見つかりません: $PROJECT_DIR"
  exit 1
fi

PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
CLAUDE_DIR="$PROJECT_DIR/.claude"

log "プロジェクト: $PROJECT_DIR"

# 2. 既存 .claude/ のバックアップ
if [ -d "$CLAUDE_DIR" ]; then
  BACKUP_DIR="$CLAUDE_DIR.backup.$(date +%Y%m%d%H%M%S)"
  warn "既存の .claude/ を検出。バックアップ: $BACKUP_DIR"
  cp -r "$CLAUDE_DIR" "$BACKUP_DIR"
fi

# 3. テンポラリにクローン
TMPDIR="$(mktemp -d)"
trap "rm -rf $TMPDIR" EXIT

log "テンプレートをダウンロード中..."
if command -v git &> /dev/null; then
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMPDIR/repo" 2>/dev/null
else
  error "git が必要です。インストールしてください。"
  exit 1
fi

# 4. .claude/ をコピー
log ".claude/ をコピー中..."
mkdir -p "$CLAUDE_DIR"

# ディレクトリ構造を作成
for dir in hooks scripts scripts/lib pipelines skills state; do
  mkdir -p "$CLAUDE_DIR/$dir"
done

# コアファイルをコピー (既存ファイルは上書きしない)
copy_if_new() {
  local src="$1"
  local dst="$2"
  if [ -f "$dst" ]; then
    warn "  スキップ (既存): $(basename "$dst")"
  else
    cp "$src" "$dst"
    log "  コピー: $(basename "$dst")"
  fi
}

# settings.json は特別扱い (既存があればマージが必要)
if [ ! -f "$CLAUDE_DIR/settings.json" ]; then
  cp "$TMPDIR/repo/.claude/settings.json" "$CLAUDE_DIR/settings.json"
  log "  コピー: settings.json"
else
  warn "  既存の settings.json を検出。手動でマージしてください。"
  cp "$TMPDIR/repo/.claude/settings.json" "$CLAUDE_DIR/settings.json.template"
  log "  テンプレート保存: settings.json.template"
fi

# Hooks
for file in "$TMPDIR/repo/.claude/hooks/"*.mjs; do
  [ -f "$file" ] && copy_if_new "$file" "$CLAUDE_DIR/hooks/$(basename "$file")"
done

# Scripts
for file in "$TMPDIR/repo/.claude/scripts/"*.mjs; do
  [ -f "$file" ] && copy_if_new "$file" "$CLAUDE_DIR/scripts/$(basename "$file")"
done

# Scripts/lib
for file in "$TMPDIR/repo/.claude/scripts/lib/"*.mjs; do
  [ -f "$file" ] && copy_if_new "$file" "$CLAUDE_DIR/scripts/lib/$(basename "$file")"
done

# Pipelines
for file in "$TMPDIR/repo/.claude/pipelines/"*.yaml; do
  [ -f "$file" ] && copy_if_new "$file" "$CLAUDE_DIR/pipelines/$(basename "$file")"
done

# 5. .gitignore に state/ を追加
GITIGNORE="$PROJECT_DIR/.gitignore"
if [ -f "$GITIGNORE" ]; then
  if ! grep -q ".claude/state/" "$GITIGNORE"; then
    echo -e "\n# oh-my-claude-code runtime state\n.claude/state/" >> "$GITIGNORE"
    log ".gitignore に .claude/state/ を追加"
  fi
else
  echo -e "# oh-my-claude-code runtime state\n.claude/state/" > "$GITIGNORE"
  log ".gitignore を作成"
fi

# 6. 完了
echo ""
log "${CYAN}インストール完了!${NC}"
echo ""
echo "  使い方:"
echo "    cd $PROJECT_DIR"
echo "    claude  # Claude Code を起動"
echo ""
echo "  コマンド例:"
echo "    「完了まで実装して」  → Persistent Mode"
echo "    「ターボで」          → Turbo Mode"
echo "    「QA回して」          → QA Mode"
echo "    「/cancel」           → モード終了"
echo ""
echo "  設定: $CLAUDE_DIR/settings.json"
echo "  ドキュメント: $REPO_URL#readme"
echo ""
