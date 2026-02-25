#!/usr/bin/env python3
"""
expect_fail.py - コマンドが失敗してこそ成功とみなすTDD補助スクリプト

Usage:
  python3 .quality/scripts/expect_fail.py -- npm test test/path_to_test.ts
  python3 .quality/scripts/expect_fail.py npm test test/path_to_test.ts

Exit Codes:
  0 - コマンドが失敗した (予想通りRed)
  1 - コマンドが成功した (予想と異なる)
  2 - 実行エラー
"""

import sys
import subprocess


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("Usage: expect_fail.py -- <command>", file=sys.stderr)
        sys.exit(2)

    if "--" in args:
        idx = args.index("--")
        cmd = args[idx + 1 :]
    else:
        cmd = args

    if not cmd:
        print("Usage: expect_fail.py -- <command>", file=sys.stderr)
        sys.exit(2)

    try:
        result = subprocess.run(cmd)
    except OSError as e:
        print(f"❌ 実行失敗: {e}", file=sys.stderr)
        sys.exit(2)

    if result.returncode == 0:
        print("❌ 失敗が必要でしたがコマンドが成功しました (Red確認失敗)")
        sys.exit(1)

    print(f"✅ 予想通り失敗しました (exit code: {result.returncode})")
    sys.exit(0)


if __name__ == "__main__":
    main()
