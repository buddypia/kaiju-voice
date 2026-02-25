#!/usr/bin/env python3
"""
Research Gap Analyzer Script

プロジェクト プロジェクトの機能とリサーチ文書を分析してギャップを識別します。

Usage:
    python analyze_gaps.py --features-dir <path> --research-dir <path>
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

@dataclass
class ResearchGap:
    """リサーチギャップ情報"""
    kpi: str
    area: str
    priority: str
    related_features: List[str]
    expected_filename_pattern: str
    status: str  # missing, incomplete, outdated

@dataclass
class AnalysisResult:
    """分析結果"""
    total_features: int
    total_research_files: int
    gaps: List[ResearchGap]
    coverage_rate: float
    timestamp: str

# KPI別必須リサーチ領域 (gap-analysis-matrix.md 基準)
REQUIRED_RESEARCH = {
    "d7_retention": [
        ("FTUE 最適化", "ftue-|first-time-user", "P0", ["004", "023"]),
        ("Day 1-7 学習ジャーニー", "early-retention-|day-1-7", "P0", ["005", "006"]),
        ("習慣形成心理学", "habit-formation-|habit-psychology", "P1", ["006", "015"]),
        ("通知最適化", "notification-optimization", "P1", ["010"]),
    ],
    "conversion_8pct": [
        ("ペイウォール UX", "paywall-ux|paywall-optimization", "P0", ["008"]),
        ("価格弾力性", "price-elasticity|pricing-sensitivity", "P0", ["008"]),
        ("無料-有料 価値差別化", "free-premium-|freemium-value", "P0", ["008"]),
        ("コンバージョントリガー", "conversion-trigger|purchase-trigger", "P1", ["008", "005"]),
    ],
    "churn_under_8pct": [
        ("サブスクリプション更新失敗", "renewal-failure|subscription-renewal", "P0", ["008"]),
        ("長期維持戦略", "long-term-retention|customer-lifetime", "P0", ["019"]),
        ("離脱予測モデル", "churn-prediction|churn-model", "P1", ["019"]),
        ("再活性化キャンペーン", "reactivation-|win-back", "P1", ["010", "019"]),
    ],
    "ltv_30plus": [
        ("LTV シミュレーション", "ltv-simulation|lifetime-value-model", "P0", ["008"]),
        ("アップセルタイミング", "upsell-timing|upgrade-timing", "P0", ["008"]),
        ("顧客セグメント", "customer-segment|user-segment", "P1", ["008", "019"]),
        ("年間サブスクリプション転換", "annual-subscription|yearly-plan", "P1", ["008"]),
    ],
    "ai_upgrade_20pct": [
        ("AI 機能価値認識", "ai-feature-value|ai-perception", "P0", ["024", "002"]),
        ("アップグレードトリガー", "upgrade-trigger|tier-upgrade", "P0", ["008", "024"]),
        ("AI 使用量セグメンテーション", "ai-usage-segment|usage-pattern", "P1", ["020"]),
    ],
}

def scan_research_files(research_dir: Path) -> Set[str]:
    """リサーチファイルスキャン"""
    research_files = set()
    if research_dir.exists():
        for file in research_dir.glob("*.md"):
            research_files.add(file.stem.lower())
    return research_files

def scan_features(features_dir: Path) -> List[str]:
    """機能フォルダスキャン"""
    features = []
    if features_dir.exists():
        for folder in features_dir.iterdir():
            if folder.is_dir() and folder.name[0].isdigit():
                features.append(folder.name.split("-")[0])
    return sorted(features)

def check_pattern_match(research_files: Set[str], pattern: str) -> bool:
    """パターンマッチング確認"""
    patterns = pattern.split("|")
    for file in research_files:
        for p in patterns:
            if re.search(p, file):
                return True
    return False

def analyze_gaps(features_dir: Path, research_dir: Path) -> AnalysisResult:
    """ギャップ分析実行"""
    research_files = scan_research_files(research_dir)
    features = scan_features(features_dir)
    gaps = []

    total_areas = 0
    covered_areas = 0

    for kpi, areas in REQUIRED_RESEARCH.items():
        for area_name, pattern, priority, related in areas:
            total_areas += 1
            if check_pattern_match(research_files, pattern):
                covered_areas += 1
            else:
                gaps.append(ResearchGap(
                    kpi=kpi,
                    area=area_name,
                    priority=priority,
                    related_features=related,
                    expected_filename_pattern=pattern,
                    status="missing"
                ))

    coverage_rate = (covered_areas / total_areas * 100) if total_areas > 0 else 0

    return AnalysisResult(
        total_features=len(features),
        total_research_files=len(research_files),
        gaps=gaps,
        coverage_rate=round(coverage_rate, 1),
        timestamp=datetime.now().isoformat()
    )

def generate_report(result: AnalysisResult) -> str:
    """レポート生成"""
    report = []
    report.append("# Research Gap Analysis Report")
    report.append(f"\n生成時刻: {result.timestamp}")
    report.append(f"\n## 要約")
    report.append(f"- 分析機能数: {result.total_features}")
    report.append(f"- 既存リサーチ数: {result.total_research_files}")
    report.append(f"- カバレッジ: {result.coverage_rate}%")
    report.append(f"- 識別されたギャップ: {len(result.gaps)}件")

    # 優先順位別グループ化
    p0_gaps = [g for g in result.gaps if g.priority == "P0"]
    p1_gaps = [g for g in result.gaps if g.priority == "P1"]

    report.append(f"\n## P0 ギャップ (即時解決必要)")
    for gap in p0_gaps:
        report.append(f"- [{gap.kpi}] {gap.area}")
        report.append(f"  - 関連機能: {', '.join(gap.related_features)}")
        report.append(f"  - パターン: {gap.expected_filename_pattern}")

    report.append(f"\n## P1 ギャップ (重要)")
    for gap in p1_gaps:
        report.append(f"- [{gap.kpi}] {gap.area}")
        report.append(f"  - 関連機能: {', '.join(gap.related_features)}")

    return "\n".join(report)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Research Gap Analyzer")
    parser.add_argument("--features-dir", required=True, help="Features directory path")
    parser.add_argument("--research-dir", required=True, help="Research directory path")
    parser.add_argument("--output", help="Output file path (optional)")

    args = parser.parse_args()

    features_path = Path(args.features_dir)
    research_path = Path(args.research_dir)

    result = analyze_gaps(features_path, research_path)
    report = generate_report(result)

    print(report)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"\nレポート保存: {args.output}")
