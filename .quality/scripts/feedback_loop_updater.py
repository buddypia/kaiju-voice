#!/usr/bin/env python3
"""
feedback_loop_updater.py — Feature "Done" 時に gap-candidates/competitor-registry を更新。

Feature が Done 状態に到達した場合:
  - gap-candidates.json: 該当 candidate の already_tracked, existing_feature_id, recommended_action を更新
  - competitor-registry.json: 該当 feature の hackathon_project_depth を最低 3 に更新

Usage:
    python3 feedback_loop_updater.py                # dry-run (全体)
    python3 feedback_loop_updater.py --apply        # 全体適用
    python3 feedback_loop_updater.py --feature 001  # 特定 Feature のみ
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Project Root ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURES_DIR = PROJECT_ROOT / "docs" / "features"
REGISTRY_PATH = PROJECT_ROOT / "docs" / "analysis" / "competitor-registry.json"
GAP_CANDIDATES_PATH = PROJECT_ROOT / "docs" / "analysis" / "gap-candidates.json"
EXCLUDE_DIRS = {"_templates", "candidates", "priority"}


def _load_json(path: Path) -> dict | None:
    """JSON ファイルをロードする。"""
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_json(path: Path, data: dict) -> None:
    """JSON ファイルを保存する。"""
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _discover_features(feature_filter: str | None) -> list[Path]:
    """Feature ディレクトリを探索する。"""
    if not FEATURES_DIR.exists():
        return []

    dirs = sorted(
        d
        for d in FEATURES_DIR.iterdir()
        if d.is_dir() and d.name not in EXCLUDE_DIRS and re.match(r"\d{3}-", d.name)
    )

    if feature_filter:
        dirs = [d for d in dirs if d.name.startswith(feature_filter)]

    return dirs


def _extract_feature_number(feature_id: str) -> str:
    """Feature ID から 3 桁の数字を抽出する。'001-bridge-grammar-engine' → '001'"""
    match = re.match(r"(\d{3})", feature_id)
    return match.group(1) if match else feature_id


def _find_done_features_with_comp_ids(
    dirs: list[Path],
) -> list[dict]:
    """Done 状態の Feature のうち competitive_data.comp_ids があるものを収集する。

    schema v5 以前の Feature は competitor-registry の hackathon_project_coverage 逆引きで補完。
    """
    results = []
    for d in dirs:
        ctx = _load_json(d / "CONTEXT.json")
        if not ctx:
            continue

        state = ctx.get("quick_resume", {}).get("current_state", "")
        if state != "Done":
            continue

        feature_num = _extract_feature_number(d.name)

        # Schema v5: competitive_data.comp_ids を直接参照
        comp_data = ctx.get("competitive_data", {})
        comp_ids = comp_data.get("comp_ids", []) if comp_data else []

        results.append(
            {
                "feature_dir": d,
                "feature_id": d.name,
                "feature_num": feature_num,
                "comp_ids": list(comp_ids),  # コピー
            }
        )

    return results


def _reverse_lookup_comp_ids(
    registry: dict, feature_num: str
) -> list[str]:
    """competitor-registry から hackathon_project_coverage が feature_num である comp_id を逆引きする。"""
    comp_ids = []
    for feat in registry.get("features", []):
        coverage = feat.get("hackathon_project_coverage") or ""
        # "005", "005-partial", "001,034" 等のパターン
        coverage_nums = [c.strip().split("-")[0] for c in coverage.split(",")]
        if feature_num in coverage_nums:
            comp_ids.append(feat["id"])
    return comp_ids


def update_gap_candidates(
    gap_data: dict,
    done_features: list[dict],
    registry: dict | None,
) -> list[dict]:
    """gap-candidates.json を更新し、変更履歴を返す。"""
    changes: list[dict] = []
    candidates = gap_data.get("candidates", [])

    # feature_num → comp_ids マッピングを構築
    feature_comp_map: dict[str, list[str]] = {}
    for feat in done_features:
        comp_ids = feat["comp_ids"]
        # comp_ids がなければ registry を逆引き
        if not comp_ids and registry:
            comp_ids = _reverse_lookup_comp_ids(registry, feat["feature_num"])
        feature_comp_map[feat["feature_num"]] = comp_ids

    for candidate in candidates:
        comp_id = candidate.get("comp_id", "")
        for feat_num, comp_ids in feature_comp_map.items():
            if comp_id in comp_ids:
                old_tracked = candidate.get("already_tracked", False)
                old_action = candidate.get("recommended_action", "")
                old_feature_id = candidate.get("existing_feature_id")

                needs_update = (
                    not old_tracked
                    or old_action != "completed"
                    or old_feature_id != feat_num
                )

                if needs_update:
                    candidate["already_tracked"] = True
                    candidate["existing_feature_id"] = feat_num
                    candidate["recommended_action"] = "completed"
                    changes.append(
                        {
                            "comp_id": comp_id,
                            "feature_num": feat_num,
                            "field": "gap-candidates",
                            "old": {
                                "already_tracked": old_tracked,
                                "recommended_action": old_action,
                                "existing_feature_id": old_feature_id,
                            },
                            "new": {
                                "already_tracked": True,
                                "recommended_action": "completed",
                                "existing_feature_id": feat_num,
                            },
                        }
                    )
                break  # 1つの candidate に対して最初にマッチした feature のみ

    return changes


def update_competitor_registry(
    registry: dict,
    done_features: list[dict],
) -> list[dict]:
    """competitor-registry.json の hackathon_project_depth を更新する。"""
    changes: list[dict] = []
    features_list = registry.get("features", [])

    # feature_num → comp_ids マッピング
    feature_comp_map: dict[str, list[str]] = {}
    for feat in done_features:
        comp_ids = feat["comp_ids"]
        if not comp_ids:
            comp_ids = _reverse_lookup_comp_ids(registry, feat["feature_num"])
        feature_comp_map[feat["feature_num"]] = comp_ids

    for reg_feat in features_list:
        comp_id = reg_feat.get("id", "")
        for feat_num, comp_ids in feature_comp_map.items():
            if comp_id in comp_ids:
                old_depth = reg_feat.get("hackathon_project_depth", 0) or 0
                if old_depth < 3:
                    reg_feat["hackathon_project_depth"] = 3
                    changes.append(
                        {
                            "comp_id": comp_id,
                            "feature_num": feat_num,
                            "field": "competitor-registry.hackathon_project_depth",
                            "old": old_depth,
                            "new": 3,
                        }
                    )
                break

    return changes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Feature Done 状態時の gap-candidates/competitor-registry フィードバックループ更新"
    )
    parser.add_argument("--apply", action="store_true", help="実際のファイルに適用")
    parser.add_argument("--feature", type=str, help="特定の Feature ID (例: 001)")
    args = parser.parse_args()

    feature_filter = args.feature
    if feature_filter and not feature_filter.endswith("-"):
        feature_filter = feature_filter if "-" in feature_filter else f"{feature_filter}-"

    dirs = _discover_features(feature_filter)
    if not dirs:
        print("対象の Feature がありません。")
        sys.exit(0)

    # データロード
    gap_data = _load_json(GAP_CANDIDATES_PATH)
    registry = _load_json(REGISTRY_PATH)

    if not gap_data:
        print(f"WARNING: {GAP_CANDIDATES_PATH} のロードに失敗しました")
        gap_data = {"candidates": []}

    if not registry:
        print(f"WARNING: {REGISTRY_PATH} のロードに失敗しました")
        registry = {"features": []}

    # Done Feature の収集
    done_features = _find_done_features_with_comp_ids(dirs)

    if not done_features:
        print("Done 状態の Feature がありません。")
        sys.exit(0)

    print(f"Done 状態の Feature: {len(done_features)}件")
    for f in done_features:
        comp_ids = f["comp_ids"]
        if not comp_ids:
            comp_ids = _reverse_lookup_comp_ids(registry, f["feature_num"])
        print(f"  {f['feature_id']} → comp_ids: {comp_ids or '(逆引き予定)'}")

    # 更新
    gap_changes = update_gap_candidates(gap_data, done_features, registry)
    reg_changes = update_competitor_registry(registry, done_features)

    all_changes = gap_changes + reg_changes

    # 結果出力
    print()
    if not all_changes:
        print("変更事項はありません (既に最新の状態です)。")
    else:
        print(f"{'Comp ID':<14} {'Feature':<8} {'Field':<42} {'Old':<20} {'New'}")
        print("-" * 100)
        for c in all_changes:
            if c["field"] == "gap-candidates":
                old_str = c["old"]["recommended_action"] or "null"
                new_str = c["new"]["recommended_action"]
            else:
                old_str = str(c["old"])
                new_str = str(c["new"])
            print(f"{c['comp_id']:<14} {c['feature_num']:<8} {c['field']:<42} {old_str:<20} {new_str}")

        print("-" * 100)
        print(f"gap-candidates 変更: {len(gap_changes)} | competitor-registry 変更: {len(reg_changes)}")

    # 適用
    if args.apply and all_changes:
        if gap_changes:
            _save_json(GAP_CANDIDATES_PATH, gap_data)
            print(f"\n[APPLIED] {GAP_CANDIDATES_PATH.relative_to(PROJECT_ROOT)}")
        if reg_changes:
            _save_json(REGISTRY_PATH, registry)
            print(f"[APPLIED] {REGISTRY_PATH.relative_to(PROJECT_ROOT)}")
    elif all_changes:
        print("\n[DRY-RUN] --apply フラグで実行するとファイルが更新されます。")


if __name__ == "__main__":
    main()
