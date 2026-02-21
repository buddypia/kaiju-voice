#!/usr/bin/env python3
"""
migrate_scan_status.py - scan-status.json v1 → v2 マイグレーション

v1 スキーマから v2 へアップグレードします:
- schema_version: 1 → 2
- 各 candidate に history 配列を追加 (既存の状態から逆算)

Exit Codes:
  0 - マイグレーション成功 (または既に v2)
  1 - エラー発生

Usage:
  python migrate_scan_status.py [--dry-run] [--no-backup]

Options:
  --dry-run     変更内容のプレビュー (ファイル修正なし)
  --no-backup   バックアップファイルを生成しない
"""

import json
import sys
import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path


SCAN_STATUS_PATH = Path(".claude/skills/market-intelligence-scanner/assets/scan-status.json")


def build_history_for_candidate(candidate: dict) -> list[dict]:
    """
    既存の candidate 状態から history 配列を逆算します。

    状態別の推論:
    - converted: pending_review → approved → converted
    - merged: pending_review → merged
    - approved: pending_review → approved
    - rejected: pending_review → rejected
    - deferred: pending_review → deferred
    - pending_review: 初期作成のみ記録
    """
    status = candidate.get("status", "pending_review")
    created_at = candidate.get("created_at", "2026-01-25T00:00:00Z")
    reviewed_at = candidate.get("reviewed_at")
    history = []

    if status == "pending_review":
        # まだレビューされていない - 初期作成の記録のみ
        history.append({
            "at": created_at,
            "from_status": "pending_review",
            "to_status": "pending_review",
            "triggered_by": "market-intelligence-scanner",
            "note": "v2 マイグレーション: 初期作成記録"
        })

    elif status == "converted":
        # pending_review → approved → converted
        # approved の時点は reviewed_at の直前と推定
        approve_time = reviewed_at or created_at
        convert_time = reviewed_at or created_at

        history.append({
            "at": approve_time,
            "from_status": "pending_review",
            "to_status": "approved",
            "triggered_by": "manual",
            "note": "v2 マイグレーション: 承認時点の逆算"
        })
        history.append({
            "at": convert_time,
            "from_status": "approved",
            "to_status": "converted",
            "triggered_by": "feature-architect",
            "note": f"v2 マイグレーション: converted_to={candidate.get('converted_to', 'unknown')}"
        })

    elif status == "merged":
        merge_time = reviewed_at or created_at
        history.append({
            "at": merge_time,
            "from_status": "pending_review",
            "to_status": "merged",
            "triggered_by": "manual",
            "note": f"v2 マイグレーション: merged_into={candidate.get('merged_into', 'unknown')}"
        })

    elif status == "approved":
        approve_time = reviewed_at or created_at
        history.append({
            "at": approve_time,
            "from_status": "pending_review",
            "to_status": "approved",
            "triggered_by": "manual",
            "note": "v2 マイグレーション: 承認記録"
        })

    elif status == "rejected":
        reject_time = reviewed_at or created_at
        history.append({
            "at": reject_time,
            "from_status": "pending_review",
            "to_status": "rejected",
            "triggered_by": "manual",
            "note": f"v2 マイグレーション: reason={candidate.get('rejection_reason', 'unknown')}"
        })

    elif status == "deferred":
        defer_time = reviewed_at or created_at
        history.append({
            "at": defer_time,
            "from_status": "pending_review",
            "to_status": "deferred",
            "triggered_by": "manual",
            "note": f"v2 マイグレーション: reason={candidate.get('deferred_reason', 'unknown')}"
        })

    elif status == "reverted":
        # converted → reverted: 承認、変換、復元の3段階を逆算
        reverted_from = candidate.get("reverted_from", "converted")
        approve_time = reviewed_at or created_at
        revert_time = reviewed_at or created_at
        history.append({
            "at": approve_time,
            "from_status": "pending_review",
            "to_status": "approved",
            "triggered_by": "manual",
            "note": "v2 マイグレーション: 承認時点の逆算"
        })
        history.append({
            "at": approve_time,
            "from_status": "approved",
            "to_status": reverted_from,
            "triggered_by": "feature-architect",
            "note": f"v2 マイグレーション: {reverted_from} 時点の逆算"
        })
        history.append({
            "at": revert_time,
            "from_status": reverted_from,
            "to_status": "reverted",
            "triggered_by": "manual",
            "note": f"v2 マイグレーション: reason={candidate.get('revert_reason', 'unknown')}"
        })

    return history


def migrate(dry_run: bool = False, no_backup: bool = False) -> dict:
    """
    v1 → v2 マイグレーションを実行します。

    Returns:
        マイグレーション結果の辞書
    """
    # 1. ファイル読み込み
    if not SCAN_STATUS_PATH.exists():
        return {"status": "error", "message": "scan-status.json ファイルが見つかりません"}

    try:
        with open(SCAN_STATUS_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"JSON パース失敗: {e}"}

    # 2. バージョン確認
    current_version = data.get("schema_version", 1)
    if current_version >= 2:
        return {"status": "skip", "message": f"既に v{current_version} です。マイグレーション不要。"}

    # 3. マイグレーション実行
    changes = []

    # schema_version アップグレード
    data["schema_version"] = 2
    changes.append("schema_version: 1 → 2")

    # last_updated 更新
    now_iso = datetime.now(timezone.utc).isoformat()
    data["last_updated"] = now_iso
    changes.append(f"last_updated: {now_iso}")

    # 各 candidate に history を追加
    for candidate in data.get("candidates", []):
        cid = candidate.get("candidate_id", "unknown")
        if "history" not in candidate:
            history = build_history_for_candidate(candidate)
            candidate["history"] = history
            changes.append(f"candidate[{cid}]: history 追加 ({len(history)}件のエントリ)")
        else:
            changes.append(f"candidate[{cid}]: history が既に存在 (スキップ)")

    result = {
        "status": "success",
        "from_version": 1,
        "to_version": 2,
        "changes": changes,
        "total_candidates": len(data.get("candidates", [])),
    }

    if dry_run:
        result["status"] = "dry_run"
        result["message"] = "変更内容のプレビュー (ファイル修正なし)"
        return result

    # 4. バックアップ
    if not no_backup:
        backup_path = SCAN_STATUS_PATH.with_suffix(".json.v1.bak")
        shutil.copy2(SCAN_STATUS_PATH, backup_path)
        result["backup_path"] = str(backup_path)

    # 5. 保存
    with open(SCAN_STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return result


def main():
    parser = argparse.ArgumentParser(description="scan-status.json v1 → v2 マイグレーション")
    parser.add_argument("--dry-run", action="store_true", help="変更内容のプレビュー (ファイル修正なし)")
    parser.add_argument("--no-backup", action="store_true", help="バックアップファイルを生成しない")
    args = parser.parse_args()

    result = migrate(dry_run=args.dry_run, no_backup=args.no_backup)

    if result["status"] == "error":
        print(f"ERROR: {result['message']}")
        sys.exit(1)

    if result["status"] == "skip":
        print(f"INFO: {result['message']}")
        sys.exit(0)

    mode = "DRY RUN" if result["status"] == "dry_run" else "マイグレーション完了"
    print(f"\n{mode}: v{result['from_version']} → v{result['to_version']}")
    print(f"   candidates: {result['total_candidates']}件")

    if "backup_path" in result:
        print(f"   バックアップ: {result['backup_path']}")

    print(f"\n   変更事項 ({len(result['changes'])}件):")
    for change in result["changes"]:
        print(f"   - {change}")

    if result["status"] != "dry_run":
        print("\n   検証: python .quality/scripts/check_scan_status.py")

    print()
    sys.exit(0)


if __name__ == "__main__":
    main()
