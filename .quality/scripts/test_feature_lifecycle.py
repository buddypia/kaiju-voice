#!/usr/bin/env python3
"""
test_feature_lifecycle.py — feature_lifecycle.py 共有ユーティリティ + パイプライン統合テスト

テスト範囲:
  1. feature_lifecycle.py ユーティリティ関数 (is_active, get_lifecycle_state 等)
  2. rice_calculator.py の Archived フィルタリング
  3. check_priority_stale.py の Archived フィルタリング
  4. brief_regenerator.py の Archived フィルタリング
  5. context_schema.json の archived フィールド妥当性
  6. 032 CONTEXT.json データ整合性
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# プロジェクトルート基準パス
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from feature_lifecycle import (
    INACTIVE_STATES,
    get_archived_reason,
    get_archived_ref,
    get_lifecycle_state,
    is_active,
    load_context,
)


class TestIsActive(unittest.TestCase):
    """is_active() 関数テスト"""

    def test_archived_is_inactive(self):
        ctx = {"quick_resume": {"current_state": "Archived"}}
        self.assertFalse(is_active(ctx))

    def test_failed_is_inactive(self):
        ctx = {"quick_resume": {"current_state": "Failed"}}
        self.assertFalse(is_active(ctx))

    def test_done_is_active(self):
        ctx = {"quick_resume": {"current_state": "Done"}}
        self.assertTrue(is_active(ctx))

    def test_implementing_is_active(self):
        ctx = {"quick_resume": {"current_state": "Implementing"}}
        self.assertTrue(is_active(ctx))

    def test_idle_is_active(self):
        ctx = {"quick_resume": {"current_state": "Idle"}}
        self.assertTrue(is_active(ctx))

    def test_spec_drafting_is_active(self):
        ctx = {"quick_resume": {"current_state": "SpecDrafting"}}
        self.assertTrue(is_active(ctx))

    def test_blocked_is_active(self):
        """Blockedは一時的な状態のためアクティブと判定"""
        ctx = {"quick_resume": {"current_state": "Blocked"}}
        self.assertTrue(is_active(ctx))

    def test_missing_quick_resume_is_active(self):
        """quick_resume がなければ unknown → アクティブと判定（下位互換）"""
        ctx = {}
        self.assertTrue(is_active(ctx))

    def test_missing_current_state_is_active(self):
        ctx = {"quick_resume": {}}
        self.assertTrue(is_active(ctx))


class TestGetLifecycleState(unittest.TestCase):
    """get_lifecycle_state() 関数テスト"""

    def test_returns_state(self):
        ctx = {"quick_resume": {"current_state": "Done"}}
        self.assertEqual(get_lifecycle_state(ctx), "Done")

    def test_returns_unknown_when_missing(self):
        ctx = {}
        self.assertEqual(get_lifecycle_state(ctx), "unknown")

    def test_returns_unknown_when_no_state(self):
        ctx = {"quick_resume": {}}
        self.assertEqual(get_lifecycle_state(ctx), "unknown")


class TestGetArchivedMetadata(unittest.TestCase):
    """archived_reason / archived_ref 関数テスト"""

    def test_archived_reason(self):
        ctx = {"archived_reason": "merged"}
        self.assertEqual(get_archived_reason(ctx), "merged")

    def test_archived_ref(self):
        ctx = {"archived_ref": "031-casual-banmal-mode"}
        self.assertEqual(get_archived_ref(ctx), "031-casual-banmal-mode")

    def test_missing_reason_returns_none(self):
        ctx = {}
        self.assertIsNone(get_archived_reason(ctx))

    def test_missing_ref_returns_none(self):
        ctx = {}
        self.assertIsNone(get_archived_ref(ctx))


class TestLoadContext(unittest.TestCase):
    """load_context() 関数テスト"""

    def test_load_existing_context(self):
        """実プロジェクトの 032 CONTEXT.json ロードテスト"""
        feature_dir = PROJECT_ROOT / "docs" / "features" / "032-text-adventure-mode"
        if not feature_dir.exists():
            self.skipTest("032 feature dir not found")
        ctx = load_context(feature_dir)
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx["feature_id"], "032-text-adventure-mode")

    def test_load_nonexistent_returns_none(self):
        ctx = load_context(Path("/nonexistent/path"))
        self.assertIsNone(ctx)

    def test_load_invalid_json_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx_path = Path(tmpdir) / "CONTEXT.json"
            ctx_path.write_text("{invalid json", encoding="utf-8")
            ctx = load_context(Path(tmpdir))
            self.assertIsNone(ctx)


class TestInactiveStates(unittest.TestCase):
    """INACTIVE_STATES 定数テスト"""

    def test_is_frozenset(self):
        self.assertIsInstance(INACTIVE_STATES, frozenset)

    def test_contains_archived(self):
        self.assertIn("Archived", INACTIVE_STATES)

    def test_contains_failed(self):
        self.assertIn("Failed", INACTIVE_STATES)

    def test_does_not_contain_active_states(self):
        active = ["Idle", "Done", "Implementing", "SpecDrafting", "Blocked"]
        for state in active:
            self.assertNotIn(state, INACTIVE_STATES)


class TestContextSchema(unittest.TestCase):
    """context_schema.json の archived フィールド妥当性テスト"""

    @classmethod
    def setUpClass(cls):
        schema_path = PROJECT_ROOT / "docs" / "_templates" / "context_schema.json"
        if not schema_path.exists():
            raise unittest.SkipTest("context_schema.json not found")
        with open(schema_path, encoding="utf-8") as f:
            cls.schema = json.load(f)

    def test_archived_reason_exists(self):
        self.assertIn("archived_reason", self.schema["properties"])

    def test_archived_reason_enum(self):
        ar = self.schema["properties"]["archived_reason"]
        expected = ["merged", "superseded", "deferred", "abandoned", "duplicate"]
        self.assertEqual(ar["enum"], expected)

    def test_archived_ref_exists(self):
        self.assertIn("archived_ref", self.schema["properties"])

    def test_archived_ref_pattern(self):
        ar = self.schema["properties"]["archived_ref"]
        self.assertEqual(ar["pattern"], "^[0-9]{3}-[a-z0-9-]+$")

    def test_archived_fields_not_required(self):
        """archived フィールドはオプショナルであること"""
        required = self.schema.get("required", [])
        self.assertNotIn("archived_reason", required)
        self.assertNotIn("archived_ref", required)


class TestFeature032DataIntegrity(unittest.TestCase):
    """032 CONTEXT.json データ整合性テスト"""

    @classmethod
    def setUpClass(cls):
        ctx_path = PROJECT_ROOT / "docs" / "features" / "032-text-adventure-mode" / "CONTEXT.json"
        if not ctx_path.exists():
            raise unittest.SkipTest("032 CONTEXT.json not found")
        with open(ctx_path, encoding="utf-8") as f:
            cls.ctx = json.load(f)

    def test_state_is_archived(self):
        self.assertEqual(
            self.ctx["quick_resume"]["current_state"], "Archived"
        )

    def test_archived_reason_is_merged(self):
        self.assertEqual(self.ctx["archived_reason"], "merged")

    def test_archived_ref_is_031(self):
        self.assertEqual(self.ctx["archived_ref"], "031-casual-banmal-mode")

    def test_feature_type_preserved(self):
        """feature_type は元の値 (ui_feature) を維持"""
        self.assertEqual(self.ctx["feature_type"], "ui_feature")

    def test_is_inactive(self):
        self.assertFalse(is_active(self.ctx))


class TestPipelineIntegration(unittest.TestCase):
    """パイプラインスクリプトの Archived フィルタリング統合テスト"""

    def test_rice_calculator_skips_archived(self):
        """rice_calculator.process_feature() が Archived をスキップするか確認"""
        feature_dir = PROJECT_ROOT / "docs" / "features" / "032-text-adventure-mode"
        if not feature_dir.exists():
            self.skipTest("032 feature dir not found")

        # process_feature の import に必要なモジュールパス
        from rice_calculator import process_feature, RegistryData, GapData

        registry = RegistryData()
        gaps = GapData()
        result = process_feature(feature_dir, registry, gaps, None, False, False)
        self.assertEqual(result["status"], "skipped")
        self.assertTrue(any("非アクティブ" in d for d in result["diffs"]))

    def test_brief_regenerator_skips_archived(self):
        """brief_regenerator.regenerate_brief() が Archived をスキップするか確認"""
        feature_dir = PROJECT_ROOT / "docs" / "features" / "032-text-adventure-mode"
        if not feature_dir.exists():
            self.skipTest("032 feature dir not found")

        from brief_regenerator import regenerate_brief

        result = regenerate_brief(feature_dir, apply=False, verbose=False)
        self.assertEqual(result["action"], "skipped_inactive")

    def test_active_feature_not_skipped(self):
        """アクティブな Feature (001) はスキップされないことを確認"""
        feature_dir = PROJECT_ROOT / "docs" / "features" / "001-bridge-grammar-engine"
        if not feature_dir.exists():
            self.skipTest("001 feature dir not found")

        from brief_regenerator import regenerate_brief

        result = regenerate_brief(feature_dir, apply=False, verbose=False)
        self.assertNotEqual(result["action"], "skipped_inactive")


if __name__ == "__main__":
    unittest.main(verbosity=2)
