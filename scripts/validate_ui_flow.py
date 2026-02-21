#!/usr/bin/env python3
"""
UI Flow Graph Validator — ui-flow.json の構造・整合性を検証するスクリプト

12項目検証、3段階深刻度:
  MVS (exit 1)  — コミット不可
  Tier (exit 2) — 警告（推奨修正）
  Warning (exit 0) — 情報提供のみ

使用法:
    python3 scripts/validate_ui_flow.py docs/ui-flow/ui-flow.json
    python3 scripts/validate_ui_flow.py docs/ui-flow/ui-flow.json --json
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from jsonschema import Draft202012Validator
except ImportError:
    print("❌ jsonschema パッケージが必要です: pip install jsonschema")
    sys.exit(1)

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = PROJECT_ROOT / "docs" / "ui-flow" / "ui-flow.schema.json"
FEATURES_DIR = PROJECT_ROOT / "src" / "features"
PAGE_TSX = PROJECT_ROOT / "src" / "app" / "page.tsx"

# 期待値定数
EXPECTED_STATES = {"idle", "analyzing", "explaining", "diffReady", "quizzing", "complete"}
EXPECTED_PANELS = {
    "CodeInputPanel", "AgentLogPanel", "AnalysisProgress",
    "ExplanationPanel", "ProgressiveHintsPanel", "DiffViewPanel",
    "QuizPanel", "CodeSandboxPanel", "CompletionCard",
    "FollowUpChatPanel", "LearningHistoryPanel", "ErrorBanner",
}
EXPECTED_PHASES = {"idle", "analyzing", "explaining", "diffReady", "quizzing", "complete"}
EXPECTED_SSE_EVENTS = {
    "agent-log", "explanation", "error-category", "hints",
    "diff", "quiz", "complete", "error",
}


@dataclass
class CheckResult:
    """個別検証結果"""
    id: str
    name: str
    severity: str  # "MVS" | "Tier" | "Warning"
    passed: bool
    details: list = field(default_factory=list)


@dataclass
class ValidationReport:
    """検証レポート全体"""
    file_path: str
    results: list = field(default_factory=list)
    mvs_failures: int = 0
    tier_failures: int = 0
    warnings: int = 0

    @property
    def exit_code(self) -> int:
        if self.mvs_failures > 0:
            return 1
        if self.tier_failures > 0:
            return 2
        return 0


def load_json(path: Path) -> Optional[dict]:
    """JSONファイルの読み込み"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return None


def v1_schema_validation(data: dict, schema: dict) -> CheckResult:
    """V1: JSON Schema構造検証"""
    result = CheckResult(id="V1", name="JSON Schema構造検証", severity="MVS", passed=True)
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(data))
    if errors:
        result.passed = False
        for e in errors:
            path = " > ".join(str(p) for p in e.absolute_path) or "(root)"
            result.details.append(f"[{path}] {e.message}")
    return result


def v2_statechart_completeness(data: dict) -> CheckResult:
    """V2: statechart完全性（6状態存在）"""
    result = CheckResult(id="V2", name="statechart完全性", severity="MVS", passed=True)
    states = set(data.get("statechart", {}).get("states", {}).keys())
    missing = EXPECTED_STATES - states
    extra = states - EXPECTED_STATES
    if missing:
        result.passed = False
        result.details.append(f"不足状態: {', '.join(sorted(missing))}")
    if extra:
        result.details.append(f"追加状態（想定外）: {', '.join(sorted(extra))}")
    return result


def v3_panels_completeness(data: dict) -> CheckResult:
    """V3: panels完全性（12パネル存在）"""
    result = CheckResult(id="V3", name="panels完全性", severity="MVS", passed=True)
    panels = set(data.get("panels", {}).keys())
    missing = EXPECTED_PANELS - panels
    extra = panels - EXPECTED_PANELS
    if missing:
        result.passed = False
        result.details.append(f"不足パネル: {', '.join(sorted(missing))}")
    if extra:
        result.details.append(f"追加パネル（想定外）: {', '.join(sorted(extra))}")
    return result


def v4_phases_completeness(data: dict) -> CheckResult:
    """V4: phases完全性（6フェーズ存在）"""
    result = CheckResult(id="V4", name="phases完全性", severity="MVS", passed=True)
    phases = set(data.get("phases", {}).keys())
    missing = EXPECTED_PHASES - phases
    extra = phases - EXPECTED_PHASES
    if missing:
        result.passed = False
        result.details.append(f"不足フェーズ: {', '.join(sorted(missing))}")
    if extra:
        result.details.append(f"追加フェーズ（想定外）: {', '.join(sorted(extra))}")
    return result


def v5_sse_mapping_completeness(data: dict) -> CheckResult:
    """V5: sse_mapping完全性（8イベント存在）"""
    result = CheckResult(id="V5", name="sse_mapping完全性", severity="MVS", passed=True)
    events = set(data.get("sse_mapping", {}).keys())
    missing = EXPECTED_SSE_EVENTS - events
    extra = events - EXPECTED_SSE_EVENTS
    if missing:
        result.passed = False
        result.details.append(f"不足SSEイベント: {', '.join(sorted(missing))}")
    if extra:
        result.details.append(f"追加SSEイベント（想定外）: {', '.join(sorted(extra))}")
    return result


def v6_sse_panel_ref_integrity(data: dict) -> CheckResult:
    """V6: SSE→パネル参照整合性"""
    result = CheckResult(id="V6", name="SSE→パネル参照整合性", severity="MVS", passed=True)
    panels = set(data.get("panels", {}).keys())
    for event_name, mapping in data.get("sse_mapping", {}).items():
        target = mapping.get("target_panel", "")
        if target not in panels:
            result.passed = False
            result.details.append(f"SSE '{event_name}' → パネル '{target}' が panels に未定義")
    return result


def v7_phase_panel_ref_integrity(data: dict) -> CheckResult:
    """V7: phase→パネル参照整合性"""
    result = CheckResult(id="V7", name="phase→パネル参照整合性", severity="MVS", passed=True)
    panels = set(data.get("panels", {}).keys())
    for phase_name, phase in data.get("phases", {}).items():
        for panel_id in phase.get("active_panels", []):
            if panel_id not in panels:
                result.passed = False
                result.details.append(f"phase '{phase_name}' → パネル '{panel_id}' が panels に未定義")
    return result


def v8_panel_feature_dir_exists(data: dict) -> CheckResult:
    """V8: パネル→featureディレクトリ存在"""
    result = CheckResult(id="V8", name="パネル→featureディレクトリ存在", severity="MVS", passed=True)
    for panel_name, panel in data.get("panels", {}).items():
        feature = panel.get("feature", "")
        if feature == "shared":
            # shared は src/shared/ にあるのでスキップ
            continue
        feature_dir = FEATURES_DIR / feature
        if not feature_dir.exists():
            result.passed = False
            result.details.append(f"パネル '{panel_name}' → feature '{feature}' ディレクトリ未存在: {feature_dir}")
    return result


def v9_transition_coverage(data: dict) -> CheckResult:
    """V9: 遷移完全性（全状態遷移カバー）"""
    result = CheckResult(id="V9", name="遷移完全性", severity="Tier", passed=True)

    # statechart の on から全遷移を収集
    statechart_transitions = set()
    for state_name, state in data.get("statechart", {}).get("states", {}).items():
        for event_name, transition in state.get("on", {}).items():
            target = transition.get("target", "")
            statechart_transitions.add((state_name, event_name, target))

    # transitions 配列から全遷移を収集
    declared_transitions = set()
    for t in data.get("transitions", []):
        declared_transitions.add((t.get("from", ""), t.get("event", ""), t.get("to", "")))

    # statechart にあるが transitions に無い
    missing_in_transitions = statechart_transitions - declared_transitions
    if missing_in_transitions:
        result.passed = False
        for frm, evt, to in sorted(missing_in_transitions):
            result.details.append(f"statechart の遷移 {frm} --{evt}--> {to} が transitions に未宣言")

    # transitions にあるが statechart に無い
    extra_in_transitions = declared_transitions - statechart_transitions
    if extra_in_transitions:
        result.passed = False
        for frm, evt, to in sorted(extra_in_transitions):
            result.details.append(f"transitions の遷移 {frm} --{evt}--> {to} が statechart に未定義")

    return result


def v10_xstate_compatibility(data: dict) -> CheckResult:
    """V10: statechart XState互換性"""
    result = CheckResult(id="V10", name="XState互換性", severity="Tier", passed=True)
    statechart = data.get("statechart", {})

    # initial が states に存在するか
    initial = statechart.get("initial", "")
    states = statechart.get("states", {})
    if initial and initial not in states:
        result.passed = False
        result.details.append(f"initial '{initial}' が states に未定義")

    # 全遷移先が states に存在するか
    for state_name, state in states.items():
        for event_name, transition in state.get("on", {}).items():
            target = transition.get("target", "")
            if target not in states:
                result.passed = False
                result.details.append(f"状態 '{state_name}' のイベント '{event_name}' の遷移先 '{target}' が未定義")

    # id が存在するか
    if not statechart.get("id"):
        result.passed = False
        result.details.append("statechart.id が未定義")

    return result


def v11_auto_scroll_ref_integrity(data: dict) -> CheckResult:
    """V11: auto_scroll_ref整合性"""
    result = CheckResult(id="V11", name="auto_scroll_ref整合性", severity="Tier", passed=True)

    # page.tsx で定義されている ref 名
    known_refs = {"explanationRef", "quizRef", "diffQuizRef", "hintsRef", "completionRef"}

    for phase_name, phase in data.get("phases", {}).items():
        ref = phase.get("auto_scroll_ref")
        if ref is not None and ref not in known_refs:
            result.passed = False
            result.details.append(f"phase '{phase_name}' の auto_scroll_ref '{ref}' が既知のref一覧に無い")

    return result


def v12_user_actions_handler_exists(data: dict) -> CheckResult:
    """V12: user_actionsハンドラ存在確認"""
    result = CheckResult(id="V12", name="user_actionsハンドラ存在", severity="Warning", passed=True)

    if not PAGE_TSX.exists():
        result.details.append(f"page.tsx が見つかりません: {PAGE_TSX}")
        return result

    page_content = PAGE_TSX.read_text(encoding="utf-8")

    for action_name, action in data.get("user_actions", {}).items():
        handler = action.get("handler", "")
        if handler and handler not in page_content:
            result.passed = False
            result.details.append(f"アクション '{action_name}' のハンドラ '{handler}' が page.tsx に未定義")

    return result


def run_all_checks(data: dict, schema: dict) -> ValidationReport:
    """全12項目の検証を実行"""
    report = ValidationReport(file_path="ui-flow.json")

    checks = [
        v1_schema_validation(data, schema),
        v2_statechart_completeness(data),
        v3_panels_completeness(data),
        v4_phases_completeness(data),
        v5_sse_mapping_completeness(data),
        v6_sse_panel_ref_integrity(data),
        v7_phase_panel_ref_integrity(data),
        v8_panel_feature_dir_exists(data),
        v9_transition_coverage(data),
        v10_xstate_compatibility(data),
        v11_auto_scroll_ref_integrity(data),
        v12_user_actions_handler_exists(data),
    ]

    for check in checks:
        report.results.append(check)
        if not check.passed:
            if check.severity == "MVS":
                report.mvs_failures += 1
            elif check.severity == "Tier":
                report.tier_failures += 1
            else:
                report.warnings += 1

    return report


def print_report_markdown(report: ValidationReport) -> None:
    """Markdown形式でレポート出力"""
    print("\n## UI Flow Graph 検証結果\n")
    print("| # | 検証項目 | 深刻度 | 結果 |")
    print("|---|---------|--------|:----:|")

    for r in report.results:
        if r.passed:
            icon = "✅"
        elif r.severity == "Warning":
            icon = "⚠️"
        else:
            icon = "❌"
        print(f"| {r.id} | {r.name} | {r.severity} | {icon} |")

    # 詳細（失敗項目のみ）
    failed = [r for r in report.results if not r.passed]
    if failed:
        print("\n### 詳細\n")
        for r in failed:
            icon = "❌" if r.severity in ("MVS", "Tier") else "⚠️"
            print(f"**{r.id} {r.name}** ({r.severity})")
            for detail in r.details:
                print(f"  - {icon} {detail}")
            print()

    # サマリー
    total = len(report.results)
    passed = sum(1 for r in report.results if r.passed)
    print("### サマリー\n")
    print(f"| 項目 | 結果 |")
    print(f"|------|:----:|")
    print(f"| 合格 | {passed}/{total} |")
    print(f"| MVS失敗 | {report.mvs_failures} |")
    print(f"| Tier失敗 | {report.tier_failures} |")
    print(f"| 警告 | {report.warnings} |")

    status = "**PASSED**" if report.exit_code == 0 else "**FAILED**"
    print(f"| 全体 | {status} (exit {report.exit_code}) |")

    if report.exit_code == 1:
        print("\n→ MVS項目の修正が必要です（コミット不可）")
    elif report.exit_code == 2:
        print("\n→ Tier項目の修正を推奨します")


def print_report_json(report: ValidationReport) -> None:
    """JSON形式でレポート出力"""
    output = {
        "file_path": report.file_path,
        "exit_code": report.exit_code,
        "mvs_failures": report.mvs_failures,
        "tier_failures": report.tier_failures,
        "warnings": report.warnings,
        "results": [
            {
                "id": r.id,
                "name": r.name,
                "severity": r.severity,
                "passed": r.passed,
                "details": r.details,
            }
            for r in report.results
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="UI Flow Graph の構造・整合性を検証します",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python3 scripts/validate_ui_flow.py docs/ui-flow/ui-flow.json
  python3 scripts/validate_ui_flow.py docs/ui-flow/ui-flow.json --json
        """,
    )
    parser.add_argument("target", help="ui-flow.json ファイルパス")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    args = parser.parse_args()

    # ui-flow.json 読み込み
    target_path = Path(args.target)
    if not target_path.is_absolute():
        target_path = PROJECT_ROOT / target_path
    data = load_json(target_path)
    if data is None:
        print(f"❌ ファイルの読み込みに失敗しました: {target_path}")
        sys.exit(1)

    # スキーマ読み込み
    schema = load_json(SCHEMA_PATH)
    if schema is None:
        print(f"❌ スキーマの読み込みに失敗しました: {SCHEMA_PATH}")
        sys.exit(1)

    # 検証実行
    report = run_all_checks(data, schema)

    # レポート出力
    if args.json:
        print_report_json(report)
    else:
        print_report_markdown(report)

    sys.exit(report.exit_code)


if __name__ == "__main__":
    main()
