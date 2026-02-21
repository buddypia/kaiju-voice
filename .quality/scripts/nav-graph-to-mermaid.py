#!/usr/bin/env python3
"""nav-graph.json → Mermaid stateDiagram-v2 変換器。

Usage:
    python nav-graph-to-mermaid.py [path-to-nav-graph.json]
    python nav-graph-to-mermaid.py --feature 022
    python nav-graph-to-mermaid.py --output docs/navigation/nav-graph.mmd
    python nav-graph-to-mermaid.py --project-root /path/to/project
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

# screen_type → 絵文字マッピング
SCREEN_TYPE_EMOJI = {
    "tab": "\U0001f3e0",        # 🏠
    "page": "\U0001f4c4",       # 📄
    "dialog": "\U0001f4ac",     # 💬
    "bottomSheet": "\U0001f4cb",  # 📋
    "overlay": "\U0001f50d",    # 🔍
}

# gesture → Mermaid edge labelプレフィックス
GESTURE_LABEL = {
    "tap": "tap",
    "longPress": "longPress",
    "swipe": "swipe",
    "doubleTap": "doubleTap",
    "auto": "auto",
}

MAX_LABEL_LEN = 50


def mermaid_id(screen_id: str) -> str:
    """SCR-022-HOME → SCR_022_HOME (Mermaid有効ID)。"""
    return screen_id.replace("-", "_")


def truncate(text: str, max_len: int = MAX_LABEL_LEN) -> str:
    """長いラベルを切り詰めてMermaidレンダリングの崩れを防止。"""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def extract_feature_num(feature_str: str) -> str:
    """'022-home-screen' → '022'."""
    return feature_str.split("-")[0]


def feature_display_name(feature_str: str) -> str:
    """'022-home-screen' → 'Home Screen (022)'.

    ハイフン区切りの名前をTitle Caseに変換し、番号を括弧に入れる。
    """
    parts = feature_str.split("-")
    num = parts[0]
    name = " ".join(p.capitalize() for p in parts[1:]) if len(parts) > 1 else feature_str
    return f"{name} ({num})"


def build_screen_state_line(screen: dict) -> str:
    """単一screenのstate宣言行を生成。"""
    sid = mermaid_id(screen["id"])
    emoji = SCREEN_TYPE_EMOJI.get(screen["screen_type"], "")
    label = truncate(f"{emoji} {screen['name']}")
    return f'    state "{label}" as {sid}'


def build_trigger_lines(source_screen: dict, all_screens: dict) -> list[str]:
    """1つのscreenのtriggersをedge行リストに変換。"""
    lines: list[str] = []
    src = mermaid_id(source_screen["id"])

    for trigger in source_screen.get("triggers", []):
        target_id = trigger["target"]
        # targetがグラフに存在しなければスキップ
        if target_id not in all_screens:
            continue

        tgt = mermaid_id(target_id)

        # self-loopスキップ（Mermaid stateDiagramでのサポートが限定的）
        if src == tgt:
            continue

        gesture = GESTURE_LABEL.get(trigger.get("gesture", "tap"), trigger.get("gesture", ""))
        element = trigger.get("element", "")

        # label組み立て: gesture(element)
        if element:
            label = f"{gesture}({truncate(element, 30)})"
        else:
            label = gesture

        # guard条件を追加
        guards = trigger.get("guards", [])
        if guards:
            conditions = ", ".join(g["condition"] for g in guards)
            label = f"{label} [{truncate(conditions, 25)}]"

        lines.append(f"    {src} --> {tgt} : {label}")

        # guard fallback edges
        for guard in guards:
            fb_id = guard.get("fallback_screen", "")
            if fb_id and fb_id in all_screens:
                fb_mermaid = mermaid_id(fb_id)
                fb_type = guard.get("fallback_type", "redirect")
                cond = guard["condition"]
                fb_label = f"!{truncate(cond, 20)} ({fb_type})"
                lines.append(f"    {src} --> {fb_mermaid} : {fb_label}")

    return lines


def find_entry_screen(screens: dict) -> str | None:
    """アプリのエントリーポイントscreenを推論する。

    優先順位:
    1. entry_conditionsに'none'のみがありscreen_typeが'page'のログイン/スプラッシュ
    2. tab_index == 0のタブscreen
    3. 最初のscreen（fallback）
    """
    # ログイン/スプラッシュscreenを探索
    for screen in screens.values():
        name_lower = screen.get("name", "").lower()
        if any(kw in name_lower for kw in ("login", "splash", "onboarding")):
            return screen["id"]

    # tab_index 0
    for screen in screens.values():
        if screen.get("tab_index") == 0:
            return screen["id"]

    # fallback: 最初のもの
    if screens:
        return next(iter(screens.values()))["id"]

    return None


def group_screens_by_feature(screens: dict) -> dict[str, list[dict]]:
    """screensをfeature基準でグルーピング。"""
    groups: dict[str, list[dict]] = defaultdict(list)
    for screen in screens.values():
        feature = screen.get("feature", "unknown")
        groups[feature].append(screen)

    # 各グループ内でID基準でソート
    for feature in groups:
        groups[feature].sort(key=lambda s: s["id"])

    return dict(sorted(groups.items()))


def generate_master_flow(screens: dict) -> str:
    """全screenをfeature別subgraphでグルーピングしたMermaidダイアグラム。"""
    lines = ["stateDiagram-v2"]

    groups = group_screens_by_feature(screens)

    # Feature別subgraph + state宣言
    for feature, feature_screens in groups.items():
        feature_mermaid_id = f"feature_{feature.replace('-', '_')}"
        display = feature_display_name(feature)
        lines.append(f'    state "{display}" as {feature_mermaid_id} {{')
        for screen in feature_screens:
            sid = mermaid_id(screen["id"])
            emoji = SCREEN_TYPE_EMOJI.get(screen["screen_type"], "")
            label = truncate(f"{emoji} {screen['name']}")
            lines.append(f'        state "{label}" as {sid}')
        lines.append("    }")
        lines.append("")

    # Entry point
    entry = find_entry_screen(screens)
    if entry:
        lines.append(f"    [*] --> {mermaid_id(entry)}")
        lines.append("")

    # Tab navigation edges
    tab_screens = sorted(
        [s for s in screens.values() if s.get("screen_type") == "tab"],
        key=lambda s: s.get("tab_index", 0),
    )
    if len(tab_screens) > 1:
        lines.append('    state "Tab Navigation" as tab_nav {')
        first_tab = tab_screens[0]
        for tab in tab_screens[1:]:
            idx = tab.get("tab_index", "?")
            lines.append(
                f"        {mermaid_id(first_tab['id'])} --> {mermaid_id(tab['id'])} : tab[{idx}]"
            )
        lines.append("    }")
        lines.append("")

    # Trigger edges（tab navigation除外 - 別途処理済み）
    tab_ids = {s["id"] for s in tab_screens}
    for screen in screens.values():
        trigger_lines = build_trigger_lines(screen, screens)
        # tab間の移動はすでにTab Navigationで処理済みのため、
        # sourceとtargetの両方がtabの場合は除外
        for line in trigger_lines:
            lines.append(line)

    return "\n".join(lines) + "\n"


def generate_feature_flow(screens: dict, feature_num: str) -> str:
    """特定featureに属するscreenのみをフィルタリングしたダイアグラム。

    該当featureから外部featureへ出るedgeも含むが、
    外部screenは単純なstateとしてのみ表示する。
    """
    # feature_numに該当するscreenをフィルタ
    feature_screens = {
        sid: s for sid, s in screens.items()
        if extract_feature_num(s.get("feature", "")) == feature_num
    }

    if not feature_screens:
        return f"stateDiagram-v2\n    note right of [*] : No screens found for feature {feature_num}\n"

    # 外部target収集（feature_screensから出るedgeのtarget）
    external_targets: dict[str, dict] = {}
    for screen in feature_screens.values():
        for trigger in screen.get("triggers", []):
            target_id = trigger["target"]
            if target_id not in feature_screens and target_id in screens:
                external_targets[target_id] = screens[target_id]
            # guard fallbackもチェック
            for guard in trigger.get("guards", []):
                fb_id = guard.get("fallback_screen", "")
                if fb_id and fb_id not in feature_screens and fb_id in screens:
                    external_targets[fb_id] = screens[fb_id]

    lines = ["stateDiagram-v2"]

    # Feature内部screen state宣言
    for screen in sorted(feature_screens.values(), key=lambda s: s["id"]):
        lines.append(build_screen_state_line(screen))

    lines.append("")

    # 外部screenは別のスタイルで表示
    if external_targets:
        lines.append("    %% External screens (other features)")
        for screen in sorted(external_targets.values(), key=lambda s: s["id"]):
            sid = mermaid_id(screen["id"])
            feat_num = extract_feature_num(screen.get("feature", "???"))
            label = truncate(f"[{feat_num}] {screen['name']}")
            lines.append(f'    state "{label}" as {sid}')
        lines.append("")

    # Entry point推論: feature内で他のscreenのtargetではないscreen
    # （= feature外部から進入される「root」screen）
    all_internal_targets = set()
    for s in feature_screens.values():
        for t in s.get("triggers", []):
            if t["target"] in feature_screens:
                all_internal_targets.add(t["target"])

    root_candidates = [
        sid for sid in feature_screens if sid not in all_internal_targets
    ]
    if root_candidates:
        feature_entry = min(root_candidates)
    else:
        # すべてのscreenが相互参照 → 名前ベースのfallback
        feature_entry = None
        for s in feature_screens.values():
            name_lower = s.get("name", "").lower()
            if any(kw in name_lower for kw in ("login", "splash", "setup", "list")):
                feature_entry = s["id"]
                break
        if not feature_entry:
            feature_entry = min(feature_screens.keys())

    lines.append(f"    [*] --> {mermaid_id(feature_entry)}")
    lines.append("")

    # すべてのtrigger edges（feature内部 + 外部target含む）
    visible_screens = {**feature_screens, **external_targets}
    for screen in sorted(feature_screens.values(), key=lambda s: s["id"]):
        trigger_lines = build_trigger_lines(screen, visible_screens)
        for line in trigger_lines:
            lines.append(line)

    return "\n".join(lines) + "\n"


def load_nav_graph(path: Path) -> dict:
    """nav-graph.jsonファイルをロード。"""
    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)


def resolve_nav_graph_path(args: argparse.Namespace) -> Path:
    """nav-graph.jsonのパスを決定する。

    優先順位:
    1. 明示的な引数として渡されたパス
    2. --project-root基準のdocs/navigation/nav-graph.json
    3. CWD基準のdocs/navigation/nav-graph.json
    """
    if args.input:
        return Path(args.input)

    root = Path(args.project_root) if args.project_root else Path.cwd()
    return root / "docs" / "navigation" / "nav-graph.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="nav-graph.jsonをMermaid stateDiagram-v2に変換",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="nav-graph.jsonファイルパス（デフォルト: docs/navigation/nav-graph.json）",
    )
    parser.add_argument(
        "--feature",
        type=str,
        default=None,
        help="特定feature番号のみフィルタリング（例: 022）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="出力ファイルパス（デフォルト: stdout）",
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="プロジェクトルートディレクトリ（相対パス解釈用）",
    )

    args = parser.parse_args()

    nav_path = resolve_nav_graph_path(args)
    data = load_nav_graph(nav_path)

    screens: dict = data.get("screens", {})
    if not screens:
        print("Warning: No screens found in nav-graph.json", file=sys.stderr)
        result = "stateDiagram-v2\n    note right of [*] : Empty nav graph\n"
    elif args.feature:
        feature_num = args.feature.zfill(3)  # '22' → '022'
        result = generate_feature_flow(screens, feature_num)
    else:
        result = generate_master_flow(screens)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result, encoding="utf-8")
        print(f"Written to {out_path}", file=sys.stderr)
    else:
        sys.stdout.write(result)


if __name__ == "__main__":
    main()
