#!/usr/bin/env python3
"""Feature-First アーキテクチャ: Cross-Feature 内部 import 検査

Feature 間の import は barrel file (index.ts) 経由のみ許可。
内部ファイル直接 import（hooks/, components/, lib/, types/ 等）を検出する。

許可:
  import { useFoo } from '@/features/foo';           // barrel file OK
  import { useFoo } from '@/features/foo/index';     // barrel file OK

禁止:
  import { useFoo } from '@/features/foo/hooks/use-foo';     // 内部直接
  import { FooPanel } from '@/features/foo/components/Foo';   // 内部直接
"""

import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_FEATURES = os.path.join(PROJECT_ROOT, "src", "features")

# @/features/<name>/... の内部パスを検出する正規表現
# barrel file (@/features/<name> or @/features/<name>/index) は除外
# types/ パスは型定義のみ（コンパイル時結合）のため許容
CROSS_FEATURE_INTERNAL = re.compile(
    r"""from\s+['"]@/features/([a-z0-9-]+)/(?!index['"]|types['"/])(.*?)['"]"""
)

# 相対パス ../other-feature/... による cross-feature import
RELATIVE_CROSS_FEATURE = re.compile(
    r"""from\s+['"]\.\./(\.\./)?((?!\.)[a-z0-9-]+)/(.*?)['"]"""
)


def get_feature_name(filepath: str) -> str | None:
    """ファイルパスから feature 名を抽出"""
    rel = os.path.relpath(filepath, SRC_FEATURES)
    parts = rel.split(os.sep)
    if len(parts) >= 2:
        return parts[0]
    return None


def check_file(filepath: str) -> list[str]:
    """ファイル内の cross-feature 内部 import を検出"""
    violations = []
    feature_name = get_feature_name(filepath)
    if not feature_name:
        return violations

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return violations

    for line_num, line in enumerate(lines, 1):
        # @/features/<other>/internal/path パターン
        match = CROSS_FEATURE_INTERNAL.search(line)
        if match:
            target_feature = match.group(1)
            if target_feature != feature_name:
                rel_path = os.path.relpath(filepath, PROJECT_ROOT)
                violations.append(
                    f"  {rel_path}:{line_num}: "
                    f"@/features/{target_feature}/{match.group(2)} "
                    f"(→ @/features/{target_feature} を使用)"
                )

    return violations


def main() -> int:
    violations: list[str] = []

    if not os.path.isdir(SRC_FEATURES):
        print("src/features/ ディレクトリが見つかりません")
        return 1

    for root, _dirs, files in os.walk(SRC_FEATURES):
        for fname in files:
            if not fname.endswith((".ts", ".tsx")):
                continue
            filepath = os.path.join(root, fname)
            violations.extend(check_file(filepath))

    if violations:
        print(f"Cross-Feature 内部 import 違反: {len(violations)}件")
        print()
        for v in violations:
            print(v)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
