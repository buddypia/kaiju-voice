#!/bin/bash
#
# Wisdom Manager - 統合ワークフロー管理
#
# 根本的解決策の統合インターフェース:
# - TTL 追跡
# - 自動分割
# - COLD アーカイブ
# - 統計 および モニタリング
#

set -e

# カラー定義
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log_section() {
    echo
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo
}

cmd_dashboard() {
    log_section "Wisdom ダッシュボード"

    echo "📊 全体 統計"
    python3 "$SCRIPT_DIR/wisdom_ttl_tracker.py" --stats
    echo

    echo "📈 分割 影響 分析"
    python3 "$SCRIPT_DIR/wisdom_splitter.py" --analyze
    echo

    echo "❄️  COLD セクション (30日 以上 参照)"
    python3 "$SCRIPT_DIR/wisdom_ttl_tracker.py" --list-cold 30 | head -20
}

cmd_maintain() {
    log_section "Wisdom メンテナンス 実行"

    echo "1️⃣  COLD セクション アーカイブ 確認..."
    bash "$SCRIPT_DIR/auto_archive.sh" --archive
    echo

    echo "2️⃣  Wisdom 統計 更新..."
    python3 "$SCRIPT_DIR/wisdom_ttl_tracker.py" --stats
    echo

    echo "3️⃣  分割 必要 有無 確認..."
    python3 "$SCRIPT_DIR/wisdom_splitter.py" --analyze
    echo

    echo -e "${GREEN}✅ メンテナンス 完了${NC}"
}

cmd_split() {
    log_section "Wisdom 分割 実行"

    echo "🔍 分割 影響 分析..."
    python3 "$SCRIPT_DIR/wisdom_splitter.py" --analyze
    echo

    read -p "分割を実行しますか? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 "$SCRIPT_DIR/wisdom_splitter.py" --split
        echo -e "${GREEN}✅ 分割 完了${NC}"
    else
        echo "❌ 分割 キャンセル"
    fi
}

cmd_health_check() {
    log_section "Wisdom 健全性 チェック"

    local status=0

    # 1. サイズ チェック
    echo "1️⃣  サイズ チェック..."
    local wisdom_size=$(du -sk .claude/wisdom | cut -f1)
    local threshold_kb=100

    if [ "$wisdom_size" -gt "$threshold_kb" ]; then
        echo -e "${YELLOW}⚠️  Wisdom サイズ: ${wisdom_size}KB (閾値: ${threshold_kb}KB)${NC}"
        echo "   → 中期 戦略(分割) 導入 推奨"
        status=1
    else
        echo -e "${GREEN}✅ Wisdom サイズ: ${wisdom_size}KB (正常)${NC}"
    fi
    echo

    # 2. COLD 比率 チェック
    echo "2️⃣  COLD 比率 チェック..."
    local cold_percentage=$(python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from wisdom_ttl_tracker import WisdomTTLTracker
tracker = WisdomTTLTracker()
stats = tracker.get_statistics()
print(f\"{stats['cold_percentage']:.1f}\")
")

    if (( $(echo "$cold_percentage > 20.0" | bc -l) )); then
        echo -e "${YELLOW}⚠️  COLD 比率: ${cold_percentage}% (高い)${NC}"
        echo "   → アーカイブ 推奨"
        status=1
    else
        echo -e "${GREEN}✅ COLD 比率: ${cold_percentage}% (正常)${NC}"
    fi
    echo

    # 3. トークン コスト チェック
    echo "3️⃣  トークン コスト チェック..."
    local token_cost=$(python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from wisdom_splitter import WisdomSplitter
try:
    splitter = WisdomSplitter()
    impact = splitter.analyze_split_impact()
    print(impact['estimated_tokens_before'])
except:
    print('0')
")

    if [ "$token_cost" -gt 10000 ]; then
        echo -e "${RED}🚨 トークン/セッション: ${token_cost} (危険)${NC}"
        echo "   → 即時 分割 必要"
        status=2
    elif [ "$token_cost" -gt 5000 ]; then
        echo -e "${YELLOW}⚠️  トークン/セッション: ${token_cost} (注意)${NC}"
        echo "   → 分割 検討 推奨"
        status=1
    else
        echo -e "${GREEN}✅ トークン/セッション: ${token_cost} (正常)${NC}"
    fi
    echo

    # 最終 結果
    if [ $status -eq 0 ]; then
        echo -e "${GREEN}✅ 全体 健全性 状態: 良好${NC}"
    elif [ $status -eq 1 ]; then
        echo -e "${YELLOW}⚠️  全体 健全性 状態: 注意${NC}"
    else
        echo -e "${RED}🚨 全体 健全性 状態: 危険${NC}"
    fi

    return $status
}

show_help() {
    cat << EOF
Wisdom Manager - Wisdom システム 統合 管理

使用法: $0 <コマンド> [オプション]

コマンド:
  dashboard           全体 ダッシュボード 表示 (統計 + 分析)
  health-check        健全性 チェック (サイズ, COLD 比率, トークン コスト)
  maintain            自動 メンテナンス 実行 (アーカイブ + 統計)
  split               Wisdom 分割 実行 (core/feature)
  init                初期 設定 (メタデータ 生成)

例:
  $0 dashboard              # 現在 状態 確認
  $0 health-check           # 健全性 チェック
  $0 maintain               # 月間 メンテナンス 実行
  $0 split                  # 50個 機能 達成 時 分割

週間 配置:
  cron: 0 9 * * 1   $0 maintain    # 毎週 月曜日 9時

月間 配置:
  cron: 0 9 1 * *   $0 split       # 毎月 1日 9時 (必要 時)

EOF
}

# メイン
case "${1:-help}" in
    dashboard)
        cmd_dashboard
        ;;
    health-check)
        cmd_health_check
        ;;
    maintain)
        cmd_maintain
        ;;
    split)
        cmd_split
        ;;
    init)
        python3 "$SCRIPT_DIR/wisdom_ttl_tracker.py" --init
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "不明なコマンド: $1"
        show_help
        exit 1
        ;;
esac
