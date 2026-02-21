#!/usr/bin/env python3
"""
check_priority_stale.py - Priority Staleness 検出スクリプト

14日以上更新されていない priority セクションを検出し、警告します。

Exit Codes:
  0 - すべての priority が最新状態
  1 - エラー発生
  2 - Stale priority を検出（警告）

Usage:
  python check_priority_stale.py [--threshold DAYS] [--json]

Options:
  --threshold DAYS  Staleness 基準日数（デフォルト: 14）
  --json            JSON形式で出力
"""

import json
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path


STALE_THRESHOLD_DAYS = 14
FEATURES_DIR = Path("docs/features")


def parse_iso_datetime(dt_str: str) -> datetime:
    """ISO 8601 形式の datetime 文字列をパースします。"""
    # Python 3.11+ の fromisoformat は Z をサポートしますが、下位互換のため処理
    dt_str = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(dt_str)


def check_stale_priorities(threshold_days: int = STALE_THRESHOLD_DAYS) -> list[dict]:
    """
    すべての CONTEXT.json をスキャンして stale priority を検出します。

    Returns:
        stale priority 情報のリスト
    """
    stale_features = []
    missing_priority = []
    now = datetime.now(timezone.utc)

    context_files = sorted(FEATURES_DIR.glob("*/CONTEXT.json"))

    for context_file in context_files:
        try:
            with open(context_file, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  ファイル読み取りエラー: {context_file} - {e}", file=sys.stderr)
            continue

        feature_id = data.get("feature_id", context_file.parent.name)

        # Lifecycle フィルター: Archived/Failed Feature は staleness チェック対象から除外
        lifecycle_state = data.get("quick_resume", {}).get("current_state", "")
        if lifecycle_state in ("Archived", "Failed"):
            continue

        # priority セクションなし
        if "priority" not in data:
            missing_priority.append(feature_id)
            continue

        priority = data["priority"]
        last_updated_str = priority.get("last_updated")

        if not last_updated_str:
            missing_priority.append(feature_id)
            continue

        try:
            last_updated = parse_iso_datetime(last_updated_str)
            # timezone-naive の場合は UTC と仮定
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)

            days_old = (now - last_updated).days

            if days_old >= threshold_days:
                stale_features.append({
                    "feature_id": feature_id,
                    "days_old": days_old,
                    "last_updated": last_updated_str,
                    "rice_score": priority.get("calculated", {}).get("rice_score"),
                    "context_path": str(context_file)
                })
        except ValueError as e:
            print(f"⚠️  日付パースエラー: {feature_id} - {e}", file=sys.stderr)
            continue

    return stale_features, missing_priority


def main():
    parser = argparse.ArgumentParser(
        description="Priority staleness 検出スクリプト"
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=STALE_THRESHOLD_DAYS,
        help=f"Staleness 基準日数（デフォルト: {STALE_THRESHOLD_DAYS}）"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON形式で出力"
    )
    args = parser.parse_args()

    stale_features, missing_priority = check_stale_priorities(args.threshold)

    if args.json:
        result = {
            "stale": stale_features,
            "missing": missing_priority,
            "threshold_days": args.threshold,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # コンソール出力
        total_checked = len(list(FEATURES_DIR.glob("*/CONTEXT.json")))

        if missing_priority:
            print(f"\n📋 priority セクションなし: {len(missing_priority)}件")
            for fid in missing_priority[:5]:  # 最大5件のみ表示
                print(f"   - {fid}")
            if len(missing_priority) > 5:
                print(f"   ... 他 {len(missing_priority) - 5}件")

        if stale_features:
            print(f"\n⚠️  更新が必要（{args.threshold}日以上経過）: {len(stale_features)}件")
            print("")
            print(f"   {'Feature ID':<40} {'経過日数':>8} {'RICE':>8}")
            print(f"   {'-'*40} {'-'*8} {'-'*8}")

            # days_old 降順ソート
            for f in sorted(stale_features, key=lambda x: x["days_old"], reverse=True):
                rice = f["rice_score"]
                rice_str = f"{rice:.2f}" if rice else "N/A"
                print(f"   {f['feature_id']:<40} {f['days_old']:>6}日 {rice_str:>8}")

            print("")
            print("   💡 更新方法: /priority-analyzer --all --apply")
            print("")

        if not stale_features and not missing_priority:
            print(f"✅ すべての priority が最新状態です（{total_checked}件検査済み）")

    # Exit code
    if stale_features or missing_priority:
        sys.exit(2)  # Warning
    sys.exit(0)


if __name__ == "__main__":
    main()
