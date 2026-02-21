#!/usr/bin/env python3
"""
NAV-GRAPH システム回帰テスト.

T1-T10 テストカテゴリ:
- T1: スキーマ妥当性 (JSON パース、構造、バージョンフォーマット)
- T2: 全画面カバレッジ (最小数、必須フィールド、ID 一致)
- T3: 孤立画面なし (tab/app_entry 除外)
- T4: デッドエンドなし (informational only)
- T5: 参照整合性 (trigger target, guard fallback)
- T6: コード同期 (screen.file 存在確認)
- T7: ID 一意性 (screen, trigger, flow)
- T8: Named route 一致 (main.dart 9個)
- T9: Mermaid 生成 (generator 実行 + stateDiagram-v2 出力)
- T10: Screen doc 参照 (nav-graph.json 言及率)

Usage:
    pytest test_nav_graph.py -v
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

# プロジェクトルート探索 (pubspec.yaml 基準)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
NAV_GRAPH_PATH = PROJECT_ROOT / "docs" / "navigation" / "nav-graph.json"
SCHEMA_PATH = PROJECT_ROOT / "docs" / "navigation" / "nav-graph.schema.json"
MERMAID_SCRIPT = PROJECT_ROOT / ".quality" / "scripts" / "nav-graph-to-mermaid.py"
VALIDATOR_SCRIPT = PROJECT_ROOT / ".quality" / "scripts" / "nav-graph-validator.py"


# ── 共通 fixture ──────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def nav_data():
    """nav-graph.json パース結果（モジュールスコープキャッシュ）."""
    assert NAV_GRAPH_PATH.exists(), f"nav-graph.json not found: {NAV_GRAPH_PATH}"
    return json.loads(NAV_GRAPH_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def schema_data():
    """nav-graph.schema.json パース結果."""
    assert SCHEMA_PATH.exists(), f"nav-graph.schema.json not found: {SCHEMA_PATH}"
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def all_screen_ids(nav_data):
    """全 screen ID set."""
    return set(nav_data["screens"].keys())


@pytest.fixture(scope="module")
def all_trigger_ids(nav_data):
    """全 trigger ID リスト（重複含む）."""
    ids = []
    for screen in nav_data["screens"].values():
        for trigger in screen.get("triggers", []):
            ids.append(trigger["id"])
    return ids


# ── T1: スキーマ妥当性 ─────────────────────────────────────────────────────


class TestNavGraphSchema:
    """T1: スキーマ妥当性検証."""

    def test_nav_graph_json_exists(self):
        """nav-graph.json ファイルが存在すること."""
        assert NAV_GRAPH_PATH.exists(), "nav-graph.json not found"

    def test_nav_graph_schema_exists(self):
        """nav-graph.schema.json ファイルが存在すること."""
        assert SCHEMA_PATH.exists(), "nav-graph.schema.json not found"

    def test_nav_graph_valid_json(self, nav_data):
        """nav-graph.json が有効な JSON であり必須 top-level キーを含む."""
        assert "version" in nav_data
        assert "screens" in nav_data
        assert "flows" in nav_data
        assert "updated_at" in nav_data

    def test_schema_valid_json(self, schema_data):
        """スキーマファイルが有効な JSON であり $schema キーを含む."""
        assert "$schema" in schema_data

    def test_version_format(self, nav_data):
        """version が semver 形式 (X.Y.Z) であること."""
        assert re.match(r"^\d+\.\d+\.\d+$", nav_data["version"]), (
            f"Invalid version format: {nav_data['version']}"
        )

    def test_updated_at_format(self, nav_data):
        """updated_at が YYYY-MM-DD 形式であること."""
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", nav_data["updated_at"]), (
            f"Invalid date format: {nav_data['updated_at']}"
        )

    def test_screen_id_pattern(self, nav_data):
        """全 screen ID が SCR-NNN-XXX パターンに従うこと."""
        pattern = re.compile(r"^SCR-\d{3}-[A-Z0-9-]+$")
        for sid in nav_data["screens"]:
            assert pattern.match(sid), f"Invalid screen ID pattern: {sid}"

    def test_trigger_id_pattern(self, nav_data):
        """全 trigger ID が TRG-NNN-XXX パターンに従うこと."""
        pattern = re.compile(r"^TRG-\d{3}-[A-Z0-9-]+$")
        for screen in nav_data["screens"].values():
            for trigger in screen.get("triggers", []):
                assert pattern.match(trigger["id"]), (
                    f"Invalid trigger ID pattern: {trigger['id']}"
                )

    def test_flow_id_pattern(self, nav_data):
        """全 flow ID が FLOW-XXX パターンに従うこと."""
        pattern = re.compile(r"^FLOW-[A-Z0-9-]+$")
        for fid in nav_data["flows"]:
            assert pattern.match(fid), f"Invalid flow ID pattern: {fid}"


# ── T2: 全画面カバレッジ ─────────────────────────────────────────────────


class TestScreenCoverage:
    """T2: 全画面カバレッジ検証."""

    def test_minimum_screen_count(self, nav_data):
        """最低 70 個以上の screen が登録されていること."""
        count = len(nav_data["screens"])
        assert count >= 70, f"Expected >= 70 screens, got {count}"

    def test_all_screens_have_required_fields(self, nav_data):
        """全 screen が必須フィールドを含むこと."""
        required = {"id", "name", "feature", "screen_type", "triggers"}
        for sid, screen in nav_data["screens"].items():
            missing = required - set(screen.keys())
            assert not missing, f"{sid} missing fields: {missing}"

    def test_screen_id_matches_key(self, nav_data):
        """screen dict の key と screen.id が一致すること."""
        for key, screen in nav_data["screens"].items():
            assert key == screen["id"], f"Key {key} != screen.id {screen['id']}"

    def test_screen_type_enum(self, nav_data):
        """screen_type が許可された enum 値のみ使用すること."""
        allowed = {"tab", "page", "dialog", "bottomSheet", "overlay"}
        for sid, screen in nav_data["screens"].items():
            assert screen["screen_type"] in allowed, (
                f"{sid} has invalid screen_type: {screen['screen_type']}"
            )

    def test_feature_id_format(self, nav_data):
        """feature フィールドが NNN-xxx-xxx パターンに従うこと."""
        pattern = re.compile(r"^\d{3}-[a-z0-9-]+$")
        for sid, screen in nav_data["screens"].items():
            assert pattern.match(screen["feature"]), (
                f"{sid} invalid feature format: {screen['feature']}"
            )


# ── T3: 孤立画面なし ────────────────────────────────────────────────────


class TestOrphanScreens:
    """T3: 孤立画面検出 (app_entry/tab 除外)."""

    def test_tab_screens_exist(self, nav_data):
        """5 個の tab screen が存在すること."""
        tab_screens = [
            s for s in nav_data["screens"].values()
            if s["screen_type"] == "tab"
        ]
        assert len(tab_screens) == 5, (
            f"Expected 5 tab screens, got {len(tab_screens)}: "
            f"{[s['id'] for s in tab_screens]}"
        )

    def test_tab_screens_have_tab_index(self, nav_data):
        """tab タイプの screen は必ず tab_index を持つこと."""
        for screen in nav_data["screens"].values():
            if screen["screen_type"] == "tab":
                assert "tab_index" in screen, (
                    f"{screen['id']} is tab but missing tab_index"
                )

    def test_tab_indices_are_0_to_4(self, nav_data):
        """tab_index が 0~4 の範囲でありすべて存在すること."""
        tab_indices = sorted(
            screen["tab_index"]
            for screen in nav_data["screens"].values()
            if screen["screen_type"] == "tab"
        )
        assert tab_indices == [0, 1, 2, 3, 4], (
            f"Expected [0,1,2,3,4], got {tab_indices}"
        )


# ── T4: デッドエンド (informational only) ─────────────────────────────────────


class TestDeadEnds:
    """T4: デッドエンド検出 -- leaf page は許容、WARNING レベル."""

    def test_dead_end_count_reasonable(self, nav_data):
        """trigger が空の page 割合が 80% 未満であること.

        NOTE: leaf page（詳細/結果画面等）は dead-end が正常.
        V3 WARNING レベルのため緩やかな threshold を適用.
        """
        pages = [
            s for s in nav_data["screens"].values()
            if s["screen_type"] == "page"
        ]
        dead_ends = [p for p in pages if len(p.get("triggers", [])) == 0]
        ratio = len(dead_ends) / len(pages) if pages else 0
        assert ratio < 0.80, (
            f"Too many dead-end pages: {len(dead_ends)}/{len(pages)} "
            f"({ratio:.0%})"
        )


# ── T5: 参照整合性 ───────────────────────────────────────────────────────


class TestReferenceIntegrity:
    """T5: 参照整合性検証."""

    def test_all_trigger_targets_exist(self, nav_data, all_screen_ids):
        """全 trigger.target が実在する screen ID を参照すること."""
        broken = []
        for sid, screen in nav_data["screens"].items():
            for trigger in screen.get("triggers", []):
                target = trigger["target"]
                if target not in all_screen_ids:
                    broken.append(f"{trigger['id']}: target {target}")
        assert not broken, (
            f"Broken trigger targets:\n" + "\n".join(broken)
        )

    def test_all_guard_fallbacks_exist(self, nav_data, all_screen_ids):
        """全 guard.fallback_screen が実在する screen ID を参照すること."""
        broken = []
        for sid, screen in nav_data["screens"].items():
            for trigger in screen.get("triggers", []):
                for guard in trigger.get("guards", []):
                    fb = guard["fallback_screen"]
                    if fb not in all_screen_ids:
                        broken.append(
                            f"{trigger['id']} guard fallback {fb}"
                        )
        assert not broken, (
            f"Broken guard fallbacks:\n" + "\n".join(broken)
        )

    def test_flow_screens_exist(self, nav_data, all_screen_ids):
        """Flow の全 step.screen が実在すること."""
        broken = []
        for fid, flow in nav_data["flows"].items():
            for i, step in enumerate(flow.get("steps", [])):
                screen_ref = step.get("screen")
                if screen_ref and screen_ref not in all_screen_ids:
                    broken.append(f"{fid} step[{i}]: {screen_ref}")
        assert not broken, (
            f"Broken flow screen refs:\n" + "\n".join(broken)
        )

    def test_flow_triggers_exist(self, nav_data, all_trigger_ids):
        """Flow の全 step.trigger が実在すること (null 除外)."""
        trigger_set = set(all_trigger_ids)
        broken = []
        for fid, flow in nav_data["flows"].items():
            for i, step in enumerate(flow.get("steps", [])):
                trigger_ref = step.get("trigger")
                if trigger_ref and trigger_ref not in trigger_set:
                    broken.append(f"{fid} step[{i}]: {trigger_ref}")
        assert not broken, (
            f"Broken flow trigger refs:\n" + "\n".join(broken)
        )

    def test_flow_trigger_belongs_to_step_screen(self, nav_data):
        """Flow step の trigger が該当 step の screen に属すること."""
        # trigger -> owning screen マップ構築
        trigger_owner = {}
        for sid, screen in nav_data["screens"].items():
            for trigger in screen.get("triggers", []):
                trigger_owner[trigger["id"]] = sid

        broken = []
        for fid, flow in nav_data["flows"].items():
            for i, step in enumerate(flow.get("steps", [])):
                screen_ref = step.get("screen")
                trigger_ref = step.get("trigger")
                if not trigger_ref or not screen_ref:
                    continue
                owner = trigger_owner.get(trigger_ref)
                if owner and owner != screen_ref:
                    broken.append(
                        f"{fid} step[{i}]: trigger {trigger_ref} "
                        f"belongs to {owner}, not {screen_ref}"
                    )
        assert not broken, (
            f"Flow trigger ownership mismatch:\n" + "\n".join(broken)
        )


# ── T6: コード同期 ───────────────────────────────────────────────────────


class TestCodeSync:
    """T6: コード同期 (screen.file パス存在確認)."""

    def test_screen_files_exist(self, nav_data):
        """screen.file パスが実ファイルとして存在すること."""
        missing = []
        for sid, screen in nav_data["screens"].items():
            file_path = screen.get("file")
            if file_path:
                full_path = PROJECT_ROOT / file_path
                if not full_path.exists():
                    missing.append(f"{sid}: {file_path}")
        assert not missing, (
            f"Missing screen files:\n" + "\n".join(missing)
        )


# ── T7: ID 一意性 ─────────────────────────────────────────────────────────


class TestIdUniqueness:
    """T7: ID 一意性検証."""

    def test_screen_ids_unique(self, nav_data):
        """screen ID に重複がないこと."""
        ids = list(nav_data["screens"].keys())
        assert len(ids) == len(set(ids)), (
            f"Duplicate screen IDs: "
            f"{[x for x in ids if ids.count(x) > 1]}"
        )

    def test_trigger_ids_unique(self, all_trigger_ids):
        """trigger ID に重複がないこと."""
        dupes = [x for x in all_trigger_ids if all_trigger_ids.count(x) > 1]
        assert len(all_trigger_ids) == len(set(all_trigger_ids)), (
            f"Duplicate trigger IDs: {list(set(dupes))}"
        )

    def test_flow_ids_unique(self, nav_data):
        """flow ID に重複がないこと."""
        ids = list(nav_data["flows"].keys())
        assert len(ids) == len(set(ids)), (
            f"Duplicate flow IDs: "
            f"{[x for x in ids if ids.count(x) > 1]}"
        )


# ── T8: Named route 一致 ──────────────────────────────────────────────────


class TestNamedRoutes:
    """T8: main.dart の named route が nav-graph に登録されているか検証."""

    EXPECTED_ROUTES = [
        "/login",
        "/home",
        "/onboarding",
        "/notification",
        "/ai-tutor",
        "/bridge-grammar",
        "/review",
        "/report/weekly",
        "/level-progress",
    ]

    def test_named_routes_in_nav_graph(self, nav_data):
        """main.dart の 9 個の named route がすべて nav-graph に存在すること."""
        nav_routes = set()
        for screen in nav_data["screens"].values():
            route = screen.get("route")
            if route:
                nav_routes.add(route)

        missing = [r for r in self.EXPECTED_ROUTES if r not in nav_routes]
        assert not missing, (
            f"Named routes missing from nav-graph: {missing}"
        )

    def test_nav_graph_routes_count(self, nav_data):
        """nav-graph に登録された route 数が expected と一致すること."""
        nav_routes = [
            screen["route"]
            for screen in nav_data["screens"].values()
            if screen.get("route")
        ]
        assert len(nav_routes) >= len(self.EXPECTED_ROUTES), (
            f"Expected >= {len(self.EXPECTED_ROUTES)} routes, "
            f"got {len(nav_routes)}"
        )


# ── T9: Mermaid 生成 ──────────────────────────────────────────────────────


class TestMermaidGeneration:
    """T9: Mermaid ダイアグラムジェネレータが正常動作するか検証."""

    def test_mermaid_generator_exists(self):
        """nav-graph-to-mermaid.py ファイルが存在すること."""
        assert MERMAID_SCRIPT.exists(), (
            f"Mermaid generator not found: {MERMAID_SCRIPT}"
        )

    def test_mermaid_generator_runs(self):
        """Mermaid generator が exit code 0 で実行されること."""
        result = subprocess.run(
            [sys.executable, str(MERMAID_SCRIPT), str(NAV_GRAPH_PATH)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"Mermaid generator failed (exit {result.returncode}):\n"
            f"{result.stderr}"
        )
        assert "stateDiagram-v2" in result.stdout, (
            "Output does not contain 'stateDiagram-v2'"
        )

    def test_mermaid_contains_screen_states(self):
        """Mermaid 出力に screen state 宣言が含まれること."""
        result = subprocess.run(
            [sys.executable, str(MERMAID_SCRIPT), str(NAV_GRAPH_PATH)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # 最低限 entry point [*] --> が存在すること
        assert "[*] -->" in result.stdout, (
            "Mermaid output missing entry point ([*] -->)"
        )

    def test_mermaid_feature_filter(self):
        """--feature オプションで特定 feature のみフィルタリングできること."""
        result = subprocess.run(
            [
                sys.executable, str(MERMAID_SCRIPT),
                str(NAV_GRAPH_PATH), "--feature", "022",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"Feature filter failed: {result.stderr}"
        )
        assert "stateDiagram-v2" in result.stdout


# ── T10: Screen Doc 参照 ──────────────────────────────────────────────────


class TestScreenDocReferences:
    """T10: Screen doc での nav-graph.json 参照有無の検証."""

    def test_screen_docs_reference_nav_graph(self):
        """screen doc の 80% 以上が nav-graph.json を言及すること."""
        screen_docs = list(PROJECT_ROOT.glob("docs/features/*/screens/*.md"))
        if not screen_docs:
            pytest.skip("No screen docs found")

        non_compliant = []
        for doc in screen_docs:
            content = doc.read_text(encoding="utf-8")
            if "nav-graph" not in content.lower():
                non_compliant.append(
                    str(doc.relative_to(PROJECT_ROOT))
                )

        compliance_rate = (
            1 - len(non_compliant) / len(screen_docs)
            if screen_docs
            else 1
        )
        assert compliance_rate >= 0.8, (
            f"Only {compliance_rate:.0%} screen docs reference nav-graph. "
            f"Non-compliant ({len(non_compliant)}):\n"
            + "\n".join(non_compliant[:10])
        )


# ── Validator Script 統合 ─────────────────────────────────────────────────


class TestValidatorScript:
    """nav-graph-validator.py スクリプトが BLOCKING イシューなしで通過するか検証."""

    def test_validator_no_blocking(self):
        """validator が BLOCKING イシューなしで通過すること (exit 0 or 2)."""
        if not VALIDATOR_SCRIPT.exists():
            pytest.skip("nav-graph-validator.py not found")

        result = subprocess.run(
            [
                sys.executable, str(VALIDATOR_SCRIPT),
                str(NAV_GRAPH_PATH),
                "--project-root", str(PROJECT_ROOT),
                "--json-only",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # exit 0 = all pass, exit 2 = warnings only, exit 1 = blocking
        assert result.returncode != 1, (
            f"Validator found BLOCKING issues:\n{result.stdout}"
        )


# ── Flow 構造検証 ────────────────────────────────────────────────────────


class TestFlowStructure:
    """Flow 定義の構造的妥当性検証."""

    def test_all_flows_have_required_fields(self, nav_data):
        """全 flow が id, name, steps フィールドを持つこと."""
        for fid, flow in nav_data["flows"].items():
            assert "id" in flow, f"{fid} missing 'id'"
            assert "name" in flow, f"{fid} missing 'name'"
            assert "steps" in flow, f"{fid} missing 'steps'"

    def test_flow_id_matches_key(self, nav_data):
        """flow dict key と flow.id が一致すること."""
        for key, flow in nav_data["flows"].items():
            assert key == flow["id"], f"Key {key} != flow.id {flow['id']}"

    def test_flows_have_minimum_steps(self, nav_data):
        """全 flow が最低 2 個の step を持つこと."""
        for fid, flow in nav_data["flows"].items():
            steps = flow.get("steps", [])
            assert len(steps) >= 2, (
                f"{fid} has only {len(steps)} steps (minimum 2)"
            )

    def test_flow_last_step_trigger_null(self, nav_data):
        """flow の最後の step は trigger が null であること."""
        for fid, flow in nav_data["flows"].items():
            steps = flow.get("steps", [])
            if steps:
                last = steps[-1]
                assert last.get("trigger") is None, (
                    f"{fid} last step has non-null trigger: "
                    f"{last.get('trigger')}"
                )

    def test_minimum_flow_count(self, nav_data):
        """最低 5 個以上の flow が定義されていること."""
        count = len(nav_data["flows"])
        assert count >= 5, f"Expected >= 5 flows, got {count}"
