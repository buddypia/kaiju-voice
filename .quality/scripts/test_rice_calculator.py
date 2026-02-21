#!/usr/bin/env python3
"""
rice_calculator.py v2 テストスイート.

カバレッジ (~93個):
- BriefData パース (Format A/B, エッジケース) — 12個
- ContextData research_ids 解釈 — 4個
- RegistryData Feature ID マッチング (hackathon_project_coverage, 複数値, partial) — 10個
- GapData (get_opportunity_score, get_is_industry_standard) — 4個
- calc_reach 純粋加重和 — 8個
- calc_impact 純粋シグナル — 8個
- calc_confidence 4ファクター — 7個
- calc_effort — 3個
- calc_competitive_adjustment — 8個
- compose_final_score — 4個
- _normalize_manual_override — 5個
- calc_rice_score — 4個
- Property-based — 5個
- Golden file (代表 5 Feature) — 5個
- process_feature オーケストレーション — 4個
- Recalculation (冪等性, 履歴) — 2個
- Integration — 3個
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# rice_calculator を import できるようにパス追加
sys.path.insert(0, str(Path(__file__).parent))
from rice_calculator import (
    BriefData,
    ContextData,
    GapData,
    RegistryData,
    SpecData,
    _normalize_manual_override,
    calc_competitive_adjustment,
    calc_confidence,
    calc_effort,
    calc_impact,
    calc_reach,
    calc_rice_score,
    compose_final_score,
    process_feature,
)


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_dir(tmp_path):
    """一時 Feature ディレクトリ."""
    return tmp_path


def _write_brief_format_a(path: Path) -> Path:
    """Format A: ### サブヘディング形式 BRIEF.md 生成."""
    brief = path / "BRIEF.md"
    brief.write_text(
        """# Feature Brief: 999-test-feature

---

## 0. Original Request

> テスト元リクエスト

---

## 1. Problem & Why

### Core Goal

Freemium モデルで持続可能な収益を創出する。

### User Value

無料ユーザーが価値を確認後アップグレードできる。

### Business Metric

| 指標 | 目標 |
|------|------|
| コンバージョン率 | 5-8% |
| MRR | ¥500K+ |
| LTV | $80+ |

---

## 2. User Stories

- 学習者は無料でアプリを体験したい
- 学習者はプレミアム機能の価値を感じたい

---

## 3. User Journey

1. アプリインストール後無料体験開始
2. 14日後に決済案内

---

## 4. Acceptance Criteria (BDD)

- Unit Test: subscription_viewmodel_test.dart 通過
- Widget Test: paywall_sheet_test.dart 通過

---

## 5. Scope Boundaries

### In Scope
- サブスクリプション管理 UI
- RevenueCat SDK 連携

### Out of Scope
- 広告ベースの収益モデル

---

## 6. Constraints

### Hard Constraints (違反禁止)
- [x] RevenueCat 必須
- [x] PII 最小保存

### Soft Constraints (推奨)
- [ ] 価格 A/B テスト

---

## 7. Business Metrics

- 月間離脱率 < 5%
- サブスク更新率 85%+
- retention 指標追跡
""",
        encoding="utf-8",
    )
    return brief


def _write_brief_format_b(path: Path) -> Path:
    """Format B: インラインボールドラベル形式 BRIEF.md 生成."""
    brief = path / "BRIEF.md"
    brief.write_text(
        """# Feature Brief: 999-test-inline

---

## 0. Original Request

> 競合分析で発見された機能欠落

---

## 1. Problem & Why

*この機能がなぜ必要かを記述します。*
- **Core Goal**: ハングルキーボードで直接タイピング入力学習を提供する。
- **User Value**: Active Recall 効果が2-3倍高い。
- **Business Metric**: 学習セッション当たりの Active Recall 比率 +30%

---

## 2. User Stories

- 学習者はハングルキーボードで直接入力して学習したい

---

## 3. User Journey

1. タイピング問題出題
2. 入力後の採点

---

## 4. Acceptance Criteria (BDD)

- Unit Test: typing_practice_test.dart

---

## 5. Scope Boundaries

### In Scope
- ハングルキーボード直接入力

### Out of Scope
- 筆記認識

---

## 6. Constraints

### Hard Constraints (違反禁止)
- [x] OS キーボード使用

---

## 7. Business Metrics

- 語彙長期記憶率 +20%
""",
        encoding="utf-8",
    )
    return brief


def _make_context_data(
    progress_pct=0,
    fr_total=0,
    fr_completed=0,
    feature_id="999-test-feature",
    research_ids_in_refs=None,
) -> ContextData:
    """テスト用 ContextData 生成."""
    data = {
        "feature_id": feature_id,
        "progress": {
            "percentage": progress_pct,
            "fr_total": fr_total,
            "fr_completed": fr_completed,
        },
        "quick_resume": {"current_state": "Testing"},
        "brief_context": {},
        "references": {},
        "priority": {},
    }
    if research_ids_in_refs is not None:
        data["references"]["research_links"] = {
            "research_ids": research_ids_in_refs,
            "id_format": "R-YYYYMMDD-NNN",
        }
    return ContextData(data)


def _empty_registry():
    """空の RegistryData."""
    r = RegistryData.__new__(RegistryData)
    r.features = []
    r.apps = []
    return r


def _make_registry(features: list[dict]) -> RegistryData:
    """カスタム features を持つ RegistryData."""
    r = RegistryData.__new__(RegistryData)
    r.features = features
    r.apps = []
    return r


def _empty_gaps():
    """空の GapData."""
    g = GapData.__new__(GapData)
    g.candidates = []
    return g


def _make_gaps(candidates: list[dict]) -> GapData:
    """カスタム candidates を持つ GapData."""
    g = GapData.__new__(GapData)
    g.candidates = candidates
    return g


# ── BriefData Tests (12個) ──────────────────────────────────────────────


class TestBriefData:
    """BriefData パーステスト."""

    def test_format_a_core_goal(self, tmp_dir):
        _write_brief_format_a(tmp_dir)
        b = BriefData(tmp_dir / "BRIEF.md")
        assert b.exists
        assert "Freemium" in b.core_goal
        assert "収益" in b.core_goal

    def test_format_a_user_value(self, tmp_dir):
        _write_brief_format_a(tmp_dir)
        b = BriefData(tmp_dir / "BRIEF.md")
        assert "無料ユーザー" in b.user_value

    def test_format_a_business_metrics(self, tmp_dir):
        _write_brief_format_a(tmp_dir)
        b = BriefData(tmp_dir / "BRIEF.md")
        assert len(b.business_metrics) >= 2
        for m in b.business_metrics:
            assert "------" not in m

    def test_format_a_ltv_keywords(self, tmp_dir):
        _write_brief_format_a(tmp_dir)
        b = BriefData(tmp_dir / "BRIEF.md")
        assert b.has_ltv_keywords

    def test_format_a_retention_keywords(self, tmp_dir):
        _write_brief_format_a(tmp_dir)
        b = BriefData(tmp_dir / "BRIEF.md")
        assert b.has_retention_keywords

    def test_format_a_constraints(self, tmp_dir):
        _write_brief_format_a(tmp_dir)
        b = BriefData(tmp_dir / "BRIEF.md")
        assert b.hard_constraint_count >= 2
        assert b.soft_constraint_count >= 1

    def test_format_a_section_count(self, tmp_dir):
        _write_brief_format_a(tmp_dir)
        b = BriefData(tmp_dir / "BRIEF.md")
        assert b.section_count >= 3

    def test_format_b_core_goal(self, tmp_dir):
        _write_brief_format_b(tmp_dir)
        b = BriefData(tmp_dir / "BRIEF.md")
        assert "ハングルキーボード" in b.core_goal

    def test_format_b_user_value(self, tmp_dir):
        _write_brief_format_b(tmp_dir)
        b = BriefData(tmp_dir / "BRIEF.md")
        assert "Active Recall" in b.user_value

    def test_format_b_business_metrics(self, tmp_dir):
        _write_brief_format_b(tmp_dir)
        b = BriefData(tmp_dir / "BRIEF.md")
        assert len(b.business_metrics) >= 1
        assert any("Active Recall" in m for m in b.business_metrics)

    def test_nonexistent_brief(self, tmp_dir):
        b = BriefData(tmp_dir / "BRIEF.md")
        assert not b.exists
        assert b.core_goal == ""
        assert b.section_count == 0

    def test_section_title_not_in_content(self, tmp_dir):
        """セクション見出しが content に含まれないこと（回帰防止）."""
        _write_brief_format_a(tmp_dir)
        b = BriefData(tmp_dir / "BRIEF.md")
        assert b.user_story != "User Stories"
        assert "学習者" in b.user_story


# ── ContextData Tests (6個) ────────────────────────────────────────────


class TestContextData:
    """ContextData research_ids 解釈テスト."""

    def test_canonical_path(self):
        ctx = _make_context_data(research_ids_in_refs=["R-001", "R-002"])
        assert ctx.research_ids == ["R-001", "R-002"]

    def test_no_research_ids(self):
        ctx = _make_context_data()
        assert ctx.research_ids == []

    def test_empty_array_returns_empty(self):
        ctx = _make_context_data(research_ids_in_refs=[])
        assert ctx.research_ids == []

    def test_single_research_id(self):
        ctx = _make_context_data(research_ids_in_refs=["R-200"])
        assert ctx.research_ids == ["R-200"]


# ── RegistryData Tests (10個) ──────────────────────────────────────────


class TestRegistryData:
    """RegistryData Feature ID マッチング (hackathon_project_coverage)."""

    def test_extract_feature_num(self):
        assert RegistryData._extract_feature_num("008-monetization-system") == "8"
        assert RegistryData._extract_feature_num("001-bridge-grammar") == "1"
        assert RegistryData._extract_feature_num("47-typing") == "47"

    def test_extract_feature_num_no_match(self):
        assert RegistryData._extract_feature_num("no-digits") is None

    def test_find_single_coverage(self):
        """単一値 hackathon_project_coverage マッチング."""
        r = _make_registry([
            {"hackathon_project_coverage": "004", "name": "Assessment"},
        ])
        feat = r._find_registry_feature("004-onboarding-level-test")
        assert feat is not None
        assert feat["name"] == "Assessment"

    def test_find_multi_coverage(self):
        """複数値 '001,034' → Feature 001 マッチング."""
        r = _make_registry([
            {"hackathon_project_coverage": "001,034", "name": "Grammar+Explain"},
        ])
        feat = r._find_registry_feature("001-bridge-grammar-engine")
        assert feat is not None
        assert feat["name"] == "Grammar+Explain"

    def test_find_multi_coverage_second(self):
        """複数値 '001,034' → Feature 034 マッチング."""
        r = _make_registry([
            {"hackathon_project_coverage": "001,034", "name": "Grammar+Explain"},
        ])
        feat = r._find_registry_feature("034-explain-my-answer")
        assert feat is not None

    def test_find_partial_coverage(self):
        """接尾辞 '027-partial' → Feature 027 マッチング."""
        r = _make_registry([
            {"hackathon_project_coverage": "027-partial", "name": "Hangul"},
        ])
        feat = r._find_registry_feature("027-hangul-learning")
        assert feat is not None
        assert feat["name"] == "Hangul"

    def test_find_null_coverage(self):
        """null coverage → マッチング不可."""
        r = _make_registry([
            {"hackathon_project_coverage": None, "name": "NoMatch"},
        ])
        assert r._find_registry_feature("005-core") is None

    def test_find_non_numeric_coverage(self):
        """非数値 'cloud-tts' → スキップ（数字接頭辞なし）."""
        r = _make_registry([
            {"hackathon_project_coverage": "cloud-tts", "name": "TTS"},
        ])
        assert r._find_registry_feature("005-core") is None

    def test_get_all_matching_features(self):
        """一つの Feature に複数の registry 項目がマッチング."""
        r = _make_registry([
            {"hackathon_project_coverage": "005", "name": "A", "assessments": {}},
            {"hackathon_project_coverage": "005,012", "name": "B", "assessments": {}},
            {"hackathon_project_coverage": "012", "name": "C", "assessments": {}},
        ])
        matches = r.get_all_matching_features("005-core-learning-session")
        assert len(matches) == 2
        names = {m["name"] for m in matches}
        assert names == {"A", "B"}

    def test_get_assessment_count(self):
        """assessment_count は hackathon_project_coverage でマッチング."""
        r = _make_registry([
            {
                "hackathon_project_coverage": "008",
                "assessments": {
                    "duolingo": {"depth": 3, "confidence": 0.7},
                    "speak": {"depth": 2, "confidence": 0.5},
                },
            },
        ])
        assert r.get_assessment_count("008-monetization-system") == 2


# ── GapData Tests (4個) ────────────────────────────────────────────────


class TestGapData:
    """GapData 照会テスト."""

    def test_get_opportunity_score_found(self):
        g = _make_gaps([
            {"existing_feature_id": "012", "opportunity_score": 5.4, "gap_severity": "MEDIUM"},
        ])
        assert g.get_opportunity_score("012-topik") == 5.4

    def test_get_opportunity_score_not_found(self):
        g = _make_gaps([
            {"existing_feature_id": "012", "opportunity_score": 5.4},
        ])
        assert g.get_opportunity_score("999-nonexistent") is None

    def test_get_is_industry_standard_true(self):
        g = _make_gaps([
            {"existing_feature_id": "005", "is_industry_standard": True},
        ])
        assert g.get_is_industry_standard("005-core") is True

    def test_get_is_industry_standard_false(self):
        g = _make_gaps([
            {"existing_feature_id": "005", "is_industry_standard": False},
        ])
        assert g.get_is_industry_standard("005-core") is False


# ── calc_reach Tests (8個) ─────────────────────────────────────────────


class TestCalcReach:
    """Reach スコア計算テスト — 純粋独立加重和."""

    def test_completed_feature_reach_is_1(self, tmp_dir):
        """100% 完了機能は Reach=1."""
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        ctx = _make_context_data(progress_pct=100)
        result = calc_reach(brief, ctx)
        assert result["score"] == 1

    def test_high_progress_reduces_reach(self, tmp_dir):
        """高い進捗率 → Reach 減少."""
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        ctx_80 = _make_context_data(progress_pct=85)
        ctx_0 = _make_context_data(progress_pct=0)
        r80 = calc_reach(brief, ctx_80)
        r0 = calc_reach(brief, ctx_0)
        assert r80["score"] < r0["score"]

    def test_reach_bounds(self, tmp_dir):
        """Reach は 1-10 範囲."""
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        ctx = _make_context_data()
        result = calc_reach(brief, ctx)
        assert 1 <= result["score"] <= 10

    def test_no_brief_reach(self, tmp_dir):
        """BRIEF がなければデフォルト値付近."""
        brief = BriefData(tmp_dir / "BRIEF.md")
        ctx = _make_context_data()
        result = calc_reach(brief, ctx)
        assert 1 <= result["score"] <= 10

    def test_uses_brief_not_cache(self, tmp_dir):
        """calc_reach は BriefData を使用し brief_context キャッシュを無視."""
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        ctx = _make_context_data()
        ctx.brief_context = {"core_goal": "STALE CACHE DATA"}
        result = calc_reach(brief, ctx)
        assert "Freemium" in result["evidence"]["target_user_scope"]["value"]

    def test_ltv_retention_boosts_biz(self, tmp_dir):
        """LTV+retention キーワード → biz_score=9."""
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        ctx = _make_context_data()
        result = calc_reach(brief, ctx)
        # Format A has both LTV and retention → biz=9
        assert result["score"] >= 5  # 上方補正確認

    def test_no_metrics_low_biz(self, tmp_dir):
        """ビジネスメトリクスなし → biz_score=3."""
        brief = BriefData(tmp_dir / "NONEXIST.md")
        ctx = _make_context_data()
        result = calc_reach(brief, ctx)
        # user_scope=5*0.4 + biz=3*0.35 + progress=6*0.25 = 2+1.05+1.5 = 4.55
        assert result["score"] == 4.5  # round(4.55, 1) → 4.5 (IEEE 754 banker's rounding)

    def test_no_registry_in_signature(self, tmp_dir):
        """calc_reach は registry パラメータを受け取らない."""
        import inspect
        sig = inspect.signature(calc_reach)
        param_names = list(sig.parameters.keys())
        assert "registry" not in param_names


# ── calc_impact Tests (8個) ────────────────────────────────────────────


class TestCalcImpact:
    """Impact スコア計算テスト."""

    def test_impact_snap_to_grid(self, tmp_dir):
        """Impact は Intercom 5 段階のいずれか."""
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        ctx = _make_context_data()
        result = calc_impact(brief, ctx, _empty_gaps())
        assert result["score"] in {0.25, 0.5, 1, 2, 3}

    def test_completed_feature_minimal_impact(self, tmp_dir):
        """100% 完了は Impact=0.25 (Minimal)."""
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        ctx = _make_context_data(progress_pct=100)
        result = calc_impact(brief, ctx, _empty_gaps())
        assert result["score"] == 0.25

    def test_monetization_keyword_high_impact(self, tmp_dir):
        """収益/monetization キーワード → Impact >= 2."""
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        ctx = _make_context_data()
        result = calc_impact(brief, ctx, _empty_gaps())
        assert result["score"] >= 2  # "収益" in core_goal

    def test_uses_brief_not_cache(self, tmp_dir):
        """calc_impact は BriefData を使用し brief_context キャッシュを無視."""
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        ctx = _make_context_data()
        ctx.brief_context = {"core_goal": "STALE CACHE"}
        result = calc_impact(brief, ctx, _empty_gaps())
        assert "Freemium" in result["evidence"]["core_goal"]["value"]

    def test_gap_high_floor(self, tmp_dir):
        """HIGH gap severity → 最低 Impact=2."""
        _write_brief_format_b(tmp_dir)  # no monetization keyword
        brief = BriefData(tmp_dir / "BRIEF.md")
        ctx = _make_context_data(feature_id="012-topik")
        gaps = _make_gaps([
            {"existing_feature_id": "012", "gap_severity": "HIGH"},
        ])
        result = calc_impact(brief, ctx, gaps)
        assert result["score"] >= 2

    def test_gap_medium_floor(self, tmp_dir):
        """MEDIUM gap severity → 最低 Impact=1."""
        brief = BriefData(tmp_dir / "NONEXIST.md")
        ctx = _make_context_data(feature_id="027-hangul")
        gaps = _make_gaps([
            {"existing_feature_id": "027", "gap_severity": "MEDIUM"},
        ])
        result = calc_impact(brief, ctx, gaps)
        assert result["score"] >= 1

    def test_no_registry_in_signature(self, tmp_dir):
        """calc_impact は registry パラメータを受け取らない."""
        import inspect
        sig = inspect.signature(calc_impact)
        param_names = list(sig.parameters.keys())
        assert "registry" not in param_names

    def test_gap_severity_in_evidence(self, tmp_dir):
        """evidence に gap_severity が含まれる."""
        _write_brief_format_b(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        ctx = _make_context_data(feature_id="012-topik")
        gaps = _make_gaps([
            {"existing_feature_id": "012", "gap_severity": "HIGH"},
        ])
        result = calc_impact(brief, ctx, gaps)
        assert "gap_severity" in result["evidence"]
        assert result["evidence"]["gap_severity"]["value"] == "HIGH"


# ── calc_confidence Tests (7個) ────────────────────────────────────────


class TestCalcConfidence:
    """Confidence スコア計算（4ファクター）."""

    def test_confidence_floor(self, tmp_dir):
        """全 factor が 0 でも confidence >= 0.05."""
        brief = BriefData(tmp_dir / "NONEXIST.md")
        spec = SpecData(None)
        ctx = _make_context_data()
        result = calc_confidence(brief, spec, ctx)
        assert result["score"] >= 0.05

    def test_empty_research_ids_zero_score(self):
        """research_ids=[] なら research_evidence.score=0.0."""
        ctx = _make_context_data()
        brief = BriefData(Path("/nonexistent"))
        spec = SpecData(None)
        result = calc_confidence(brief, spec, ctx)
        assert result["factors"]["research_evidence"]["score"] == 0.0

    def test_research_ids_increase_confidence(self, tmp_dir):
        """research_ids があれば confidence 上昇."""
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        spec = SpecData(None)
        ctx_with = _make_context_data(research_ids_in_refs=["R-1", "R-2", "R-3"])
        ctx_without = _make_context_data()
        c_with = calc_confidence(brief, spec, ctx_with)
        c_without = calc_confidence(brief, spec, ctx_without)
        assert c_with["score"] > c_without["score"]

    def test_confidence_range(self, tmp_dir):
        """Confidence は 0.05-1.0 範囲."""
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        spec = SpecData(None)
        ctx = _make_context_data(
            progress_pct=80,
            research_ids_in_refs=["R-1", "R-2", "R-3", "R-4", "R-5"],
        )
        result = calc_confidence(brief, spec, ctx)
        assert 0.05 <= result["score"] <= 1.0

    def test_high_brief_completeness(self, tmp_dir):
        """BRIEF セクションが多ければ brief_completeness が高い."""
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        spec = SpecData(None)
        ctx = _make_context_data()
        result = calc_confidence(brief, spec, ctx)
        assert result["factors"]["brief_completeness"]["score"] >= 0.5

    def test_no_competitor_data_factor(self, tmp_dir):
        """v2: competitor_data ファクターがないこと."""
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        spec = SpecData(None)
        ctx = _make_context_data()
        result = calc_confidence(brief, spec, ctx)
        assert "competitor_data" not in result["factors"]

    def test_four_factors_only(self, tmp_dir):
        """正確に 4 個のファクターのみ存在."""
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        spec = SpecData(None)
        ctx = _make_context_data()
        result = calc_confidence(brief, spec, ctx)
        assert set(result["factors"].keys()) == {
            "brief_completeness", "spec_quality", "research_evidence", "implementation_status"
        }


# ── calc_effort Tests (3個) ────────────────────────────────────────────


class TestCalcEffort:
    """Effort スコア計算テスト."""

    def test_effort_bounds(self, tmp_dir):
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        spec = SpecData(None)
        ctx = _make_context_data(fr_total=5)
        result = calc_effort(brief, spec, ctx)
        assert 0.5 <= result["score"] <= 20

    def test_completed_feature_minimal_effort(self, tmp_dir):
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        spec = SpecData(None)
        ctx = _make_context_data(progress_pct=100, fr_total=10)
        result = calc_effort(brief, spec, ctx)
        assert result["score"] == 0.5

    def test_more_frs_more_effort(self, tmp_dir):
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        spec = SpecData(None)
        ctx_few = _make_context_data(fr_total=2)
        ctx_many = _make_context_data(fr_total=10)
        e_few = calc_effort(brief, spec, ctx_few)
        e_many = calc_effort(brief, spec, ctx_many)
        assert e_many["score"] > e_few["score"]


# ── calc_competitive_adjustment Tests (8個) ────────────────────────────


class TestCalcCompetitiveAdjustment:
    """Competitive adjustment post-multiplier."""

    def test_no_data_neutral(self):
        """データなし → 1.0（中立）."""
        r = _empty_registry()
        g = _empty_gaps()
        ctx = _make_context_data(feature_id="999-none")
        result = calc_competitive_adjustment(r, g, ctx)
        assert result["adjustment"] == 1.0
        assert result["has_data"] is False

    def test_high_assessments(self):
        """7+ assessments → +0.10."""
        r = _make_registry([{
            "hackathon_project_coverage": "005",
            "assessments": {f"app{i}": {"depth": 3, "confidence": 0.7} for i in range(8)},
        }])
        g = _empty_gaps()
        ctx = _make_context_data(feature_id="005-core")
        result = calc_competitive_adjustment(r, g, ctx)
        assert result["adjustment"] >= 1.10

    def test_industry_standard_bonus(self):
        """is_industry_standard=True → +0.05."""
        r = _empty_registry()
        g = _make_gaps([
            {"existing_feature_id": "005", "is_industry_standard": True},
        ])
        ctx = _make_context_data(feature_id="005-core")
        result = calc_competitive_adjustment(r, g, ctx)
        assert result["adjustment"] >= 1.05

    def test_high_opportunity_bonus(self):
        """opportunity_score >= 7 → +0.10."""
        r = _empty_registry()
        g = _make_gaps([
            {"existing_feature_id": "005", "opportunity_score": 8.0},
        ])
        ctx = _make_context_data(feature_id="005-core")
        result = calc_competitive_adjustment(r, g, ctx)
        assert result["adjustment"] >= 1.10

    def test_low_opportunity_penalty(self):
        """opportunity_score < 3 → -0.05."""
        r = _empty_registry()
        g = _make_gaps([
            {"existing_feature_id": "005", "opportunity_score": 2.0},
        ])
        ctx = _make_context_data(feature_id="005-core")
        result = calc_competitive_adjustment(r, g, ctx)
        assert result["adjustment"] < 1.0

    def test_high_gap_severity(self):
        """HIGH gap → +0.10."""
        r = _empty_registry()
        g = _make_gaps([
            {"existing_feature_id": "005", "gap_severity": "HIGH"},
        ])
        ctx = _make_context_data(feature_id="005-core")
        result = calc_competitive_adjustment(r, g, ctx)
        assert result["adjustment"] >= 1.10

    def test_range_clamped(self):
        """調整値が 0.8-1.3 の範囲に制限."""
        # 全シグナル最大
        r = _make_registry([{
            "hackathon_project_coverage": "005",
            "assessments": {f"app{i}": {"depth": 5, "confidence": 0.9} for i in range(10)},
        }])
        g = _make_gaps([{
            "existing_feature_id": "005",
            "is_industry_standard": True,
            "opportunity_score": 10.0,
            "gap_severity": "HIGH",
        }])
        ctx = _make_context_data(feature_id="005-core")
        result = calc_competitive_adjustment(r, g, ctx)
        assert 0.8 <= result["adjustment"] <= 1.3

    def test_evidence_transparency(self):
        """全シグナルの evidence が記録される."""
        r = _empty_registry()
        g = _empty_gaps()
        ctx = _make_context_data(feature_id="999-none")
        result = calc_competitive_adjustment(r, g, ctx)
        evidence = result["evidence"]
        assert "assessment_count" in evidence
        assert "is_industry_standard" in evidence
        assert "opportunity_score" in evidence
        assert "gap_severity" in evidence


# ── compose_final_score Tests (4個) ────────────────────────────────────


class TestComposeFinalScore:
    """最終スコア合成."""

    def test_basic_composition(self):
        """adjusted = rice × comp × override."""
        rice = {"rice_score": 4.0, "component_breakdown": {"numerator": 8, "denominator": 2}}
        comp = {"adjustment": 1.1}
        override = {"value": 1.0, "reason": None}
        result = compose_final_score(rice, comp, override)
        assert result["rice_score"] == 4.0
        assert result["adjusted_score"] == 4.4  # 4.0 * 1.1 * 1.0

    def test_with_override(self):
        rice = {"rice_score": 5.0, "component_breakdown": {"numerator": 10, "denominator": 2}}
        comp = {"adjustment": 1.0}
        override = {"value": 1.2, "reason": "手動引き上げ"}
        result = compose_final_score(rice, comp, override)
        assert result["adjusted_score"] == 6.0  # 5.0 * 1.0 * 1.2

    def test_formula_string(self):
        rice = {"rice_score": 1.0, "component_breakdown": {"numerator": 1, "denominator": 1}}
        comp = {"adjustment": 1.0}
        override = {"value": 1.0, "reason": None}
        result = compose_final_score(rice, comp, override)
        assert "CompAdj" in result["formula"]
        assert "Override" in result["formula"]

    def test_all_fields_present(self):
        rice = {"rice_score": 2.0, "component_breakdown": {"numerator": 4, "denominator": 2}}
        comp = {"adjustment": 1.05}
        override = {"value": 0.9, "reason": "test"}
        result = compose_final_score(rice, comp, override)
        assert "rice_score" in result
        assert "adjusted_score" in result
        assert "competitive_adjustment" in result
        assert "manual_override_applied" in result


# ── _normalize_manual_override Tests (5個) ─────────────────────────────


class TestNormalizeManualOverride:
    """manual_override 正規化."""

    def test_dict_input(self):
        result = _normalize_manual_override({"value": 1.1, "reason": "test"})
        assert result["value"] == 1.1
        assert result["reason"] == "test"

    def test_flat_float(self):
        """flat float → dict 変換."""
        result = _normalize_manual_override(1.15)
        assert result["value"] == 1.15
        assert result["reason"] is None

    def test_none_input(self):
        result = _normalize_manual_override(None)
        assert result["value"] == 1.0
        assert result["reason"] is None

    def test_clamp_high(self):
        """1.5 → 1.2 に clamp."""
        result = _normalize_manual_override({"value": 1.5, "reason": "too high"})
        assert result["value"] == 1.2

    def test_clamp_low(self):
        """0.5 → 0.8 に clamp."""
        result = _normalize_manual_override(0.5)
        assert result["value"] == 0.8


# ── calc_rice_score Tests (4個) ────────────────────────────────────────


class TestCalcRiceScore:
    """RICE 最終スコア（純粋、manual_override なし）."""

    def test_basic_formula(self):
        """Score = (R × I × C) / E."""
        result = calc_rice_score(
            {"score": 5}, {"score": 2}, {"score": 0.8}, {"score": 4}
        )
        # 5 * 2 * 0.8 / 4 = 2.0
        assert result["rice_score"] == 2.0

    def test_zero_effort_safety(self):
        """Effort=0 なら 0.5 で代替."""
        result = calc_rice_score(
            {"score": 5}, {"score": 1}, {"score": 0.5}, {"score": 0}
        )
        # 5 * 1 * 0.5 / 0.5 = 5.0
        assert result["rice_score"] == 5.0

    def test_no_manual_override_param(self):
        """calc_rice_score に manual_override パラメータなし."""
        import inspect
        sig = inspect.signature(calc_rice_score)
        assert "manual_override" not in sig.parameters

    def test_component_breakdown(self):
        result = calc_rice_score(
            {"score": 6}, {"score": 3}, {"score": 0.5}, {"score": 3}
        )
        assert result["component_breakdown"]["numerator"] == 9.0
        assert result["component_breakdown"]["denominator"] == 3


# ── Property-based Tests (5個) ─────────────────────────────────────────


class TestPropertyBased:
    """数学的不変条件検証."""

    def test_reach_progress_inverse(self, tmp_dir):
        """進捗率逆比例: progress↑ → reach↓."""
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        scores = []
        for pct in [0, 25, 50, 80, 100]:
            ctx = _make_context_data(progress_pct=pct)
            scores.append(calc_reach(brief, ctx)["score"])
        # 単調減少確認（非厳密）
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], f"progress {[0,25,50,80,100][i]}→{[0,25,50,80,100][i+1]}: {scores[i]} >= {scores[i+1]}"

    def test_competitive_adj_range_always(self):
        """どの入力でも competitive_adjustment は 0.8-1.3."""
        for opp in [0, 2, 5, 7, 10]:
            for sev in [None, "LOW", "MEDIUM", "HIGH"]:
                r = _empty_registry()
                candidates = [{"existing_feature_id": "005", "opportunity_score": opp}]
                if sev:
                    candidates[0]["gap_severity"] = sev
                g = _make_gaps(candidates)
                ctx = _make_context_data(feature_id="005-core")
                result = calc_competitive_adjustment(r, g, ctx)
                assert 0.8 <= result["adjustment"] <= 1.3, f"opp={opp}, sev={sev}: {result['adjustment']}"

    def test_manual_override_clamp_always(self):
        """どの入力でも manual_override は 0.8-1.2."""
        for val in [-1, 0, 0.5, 0.8, 1.0, 1.2, 1.5, 100]:
            result = _normalize_manual_override(val)
            assert 0.8 <= result["value"] <= 1.2, f"val={val}: {result['value']}"

    def test_rice_score_non_negative(self, tmp_dir):
        """RICE スコアは常に 0 以上."""
        _write_brief_format_a(tmp_dir)
        brief = BriefData(tmp_dir / "BRIEF.md")
        for pct in [0, 50, 100]:
            ctx = _make_context_data(progress_pct=pct)
            r = calc_reach(brief, ctx)
            i = calc_impact(brief, ctx, _empty_gaps())
            c = calc_confidence(brief, SpecData(None), ctx)
            e = calc_effort(brief, SpecData(None), ctx)
            score = calc_rice_score(r, i, c, e)
            assert score["rice_score"] >= 0

    def test_confidence_floor_always(self, tmp_dir):
        """どの入力でも confidence >= 0.05."""
        for pct in [0, 50, 100]:
            brief = BriefData(tmp_dir / "NONEXIST.md")
            spec = SpecData(None)
            ctx = _make_context_data(progress_pct=pct)
            result = calc_confidence(brief, spec, ctx)
            assert result["score"] >= 0.05


# ── Golden File Tests (5個) ────────────────────────────────────────────


class TestGoldenFile:
    """代表 5 Feature スナップショット基準検証."""

    @pytest.fixture
    def real_features_dir(self):
        d = Path(__file__).resolve().parents[2] / "docs" / "features"
        if not d.exists():
            pytest.skip("実プロジェクト Feature ディレクトリなし")
        return d

    def _calc_for_feature(self, feature_dir, feature_name):
        """特定 Feature の全体 RICE 計算."""
        fd = feature_dir / feature_name
        if not (fd / "CONTEXT.json").exists():
            pytest.skip(f"{feature_name} CONTEXT.json なし")
        data = json.loads((fd / "CONTEXT.json").read_text())
        brief = BriefData(fd / "BRIEF.md")
        spec_paths = list(fd.glob("SPEC*.md"))
        spec = SpecData(spec_paths[0] if spec_paths else None)
        ctx = ContextData(data)
        r = calc_reach(brief, ctx)
        i = calc_impact(brief, ctx, GapData())
        c = calc_confidence(brief, spec, ctx)
        e = calc_effort(brief, spec, ctx)
        rice = calc_rice_score(r, i, c, e)
        return r, i, c, e, rice

    def test_f008_monetization(self, real_features_dir):
        """F008 マネタイズ: Impact >= 2（収益キーワード）."""
        r, i, c, e, rice = self._calc_for_feature(real_features_dir, "008-monetization-system")
        assert i["score"] >= 2

    def test_f024_ai_tutor(self, real_features_dir):
        """F024 AI チューター: コア機能、RICE > 0."""
        r, i, c, e, rice = self._calc_for_feature(real_features_dir, "024-ai-tutor-system")
        assert rice["rice_score"] > 0

    def test_f001_bridge_grammar(self, real_features_dir):
        """F001 ブリッジ文法: research_ids 多数 → confidence 高."""
        r, i, c, e, rice = self._calc_for_feature(real_features_dir, "001-bridge-grammar-engine")
        assert c["score"] >= 0.2  # research_ids 10個

    def test_f025_auth(self, real_features_dir):
        """F025 認証: 高い progress → Reach 減少."""
        r, i, c, e, rice = self._calc_for_feature(real_features_dir, "025-authentication-flow")
        # 認証は通常高い進捗率または完了
        assert r["score"] <= 7  # 未着手でなければ 10 にはならない

    def test_f005_core_learning(self, real_features_dir):
        """F005 コア学習: 全体フローエラーなし."""
        r, i, c, e, rice = self._calc_for_feature(real_features_dir, "005-core-learning-session")
        assert rice["rice_score"] >= 0


# ── process_feature Tests (4個) ────────────────────────────────────────


class TestProcessFeature:
    """process_feature オーケストレーション."""

    def test_missing_context_skipped(self, tmp_dir):
        """CONTEXT.json がなければ skipped."""
        r = _empty_registry()
        g = _empty_gaps()
        result = process_feature(tmp_dir, r, g, None, False, False)
        assert result["status"] == "skipped"

    def test_valid_feature_updates(self, tmp_dir):
        """有効な Feature → updated."""
        _write_brief_format_a(tmp_dir)
        (tmp_dir / "CONTEXT.json").write_text(json.dumps({
            "feature_id": "999-test",
            "progress": {"percentage": 0, "fr_total": 5, "fr_completed": 0},
            "quick_resume": {"current_state": "Planning"},
            "priority": {"schema": "rice-v2", "phase": "mvp", "calculated": {"rice_score": 1.0}},
        }))
        r = _empty_registry()
        g = _empty_gaps()
        result = process_feature(tmp_dir, r, g, None, False, False)
        assert result["status"] == "updated"
        assert result["new_score"] > 0

    def test_schema_remains_v2(self, tmp_dir):
        """rice-v2 スキーマ維持確認."""
        _write_brief_format_a(tmp_dir)
        (tmp_dir / "CONTEXT.json").write_text(json.dumps({
            "feature_id": "999-test",
            "progress": {"percentage": 0, "fr_total": 3, "fr_completed": 0},
            "priority": {"schema": "rice-v2", "phase": "mvp", "calculated": {"rice_score": 1.0}},
        }))
        r = _empty_registry()
        g = _empty_gaps()
        result = process_feature(tmp_dir, r, g, None, True, False)
        # ファイルを再読み込みして schema 確認
        data = json.loads((tmp_dir / "CONTEXT.json").read_text())
        assert data["priority"]["schema"] == "rice-v2"
        assert data["priority"]["version"] == "3.0"
        assert "competitive_adjustment" in data["priority"]

    def test_json_error_handled(self, tmp_dir):
        """不正な JSON → error."""
        (tmp_dir / "CONTEXT.json").write_text("{ broken json")
        r = _empty_registry()
        g = _empty_gaps()
        result = process_feature(tmp_dir, r, g, None, False, False)
        assert result["status"] == "error"


# ── Migration v1→v2 Tests (3個) ───────────────────────────────────────


class TestRecalculation:
    """再計算動作テスト (process_feature ベース)."""

    def test_idempotent_rerun(self, tmp_dir):
        """2回実行しても結果同一（冪等性）."""
        _write_brief_format_a(tmp_dir)
        ctx_data = {
            "feature_id": "999-test",
            "progress": {"percentage": 30, "fr_total": 4, "fr_completed": 1},
            "priority": {"schema": "rice-v2", "phase": "mvp", "calculated": {"rice_score": 2.0}},
        }
        (tmp_dir / "CONTEXT.json").write_text(json.dumps(ctx_data))
        r = _empty_registry()
        g = _empty_gaps()
        process_feature(tmp_dir, r, g, None, True, False)
        data1 = json.loads((tmp_dir / "CONTEXT.json").read_text())
        score1 = data1["priority"]["calculated"]["adjusted_score"]

        # 2回目実行
        process_feature(tmp_dir, r, g, None, True, False)
        data2 = json.loads((tmp_dir / "CONTEXT.json").read_text())
        score2 = data2["priority"]["calculated"]["adjusted_score"]

        assert score1 == score2

    def test_history_appended(self, tmp_dir):
        """実行ごとに history に項目追加."""
        _write_brief_format_a(tmp_dir)
        (tmp_dir / "CONTEXT.json").write_text(json.dumps({
            "feature_id": "999-test",
            "progress": {"percentage": 0, "fr_total": 3, "fr_completed": 0},
            "priority": {"schema": "rice-v2", "phase": "mvp", "calculated": {"rice_score": 1.0}},
        }))
        r = _empty_registry()
        g = _empty_gaps()
        process_feature(tmp_dir, r, g, None, True, False)
        data = json.loads((tmp_dir / "CONTEXT.json").read_text())
        assert len(data["priority"]["history"]) >= 1
        latest = data["priority"]["history"][-1]
        assert "rice_score" in latest
        assert "adjusted_score" in latest


# ── Integration Tests (3個) ────────────────────────────────────────────


class TestIntegration:
    """実 Feature データ基準統合テスト."""

    @pytest.fixture
    def real_features_dir(self):
        d = Path(__file__).resolve().parents[2] / "docs" / "features"
        if not d.exists():
            pytest.skip("実プロジェクト Feature ディレクトリなし")
        return d

    def test_f001_research_ids_from_canonical(self, real_features_dir):
        """F001 は canonical パスから research_ids を読み取ること."""
        ctx_path = real_features_dir / "001-bridge-grammar-engine" / "CONTEXT.json"
        if not ctx_path.exists():
            pytest.skip("F001 CONTEXT.json なし")
        data = json.loads(ctx_path.read_text())
        ctx = ContextData(data)
        assert len(ctx.research_ids) >= 5

    def test_f008_no_research_ids(self, real_features_dir):
        """F008 は research_ids がないこと."""
        ctx_path = real_features_dir / "008-monetization-system" / "CONTEXT.json"
        if not ctx_path.exists():
            pytest.skip("F008 CONTEXT.json なし")
        data = json.loads(ctx_path.read_text())
        ctx = ContextData(data)
        assert len(ctx.research_ids) == 0

    def test_all_features_no_errors(self, real_features_dir):
        """全 Feature でエラーなく RICE v2 計算可能."""
        registry = RegistryData()
        gaps = GapData()
        errors = []
        for fd in sorted(real_features_dir.iterdir()):
            ctx_path = fd / "CONTEXT.json"
            if not ctx_path.exists():
                continue
            try:
                data = json.loads(ctx_path.read_text())
                brief = BriefData(fd / "BRIEF.md")
                spec_paths = list(fd.glob("SPEC*.md"))
                spec = SpecData(spec_paths[0] if spec_paths else None)
                ctx = ContextData(data)
                r = calc_reach(brief, ctx)
                i = calc_impact(brief, ctx, gaps)
                c = calc_confidence(brief, spec, ctx)
                e = calc_effort(brief, spec, ctx)
                rice = calc_rice_score(r, i, c, e)
                comp = calc_competitive_adjustment(registry, gaps, ctx)
                override = _normalize_manual_override(1.0)
                final = compose_final_score(rice, comp, override)
                assert final["adjusted_score"] >= 0
            except Exception as ex:
                errors.append(f"{fd.name}: {ex}")
        assert errors == [], f"Errors in features: {errors}"
