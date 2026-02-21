#!/usr/bin/env python3
"""
RICE Calculator — Multi-Source Priority Calculator for CONTEXT.json.

BRIEF.md, SPEC.md, competitor-registry.json, gap-candidates.jsonを
実際に読み込み、エビデンスベースのRICEスコアを算出する。

公式: RICE Score = (Reach × Impact × Confidence) / Effort

Usage:
    python3 rice_calculator.py                      # dry-run (全体)
    python3 rice_calculator.py --apply               # 全体再計算 + ファイル更新
    python3 rice_calculator.py --feature 034         # 特定Featureのみ
    python3 rice_calculator.py --verbose              # 詳細出力
    python3 rice_calculator.py --json-output          # JSON出力
    python3 rice_calculator.py --set-phase growth     # Phase変更
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ── Project Root ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURES_DIR = PROJECT_ROOT / "docs" / "features"
REGISTRY_PATH = PROJECT_ROOT / "docs" / "analysis" / "competitor-registry.json"
GAP_CANDIDATES_PATH = PROJECT_ROOT / "docs" / "analysis" / "gap-candidates.json"

# ── Constants ─────────────────────────────────────────────────────────────

# Impact 許容値 (Intercom 5段階)
IMPACT_LEVELS = {0.25: "Minimal", 0.5: "Low", 1: "Medium", 2: "High", 3: "Massive"}

# Confidence 要素別ウェイト (v2: competitor_data 除去、4ファクター再配分)
CONFIDENCE_WEIGHTS = {
    "brief_completeness": 0.30,
    "spec_quality": 0.25,
    "research_evidence": 0.25,
    "implementation_status": 0.20,
}

# BRIEF.md 期待セクション (§0~§7)
BRIEF_SECTIONS = [
    "0. Original Request",
    "1. Problem & Why",
    "2. User Stories",
    "3. User Journey",
    "4. Acceptance Criteria",
    "5. Scope Boundaries",
    "6. Constraints",
    "7. Business Metrics",
]

# ── Data Models ───────────────────────────────────────────────────────────

class BriefData:
    """BRIEF.md パース結果。calc_reach/calc_impact/calc_confidenceの単一データソース。"""
    def __init__(self, path: Path):
        self.path = path
        self.exists = path.exists()
        self.sections: dict[str, str] = {}
        self.section_count = 0
        # ── ブールフラグ (calc_confidence 用) ──
        self.has_core_goal = False
        self.has_user_value = False
        self.has_business_metrics = False
        self.has_ltv_keywords = False
        self.has_retention_keywords = False
        self.hard_constraint_count = 0
        self.soft_constraint_count = 0
        self.in_scope_count = 0
        self.out_scope_count = 0
        # ── テキストコンテンツ (calc_reach/calc_impact 用 — brief_context キャッシュ代替) ──
        self.core_goal = ""
        self.user_value = ""
        self.business_metrics: list[str] = []
        self.user_story = ""
        if self.exists:
            self._parse()

    def _parse(self):
        text = self.path.read_text(encoding="utf-8")
        # セクション分割: ## N. パターン
        parts = re.split(r'\n## (\d+)\. ', text)
        # parts[0] = ヘッダー, parts[1]=N, parts[2]=content, ...
        for i in range(1, len(parts) - 1, 2):
            section_num = parts[i]
            raw = parts[i + 1] if i + 1 < len(parts) else ""
            # 先頭行はセクションタイトルの残り("User Stories\n..." 等) → 除去
            lines = raw.split('\n', 1)
            content = lines[1] if len(lines) > 1 else ""
            self.sections[section_num] = content

        # 実質的な内容があるセクション数 (auto-migrated/未定義を除外)
        for num, content in self.sections.items():
            # 空の内容やauto-migratedマーカーのみの場合は除外
            stripped = content.strip()
            if stripped and "[auto-migrated]" not in stripped[:100]:
                first_line = stripped.split('\n')[0]
                if len(first_line) > 20:  # 実質的な内容の判定
                    self.section_count += 1

        # §1 テキスト抽出 — サブヘッダー(### Core Goal, ### User Value 等)ベース
        s1 = self.sections.get("1", "")
        self.core_goal = self._extract_subsection(s1, "Core Goal")
        self.user_value = self._extract_subsection(s1, "User Value")
        self.has_core_goal = bool(self.core_goal)
        self.has_user_value = bool(self.user_value)

        # §7 Business Metrics (または §1 内の Business Metric)
        s7 = self.sections.get("7", "")
        biz_text = self._extract_subsection(s1, "Business Metric")
        if not biz_text:
            biz_text = s7
        self.business_metrics = self._extract_metric_lines(biz_text)
        self.has_business_metrics = bool(self.business_metrics)

        # §2 User Stories
        s2 = self.sections.get("2", "")
        self.user_story = self._extract_first_paragraph(s2)

        # LTV/リテンションキーワード (全テキストスキャン)
        all_text = text.lower()
        self.has_ltv_keywords = bool(re.search(r'(ltv|生涯\s*価値|lifetime\s*value|arpu|mrr)', all_text))
        self.has_retention_keywords = bool(re.search(r'(retention|リテンション|離脱率|churn|更新率)', all_text))

        # §6 Constraints
        s6 = self.sections.get("6", "")
        self.hard_constraint_count = len(re.findall(r'(?i)(hard\s*constraint|違反\s*禁止|\[x\])', s6))
        self.soft_constraint_count = len(re.findall(r'(?i)(soft\s*constraint|推奨|\[ \])', s6))

        # §5 Scope
        s5 = self.sections.get("5", "")
        self.in_scope_count = len(re.findall(r'(?i)(in.scope|含む)', s5))
        self.out_scope_count = len(re.findall(r'(?i)(out.scope|除外|非対象)', s5))

    @staticmethod
    def _extract_subsection(section_text: str, heading: str) -> str:
        """2種類のBRIEF形式からテキストを抽出。

        Format A (### heading): ### Core Goal\\nテキスト...
        Format B (インラインボールド): - **Core Goal**: テキスト...
        """
        # Format A: ### heading サブセクション
        pattern_a = rf'###\s*{re.escape(heading)}[^\n]*\n(.*?)(?=\n###|\Z)'
        match = re.search(pattern_a, section_text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Format B: - **heading**: インラインテキスト
        pattern_b = rf'\*\*{re.escape(heading)}\*\*\s*:\s*(.+)'
        match = re.search(pattern_b, section_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return ""

    @staticmethod
    def _extract_metric_lines(text: str) -> list[str]:
        """ビジネスメトリクスのテキストから意味のある行を抽出。"""
        lines = []
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or line == '---':
                continue
            # マークダウンテーブル区切り線を除外
            if re.match(r'^[\|\-\s:]+$', line):
                continue
            lines.append(line)
        return lines[:10]  # 最大10行

    @staticmethod
    def _extract_first_paragraph(text: str) -> str:
        """セクションの最初の意味のある段落を抽出。"""
        for line in text.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and line != '---' and '[auto-migrated]' not in line:
                return line
        return ""


class SpecData:
    """SPEC.md パース結果。"""
    def __init__(self, path: Optional[Path]):
        self.path = path
        self.exists = path is not None and path.exists()
        self.fr_count = 0
        self.ac_count = 0
        self.target_file_count = 0
        if self.exists:
            self._parse()

    def _parse(self):
        text = self.path.read_text(encoding="utf-8")
        # FR 個数: FR-NNN パターン
        self.fr_count = len(set(re.findall(r'FR-\d{3,4}', text)))
        # AC 個数: AC-NNN または AC N パターン
        self.ac_count = len(re.findall(r'(?:AC-?\d+|AC\d+)', text))
        if self.ac_count == 0:
            # BDD Given/When/Then パターンもカウント
            self.ac_count = len(re.findall(r'(?i)(given|when|then)\s', text))
        # Target Files: §0でのファイルパスパターン
        self.target_file_count = len(re.findall(r'(?:lib/|test/)\S+\.dart', text))


class ContextData:
    """CONTEXT.json データ。"""
    def __init__(self, data: dict):
        self.data = data
        self.progress_pct = data.get("progress", {}).get("percentage", 0)
        self.fr_total = data.get("progress", {}).get("fr_total", 0)
        self.fr_completed = data.get("progress", {}).get("fr_completed", 0)
        self.research_ids = self._resolve_research_ids(data)
        self.feature_id = data.get("feature_id", "unknown")
        self.state = data.get("quick_resume", {}).get("current_state", "unknown")
        self.brief_context = data.get("brief_context", {})

    @staticmethod
    def _resolve_research_ids(data: dict) -> list:
        """research_idsをcanonical位置から探索。

        位置: references.research_links.research_ids
        """
        ids = (data.get("references") or {}).get("research_links", {}).get("research_ids", [])
        return ids if ids else []


class RegistryData:
    """competitor-registry.json データ。"""
    def __init__(self):
        self.features: list[dict] = []
        self.apps: list[dict] = []
        self._load()

    def _load(self):
        if not REGISTRY_PATH.exists():
            return
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        self.features = data.get("features", [])
        self.apps = data.get("apps", [])

    @staticmethod
    def _extract_feature_num(feature_id: str) -> Optional[str]:
        """Feature IDから数字部分を抽出。'008-monetization-system' → '8'。"""
        match = re.match(r'(\d+)', feature_id)
        return match.group(1).lstrip("0") if match else None

    def _find_registry_feature(self, feature_id: str) -> Optional[dict]:
        """RegistryからFeature IDにマッチする最初の項目を返却。

        hackathon_project_coverage フィールド形式:
        - 単一値: "004" → Feature 004 マッチ
        - 複数値: "001,034" → Feature 001 OR 034 マッチ
        - 接尾辞: "027-partial" → Feature 027 マッチ
        - null/非数値("cloud-tts") → スキップ
        """
        num = self._extract_feature_num(feature_id)
        if not num:
            return None
        for feat in self.features:
            if self._coverage_matches(feat, num):
                return feat
        return None

    @staticmethod
    def _coverage_matches(feat: dict, target_num: str) -> bool:
        """hackathon_project_coverage フィールドがtarget_numとマッチするか確認。"""
        coverage = feat.get("hackathon_project_coverage")
        if not coverage or not isinstance(coverage, str):
            return False
        # カンマ区切り複数値処理
        for part in coverage.split(","):
            part = part.strip()
            if not part:
                continue
            # 数字プレフィックス抽出 (例: "027-partial" → "027")
            match = re.match(r'(\d+)', part)
            if match and match.group(1).lstrip("0") == target_num:
                return True
        return False

    def get_all_matching_features(self, feature_id: str) -> list[dict]:
        """Feature IDにマッチするすべてのregistry項目を返却。

        1つのFeatureが複数のregistry項目にマッチする場合がある
        (例: feature 005 → comp-011, comp-012, comp-014)。
        """
        num = self._extract_feature_num(feature_id)
        if not num:
            return []
        return [f for f in self.features if self._coverage_matches(f, num)]


    def get_opportunity_score(self, feature_id: str) -> Optional[float]:
        """Opportunity Score = Importance + max(Importance - Satisfaction, 0)."""
        feat = self._find_registry_feature(feature_id)
        if not feat:
            return None
        opp = feat.get("opportunity_score")
        return float(opp) if opp is not None else None

    def get_assessment_count(self, feature_id: str) -> int:
        """該当featureの競合他社assessment数。"""
        feat = self._find_registry_feature(feature_id)
        if feat:
            assessments = feat.get("assessments", {})
            return len([a for a in assessments.values() if isinstance(a, dict)])
        return 0


class GapData:
    """gap-candidates.json データ。"""
    def __init__(self):
        self.candidates: list[dict] = []
        self._load()

    def _load(self):
        if not GAP_CANDIDATES_PATH.exists():
            return
        data = json.loads(GAP_CANDIDATES_PATH.read_text(encoding="utf-8"))
        self.candidates = data.get("candidates", [])

    def _find_candidate(self, feature_id: str) -> Optional[dict]:
        """Feature IDにマッチするgap candidateを返却。"""
        num = feature_id.split("-")[0].lstrip("0")
        if not num:
            return None
        for c in self.candidates:
            existing_id = c.get("existing_feature_id", "")
            if existing_id and existing_id.lstrip("0") == num:
                return c
        return None

    def get_gap_severity(self, feature_id: str) -> Optional[str]:
        """Featureに関連するgap severityを返却。"""
        c = self._find_candidate(feature_id)
        return c.get("gap_severity") if c else None

    def get_opportunity_score(self, feature_id: str) -> Optional[float]:
        """Featureに関連するopportunity scoreを返却 (gap-candidates.json 専用)。"""
        c = self._find_candidate(feature_id)
        if c:
            opp = c.get("opportunity_score")
            return float(opp) if opp is not None else None
        return None

    def get_is_industry_standard(self, feature_id: str) -> bool:
        """Featureが業界標準かどうか。"""
        c = self._find_candidate(feature_id)
        return bool(c.get("is_industry_standard")) if c else False


# ── Utilities ────────────────────────────────────────────────────────────

def _normalize_manual_override(raw: Any) -> dict:
    """manual_overrideを正規化。dictまたはflat float形式の両方を処理。

    Returns:
        {"value": float (clamped 0.8-1.2), "reason": str|None}
    """
    if isinstance(raw, dict):
        val = raw.get("value", 1.0)
        reason = raw.get("reason")
    elif isinstance(raw, (int, float)):
        val = float(raw)
        reason = None
    else:
        return {"value": 1.0, "reason": None}

    if not isinstance(val, (int, float)):
        val = 1.0
    val = max(0.8, min(1.2, float(val)))
    return {"value": round(val, 2), "reason": reason}


# ── RICE Component Calculators ────────────────────────────────────────────

def calc_reach(brief: BriefData, context: ContextData) -> dict:
    """Reachスコア算出 (1-10) — 純粋RICE、独立加重合計。

    score = user_scope * 0.40 + biz_metrics * 0.35 + progress_factor * 0.25
    progress >= 100% → 強制 score = 1
    """
    evidence = {}

    # 1. Target user scope (ウェイト 0.40) — BRIEF.md §1
    if brief.exists and brief.core_goal:
        core_goal = brief.core_goal
        if re.search(r'(すべての\s*ユーザー|全体|all\s*user|every)', core_goal, re.I):
            user_scope = 9
        elif re.search(r'(大半|most|多くの)', core_goal, re.I):
            user_scope = 7
        elif re.search(r'(特定|specific|niche)', core_goal, re.I):
            user_scope = 3
        else:
            user_scope = 5
        evidence["target_user_scope"] = {"value": core_goal[:100], "source": "BRIEF.md §1"}
    else:
        user_scope = 5
        evidence["target_user_scope"] = {"value": "BRIEFなし", "source": "BRIEF.md (未存在)"}

    # 2. Business metrics (ウェイト 0.35) — BRIEF.md §7
    if brief.has_ltv_keywords and brief.has_retention_keywords:
        biz_score = 9
    elif brief.has_ltv_keywords or brief.has_retention_keywords:
        biz_score = 7
    elif brief.has_business_metrics:
        biz_score = 5
    else:
        biz_score = 3
    evidence["business_metrics"] = {
        "value": str(brief.business_metrics[:2]) if brief.business_metrics else "メトリクスなし",
        "source": "BRIEF.md §7"
    }

    # 3. Progress factor (ウェイト 0.25) — 進捗率に反比例
    progress = context.progress_pct
    if progress >= 100:
        progress_factor = 2  # 最小値 (完了 → 低いreach)
    elif progress >= 80:
        progress_factor = 3
    elif progress >= 50:
        progress_factor = 4
    elif progress > 0:
        progress_factor = 5
    else:
        progress_factor = 6  # 未着手 → 高いreach
    evidence["progress_adjustment"] = {"value": progress, "source": "CONTEXT.json progress"}

    # 独立加重合計
    score = user_scope * 0.40 + biz_score * 0.35 + progress_factor * 0.25

    # 完了機能の強制override
    if progress >= 100:
        score = 1

    score = round(max(1, min(10, score)), 1)

    rationale_parts = []
    if progress >= 100:
        rationale_parts.append(f"完了機能(progress={progress}%) → Reach=1")
    rationale_parts.append(f"user_scope={user_scope}, biz={biz_score}, progress_factor={progress_factor}")

    return {
        "score": score,
        "evidence": evidence,
        "rationale": ". ".join(rationale_parts)
    }


def calc_impact(brief: BriefData, context: ContextData,
                gaps: GapData) -> dict:
    """Impactスコア算出 (0.25/0.5/1/2/3) — 純粋RICE、競合データ分離。

    優先順位シグナルチェーン:
    1. 完了(100%) → 強制 0.25
    2. Core goalキーワード → 基本レベル設定
    3. LTVキーワード → 最低保証 (floor)
    4. Gap severity → 最低保証 (floor)
    5. Intercom 5段階 snap
    """
    raw_score = 1.0  # デフォルト: Medium
    evidence = {}

    # 1. 完了機能は即座にMinimal
    if context.progress_pct >= 100:
        evidence["core_goal"] = {"value": "完了機能", "source": "CONTEXT.json progress"}
        evidence["ltv_contribution"] = {"value": "N/A (完了)", "source": "BRIEF.md"}
        return {
            "score": 0.25,
            "evidence": evidence,
            "rationale": f"完了機能(progress={context.progress_pct}%) → Impact=Minimal (0.25)"
        }

    # 2. Core goalキーワード → 基本レベル設定
    core_goal = brief.core_goal if brief.exists else ""
    if re.search(r'(核心|critical|必須|ゲーム\s*チェンジャー|game.changer|収益|monetiz)', core_goal, re.I):
        raw_score = 2.0
    elif re.search(r'(重要|important|改善|improv)', core_goal, re.I):
        raw_score = 1.0
    else:
        raw_score = 1.0
    evidence["core_goal"] = {"value": core_goal[:100] if core_goal else "N/A", "source": "BRIEF.md §1"}

    # 3. LTVキーワード → 最低保証 (floor役割のみ、既存の高い値を維持)
    if brief.has_ltv_keywords:
        raw_score = max(raw_score, 2.0)
        evidence["ltv_contribution"] = {"value": "LTV関連キーワード検出", "source": "BRIEF.md"}
    elif brief.has_retention_keywords:
        raw_score = max(raw_score, 1.0)
        evidence["ltv_contribution"] = {"value": "リテンション関連キーワード検出", "source": "BRIEF.md"}
    else:
        evidence["ltv_contribution"] = {"value": "LTV/リテンションキーワードなし", "source": "BRIEF.md"}

    # 4. Gap severity → 最低保証 (floor役割)
    gap_sev = gaps.get_gap_severity(context.feature_id)
    if gap_sev == "HIGH":
        raw_score = max(raw_score, 2.0)
    elif gap_sev == "MEDIUM":
        raw_score = max(raw_score, 1.0)
    evidence["gap_severity"] = {"value": gap_sev or "N/A", "source": "gap-candidates.json"}

    # 5. Intercom 5段階 snap
    levels = sorted(IMPACT_LEVELS.keys())
    impact_score = min(levels, key=lambda x: abs(x - raw_score))

    return {
        "score": impact_score,
        "evidence": evidence,
        "rationale": f"Impact={IMPACT_LEVELS[impact_score]} ({impact_score}). Gap severity={gap_sev or 'N/A'}"
    }


def calc_confidence(brief: BriefData, spec: SpecData,
                    context: ContextData) -> dict:
    """Confidenceスコア算出 (0.05-1.0) — 4ファクター加重合計 (v2: competitor_data 除去)。"""
    factors = {}

    # 1. BRIEF 完成度 (ウェイト 0.30)
    if brief.exists:
        brief_score = min(1.0, brief.section_count / 6)
    else:
        brief_score = 0.0
    factors["brief_completeness"] = {
        "score": round(brief_score, 2),
        "section_count": brief.section_count if brief.exists else 0,
        "source": "BRIEF.md"
    }

    # 2. SPEC 品質 (ウェイト 0.25)
    if spec.exists:
        spec_score = min(1.0, spec.fr_count * 0.15)
        if spec.fr_count == 0:
            spec_score = 0.3
    else:
        spec_score = 0.0
    factors["spec_quality"] = {
        "score": round(spec_score, 2),
        "fr_count": spec.fr_count if spec.exists else 0,
        "source": "SPEC.md" if spec.exists else "SPEC.md (未存在)"
    }

    # 3. リサーチ根拠 (ウェイト 0.25)
    research_ids = context.research_ids
    if research_ids:
        research_score = min(1.0, len(research_ids) * 0.2)
    else:
        research_score = 0.0
    factors["research_evidence"] = {
        "score": round(research_score, 2),
        "research_count": len(research_ids),
        "sources": research_ids[:5]
    }

    # 4. 実装実績 (ウェイト 0.20)
    progress = context.progress_pct
    if progress >= 80:
        impl_score = 1.0
    elif progress >= 50:
        impl_score = 0.7
    elif progress >= 20:
        impl_score = 0.4
    elif progress > 0:
        impl_score = 0.2
    else:
        impl_score = 0.0
    factors["implementation_status"] = {
        "score": round(impl_score, 2),
        "progress_pct": progress,
        "source": "CONTEXT.json progress"
    }

    # 加重合算 + 最小値 0.05 強制
    total = 0.0
    for key, weight in CONFIDENCE_WEIGHTS.items():
        total += factors[key]["score"] * weight
    total = max(0.05, total)

    return {
        "score": round(total, 2),
        "factors": factors
    }


def calc_effort(brief: BriefData, spec: SpecData, context: ContextData) -> dict:
    """Effort算出 (0.5-20 person-weeks)。"""
    evidence = {}
    base_effort = 2.0  # デフォルト 2週

    # 1. FR個数ベース (SPECまたはCONTEXT)
    fr_count = spec.fr_count if spec.exists else context.fr_total
    if fr_count > 0:
        # FR当たり 0.5~1.5 person-weeks (複雑度による)
        base_effort = fr_count * 0.8
    evidence["fr_count"] = {
        "value": fr_count,
        "source": "SPEC.md §2" if spec.exists else "CONTEXT.json progress.fr_total"
    }

    # 2. Target files
    target_files = spec.target_file_count if spec.exists else 0
    if target_files > 0:
        # ファイル数が多い場合はeffort増加補正
        file_factor = 1 + (target_files / 50)  # 50ファイルなら2倍
        base_effort *= min(file_factor, 2.0)
    evidence["target_files"] = {
        "value": target_files if target_files > 0 else None,
        "source": "SPEC.md §0" if spec.exists else "SPEC.md (未存在)"
    }

    # 3. Constraint 加重
    constraint_count = brief.hard_constraint_count + brief.soft_constraint_count
    if constraint_count > 5:
        base_effort *= 1.3
    elif constraint_count > 2:
        base_effort *= 1.1
    evidence["constraint_count"] = {
        "value": constraint_count,
        "source": "BRIEF.md §6"
    }

    # 4. 残りの作業のみ計算 (既に完了したFRを除外)
    remaining_pct = max(0, 100 - context.progress_pct)
    base_effort *= (remaining_pct / 100)
    evidence["remaining_pct"] = {
        "value": remaining_pct,
        "source": "CONTEXT.json progress"
    }

    # 範囲制限
    final_effort = round(max(0.5, min(20, base_effort)), 1)

    rationale_parts = []
    if fr_count > 0:
        rationale_parts.append(f"FR {fr_count}個")
    if remaining_pct < 100:
        rationale_parts.append(f"残り {remaining_pct}%")
    if constraint_count > 2:
        rationale_parts.append(f"制約 {constraint_count}個")

    return {
        "score": final_effort,
        "unit": "person-weeks",
        "evidence": evidence,
        "rationale": ". ".join(rationale_parts) if rationale_parts else "デフォルト推定"
    }


# ── Competitive Adjustment ────────────────────────────────────────────────

def calc_competitive_adjustment(registry: RegistryData, gaps: GapData,
                                 context: ContextData) -> dict:
    """競合他社データベースのpost-multiplier (0.8-1.3)。

    RICEサブスコアと分離された別途の調整係数。
    データなし → 1.0 (中立)。

    4つのシグナル:
    - assessment_count: 競合他社分析カバレッジ (+0.00 ~ +0.10)
    - is_industry_standard: 業界標準かどうか (+0.00 ~ +0.05)
    - opportunity_score: 機会スコア (-0.05 ~ +0.10)
    - gap_severity: ギャップ深刻度 (-0.02 ~ +0.10)
    """
    adjustment = 1.0
    evidence = {}
    has_data = False

    feature_id = context.feature_id

    # 1. Assessment count — 競合他社分析カバレッジ
    all_matches = registry.get_all_matching_features(feature_id)
    total_assessments = 0
    for feat in all_matches:
        assessments = feat.get("assessments", {})
        total_assessments += len([a for a in assessments.values() if isinstance(a, dict)])

    if total_assessments > 0:
        has_data = True
        # 1-3 → +0.03, 4-6 → +0.06, 7+ → +0.10
        if total_assessments >= 7:
            adj = 0.10
        elif total_assessments >= 4:
            adj = 0.06
        else:
            adj = 0.03
        adjustment += adj
    evidence["assessment_count"] = {
        "value": total_assessments,
        "contribution": round(adjustment - 1.0, 3),
        "source": "competitor-registry.json"
    }

    # 2. Industry standard — 業界標準なら若干加算
    is_standard = gaps.get_is_industry_standard(feature_id)
    if is_standard:
        has_data = True
        adjustment += 0.05
    evidence["is_industry_standard"] = {
        "value": is_standard,
        "contribution": 0.05 if is_standard else 0.0,
        "source": "gap-candidates.json"
    }

    # 3. Opportunity score
    opp = gaps.get_opportunity_score(feature_id)
    if opp is not None:
        has_data = True
        if opp >= 7:
            opp_adj = 0.10
        elif opp >= 5:
            opp_adj = 0.05
        elif opp >= 3:
            opp_adj = 0.0
        else:
            opp_adj = -0.05
        adjustment += opp_adj
        evidence["opportunity_score"] = {
            "value": round(opp, 2),
            "contribution": opp_adj,
            "source": "gap-candidates.json"
        }
    else:
        evidence["opportunity_score"] = {
            "value": None,
            "contribution": 0.0,
            "source": "gap-candidates.json (マッピングなし)"
        }

    # 4. Gap severity
    gap_sev = gaps.get_gap_severity(feature_id)
    if gap_sev == "HIGH":
        has_data = True
        gap_adj = 0.10
    elif gap_sev == "MEDIUM":
        has_data = True
        gap_adj = 0.05
    elif gap_sev == "LOW":
        has_data = True
        gap_adj = -0.02
    else:
        gap_adj = 0.0
    adjustment += gap_adj
    evidence["gap_severity"] = {
        "value": gap_sev or "N/A",
        "contribution": gap_adj,
        "source": "gap-candidates.json"
    }

    # データがなければ中立
    if not has_data:
        adjustment = 1.0

    # 範囲制限 0.8-1.3
    adjustment = round(max(0.8, min(1.3, adjustment)), 3)

    return {
        "adjustment": adjustment,
        "has_data": has_data,
        "evidence": evidence,
        "rationale": f"CompAdj={adjustment}" + (" (データなし → 中立)" if not has_data else "")
    }


# ── RICE Score ────────────────────────────────────────────────────────────

def calc_rice_score(reach: dict, impact: dict, confidence: dict,
                    effort: dict) -> dict:
    """純粋RICEスコア計算 (manual_override/competitive 未含)。"""
    r = reach["score"]
    i = impact["score"]
    c = confidence["score"]
    e = effort["score"]

    numerator = r * i * c
    denominator = e if e > 0 else 0.5

    rice_score = round(numerator / denominator, 2)

    return {
        "rice_score": rice_score,
        "formula": "Score = (Reach × Impact × Confidence) / Effort",
        "component_breakdown": {
            "numerator": round(numerator, 2),
            "denominator": denominator
        }
    }


def compose_final_score(rice: dict, competitive_adj: dict,
                         manual_override: dict) -> dict:
    """最終スコア = 純粋RICE × CompAdj × ManualOverride。

    Args:
        rice: calc_rice_score() 結果
        competitive_adj: calc_competitive_adjustment() 結果
        manual_override: {"value": float, "reason": str|None}

    Returns:
        統合 calculated セクション (rice_score, adjusted_score, formula 等)
    """
    pure = rice["rice_score"]
    comp_adj = competitive_adj["adjustment"]
    override_val = manual_override["value"]

    adjusted = round(pure * comp_adj * override_val, 2)

    return {
        "rice_score": pure,
        "adjusted_score": adjusted,
        "competitive_adjustment": comp_adj,
        "manual_override_applied": override_val,
        "formula": "Adjusted = (R×I×C)/E × CompAdj × Override",
        "component_breakdown": rice["component_breakdown"],
    }


# ── File Processing ───────────────────────────────────────────────────────

def find_spec_path(feature_dir: Path) -> Optional[Path]:
    """FeatureディレクトリからSPECファイルを検索。"""
    specs = list(feature_dir.glob("SPEC*.md"))
    return specs[0] if specs else None


def process_feature(feature_dir: Path, registry: RegistryData, gaps: GapData,
                    new_phase: Optional[str], apply: bool, verbose: bool) -> dict:
    """単一Feature処理 (v2: competitive_adjustment + compose_final_score)。"""
    feature_id = feature_dir.name
    context_path = feature_dir / "CONTEXT.json"
    result = {
        "id": feature_id, "status": "unchanged",
        "old_score": 0.0, "new_score": 0.0, "diffs": []
    }

    # CONTEXT.json ロード
    if not context_path.exists():
        result["status"] = "skipped"
        result["diffs"].append("CONTEXT.jsonなし")
        return result

    try:
        data = json.loads(context_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        result["status"] = "error"
        result["diffs"].append(f"JSON読み込み失敗: {e}")
        return result

    # Lifecycleフィルター: Archived/Failed FeatureはRICE計算対象から除外
    from feature_lifecycle import is_active
    if not is_active(data):
        lifecycle_state = data.get("quick_resume", {}).get("current_state", "unknown")
        result["status"] = "skipped"
        result["diffs"].append(f"非アクティブFeature ({lifecycle_state})")
        return result

    # データソース読み込み
    brief = BriefData(feature_dir / "BRIEF.md")
    spec = SpecData(find_spec_path(feature_dir))
    context = ContextData(data)

    # 既存スコアの保存
    old_priority = data.get("priority", {})
    old_score = old_priority.get("calculated", {}).get("adjusted_score",
                old_priority.get("calculated", {}).get("rice_score", 0))
    result["old_score"] = old_score

    # Phase 決定
    phase = new_phase or old_priority.get("phase", "mvp")

    # RICEコンポーネント計算 (v2: registry/gapsをcalc_reach/calc_impactから除去)
    reach = calc_reach(brief, context)
    impact = calc_impact(brief, context, gaps)
    confidence = calc_confidence(brief, spec, context)
    effort = calc_effort(brief, spec, context)

    # 純粋RICE Score
    rice = calc_rice_score(reach, impact, confidence, effort)

    # Competitive Adjustment (別途post-multiplier)
    comp_adj = calc_competitive_adjustment(registry, gaps, context)

    # Manual override 正規化
    raw_override = old_priority.get("manual_override", 1.0)
    manual_override = _normalize_manual_override(raw_override)

    # 最終スコア合成
    calculated = compose_final_score(rice, comp_adj, manual_override)
    result["new_score"] = calculated["adjusted_score"]

    # data_sources_read 生成
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data_sources = []
    if brief.exists:
        data_sources.append(f"BRIEF.md (date: {now_str})")
    if spec.exists:
        data_sources.append(f"SPEC.md (date: {now_str})")
    data_sources.append(f"CONTEXT.json (date: {now_str})")
    if REGISTRY_PATH.exists():
        data_sources.append(f"competitor-registry.json (date: {now_str})")
    if GAP_CANDIDATES_PATH.exists():
        data_sources.append(f"gap-candidates.json (date: {now_str})")

    # AI rationale 生成
    rationale_parts = [
        f"R={reach['score']}, I={impact['score']}, C={confidence['score']}, E={effort['score']}",
        f"CompAdj={comp_adj['adjustment']}",
    ]
    if reach.get("rationale"):
        rationale_parts.append(reach["rationale"])
    if context.progress_pct >= 100:
        rationale_parts.append("完了機能 → 最小スコア")

    # 新しいpriorityセクション構築
    now_iso = datetime.now(timezone.utc).isoformat()
    new_priority = {
        "version": "3.0",
        "schema": "rice-v2",
        "last_updated": now_iso,
        "phase": phase,
        "rice_inputs": {
            "reach": reach,
            "impact": impact,
            "confidence": confidence,
            "effort": effort,
        },
        "competitive_adjustment": comp_adj,
        "calculated": calculated,
        "data_sources_read": data_sources,
        "manual_override": manual_override,
        "ai_rationale": ". ".join(rationale_parts),
        "history": old_priority.get("history", []),
    }

    # diff 計算
    diffs = []
    old_schema = old_priority.get("schema", "unknown")
    schema_changed = old_schema != "rice-v2"
    if schema_changed:
        diffs.append(f"schema: {old_schema} → rice-v2")
    if abs(result["new_score"] - result["old_score"]) > 0.01:
        diffs.append(f"score: {result['old_score']:.2f} → {result['new_score']:.2f}")
    if phase != old_priority.get("phase"):
        diffs.append(f"phase: {old_priority.get('phase')} → {phase}")

    result["diffs"] = diffs

    if not diffs:
        result["status"] = "unchanged"
        return result

    # history 追加
    new_priority["history"].append({
        "timestamp": now_iso,
        "actor": "ai",
        "change_summary": f"rice_calculator.py v2 ({old_schema}→rice-v2)" if schema_changed else "rice_calculator.py v2 再計算",
        "rice_score": calculated["rice_score"],
        "adjusted_score": calculated["adjusted_score"],
        "inputs_snapshot": {
            "reach": reach["score"],
            "impact": impact["score"],
            "confidence": confidence["score"],
            "effort": effort["score"],
            "competitive_adjustment": comp_adj["adjustment"],
        },
        "notes": "; ".join(diffs),
    })

    data["priority"] = new_priority
    result["status"] = "updated"

    if apply:
        context_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8"
        )

    return result


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="RICE Calculator for CONTEXT.json")
    parser.add_argument("--apply", action="store_true", help="ファイルに変更を保存")
    parser.add_argument("--feature", type=str, help="特定Feature ID (例: 034, 008)")
    parser.add_argument("--set-phase", type=str,
                        choices=["exploration", "mvp", "growth", "stability"],
                        help="Phase変更")
    parser.add_argument("--verbose", action="store_true", help="詳細出力")
    parser.add_argument("--json-output", action="store_true", help="JSON形式出力")
    args = parser.parse_args()

    if not FEATURES_DIR.exists():
        print(f"ERROR: {FEATURES_DIR} パスが見つかりません", file=sys.stderr)
        sys.exit(1)

    # 共有データソースのロード
    registry = RegistryData()
    gaps = GapData()

    # Feature一覧
    feature_dirs = sorted([d for d in FEATURES_DIR.iterdir()
                           if d.is_dir() and (d / "CONTEXT.json").exists()])
    if args.feature:
        keyword = args.feature.lstrip("0")
        feature_dirs = [d for d in feature_dirs if keyword in d.name]
        if not feature_dirs:
            print(f"ERROR: '{args.feature}'にマッチするFeatureなし", file=sys.stderr)
            sys.exit(1)

    results = []
    for fd in feature_dirs:
        r = process_feature(fd, registry, gaps, args.set_phase, args.apply, args.verbose)
        results.append(r)

    # JSON出力
    if args.json_output:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    # テキスト出力
    updated = [r for r in results if r["status"] == "updated"]
    unchanged = [r for r in results if r["status"] == "unchanged"]
    skipped = [r for r in results if r["status"] == "skipped"]
    errors = [r for r in results if r["status"] == "error"]

    print(f"\n{'=' * 60}")
    print(f"RICE Calculator — {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"{'=' * 60}")
    print(f"対象: {len(results)} Features | Phase: {args.set_phase or '(維持)'}")
    print(f"結果: {len(updated)} updated, {len(unchanged)} unchanged, "
          f"{len(skipped)} skipped, {len(errors)} errors")
    print()

    if updated:
        print(f"── Updated ({len(updated)}) ──")
        updated.sort(key=lambda r: abs(r["new_score"] - r["old_score"]), reverse=True)
        for r in updated:
            delta = r["new_score"] - r["old_score"]
            arrow = "▲" if delta > 0 else "▼" if delta < 0 else "="
            print(f"  {r['id']:45s} {r['old_score']:6.2f} → {r['new_score']:6.2f} ({arrow}{abs(delta):.2f})")
            if args.verbose:
                for d in r["diffs"]:
                    print(f"    • {d}")
        print()

    if errors:
        print(f"── Errors ({len(errors)}) ──")
        for r in errors:
            print(f"  {r['id']}: {'; '.join(r['diffs'])}")
        print()

    if not args.apply and updated:
        print(f"変更を適用するには: python3 {sys.argv[0]} --apply")

    # ランキングサマリー
    ranked = [r for r in results if r["status"] in ("updated", "unchanged")]
    ranked.sort(key=lambda r: r["new_score"], reverse=True)
    if ranked and len(ranked) > 5:
        print(f"\n── Top 10 RICE ──")
        for i, r in enumerate(ranked[:10], 1):
            tier = ("T1" if r["new_score"] >= 5.0
                    else "T2" if r["new_score"] >= 2.0
                    else "T3" if r["new_score"] >= 1.0
                    else "T4")
            print(f"  #{i:2d} [{tier}] {r['id']:45s} {r['new_score']:6.2f}")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
