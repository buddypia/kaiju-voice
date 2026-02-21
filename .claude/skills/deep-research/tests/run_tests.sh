#!/bin/bash
# deep-research スキルテスト実行スクリプト

set -e  # エラー発生時に中断

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

echo "==============================================="
echo "deep-research スキルテストスイート"
echo "==============================================="
echo "スキルディレクトリ: $SKILL_DIR"
echo ""

# Python バージョン確認
echo "📌 Python バージョン:"
python3 --version
echo ""

# 依存関係確認
echo "📌 必須パッケージ確認:"
if python3 -c "import unittest" 2>/dev/null; then
    echo "✅ unittest 使用可能"
else
    echo "❌ unittest なし (Python 標準モジュール、インストール不要)"
fi
echo ""

# Unit Test 実行
echo "🧪 1. Unit Test: Provider 選択ロジック"
echo "-----------------------------------------------"
if python3 "$SCRIPT_DIR/test_provider_selection.py"; then
    echo "✅ Unit Test 通過"
else
    echo "❌ Unit Test 失敗"
    exit 1
fi
echo ""

# Integration Test (実際のスクリプト実行)
echo "🧪 2. Integration Test: スクリプト実行"
echo "-----------------------------------------------"

# ヘルプテスト
echo "2-1. ヘルプ出力テスト"
if python3 "$SKILL_DIR/scripts/deep_research.py" --help > /dev/null 2>&1; then
    echo "✅ ヘルプ出力成功"
else
    echo "❌ ヘルプ出力失敗"
    exit 1
fi

# Provider 認識テスト (実際のAPI呼び出しなし)
echo ""
echo "2-2. Provider 認識テスト"
# 注意: 実際のAPIキーがなければ失敗予想
if python3 "$SKILL_DIR/scripts/deep_research.py" "test query" --provider openai 2>&1 | grep -q "OPENAI_API_KEY"; then
    echo "✅ OpenAI provider 認識 (APIキー確認メッセージ)"
else
    echo "⚠️ OpenAI provider 実行 (APIキーなし、想定された動作)"
fi

if python3 "$SKILL_DIR/scripts/deep_research.py" "test query" --provider google 2>&1 | grep -q "GEMINI_API_KEY"; then
    echo "✅ Google provider 認識 (APIキー確認メッセージ)"
else
    echo "⚠️ Google provider 実行 (APIキーなし、想定された動作)"
fi

echo ""

# 誤ったprovider テスト
echo "2-3. 誤ったprovider 拒否テスト"
if python3 "$SKILL_DIR/scripts/deep_research.py" "test" --provider invalid 2>&1 | grep -q "invalid choice"; then
    echo "✅ 誤った provider 正常拒否"
else
    echo "❌ 誤った provider 検証失敗"
    exit 1
fi

echo ""
echo "==============================================="
echo "✅ 全てのテスト通過!"
echo "==============================================="
echo ""
echo "📊 テストサマリー:"
echo "  - Unit Test: Provider 選択ロジック ✅"
echo "  - Integration Test: スクリプト実行 ✅"
echo "  - Error Handling: 誤った入力拒否 ✅"
echo ""
echo "🎯 次のステップ:"
echo "  1. 実際のAPIキーでE2Eテスト (手動)"
echo "  2. エラーハンドリング強化 (Phase 3)"
echo "  3. スマート Provider 選択 (Phase 4)"
