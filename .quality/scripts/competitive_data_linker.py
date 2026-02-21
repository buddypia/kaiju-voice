#!/usr/bin/env python3
"""competitive_data_linker.py — 競合分析データをFeature CONTEXT.jsonに連携するスクリプト.

3-Tier Matching Strategy:
  Tier 1 (Exact):    gap-candidates.jsonのexisting_feature_idで直接マッピング
  Tier 2 (Fuzzy):    Featureタイトル vs candidate name トークン類似度 (threshold: 0.5)
  Tier 3 (Hardcoded): ドメイン専門家が手動検証した既知のマッピング

Usage:
  python3 competitive_data_linker.py           # dry-run (変更なし)
  python3 competitive_data_linker.py --apply   # 実際に適用
  python3 competitive_data_linker.py --verbose # 詳細出力
  python3 competitive_data_linker.py --feature 047  # 単一Featureのみ処理
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path Constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURES_DIR = PROJECT_ROOT / "docs" / "features"
GAP_CANDIDATES_PATH = PROJECT_ROOT / "docs" / "analysis" / "gap-candidates.json"
REGISTRY_PATH = PROJECT_ROOT / "docs" / "analysis" / "competitor-registry.json"

# ---------------------------------------------------------------------------
# Gap Severity Priority (高いほど深刻)
# ---------------------------------------------------------------------------
SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "N/A": 0}

# ---------------------------------------------------------------------------
# Tier 3: Hardcoded Known Mappings
# ---------------------------------------------------------------------------
KNOWN_FEATURE_TO_COMP: dict[str, list[str]] = {
    "001": ["comp-011"],    # Bridge Grammar <-> Smart Grammar
    "002": ["comp-031"],    # Nunchi AI Coach <-> 文化/エチケットシナリオ
    "004": ["comp-005"],    # Onboarding Level Test <-> TOPIK/CEFR
    "005": ["comp-016"],    # Core Learning Session <-> コア学習セッション
    "015": ["comp-017"],    # Gamification <-> ゲーミフィケーション
    "024": ["comp-024"],    # AI Tutor <-> AI会話チューター
    "025": ["comp-003"],    # Auth Flow <-> ソーシャルログイン
    "027": ["comp-007"],    # Hangul Learning <-> ハングル発音規則
    "047": ["comp-027"],    # Typing Practice <-> 直接タイピング入力
}


# ---------------------------------------------------------------------------
# Utility: トークン化 + 類似度
# ---------------------------------------------------------------------------
# Fuzzyマッチングで無視するストップワード
_STOP_WORDS = frozenset(
    {"a", "the", "and", "or", "of", "for", "in", "on", "to", "is", "with",
     "ベース", "および", "の", "を", "が", "に", "は", "で", "と", "も", "など", "へ"}
)


def _tokenize(text: str) -> set[str]:
    """テキストを正規化されたトークン集合に変換する。"""
    text = text.lower()
    # 英文+韓国語+数字トークンのみ抽出
    tokens = set(re.findall(r"[a-z0-9]+|[\uac00-\ud7af]+", text))
    return tokens - _STOP_WORDS


def _token_similarity(a: str, b: str) -> float:
    """2つの文字列のトークンJaccard類似度 (0.0 ~ 1.0)。"""
    tokens_a = _tokenize(a)
    tokens_b = _tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_json(path: Path) -> Any:
    """JSONファイルを読み込む。"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    """JSONファイルを保存する (indent=2, ensure_ascii=False)。"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def discover_features(features_dir: Path, feature_filter: str | None = None) -> list[Path]:
    """Featureディレクトリ内のCONTEXT.jsonファイル一覧を探索する。"""
    results = []
    for d in sorted(features_dir.iterdir()):
        if not d.is_dir():
            continue
        # Feature番号を抽出 (例: 001, 047)
        match = re.match(r"^(\d{3})-", d.name)
        if not match:
            continue
        if feature_filter and match.group(1) != feature_filter:
            continue
        ctx_path = d / "CONTEXT.json"
        if ctx_path.exists():
            results.append(ctx_path)
    return results


def extract_feature_number(feature_id: str) -> str:
    """Feature IDから数字部分を抽出する (例: '001-bridge-grammar-engine' -> '001')。"""
    match = re.match(r"^(\d{3})", feature_id)
    return match.group(1) if match else ""


# ---------------------------------------------------------------------------
# Matching Engine
# ---------------------------------------------------------------------------

class CompetitiveLinker:
    """3-Tierマッチングで競合データをFeatureに連結する。"""

    def __init__(self, gap_candidates: dict, registry: dict, verbose: bool = False):
        self.candidates = gap_candidates.get("candidates", [])
        self.registry_features = registry.get("features", [])
        self.verbose = verbose
        self._candidate_by_id: dict[str, dict] = {
            c["comp_id"]: c for c in self.candidates
        }

    def match_feature(self, feature_num: str, feature_title: str) -> dict:
        """Featureにマッチするcomp_idリストを3-Tierで探索する.

        Returns:
            {
                "comp_ids": [...],
                "tiers": {"comp-005": 1, "comp-027": 3},
                "gap_severity": "HIGH",
                "is_industry_standard": True,
                "app_count": 10,
            }
        """
        comp_ids: dict[str, int] = {}  # comp_id -> tier

        # Tier 1: Exact matching via existing_feature_id
        for cand in self.candidates:
            if cand.get("existing_feature_id") == feature_num:
                cid = cand["comp_id"]
                if cid not in comp_ids:
                    comp_ids[cid] = 1
                    if self.verbose:
                        print(f"  [Tier 1] {cid} -> Feature {feature_num} (exact)")

        # Tier 3: Hardcoded (先に適用 — Tier 2より信頼度が高い)
        if feature_num in KNOWN_FEATURE_TO_COMP:
            for cid in KNOWN_FEATURE_TO_COMP[feature_num]:
                if cid not in comp_ids:
                    comp_ids[cid] = 3
                    if self.verbose:
                        print(f"  [Tier 3] {cid} -> Feature {feature_num} (hardcoded)")

        # Tier 2: Fuzzy matching via token similarity
        for cand in self.candidates:
            cid = cand["comp_id"]
            if cid in comp_ids:
                continue  # 既にマッチ済み
            sim = _token_similarity(feature_title, cand.get("name", ""))
            if sim >= 0.5:
                comp_ids[cid] = 2
                if self.verbose:
                    print(f"  [Tier 2] {cid} ({cand['name']}) -> Feature {feature_num} "
                          f"(similarity={sim:.2f})")

        if not comp_ids:
            return {
                "comp_ids": [],
                "tiers": {},
                "gap_severity": "N/A",
                "is_industry_standard": False,
                "app_count": 0,
            }

        # Aggregate: gap_severity (最高深刻度), is_industry_standard (OR), app_count (最大)
        max_severity = "N/A"
        any_industry_standard = False
        max_app_count = 0

        for cid in comp_ids:
            cand = self._candidate_by_id.get(cid)
            if not cand:
                continue
            sev = cand.get("gap_severity", "N/A")
            if SEVERITY_ORDER.get(sev, 0) > SEVERITY_ORDER.get(max_severity, 0):
                max_severity = sev
            if cand.get("is_industry_standard", False):
                any_industry_standard = True
            ac = cand.get("app_count", 0)
            if ac > max_app_count:
                max_app_count = ac

        return {
            "comp_ids": sorted(comp_ids.keys()),
            "tiers": comp_ids,
            "gap_severity": max_severity,
            "is_industry_standard": any_industry_standard,
            "app_count": max_app_count,
        }


# ---------------------------------------------------------------------------
# CONTEXT.json Updater
# ---------------------------------------------------------------------------

def update_context(ctx_data: dict, match_result: dict) -> bool:
    """CONTEXT.jsonにcompetitive_dataを追加/更新する。変更有無を返す。"""
    if not match_result["comp_ids"]:
        return False

    now = datetime.now(timezone.utc).isoformat()
    new_competitive_data = {
        "comp_ids": match_result["comp_ids"],
        "gap_severity": match_result["gap_severity"],
        "is_industry_standard": match_result["is_industry_standard"],
        "app_count": match_result["app_count"],
        "linked_at": now,
    }

    # 既存データとの比較 (linked_at を除外)
    existing = ctx_data.get("competitive_data")
    if existing:
        existing_cmp = {k: v for k, v in existing.items() if k != "linked_at"}
        new_cmp = {k: v for k, v in new_competitive_data.items() if k != "linked_at"}
        if existing_cmp == new_cmp:
            return False

    # 1. Root-level competitive_data
    ctx_data["competitive_data"] = new_competitive_data

    # 2. references.research_links.comp_ids
    refs = ctx_data.get("references")
    if refs is None:
        ctx_data["references"] = {}
        refs = ctx_data["references"]
    rl = refs.get("research_links")
    if rl is None:
        refs["research_links"] = {}
        rl = refs["research_links"]
    rl["comp_ids"] = match_result["comp_ids"]

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="競合分析データをFeature CONTEXT.jsonに連携する"
    )
    parser.add_argument("--apply", action="store_true", help="実際のファイルに適用 (デフォルト: dry-run)")
    parser.add_argument("--verbose", action="store_true", help="詳細出力")
    parser.add_argument("--feature", type=str, default=None, help="単一Feature番号 (例: 047)")
    args = parser.parse_args()

    # Feature番号の正規化 (3桁ゼロ埋め)
    feature_filter = None
    if args.feature:
        feature_filter = args.feature.zfill(3)

    # データソースの検証
    if not GAP_CANDIDATES_PATH.exists():
        print(f"ERROR: gap-candidates.json not found: {GAP_CANDIDATES_PATH}", file=sys.stderr)
        return 1
    if not REGISTRY_PATH.exists():
        print(f"ERROR: competitor-registry.json not found: {REGISTRY_PATH}", file=sys.stderr)
        return 1

    gap_data = load_json(GAP_CANDIDATES_PATH)
    registry_data = load_json(REGISTRY_PATH)

    linker = CompetitiveLinker(gap_data, registry_data, verbose=args.verbose)

    # Feature探索
    ctx_paths = discover_features(FEATURES_DIR, feature_filter)
    if not ctx_paths:
        print("WARNING: No CONTEXT.json files found.", file=sys.stderr)
        return 0

    mode_label = "APPLY" if args.apply else "DRY-RUN"
    print(f"\n=== Competitive Data Linker [{mode_label}] ===")
    print(f"Features: {len(ctx_paths)}, Candidates: {len(gap_data.get('candidates', []))}")
    print()

    # Summary table header
    results: list[dict] = []
    updated_count = 0
    skipped_count = 0

    for ctx_path in ctx_paths:
        ctx_data = load_json(ctx_path)
        feature_id = ctx_data.get("feature_id", ctx_path.parent.name)
        feature_num = extract_feature_number(feature_id)
        feature_title = ctx_data.get("title", "")

        if args.verbose:
            print(f"--- Feature {feature_num}: {feature_title} ---")

        match_result = linker.match_feature(feature_num, feature_title)

        changed = update_context(ctx_data, match_result)

        if changed:
            updated_count += 1
            if args.apply:
                save_json(ctx_path, ctx_data)
        else:
            skipped_count += 1

        # Tier情報を人間が読める形式に変換
        tier_info = ""
        if match_result["tiers"]:
            tiers_used = sorted(set(match_result["tiers"].values()))
            tier_info = ",".join(f"T{t}" for t in tiers_used)

        results.append({
            "feature_id": feature_num,
            "title": feature_title[:30],
            "comp_ids": match_result["comp_ids"],
            "match_tier": tier_info,
            "gap_severity": match_result["gap_severity"],
            "changed": changed,
        })

    # Summary table
    print(f"{'Feature':>8}  {'Title':<32} {'Comp IDs':<30} {'Tier':<6} {'Severity':<10} {'Status':<8}")
    print("-" * 100)
    for r in results:
        comp_str = ", ".join(r["comp_ids"]) if r["comp_ids"] else "-"
        status = "UPDATED" if r["changed"] else "skip"
        print(f"{r['feature_id']:>8}  {r['title']:<32} {comp_str:<30} {r['match_tier']:<6} "
              f"{r['gap_severity']:<10} {status:<8}")

    print("-" * 100)
    print(f"Total: {len(results)} features | Updated: {updated_count} | Skipped: {skipped_count}")
    if not args.apply and updated_count > 0:
        print(f"\n(Dry-runモード: --applyフラグで実行すると{updated_count}件のファイルが変更されます)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
