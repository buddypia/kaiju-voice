#!/usr/bin/env python3
"""
NAV-GRAPH Validator v1.0

ナビゲーショングラフ(nav-graph.json)の構造的整合性を検証します。

Usage:
    python nav-graph-validator.py [path-to-nav-graph.json]
    python nav-graph-validator.py --project-root /path/to/project
    python nav-graph-validator.py --json-only

Validation Rules:
    V1: JSON Schema compliance (BLOCKING)
    V2: Orphan screen detection (WARNING)
    V3: Dead-end detection (WARNING)
    V4: Reference integrity (BLOCKING)
    V5: Duplicate IDs (BLOCKING)
    V6: Code file existence (WARNING)
    V7: Guard consistency (WARNING)
    V8: Flow path validity (BLOCKING)

Exit codes:
    0: All pass (no BLOCKING, no WARNING)
    1: Has BLOCKING issues
    2: WARNING only (no BLOCKING)
"""

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# jsonschemaはオプション依存
try:
    import jsonschema

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


@dataclass
class Issue:
    """検証イシュー"""

    rule: str  # V1-V8
    severity: str  # BLOCKING | WARNING
    message: str


@dataclass
class ValidationStats:
    """検証統計"""

    screen_count: int = 0
    trigger_count: int = 0
    flow_count: int = 0


@dataclass
class ValidationResult:
    """検証結果"""

    issues: list = field(default_factory=list)
    stats: ValidationStats = field(default_factory=ValidationStats)

    @property
    def blocking_issues(self) -> list:
        return [i for i in self.issues if i.severity == "BLOCKING"]

    @property
    def warning_issues(self) -> list:
        return [i for i in self.issues if i.severity == "WARNING"]

    @property
    def has_blocking(self) -> bool:
        return len(self.blocking_issues) > 0

    @property
    def has_warning(self) -> bool:
        return len(self.warning_issues) > 0


def detect_project_root(start_path: Path) -> Optional[Path]:
    """package.jsonを基準にプロジェクトルートを探索"""
    current = start_path.resolve()
    while current != current.parent:
        if (current / "package.json").exists():
            return current
        current = current.parent
    return None


class NavGraphValidator:
    """NAV-GRAPH検証器"""

    def __init__(self, nav_graph_path: Path, project_root: Path, schema_path: Optional[Path] = None):
        self.nav_graph_path = nav_graph_path
        self.project_root = project_root
        self.schema_path = schema_path or (project_root / "docs" / "navigation" / "nav-graph.schema.json")
        self.data: dict = {}
        self.result = ValidationResult()

        # パース済みデータのキャッシュ
        self._screen_ids: set = set()
        self._trigger_ids: set = set()
        self._flow_ids: set = set()
        self._trigger_map: dict = {}  # trigger_id -> screen_id (所属画面)

    def load(self) -> bool:
        """nav-graph.jsonをロード"""
        try:
            text = self.nav_graph_path.read_text(encoding="utf-8")
            self.data = json.loads(text)
            return True
        except json.JSONDecodeError as e:
            self.result.issues.append(
                Issue("V1", "BLOCKING", f"JSONパースエラー: {e}")
            )
            return False
        except FileNotFoundError:
            self.result.issues.append(
                Issue("V1", "BLOCKING", f"ファイルが見つかりません: {self.nav_graph_path}")
            )
            return False

    def _index_data(self):
        """スクリーン、トリガー、フローIDのインデクシング"""
        screens = self.data.get("screens", {})
        flows = self.data.get("flows", {})

        for screen_key, screen in screens.items():
            sid = screen.get("id", screen_key)
            self._screen_ids.add(sid)
            for trigger in screen.get("triggers", []):
                tid = trigger.get("id")
                if tid:
                    self._trigger_ids.add(tid)
                    self._trigger_map[tid] = sid

        for flow_key, flow_data in flows.items():
            fid = flow_data.get("id", flow_key)
            self._flow_ids.add(fid)

        self.result.stats = ValidationStats(
            screen_count=len(self._screen_ids),
            trigger_count=len(self._trigger_ids),
            flow_count=len(self._flow_ids),
        )

    def validate_v1_schema(self):
        """V1: JSON Schema compliance (BLOCKING)"""
        if not HAS_JSONSCHEMA:
            self.result.issues.append(
                Issue("V1", "WARNING", "jsonschema未インストール - V1スキーマ検証スキップ (pip install jsonschema)")
            )
            return

        if not self.schema_path.exists():
            self.result.issues.append(
                Issue("V1", "WARNING", f"スキーマファイルが見つかりません: {self.schema_path}")
            )
            return

        try:
            schema_text = self.schema_path.read_text(encoding="utf-8")
            schema = json.loads(schema_text)
            jsonschema.validate(instance=self.data, schema=schema)
        except jsonschema.ValidationError as e:
            # 最も有用な情報のみ抽出
            path = " -> ".join(str(p) for p in e.absolute_path) if e.absolute_path else "(root)"
            self.result.issues.append(
                Issue("V1", "BLOCKING", f"スキーマ違反 at {path}: {e.message}")
            )
        except jsonschema.SchemaError as e:
            self.result.issues.append(
                Issue("V1", "WARNING", f"スキーマファイル自体のエラー: {e.message}")
            )
        except json.JSONDecodeError as e:
            self.result.issues.append(
                Issue("V1", "WARNING", f"スキーマファイルのJSONパースエラー: {e}")
            )

    def validate_v2_orphan_screens(self):
        """V2: Orphan screen detection (WARNING)

        incoming triggerがないスクリーンを検出します。
        例外: tabタイプのスクリーン、フローの最初のstepスクリーン
        """
        screens = self.data.get("screens", {})
        flows = self.data.get("flows", {})

        # すべてのtriggerのtargetから逆方向マップを構築
        targeted_screens: set = set()
        for screen in screens.values():
            for trigger in screen.get("triggers", []):
                target = trigger.get("target")
                if target:
                    targeted_screens.add(target)

        # フローの最初のstepスクリーンを収集
        flow_entry_screens: set = set()
        for flow_data in flows.values():
            steps = flow_data.get("steps", [])
            if steps:
                first_screen = steps[0].get("screen")
                if first_screen:
                    flow_entry_screens.add(first_screen)

        # Orphan検出
        for screen_key, screen in screens.items():
            sid = screen.get("id", screen_key)

            # 例外1: tabタイプ
            if screen.get("screen_type") == "tab":
                continue

            # 例外2: フローエントリーポイント
            if sid in flow_entry_screens:
                continue

            # incoming triggerがなければorphan
            if sid not in targeted_screens:
                name = screen.get("name", "?")
                self.result.issues.append(
                    Issue("V2", "WARNING", f"orphan screen: {sid} ({name}) - incoming triggerなし")
                )

    def validate_v3_dead_ends(self):
        """V3: Dead-end detection (WARNING)

        triggers配列が空のスクリーンを検出します。
        例外: dialog, bottomSheet, overlayタイプ（ターミナル画面）
        """
        screens = self.data.get("screens", {})
        terminal_types = {"dialog", "bottomSheet", "overlay"}

        for screen_key, screen in screens.items():
            sid = screen.get("id", screen_key)
            triggers = screen.get("triggers", [])
            screen_type = screen.get("screen_type", "page")

            if screen_type in terminal_types:
                continue

            if len(triggers) == 0:
                name = screen.get("name", "?")
                self.result.issues.append(
                    Issue("V3", "WARNING", f"dead-end screen: {sid} ({name}) - triggersが空")
                )

    def validate_v4_reference_integrity(self):
        """V4: Reference integrity (BLOCKING)

        すべてのtrigger.targetが実際に存在するscreen IDを参照しているか検証します。
        """
        screens = self.data.get("screens", {})

        for screen_key, screen in screens.items():
            sid = screen.get("id", screen_key)
            for trigger in screen.get("triggers", []):
                tid = trigger.get("id", "?")
                target = trigger.get("target")
                if target and target not in self._screen_ids:
                    self.result.issues.append(
                        Issue(
                            "V4",
                            "BLOCKING",
                            f"trigger {tid} (in {sid}) targets non-existent screen {target}",
                        )
                    )

    def validate_v5_duplicate_ids(self):
        """V5: Duplicate IDs (BLOCKING)

        screen, trigger, flow IDの重複を検出します。
        """
        screens = self.data.get("screens", {})
        flows = self.data.get("flows", {})

        # Screen ID重複チェック
        seen_screen_ids: dict = {}
        for screen_key, screen in screens.items():
            sid = screen.get("id", screen_key)
            if sid in seen_screen_ids:
                self.result.issues.append(
                    Issue("V5", "BLOCKING", f"duplicate screen ID: {sid} (keys: {seen_screen_ids[sid]}, {screen_key})")
                )
            else:
                seen_screen_ids[sid] = screen_key

        # Trigger ID重複チェック
        seen_trigger_ids: dict = {}
        for screen_key, screen in screens.items():
            sid = screen.get("id", screen_key)
            for trigger in screen.get("triggers", []):
                tid = trigger.get("id")
                if not tid:
                    continue
                if tid in seen_trigger_ids:
                    self.result.issues.append(
                        Issue(
                            "V5",
                            "BLOCKING",
                            f"duplicate trigger ID: {tid} (in {seen_trigger_ids[tid]} and {sid})",
                        )
                    )
                else:
                    seen_trigger_ids[tid] = sid

        # Flow ID重複チェック
        seen_flow_ids: dict = {}
        for flow_key, flow_data in flows.items():
            fid = flow_data.get("id", flow_key)
            if fid in seen_flow_ids:
                self.result.issues.append(
                    Issue("V5", "BLOCKING", f"duplicate flow ID: {fid} (keys: {seen_flow_ids[fid]}, {flow_key})")
                )
            else:
                seen_flow_ids[fid] = flow_key

    def validate_v6_code_files(self):
        """V6: Code file existence (WARNING)

        screen.fileパスが実際にディスク上に存在するか確認します。
        """
        screens = self.data.get("screens", {})

        for screen_key, screen in screens.items():
            sid = screen.get("id", screen_key)
            file_path = screen.get("file")
            if not file_path:
                continue

            full_path = self.project_root / file_path
            if not full_path.exists():
                self.result.issues.append(
                    Issue("V6", "WARNING", f"screen {sid}: file not found - {file_path}")
                )

    def validate_v7_guard_consistency(self):
        """V7: Guard consistency (WARNING)

        guard.fallback_screenが実際に存在するscreen IDを参照しているか確認します。
        """
        screens = self.data.get("screens", {})

        for screen_key, screen in screens.items():
            sid = screen.get("id", screen_key)
            for trigger in screen.get("triggers", []):
                tid = trigger.get("id", "?")
                for guard in trigger.get("guards", []):
                    fallback = guard.get("fallback_screen")
                    if fallback and fallback not in self._screen_ids:
                        condition = guard.get("condition", "?")
                        self.result.issues.append(
                            Issue(
                                "V7",
                                "WARNING",
                                f"guard on {tid} (in {sid}): fallback_screen {fallback} not found "
                                f"(condition: {condition})",
                            )
                        )

    def validate_v8_flow_paths(self):
        """V8: Flow path validity (BLOCKING)

        フローのすべてのstep.screenおよびstep.triggerが実際に存在するか検証します。
        """
        flows = self.data.get("flows", {})

        for flow_key, flow_data in flows.items():
            fid = flow_data.get("id", flow_key)
            steps = flow_data.get("steps", [])

            for i, step in enumerate(steps):
                screen_ref = step.get("screen")
                trigger_ref = step.get("trigger")

                # step.screenが存在するか確認
                if screen_ref and screen_ref not in self._screen_ids:
                    self.result.issues.append(
                        Issue(
                            "V8",
                            "BLOCKING",
                            f"flow {fid} step[{i}]: screen {screen_ref} not found",
                        )
                    )

                # step.triggerが存在するか確認（最後のstepはnull許容）
                if trigger_ref and trigger_ref not in self._trigger_ids:
                    self.result.issues.append(
                        Issue(
                            "V8",
                            "BLOCKING",
                            f"flow {fid} step[{i}]: trigger {trigger_ref} not found",
                        )
                    )

                # step.triggerがstep.screenに属しているか確認（存在する場合）
                if (
                    trigger_ref
                    and trigger_ref in self._trigger_ids
                    and screen_ref
                    and screen_ref in self._screen_ids
                ):
                    owning_screen = self._trigger_map.get(trigger_ref)
                    if owning_screen and owning_screen != screen_ref:
                        self.result.issues.append(
                            Issue(
                                "V8",
                                "BLOCKING",
                                f"flow {fid} step[{i}]: trigger {trigger_ref} belongs to "
                                f"{owning_screen}, not {screen_ref}",
                            )
                        )

    def validate(self) -> ValidationResult:
        """全体検証を実行"""
        if not self.load():
            return self.result

        self._index_data()

        # V1-V8を順番に実行
        self.validate_v1_schema()
        self.validate_v2_orphan_screens()
        self.validate_v3_dead_ends()
        self.validate_v4_reference_integrity()
        self.validate_v5_duplicate_ids()
        self.validate_v6_code_files()
        self.validate_v7_guard_consistency()
        self.validate_v8_flow_paths()

        return self.result


def format_text(result: ValidationResult, nav_graph_path: Path) -> str:
    """人間が読みやすいテキスト出力"""
    lines = []
    stats = result.stats

    lines.append("")
    lines.append(f"{'=' * 60}")
    lines.append(f"NAV-GRAPH Validation Results: {nav_graph_path.name}")
    lines.append(f"{'=' * 60}")
    lines.append(f"Stats: {stats.screen_count} screens, {stats.trigger_count} triggers, {stats.flow_count} flows")

    # BLOCKING
    blocking = result.blocking_issues
    if blocking:
        lines.append(f"\nBLOCKING ({len(blocking)})")
        for issue in blocking:
            lines.append(f"  - [{issue.rule}] {issue.message}")

    # WARNING
    warnings = result.warning_issues
    if warnings:
        lines.append(f"\nWARNING ({len(warnings)})")
        for issue in warnings:
            lines.append(f"  - [{issue.rule}] {issue.message}")

    # Final
    lines.append(f"\n{'=' * 60}")
    if result.has_blocking:
        lines.append("Final: FAIL (BLOCKING issues found)")
    elif result.has_warning:
        lines.append("Final: PASS with warnings")
    else:
        lines.append("Final: PASS")
    lines.append(f"{'=' * 60}")
    lines.append("")

    return "\n".join(lines)


def format_json(result: ValidationResult) -> str:
    """JSON出力 (machine-readable)"""
    output = {
        "stats": {
            "screens": result.stats.screen_count,
            "triggers": result.stats.trigger_count,
            "flows": result.stats.flow_count,
        },
        "blocking": [
            {"rule": i.rule, "message": i.message}
            for i in result.blocking_issues
        ],
        "warnings": [
            {"rule": i.rule, "message": i.message}
            for i in result.warning_issues
        ],
        "pass": not result.has_blocking,
        "exit_code": 1 if result.has_blocking else (2 if result.has_warning else 0),
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="NAV-GRAPH Validator - ナビゲーショングラフ構造検証"
    )
    parser.add_argument(
        "nav_graph",
        nargs="?",
        default=None,
        help="nav-graph.jsonパス（デフォルト: docs/navigation/nav-graph.json）",
    )
    parser.add_argument(
        "--project-root",
        default=None,
        help="プロジェクトルートパス（デフォルト: package.json自動探索）",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="JSON形式のみで出力",
    )
    args = parser.parse_args()

    # プロジェクトルートを決定
    if args.project_root:
        project_root = Path(args.project_root).resolve()
    else:
        # スクリプト位置から上位を探索
        script_dir = Path(__file__).resolve().parent
        project_root = detect_project_root(script_dir)
        if not project_root:
            print("Error: package.jsonが見つかりません。--project-rootを指定してください。", file=sys.stderr)
            sys.exit(1)

    # nav-graph.jsonパスを決定
    if args.nav_graph:
        nav_graph_path = Path(args.nav_graph)
        if not nav_graph_path.is_absolute():
            nav_graph_path = Path.cwd() / nav_graph_path
    else:
        nav_graph_path = project_root / "docs" / "navigation" / "nav-graph.json"

    # 検証を実行
    validator = NavGraphValidator(nav_graph_path, project_root)
    result = validator.validate()

    # 出力
    if args.json_only:
        print(format_json(result))
    else:
        print(format_text(result, nav_graph_path))

    # Exit code
    if result.has_blocking:
        sys.exit(1)
    elif result.has_warning:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
