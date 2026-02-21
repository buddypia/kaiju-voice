#!/usr/bin/env python3
"""
Wisdom Splitter - 参照頻度基盤 Wisdom 自動分割

根本的解決策:
- よく参照されるパターン (core) vs たまに参照されるパターン (feature) 分離
- セッションあたりのトークンコスト最適化 (coreのみ自動ロード)
- 拡張性確保 (150機能まで対応)
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass

# wisdom_ttl_trackerをimport
import sys
sys.path.insert(0, str(Path(__file__).parent))
from wisdom_ttl_tracker import WisdomTTLTracker, SectionMetadata


@dataclass
class SectionContent:
    """セクション 内容"""
    title: str
    content: str
    metadata: SectionMetadata


class WisdomSplitter:
    """Wisdom 自動分割 時ステム"""

    def __init__(self, wisdom_dir: Path = None):
        self.wisdom_dir = wisdom_dir or Path(".claude/wisdom")
        self.tracker = WisdomTTLTracker(wisdom_dir)
        self.core_threshold = 5  # 5回以上参照 → core

    def split_patterns(self, dry_run: bool = False) -> Dict:
        """project-patterns.mdをcore/featureで分割"""
        source_file = self.wisdom_dir / "project-patterns.md"
        if not source_file.exists():
            raise FileNotFoundError(f"{source_file} ファイルがありません")

        # セクション 抽出
        sections = self._extract_sections_with_content(source_file)

        # core/feature 分類
        core_sections = []
        feature_sections = []

        for section in sections:
            if section.metadata.reference_count >= self.core_threshold:
                core_sections.append(section)
            else:
                feature_sections.append(section)

        # 統計
        result = {
            "source_file": source_file.name,
            "total_sections": len(sections),
            "core_sections": len(core_sections),
            "feature_sections": len(feature_sections),
            "core_threshold": self.core_threshold
        }

        if not dry_run:
            # ファイル 生成
            self._write_split_file("core-patterns.md", core_sections, is_core=True)
            self._write_split_file("feature-patterns.md", feature_sections, is_core=False)

            # 原本 バックアップ
            backup_file = self.wisdom_dir / f"{source_file.name}.backup"
            source_file.rename(backup_file)
            result["backup_file"] = backup_file.name

        return result

    def merge_patterns(self) -> None:
        """core/featureを再び project-patterns.mdでマージ"""
        core_file = self.wisdom_dir / "core-patterns.md"
        feature_file = self.wisdom_dir / "feature-patterns.md"

        if not (core_file.exists() and feature_file.exists()):
            raise FileNotFoundError("core-patterns.md またはは feature-patterns.mdがありません")

        # マージ
        merged_content = "# Project Patterns\n\n"
        merged_content += "> このファイルは core-patterns.mdとfeature-patterns.mdをマージした ものです。\n\n"
        merged_content += "---\n\n"

        merged_content += "## Core Patterns (よく 参照)\n\n"
        merged_content += core_file.read_text(encoding="utf-8").split("\n", 3)[-1]
        merged_content += "\n\n---\n\n"

        merged_content += "## Feature Patterns (たまに 参照)\n\n"
        merged_content += feature_file.read_text(encoding="utf-8").split("\n", 3)[-1]

        output_file = self.wisdom_dir / "project-patterns.md"
        output_file.write_text(merged_content, encoding="utf-8")

        print(f"✅ マージ 完了: {output_file}")

    def _extract_sections_with_content(self, file_path: Path) -> List[SectionContent]:
        """セクション別内容抽出"""
        content = file_path.read_text(encoding="utf-8")
        sections = []

        # ## レベル セクションで分割
        pattern = r'^##\s+(.+?)$\n(.*?)(?=^##\s+|\Z)'
        matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)

        for match in matches:
            title = match.group(1).strip()
            section_content = match.group(2).strip()

            # メタデータ照会
            section_id = self.tracker._normalize_section_id(title)
            all_metadata = self.tracker.get_sections_by_file(file_path.name)
            metadata = next(
                (m for m in all_metadata if m.section_id == section_id),
                None
            )

            if metadata:
                sections.append(SectionContent(
                    title=title,
                    content=section_content,
                    metadata=metadata
                ))

        return sections

    def _write_split_file(
        self,
        filename: str,
        sections: List[SectionContent],
        is_core: bool
    ) -> None:
        """分割されたファイル作成"""
        output_file = self.wisdom_dir / filename

        # ヘッダー
        content = f"# {filename.replace('-', ' ').replace('.md', '').title()}\n\n"

        if is_core:
            content += "> **よく参照される核心パターン**\n"
            content += "> このファイルは 全ての セッションで自動的に ロードされます。\n\n"
        else:
            content += "> **たまに参照される機能別パターン**\n"
            content += "> 必要な時のみ明示的に参照してください。\n\n"

        content += f"合計 {len(sections)}個 セクション (参照 閾値: {self.core_threshold}回)\n\n"
        content += "---\n\n"

        # セクション 追加
        for section in sections:
            content += f"## {section.title}\n\n"
            content += section.content
            content += f"\n\n<!-- 参照: {section.metadata.reference_count}回 -->\n\n"

        output_file.write_text(content, encoding="utf-8")
        print(f"✅ 生成: {filename} ({len(sections)} セクション)")

    def analyze_split_impact(self) -> Dict:
        """分割 影響 分析 (トークン コスト 予測)"""
        source_file = self.wisdom_dir / "project-patterns.md"
        if not source_file.exists():
            raise FileNotFoundError(f"{source_file} ファイルがありません")

        sections = self._extract_sections_with_content(source_file)

        core_size = 0
        feature_size = 0

        for section in sections:
            section_size = len(section.title) + len(section.content)
            if section.metadata.reference_count >= self.core_threshold:
                core_size += section_size
            else:
                feature_size += section_size

        total_size = core_size + feature_size

        return {
            "total_size_bytes": total_size,
            "core_size_bytes": core_size,
            "feature_size_bytes": feature_size,
            "core_percentage": (core_size / total_size * 100) if total_size else 0,
            "estimated_tokens_before": total_size // 4,  # 1 token ≈ 4 bytes
            "estimated_tokens_after": core_size // 4,  # featureはロードしない
            "token_savings": (feature_size // 4),
            "savings_percentage": (feature_size / total_size * 100) if total_size else 0
        }


def main():
    """CLI エントリポイント"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Wisdom Splitter - 参照頻度基盤 自動分割"
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="project-patterns.mdをcore/featureで分割"
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="core/featureを再び マージ"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="分割 影響 分析 (トークン 削減 予測)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際のファイル生成なしでシミュレーションのみ"
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=5,
        help="core 閾値 (基本: 5回)"
    )

    args = parser.parse_args()
    splitter = WisdomSplitter()
    splitter.core_threshold = args.threshold

    if args.analyze:
        print("\n📊 分割 影響 分析")
        print("=" * 60)
        impact = splitter.analyze_split_impact()
        print(f"合計 サイズ: {impact['total_size_bytes']:,} bytes")
        print(f"  Core: {impact['core_size_bytes']:,} bytes ({impact['core_percentage']:.1f}%)")
        print(f"  Feature: {impact['feature_size_bytes']:,} bytes")
        print()
        print(f"トークン コスト:")
        print(f"  分割前: {impact['estimated_tokens_before']:,} トークン/セッション")
        print(f"  分割後: {impact['estimated_tokens_after']:,} トークン/セッション (coreのみ)")
        print(f"  削減: {impact['token_savings']:,} トークン ({impact['savings_percentage']:.1f}%)")

    elif args.split:
        if args.dry_run:
            print("\n🔍 Dry Run モード (実際のファイル生成なし)")
        else:
            print("\n✂️  Wisdom 分割 開始...")

        result = splitter.split_patterns(dry_run=args.dry_run)
        print("=" * 60)
        print(f"原本 ファイル: {result['source_file']}")
        print(f"合計 セクション: {result['total_sections']}")
        print(f"  Core: {result['core_sections']} セクション (≥{result['core_threshold']}回 参照)")
        print(f"  Feature: {result['feature_sections']} セクション")

        if not args.dry_run:
            print(f"\nバックアップ: {result['backup_file']}")
            print("\n✅ 分割 完了")
            print("   core-patterns.md → 全ての セッションでロード")
            print("   feature-patterns.md → 必要 時 参照")

    elif args.merge:
        print("\n🔀 Wisdom マージ 開始...")
        splitter.merge_patterns()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
