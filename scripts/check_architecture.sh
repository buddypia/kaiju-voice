#!/bin/bash
# Feature-First アーキテクチャ準拠検証スクリプト
#
# 検証項目:
# 1. 他の Feature の内部ファイル直接 import 禁止（バレルファイル使用必須）
# 2. Core → Feature import 禁止
# 3. Shared → Feature import 警告（許容するが最小化推奨）

# set -e は使用しない（各ステップの exit code を手動で処理）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# カラーコード
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Feature-First アーキテクチャ検証"
echo "========================================="

VIOLATIONS=0
WARNINGS=0

# ========================================
# 1. 他の Feature 内部の直接 import 検査
# ========================================
echo ""
echo "[1/3] 他の Feature 内部の直接 import 検査..."
echo "   (同一 Feature 内部の import は許容)"

# Python スクリプトで精密な検査を実行
CROSS_FEATURE_VIOLATIONS=$("$SCRIPT_DIR/check_cross_feature_imports.py" 2>&1)
PYTHON_EXIT_CODE=$?

if [ $PYTHON_EXIT_CODE -ne 0 ]; then
  echo -e "${RED}[FAIL] 違反: 他の Feature 内部の直接 import を検出${NC}"
  echo ""
  echo "$CROSS_FEATURE_VIOLATIONS"
  echo ""
  echo "[INFO] 正しい方法:"
  echo "   ❌ import 'package:hackathon_project/features/lesson/data/models/sentence.dart';"
  echo "   ✅ import 'package:hackathon_project/features/lesson/lesson.dart';"
  echo ""
  VIOLATIONS=$((VIOLATIONS + 1))
else
  echo -e "${GREEN}[PASS] 通過: 他の Feature 内部の直接 import なし${NC}"
fi

# ========================================
# 2. Core → Feature import 検査
# ========================================
echo ""
echo "[2/3] Core → Feature import 検査..."

CORE_TO_FEATURE=$(grep -rn "import 'package:hackathon_project/features/" \
  "$PROJECT_ROOT/lib/core" \
  --include="*.dart" \
  --exclude="*.g.dart" \
  --exclude="*.freezed.dart" \
  2>/dev/null || true)

if [ -n "$CORE_TO_FEATURE" ]; then
  echo -e "${RED}[FAIL] 違反: Core が Feature を import${NC}"
  echo ""
  echo "$CORE_TO_FEATURE"
  echo ""
  echo "[INFO] Core は Feature に依存してはなりません。依存性を逆転させてください。"
  echo ""
  VIOLATIONS=$((VIOLATIONS + 1))
else
  echo -e "${GREEN}[PASS] 通過: Core → Feature import なし${NC}"
fi

# ========================================
# 3. Shared → Feature import 検査（警告）
# ========================================
echo ""
echo "[3/3] Shared → Feature import 検査..."

SHARED_FEATURE_COUNT=$(grep -rn "import 'package:hackathon_project/features/" \
  "$PROJECT_ROOT/lib/shared" \
  --include="*.dart" \
  --exclude="*.g.dart" \
  --exclude="*.freezed.dart" \
  2>/dev/null | wc -l | tr -d ' ')

if [ "$SHARED_FEATURE_COUNT" -gt 0 ]; then
  echo -e "${YELLOW}[WARN] 警告: Shared が Feature を import ($SHARED_FEATURE_COUNT件)${NC}"
  echo ""
  echo "[INFO] Shared は Feature に依存しないのが理想的ですが、"
  echo "   Home ウィジェット等の一部のケースは許容可能です。"
  echo "   ただし最小化を推奨します。"
  echo ""
  WARNINGS=$((WARNINGS + 1))
else
  echo -e "${GREEN}[PASS] 通過: Shared → Feature import なし${NC}"
fi

# ========================================
# 結果出力
# ========================================
echo ""
echo "========================================="
if [ $VIOLATIONS -eq 0 ]; then
  if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}[WARN] 警告あり (${WARNINGS}件) - 改善推奨${NC}"
  else
    echo -e "${GREEN}[PASS] 全検証通過!${NC}"
  fi
  echo "========================================="
  exit 0
else
  echo -e "${RED}[FAIL] $VIOLATIONS個の違反検出 (警告: $WARNINGS件)${NC}"
  echo "========================================="
  echo ""
  echo "アーキテクチャガイド: docs/technical/feature-first-architecture.md"
  echo "チェックリスト: docs/technical/feature-first-compliance-checklist.md"
  exit 1
fi
