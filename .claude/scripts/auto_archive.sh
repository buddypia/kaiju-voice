#!/bin/bash
#
# Auto Archive - COLD セクション 自動アーカイブ
#
# 根本的解決策:
# - 30日以上未参照セクションを自動アーカイブ
# - Wisdom サイズを一定に維持
# - 必要時アーカイブから復旧可能
#

set -e  # エラー発生時 即時終了

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 設定
WISDOM_DIR=".claude/wisdom"
ARCHIVE_DIR=".claude/archive/wisdom"
SCRIPT_DIR=".claude/scripts"
TTL_DAYS=30
INTERACTIVE=true

# 関数定義
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

confirm() {
    if [ "$INTERACTIVE" = false ]; then
        return 0
    fi

    local prompt="$1"
    read -p "$prompt (y/N): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

archive_cold_sections() {
    log_info "COLDセクション検出中 (${TTL_DAYS}日以上未参照)..."

    # Python スクリプトでCOLD セクションリスト 生成
    COLD_JSON=$(python3 "$SCRIPT_DIR/wisdom_ttl_tracker.py" --list-cold "$TTL_DAYS" 2>/dev/null || echo "[]")

    if [ "$COLD_JSON" = "✅ ${TTL_DAYS}日以上未参照 セクション なし" ]; then
        log_success "アーカイブする COLD セクションがありません"
        return 0
    fi

    # COLD セクション個数 確認
    COLD_COUNT=$(python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from wisdom_ttl_tracker import WisdomTTLTracker
tracker = WisdomTTLTracker()
cold = tracker.find_cold_sections(min_days=$TTL_DAYS)
print(len(cold))
" 2>/dev/null || echo "0")

    if [ "$COLD_COUNT" = "0" ]; then
        log_success "アーカイブする COLD セクションがありません"
        return 0
    fi

    log_warning "発見された COLD セクション: ${COLD_COUNT}個"

    # ユーザー 確認
    if ! confirm "セクションをアーカイブしますか?"; then
        log_info "アーカイブ キャンセル"
        return 1
    fi

    # アーカイブ ディレクトリ 生成
    mkdir -p "$ARCHIVE_DIR"

    # タイムスタンプ
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    ARCHIVE_SUBDIR="$ARCHIVE_DIR/$TIMESTAMP"
    mkdir -p "$ARCHIVE_SUBDIR"

    log_info "アーカイブ中..."

    # Python スクリプトでアーカイブ 実行
    python3 "$SCRIPT_DIR/archive_sections.py" \
        --ttl-days "$TTL_DAYS" \
        --output-dir "$ARCHIVE_SUBDIR" \
        --wisdom-dir "$WISDOM_DIR"

    log_success "アーカイブ 完了: $ARCHIVE_SUBDIR"

    # 統計 出力
    python3 "$SCRIPT_DIR/wisdom_ttl_tracker.py" --stats
}

restore_from_archive() {
    local archive_date="$1"

    if [ -z "$archive_date" ]; then
        log_error "使用法: $0 --restore YYYYMMDD_HHMMSS"
        return 1
    fi

    local restore_dir="$ARCHIVE_DIR/$archive_date"

    if [ ! -d "$restore_dir" ]; then
        log_error "アーカイブが見つかりません: $restore_dir"
        return 1
    fi

    log_info "アーカイブから復旧中: $archive_date"

    if ! confirm "アーカイブを復旧しますか?"; then
        log_info "復旧キャンセル"
        return 1
    fi

    # 復旧 実行
    python3 "$SCRIPT_DIR/restore_sections.py" \
        --archive-dir "$restore_dir" \
        --wisdom-dir "$WISDOM_DIR"

    log_success "復旧 完了"
}

list_archives() {
    log_info "使用可能な アーカイブ:"
    echo

    if [ ! -d "$ARCHIVE_DIR" ] || [ -z "$(ls -A "$ARCHIVE_DIR" 2>/dev/null)" ]; then
        log_warning "アーカイブがありません"
        return 0
    fi

    for archive in "$ARCHIVE_DIR"/*; do
        if [ -d "$archive" ]; then
            local date=$(basename "$archive")
            local file_count=$(find "$archive" -type f | wc -l)
            echo "  📦 $date ($file_count ファイル)"
        fi
    done
}

show_help() {
    cat << EOF
使用法: $0 [オプション]

Wisdom COLD セクション 自動アーカイブ ツール

オプション:
  --archive           COLD セクションをアーカイブ (基本 動作)
  --restore DATE      アーカイブで復旧 (DATE: YYYYMMDD_HHMMSS)
  --list              使用可能な アーカイブ リスト
  --ttl-days N        TTL 期間 設定 (基本: 30日)
  --non-interactive   ユーザー 確認 なく自動 実行
  --help              ヘルプを 表示

例:
  $0 --archive                      # 30日以上未参照 セクション アーカイブ
  $0 --archive --ttl-days 60        # 60日以上未参照 セクション アーカイブ
  $0 --restore 20260205_140000      # 特定 アーカイブで復旧
  $0 --list                         # アーカイブ リスト 確認

EOF
}

# メインロジック
main() {
    local action="archive"

    while [[ $# -gt 0 ]]; do
        case $1 in
            --archive)
                action="archive"
                shift
                ;;
            --restore)
                action="restore"
                RESTORE_DATE="$2"
                shift 2
                ;;
            --list)
                action="list"
                shift
                ;;
            --ttl-days)
                TTL_DAYS="$2"
                shift 2
                ;;
            --non-interactive)
                INTERACTIVE=false
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "不明な オプション: $1"
                show_help
                exit 1
                ;;
        esac
    done

    case $action in
        archive)
            archive_cold_sections
            ;;
        restore)
            restore_from_archive "$RESTORE_DATE"
            ;;
        list)
            list_archives
            ;;
    esac
}

# スクリプト実行
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
