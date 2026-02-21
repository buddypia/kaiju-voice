#!/usr/bin/env bash
#
# check_test_exists.sh - テストファイル存在確認 (Web/TypeScript)
#
# 変更されたソースファイルに対応するテストファイルが存在するか確認
# (git diff で変更されたファイルのみ検査)
#
# Exit Codes:
#   0 - 全テストファイル存在
#   1 - テスト不足発見
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

MISSING=0

# git diff で変更されたファイル確認 (staged + unstaged)
CHANGED_FILES=$(git diff --name-only HEAD 2>/dev/null || git diff --name-only 2>/dev/null || echo "")

if [[ -z "$CHANGED_FILES" ]]; then
    echo "✅ No changed files to check"
    exit 0
fi

# src/features 配下のソースファイルを検査
while IFS= read -r file; do
    # src/features/{feature}/hooks/*.ts(x) を検査
    if [[ "$file" =~ ^src/features/([^/]+)/hooks/(.+)\.(ts|tsx)$ ]]; then
        feature="${BASH_REMATCH[1]}"
        basename="${BASH_REMATCH[2]}"

        # index.ts (バレルファイル) はスキップ
        if [[ "$basename" == "index" ]]; then
            continue
        fi

        # テストファイルパス候補 (tests/unit/ + tests/ 両方、flat + nested 両方)
        test_file_1="tests/unit/features/${feature}/hooks/${basename}.test.ts"
        test_file_2="tests/unit/features/${feature}/hooks/${basename}.test.tsx"
        test_file_3="tests/unit/features/${feature}/${basename}.test.ts"
        test_file_4="tests/unit/features/${feature}/${basename}.test.tsx"
        test_file_5="tests/features/${feature}/hooks/${basename}.test.ts"
        test_file_6="tests/features/${feature}/hooks/${basename}.test.tsx"
        test_file_7="src/features/${feature}/hooks/__tests__/${basename}.test.ts"
        test_file_8="src/features/${feature}/hooks/__tests__/${basename}.test.tsx"

        if [[ ! -f "$test_file_1" && ! -f "$test_file_2" && ! -f "$test_file_3" && ! -f "$test_file_4" && ! -f "$test_file_5" && ! -f "$test_file_6" && ! -f "$test_file_7" && ! -f "$test_file_8" ]]; then
            echo "⚠️ Missing test for: $file"
            MISSING=$((MISSING + 1))
        fi
    fi

    # src/features/{feature}/api/*.ts を検査
    if [[ "$file" =~ ^src/features/([^/]+)/api/(.+)\.ts$ ]]; then
        feature="${BASH_REMATCH[1]}"
        basename="${BASH_REMATCH[2]}"

        if [[ "$basename" == "index" ]]; then
            continue
        fi

        test_file_1="tests/unit/features/${feature}/api/${basename}.test.ts"
        test_file_2="tests/unit/features/${feature}/${basename}.test.ts"
        test_file_3="tests/features/${feature}/api/${basename}.test.ts"
        test_file_4="src/features/${feature}/api/__tests__/${basename}.test.ts"

        if [[ ! -f "$test_file_1" && ! -f "$test_file_2" && ! -f "$test_file_3" && ! -f "$test_file_4" ]]; then
            echo "⚠️ Missing test for: $file"
            MISSING=$((MISSING + 1))
        fi
    fi

    # src/shared/lib/*.ts を検査
    if [[ "$file" =~ ^src/shared/lib/(.+)\.ts$ ]]; then
        basename="${BASH_REMATCH[1]}"

        if [[ "$basename" == "index" ]]; then
            continue
        fi

        test_file_1="tests/unit/shared/lib/${basename}.test.ts"
        test_file_2="tests/shared/lib/${basename}.test.ts"
        test_file_3="src/shared/lib/__tests__/${basename}.test.ts"

        if [[ ! -f "$test_file_1" && ! -f "$test_file_2" && ! -f "$test_file_3" ]]; then
            echo "⚠️ Missing test for: $file"
            MISSING=$((MISSING + 1))
        fi
    fi
done <<< "$CHANGED_FILES"

if [[ $MISSING -gt 0 ]]; then
    echo ""
    echo "Found $MISSING missing test file(s)"
    exit 1
fi

echo "✅ All changed files have corresponding tests"
exit 0
