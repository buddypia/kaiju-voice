#!/usr/bin/env python3
"""
Wisdom TTL Tracker - Wisdom セクション別参照追跡およびライフサイクル管理

根本的解決策:
- セクション別参照時間追跡
- 30日以上未参照セクション自動検出
- 参照頻度基盤 優先順位 決定
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class SectionTier(Enum):
    """セクション 階層 (参照頻度基盤)"""
    HOT = "hot"      # 7日 以内 参照
    WARM = "warm"    # 7~30日 以内 参照
    COLD = "cold"    # 30日 以上 未参照


@dataclass
class SectionMetadata:
    """セクション メタデータ"""
    file_name: str
    section_id: str
    last_referenced: str  # ISO 8601
    reference_count: int
    created_at: str  # ISO 8601

    @property
    def last_ref_datetime(self) -> datetime:
        return datetime.fromisoformat(self.last_referenced)

    @property
    def days_since_reference(self) -> int:
        return (datetime.now() - self.last_ref_datetime).days

    @property
    def tier(self) -> SectionTier:
        days = self.days_since_reference
        if days <= 7:
            return SectionTier.HOT
        elif days <= 30:
            return SectionTier.WARM
        else:
            return SectionTier.COLD


class WisdomTTLTracker:
    """Wisdom TTL 追跡 システム"""

    def __init__(self, wisdom_dir: Path = None):
        self.wisdom_dir = wisdom_dir or Path(".claude/wisdom")
        self.metadata_file = self.wisdom_dir / ".metadata.json"
        self.ttl_days = 30

    def track_reference(self, file_name: str, section_id: str) -> None:
        """セクション 参照 時の メタデータ 更新"""
        metadata = self._load_metadata()
        key = self._make_key(file_name, section_id)

        now = datetime.now().isoformat()

        if key in metadata:
            # 既存 セクション 更新
            section = SectionMetadata(**metadata[key])
            section.last_referenced = now
            section.reference_count += 1
            metadata[key] = asdict(section)
        else:
            # 新規 セクション 生成
            section = SectionMetadata(
                file_name=file_name,
                section_id=section_id,
                last_referenced=now,
                reference_count=1,
                created_at=now
            )
            metadata[key] = asdict(section)

        self._save_metadata(metadata)

    def find_cold_sections(self, min_days: int = None) -> List[SectionMetadata]:
        """COLD セクション 検出"""
        min_days = min_days or self.ttl_days
        metadata = self._load_metadata()
        cold_sections = []

        for key, data in metadata.items():
            section = SectionMetadata(**data)
            if section.days_since_reference >= min_days:
                cold_sections.append(section)

        # 古い 順 + 参照 少ない順 ソート
        return sorted(
            cold_sections,
            key=lambda s: (s.days_since_reference, -s.reference_count),
            reverse=True
        )

    def get_statistics(self) -> Dict:
        """全体 統計 生成"""
        metadata = self._load_metadata()
        sections = [SectionMetadata(**data) for data in metadata.values()]

        tier_counts = {
            SectionTier.HOT: 0,
            SectionTier.WARM: 0,
            SectionTier.COLD: 0
        }

        total_refs = 0
        for section in sections:
            tier_counts[section.tier] += 1
            total_refs += section.reference_count

        return {
            "total_sections": len(sections),
            "total_references": total_refs,
            "hot_sections": tier_counts[SectionTier.HOT],
            "warm_sections": tier_counts[SectionTier.WARM],
            "cold_sections": tier_counts[SectionTier.COLD],
            "cold_percentage": (tier_counts[SectionTier.COLD] / len(sections) * 100)
                               if sections else 0
        }

    def get_sections_by_file(self, file_name: str) -> List[SectionMetadata]:
        """特定 ファイルの全ての セクション 照会"""
        metadata = self._load_metadata()
        return [
            SectionMetadata(**data)
            for data in metadata.values()
            if data["file_name"] == file_name
        ]

    def initialize_from_files(self) -> int:
        """既存 Wisdom ファイルでセクション 抽出 および 初期化"""
        count = 0
        for md_file in self.wisdom_dir.glob("*.md"):
            if md_file.name.startswith("."):
                continue

            sections = self._extract_sections(md_file)
            for section_id in sections:
                self.track_reference(md_file.name, section_id)
                count += 1

        return count

    def _extract_sections(self, file_path: Path) -> List[str]:
        """マークダウン ファイルで## レベル セクション 抽出"""
        content = file_path.read_text(encoding="utf-8")
        pattern = r'^##\s+(.+)$'
        matches = re.findall(pattern, content, re.MULTILINE)
        return [self._normalize_section_id(m) for m in matches]

    def _normalize_section_id(self, section_title: str) -> str:
        """セクション タイトル 正規化 (ID化)"""
        # "1. Title" → "title"
        # "Title (detail)" → "title-detail"
        normalized = re.sub(r'^\d+\.\s+', '', section_title)
        normalized = normalized.lower()
        normalized = re.sub(r'[^\w\s-]', '', normalized)
        normalized = re.sub(r'[\s_]+', '-', normalized)
        return normalized.strip('-')

    def _make_key(self, file_name: str, section_id: str) -> str:
        """メタデータ キー 生成"""
        return f"{file_name}#{section_id}"

    def _load_metadata(self) -> Dict:
        """メタデータ ロード"""
        if self.metadata_file.exists():
            return json.loads(self.metadata_file.read_text(encoding="utf-8"))
        return {}

    def _save_metadata(self, data: Dict) -> None:
        """メタデータ 保存"""
        self.metadata_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )


def main():
    """CLI エントリポイント"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Wisdom TTL Tracker - セクション別参照追跡およびライフサイクル管理"
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="既存 Wisdom ファイルでセクション 初期化"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="全体 統計 出力"
    )
    parser.add_argument(
        "--list-cold",
        type=int,
        nargs="?",
        const=30,
        metavar="DAYS",
        help="COLD セクション リスト (基本: 30日)"
    )
    parser.add_argument(
        "--track",
        nargs=2,
        metavar=("FILE", "SECTION"),
        help="セクション 参照 追跡"
    )

    args = parser.parse_args()
    tracker = WisdomTTLTracker()

    if args.init:
        print("🔄 Wisdom ファイルでセクション 初期化 中...")
        count = tracker.initialize_from_files()
        print(f"✅ {count}個 セクション 初期化 完了")
        print(f"📄 メタデータ: {tracker.metadata_file}")

    elif args.stats:
        stats = tracker.get_statistics()
        print("\n📊 Wisdom 統計")
        print("=" * 50)
        print(f"合計 セクション: {stats['total_sections']}")
        print(f"合計 参照: {stats['total_references']}")
        print(f"\n🔥 HOT (7日 以内): {stats['hot_sections']}")
        print(f"🔶 WARM (8-30日): {stats['warm_sections']}")
        print(f"❄️  COLD (30日+): {stats['cold_sections']} ({stats['cold_percentage']:.1f}%)")

    elif args.list_cold is not None:
        cold = tracker.find_cold_sections(min_days=args.list_cold)
        if not cold:
            print(f"✅ {args.list_cold}日 以上 参照 セクション なし")
        else:
            print(f"\n❄️  COLD セクション ({args.list_cold}日 以上 参照)")
            print("=" * 70)
            for section in cold[:10]:  # 上位 10個のみ
                print(f"{section.file_name}#{section.section_id}")
                print(f"  ⏰ {section.days_since_reference}日 前 参照")
                print(f"  📈 合計 {section.reference_count}回 参照")
                print()

    elif args.track:
        file_name, section_id = args.track
        tracker.track_reference(file_name, section_id)
        print(f"✅ 参照 追跡: {file_name}#{section_id}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
