#!/usr/bin/env python3
"""
SPEC バリデータ v3.1

SPEC 文書の完全性と Tier/MVS 準拠状況を検証します。

Usage:
    python validate_spec.py <spec_file>
    python validate_spec.py docs/features/001-bridge-grammar-engine/SPEC-001-bridge-grammar-engine.md

Exit codes:
    0: 検証通過
    1: MVS 未達（実装禁止）
    2: Tier 必須要素未達（警告）
"""

import re
import sys
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationResult:
    """検証結果"""
    passed: bool
    mvs_passed: bool
    tier_passed: bool
    tier: Optional[int] = None
    feature_type: Optional[str] = None
    missing_mvs: list = field(default_factory=list)
    missing_tier: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    arb_issues: list = field(default_factory=list)


class SpecValidator:
    """SPEC 文書バリデータ"""

    # MVS (Minimum Viable SPEC) 必須セクション
    MVS_REQUIRED = [
        (r'#{2,4}\s*0\.0\.2\s+', '§0.0.2 Naming Conventions'),
        (r'#{2,4}\s*0\.1\s+', '§0.1 Target Files'),
        (r'#{2,4}\s*1\.4\s+', '§1.4 Goals / Non-Goals'),
        (r'#{2,4}\s*FR-\d+', '§2 FR with AC'),
        (r'#{2,4}\s*6\.2\s+', '§6.2 Required i18n Keys'),
    ]

    # Tier 別必須セクション
    TIER_SECTIONS = {
        1: [  # High Risk
            (r'#{2,4}\s*0\.2\.2\s+', '§0.2.2 Provider Specifications'),
            (r'#{2,4}\s*0\.3\s+', '§0.3 Error Handling'),
            (r'#{2,4}\s*0\.9\s+', '§0.9 Design Tokens'),
            (r'#{2,4}\s*1\.5\s+', '§1.5 Screen Flow'),
            (r'#{2,4}\s*3\.4\s+', '§3.4 Sequence Diagrams'),
            (r'#{2,4}\s*5\s+', '§5 検証 & テスト'),
        ],
        2: [  # Medium Risk
            (r'#{2,4}\s*0\.2\.2\s+', '§0.2.2 Provider Specifications'),
            (r'#{2,4}\s*0\.3\s+', '§0.3 Error Handling'),
            (r'#{2,4}\s*0\.9\s+', '§0.9 Design Tokens'),
            (r'#{2,4}\s*1\.5\s+', '§1.5 Screen Flow'),
            (r'#{2,4}\s*3\.4\s+', '§3.4 Sequence Diagrams'),
        ],
        3: [  # Low Risk - MVS のみ必須
        ],
    }

    # AI 使用機能必須セクション
    AI_REQUIRED = [
        (r'#{2,4}\s*0\.7\s+', '§0.7 AI Logic & Prompts'),
        (r'#{2,4}\s*0\.8\s+', '§0.8 Safety & Guardrails'),
    ]

    # API 連携機能必須セクション
    API_REQUIRED = [
        (r'#{2,4}\s*0\.4\s+', '§0.4 Data Schema & Security'),
        (r'#{2,4}\s*0\.5\s+', '§0.5 API Contract'),
    ]

    def __init__(self, spec_path: Path):
        self.spec_path = spec_path
        self.content = spec_path.read_text(encoding='utf-8')

    def extract_tier(self) -> Optional[int]:
        """SPEC から Tier を抽出"""
        # Tier: {1/2/3} パターン検索
        match = re.search(r'\*\*Tier\*\*:\s*(\d)', self.content)
        if match:
            return int(match.group(1))
        # Tier: 1 (High Risk) パターン
        match = re.search(r'Tier.*?(\d)\s*[-–]\s*(High|Medium|Low)', self.content, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def extract_feature_type(self) -> Optional[str]:
        """SPEC から機能タイプを抽出"""
        # 機能タイプ: {UI Only/API 連携/AI 使用/決済}
        match = re.search(r'\*\*機能タイプ\*\*:\s*(\w+)', self.content)
        if match:
            return match.group(1).lower()

        # AI 関連キーワードで推論
        if re.search(r'(AI|LLM|Gemini|GPT)', self.content, re.IGNORECASE):
            if re.search(r'#{2,4}\s*0\.7', self.content):
                return 'ai'

        # API/Edge Function 関連キーワードで推論
        if re.search(r'(Edge Function|API Contract|エンドポイント)', self.content):
            return 'api'

        return 'ui'

    def check_section_exists(self, pattern: str) -> bool:
        """セクション存在確認"""
        return bool(re.search(pattern, self.content, re.MULTILINE))

    def check_na_section(self, pattern: str) -> bool:
        """セクションが N/A と明示されているか確認"""
        # セクションヘッダーの後に N/A があるか確認
        match = re.search(f'{pattern}.*?\n(.*?)\n', self.content, re.DOTALL)
        if match:
            content_after = match.group(1)
            return 'N/A' in content_after or '該当なし' in content_after
        return False

    def extract_arb_keys(self) -> list[str]:
        """SPEC で定義された ARB キーを抽出"""
        keys = []
        # §6.2 Required Keys テーブルから抽出
        # | `lesson_title` | レッスン | ... パターン
        pattern = r'\|\s*`?(\w+)`?\s*\|'
        in_i18n_section = False

        for line in self.content.split('\n'):
            if '6.2' in line and 'i18n' in line.lower():
                in_i18n_section = True
            elif in_i18n_section and line.startswith('|'):
                match = re.search(r'\|\s*`?([a-zA-Z_]+[a-zA-Z0-9_]*)`?\s*\|', line)
                if match and match.group(1) not in ['ARB', 'キー', '用途', 'ja', 'en']:
                    keys.append(match.group(1))
            elif in_i18n_section and line.startswith('#'):
                break

        return keys

    def check_arb_file(self, arb_keys: list[str]) -> list[str]:
        """ARB ファイルにキーが存在するか確認"""
        arb_path = self.spec_path.parent.parent.parent.parent / 'lib/l10n/app_ja.arb'
        if not arb_path.exists():
            return [f"ARB ファイルなし: {arb_path}"]

        try:
            arb_content = arb_path.read_text(encoding='utf-8')
            arb_data = json.loads(arb_content)
        except (json.JSONDecodeError, Exception) as e:
            return [f"ARB ファイルパースエラー: {e}"]

        missing = []
        for key in arb_keys:
            if key not in arb_data:
                missing.append(f"ARB キー欠落: {key}")

        return missing

    def check_quantified_ac(self) -> list[str]:
        """AC の Then が定量化されているか確認"""
        warnings = []

        # AC テーブル検索
        ac_pattern = r'\|\s*AC\d+\s*\|.*?\|.*?\|.*?\|(.*?)\|'
        matches = re.findall(ac_pattern, self.content)

        quantified_patterns = [
            r'\d+\s*(ms|秒|s|分|個|%|以上|以下|以内|未満)',
            r'(true|false|null)',
            r'(=|>|<|≥|≤)',
            r'\[.*?\]',  # [定量基準] 形式
        ]

        for i, then_clause in enumerate(matches, 1):
            is_quantified = any(
                re.search(p, then_clause, re.IGNORECASE)
                for p in quantified_patterns
            )
            if not is_quantified and '{' not in then_clause:  # テンプレート変数除外
                warnings.append(f"AC{i} の Then 節に定量基準なし: '{then_clause.strip()}'")

        return warnings

    def validate(self) -> ValidationResult:
        """全体検証実行"""
        result = ValidationResult(
            passed=True,
            mvs_passed=True,
            tier_passed=True,
        )

        # 1. Tier 抽出
        result.tier = self.extract_tier()
        result.feature_type = self.extract_feature_type()

        # 2. MVS 検証
        for pattern, name in self.MVS_REQUIRED:
            if not self.check_section_exists(pattern):
                result.missing_mvs.append(name)

        if result.missing_mvs:
            result.mvs_passed = False
            result.passed = False

        # 3. Tier 別必須セクション検証
        if result.tier and result.tier in self.TIER_SECTIONS:
            for pattern, name in self.TIER_SECTIONS[result.tier]:
                if not self.check_section_exists(pattern):
                    if not self.check_na_section(pattern):
                        result.missing_tier.append(name)

        # 4. 機能タイプ別必須セクション検証
        if result.feature_type == 'ai':
            for pattern, name in self.AI_REQUIRED:
                if not self.check_section_exists(pattern):
                    if not self.check_na_section(pattern):
                        result.missing_tier.append(name)

        if result.feature_type in ['api', 'ai']:
            for pattern, name in self.API_REQUIRED:
                if not self.check_section_exists(pattern):
                    if not self.check_na_section(pattern):
                        result.missing_tier.append(name)

        if result.missing_tier:
            result.tier_passed = False

        # 5. ARB キー検証
        arb_keys = self.extract_arb_keys()
        if arb_keys:
            result.arb_issues = self.check_arb_file(arb_keys)

        # 6. AC 定量化検証（警告）
        result.warnings = self.check_quantified_ac()

        return result


def print_result(result: ValidationResult, spec_path: Path):
    """検証結果出力"""
    print(f"\n{'='*60}")
    print(f"SPEC 検証結果: {spec_path.name}")
    print(f"{'='*60}")

    print(f"\n メタデータ:")
    print(f"   Tier: {result.tier or '未指定'}")
    print(f"   機能タイプ: {result.feature_type or '未指定'}")

    # MVS 結果
    print(f"\n{'[PASS]' if result.mvs_passed else '[FAIL]'} MVS (Minimum Viable SPEC):")
    if result.mvs_passed:
        print("   全必須セクション存在")
    else:
        print("   [WARN] 欠落セクション:")
        for section in result.missing_mvs:
            print(f"      - {section}")

    # Tier 結果
    print(f"\n{'[PASS]' if result.tier_passed else '[WARN]'} Tier 必須要素:")
    if result.tier_passed:
        print("   全 Tier 必須セクション存在")
    else:
        print("   欠落セクション:")
        for section in result.missing_tier:
            print(f"      - {section}")

    # ARB 結果
    if result.arb_issues:
        print(f"\n[WARN] ARB キーイシュー:")
        for issue in result.arb_issues:
            print(f"   - {issue}")

    # 警告
    if result.warnings:
        print(f"\n[INFO] 警告（品質改善推奨）:")
        for warning in result.warnings:
            print(f"   - {warning}")

    # 最終結果
    print(f"\n{'='*60}")
    if not result.mvs_passed:
        print("[FAIL] 結果: MVS 未達 - AI 実装禁止")
        print("   -> 欠落セクション補完後に再検証が必要")
    elif not result.tier_passed:
        print("[WARN] 結果: Tier 必須要素未達 - 実装可能（警告）")
        print("   -> 欠落セクション追加推奨")
    else:
        print("[PASS] 結果: 検証通過 - 実装進行可能")
    print(f"{'='*60}\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_spec.py <spec_file>")
        print("Example: python validate_spec.py docs/features/001-bridge-grammar-engine/SPEC-001-bridge-grammar-engine.md")
        sys.exit(1)

    spec_path = Path(sys.argv[1])
    if not spec_path.exists():
        print(f"Error: ファイルが見つかりません: {spec_path}")
        sys.exit(1)

    validator = SpecValidator(spec_path)
    result = validator.validate()

    print_result(result, spec_path)

    # Exit code
    if not result.mvs_passed:
        sys.exit(1)  # MVS 未達
    elif not result.tier_passed:
        sys.exit(2)  # Tier 未達（警告）
    else:
        sys.exit(0)  # 通過


if __name__ == '__main__':
    main()
