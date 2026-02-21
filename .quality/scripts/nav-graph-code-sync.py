#!/usr/bin/env python3
"""
NAV-GRAPH Code Sync Checker v1.0

nav-graph.jsonと実際のコードの同期状態を検証します。

Usage:
    python nav-graph-code-sync.py [--project-root PATH]

Checks:
    S1: コードに存在するがnav-graphに未登録のページ (WARNING)
    S2: nav-graphに登録されているがコードに存在しないページ (BLOCKING)
    S3: Named routeの不一致 (WARNING)

Exit codes:
    0: 同期完了
    1: BLOCKINGイシューあり
    2: WARNINGのみ
"""

import argparse
import glob
import json
import re
import sys
from pathlib import Path
from typing import Optional


def find_project_root(start: Optional[str] = None) -> Path:
    """pubspec.yamlを探してプロジェクトルートを返却"""
    search = Path(start) if start else Path.cwd()
    for candidate in [search, *search.parents]:
        if (candidate / "pubspec.yaml").exists():
            return candidate
    print("ERROR: pubspec.yamlが見つかりません。", file=sys.stderr)
    sys.exit(1)


def load_nav_graph(project_root: Path) -> Optional[dict]:
    """nav-graph.jsonをロード。存在しなければNoneを返却。"""
    path = project_root / "docs" / "navigation" / "nav-graph.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_barrel_file(filepath: Path) -> bool:
    """exportのみを含むbarrelファイルかどうかを判別"""
    try:
        content = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("//")
    ]
    # library宣言とexportのみであればbarrel
    non_directive = [
        line
        for line in lines
        if not line.startswith("export ")
        and not line.startswith("library")
        and not line.startswith("///")
    ]
    return len(non_directive) == 0 and any(
        line.startswith("export ") for line in lines
    )


def scan_code_pages(project_root: Path) -> list[str]:
    """lib/features/*/presentation/pages/ 配下のページファイルを収集。

    barrelファイルは除外。_frag.dartはタブフラグメントのため含む。
    """
    pattern = str(project_root / "lib" / "features" / "*" / "presentation" / "pages" / "**" / "*.dart")
    all_files = sorted(glob.glob(pattern, recursive=True))

    pages = []
    for filepath_str in all_files:
        filepath = Path(filepath_str)

        # barrelファイルを除外
        if is_barrel_file(filepath):
            continue

        # lib/基準の相対パスに変換
        rel = filepath.relative_to(project_root)
        pages.append(str(rel))

    return pages


def extract_nav_graph_screens(nav_graph: dict) -> dict[str, dict]:
    """nav-graph screensを{screen_id: screen_data}辞書として返却"""
    return nav_graph.get("screens", {})


def extract_nav_graph_file_set(screens: dict[str, dict]) -> dict[str, str]:
    """{file_path: screen_id}マッピングを生成（fileフィールドがあるscreenのみ）"""
    result = {}
    for screen_id, screen_data in screens.items():
        file_path = screen_data.get("file")
        if file_path:
            result[file_path] = screen_id
    return result


def extract_nav_graph_routes(screens: dict[str, dict]) -> dict[str, str]:
    """{route: screen_id}マッピング（routeフィールドがnon-nullのscreenのみ）"""
    result = {}
    for screen_id, screen_data in screens.items():
        route = screen_data.get("route")
        if route:
            result[route] = screen_id
    return result


def parse_main_dart_routes(project_root: Path) -> dict[str, str]:
    """main.dartからnamed routeの定義をパース。

    パターン: '/route-name': (context) => const WidgetName()
    または: '/route-name': (context) => WidgetName()

    Returns: {route_path: widget_name}
    """
    main_dart = project_root / "lib" / "main.dart"
    if not main_dart.exists():
        return {}

    content = main_dart.read_text(encoding="utf-8")

    # routes: { ... } ブロックを検索
    routes_match = re.search(r"routes:\s*\{(.*?)\}", content, re.DOTALL)
    if not routes_match:
        return {}

    routes_block = routes_match.group(1)

    # 各route定義をパース
    # '/login': (context) => const LoginPage(),
    # '/home': (context) => const MainNavigationPage(),
    route_pattern = re.compile(
        r"'([^']+)'\s*:\s*\(context\)\s*=>\s*(?:const\s+)?(\w+)\s*\("
    )

    result = {}
    for match in route_pattern.finditer(routes_block):
        route_path = match.group(1)
        widget_name = match.group(2)
        result[route_path] = widget_name

    return result


def check_s1(
    code_pages: list[str], nav_file_set: dict[str, str]
) -> list[str]:
    """S1: コードには存在するがnav-graphに未登録のページ"""
    nav_files = set(nav_file_set.keys())
    missing = []
    for page in code_pages:
        if page not in nav_files:
            missing.append(page)
    return sorted(missing)


def check_s2(
    nav_file_set: dict[str, str], project_root: Path
) -> list[tuple[str, str]]:
    """S2: nav-graphに登録されているがコードに存在しないページ

    Returns: [(screen_id, file_path), ...]
    """
    missing = []
    for file_path, screen_id in nav_file_set.items():
        full_path = project_root / file_path
        if not full_path.exists():
            missing.append((screen_id, file_path))
    return sorted(missing, key=lambda x: x[0])


def check_s3(
    code_routes: dict[str, str], nav_routes: dict[str, str]
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """S3: Named routeの不一致

    Returns: (in_code_not_nav, in_nav_not_code)
        in_code_not_nav: [(route, widget_name), ...]
        in_nav_not_code: [(route, screen_id), ...]
    """
    code_route_set = set(code_routes.keys())
    nav_route_set = set(nav_routes.keys())

    in_code_not_nav = [
        (route, code_routes[route])
        for route in sorted(code_route_set - nav_route_set)
    ]
    in_nav_not_code = [
        (route, nav_routes[route])
        for route in sorted(nav_route_set - code_route_set)
    ]

    return in_code_not_nav, in_nav_not_code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NAV-GRAPHとコードの同期検証"
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="プロジェクトルートパス（デフォルト: pubspec.yaml自動探索）",
    )
    args = parser.parse_args()

    project_root = find_project_root(args.project_root)

    # nav-graph.jsonをロード
    nav_graph = load_nav_graph(project_root)
    if nav_graph is None:
        print("NAV-GRAPH Code Sync Report")
        print("=" * 50)
        print()
        print("WARNING: docs/navigation/nav-graph.jsonが存在しません。")
        print("nav-graph.jsonを先に作成してください。")
        return 2

    # データ収集
    code_pages = scan_code_pages(project_root)
    screens = extract_nav_graph_screens(nav_graph)
    nav_file_set = extract_nav_graph_file_set(screens)
    nav_routes = extract_nav_graph_routes(screens)
    code_routes = parse_main_dart_routes(project_root)

    # 検査実行
    s1_results = check_s1(code_pages, nav_file_set)
    s2_results = check_s2(nav_file_set, project_root)
    s3_code_only, s3_nav_only = check_s3(code_routes, nav_routes)

    # レポート出力
    print("NAV-GRAPH Code Sync Report")
    print("=" * 50)
    print(
        f"Stats: {len(code_pages)} code pages, "
        f"{len(screens)} nav-graph screens, "
        f"{len(code_routes)} named routes"
    )
    print()

    # S1
    print(f"S1: Code pages not in nav-graph ({len(s1_results)})")
    if s1_results:
        for page in s1_results:
            print(f"  - {page}")
    else:
        print("  (none)")
    print()

    # S2
    print(f"S2: Nav-graph screens not in code ({len(s2_results)})")
    if s2_results:
        for screen_id, file_path in s2_results:
            print(f"  - {screen_id} -> {file_path}")
    else:
        print("  (none)")
    print()

    # S3
    s3_total = len(s3_code_only) + len(s3_nav_only)
    print(f"S3: Named route mismatches ({s3_total})")
    if s3_code_only:
        for route, widget in s3_code_only:
            print(f"  - {route}: in code ({widget}) but not in nav-graph")
    if s3_nav_only:
        for route, screen_id in s3_nav_only:
            print(f"  - {route}: in nav-graph ({screen_id}) but not in code")
    if s3_total == 0:
        print("  (none)")
    print()

    # 最終判定
    has_blocking = len(s2_results) > 0
    has_warnings = len(s1_results) > 0 or s3_total > 0

    if has_blocking:
        print("Final: BLOCKING issues found")
        return 1
    elif has_warnings:
        print("Final: Warnings (no blocking issues)")
        return 2
    else:
        print("Final: Synced")
        return 0


if __name__ == "__main__":
    sys.exit(main())
