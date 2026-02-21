#!/usr/bin/env python3
"""
ドキュメント-実装整合性検証スクリプト

feature-registry.json を SSOT として、src/features/ と docs/features/ の
完全対応・SPEC構造・CONTEXT.json必須フィールドを検証する。

8項目検証、3段階深刻度:
  MVS (exit 1)  — コミット不可
  Tier (exit 2) — 警告（推奨修正）
  Warning (exit 0) — 情報提供のみ

使用法:
    python3 scripts/validate_docs_consistency.py
    python3 scripts/validate_docs_consistency.py --json
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
FEATURES_SRC_DIR = PROJECT_ROOT / "src" / "features"
FEATURES_DOCS_DIR = PROJECT_ROOT / "docs" / "features"
REGISTRY_PATH = FEATURES_DOCS_DIR / "feature-registry.json"
INDEX_MD_PATH = FEATURES_DOCS_DIR / "index.md"

# 除外ディレクトリ
EXCLUDED_DIRS = {".DS_Store", "_example", "__pycache__"}


@dataclass
class CheckResult:
    """個別検証結果"""
    id: str
    name: str
    severity: str  # "MVS" | "Tier" | "Warning"
    passed: bool
    total: int = 0
    ok_count: int = 0
    details: list = field(default_factory=list)


@dataclass
class ValidationReport:
    """検証レポート全体"""
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


def get_src_feature_dirs() -> set:
    """src/features/ 配下のディレクトリ名一覧を取得"""
    if not FEATURES_SRC_DIR.exists():
        return set()
    return {
        d.name for d in FEATURES_SRC_DIR.iterdir()
        if d.is_dir() and d.name not in EXCLUDED_DIRS
    }


def d1_feature_directory_coverage(registry: dict) -> CheckResult:
    """D1: src/features/ の全ディレクトリが feature-registry.json に登録されていること"""
    result = CheckResult(
        id="D1", name="Feature Directory Coverage",
        severity="MVS", passed=True
    )
    src_dirs = get_src_feature_dirs()
    mappings = registry.get("mappings", {})
    registered = set(mappings.keys())

    result.total = len(src_dirs)
    missing = src_dirs - registered
    result.ok_count = result.total - len(missing)

    if missing:
        result.passed = False
        for d in sorted(missing):
            result.details.append(
                f"src/features/{d}/ が feature-registry.json に未登録"
            )
    return result


def d2_spec_directory_existence(registry: dict) -> CheckResult:
    """D2: registry に登録された全エントリの docs/features/{NNN}-{name}/ ディレクトリが存在すること"""
    result = CheckResult(
        id="D2", name="SPEC Directory Existence",
        severity="MVS", passed=True
    )
    mappings = registry.get("mappings", {})
    result.total = len(mappings)
    result.ok_count = 0

    for src_name, doc_id in sorted(mappings.items()):
        doc_dir = FEATURES_DOCS_DIR / doc_id
        if doc_dir.exists() and doc_dir.is_dir():
            result.ok_count += 1
        else:
            result.passed = False
            result.details.append(
                f"docs/features/{doc_id}/ ディレクトリが存在しない (src: {src_name})"
            )
    return result


def d3_spec_file_existence(registry: dict) -> CheckResult:
    """D3: 各 docs/features/{NNN}-*/ に SPEC-{NNN}-*.md が存在すること"""
    result = CheckResult(
        id="D3", name="SPEC File Existence",
        severity="MVS", passed=True
    )
    mappings = registry.get("mappings", {})
    result.total = len(mappings)
    result.ok_count = 0

    for src_name, doc_id in sorted(mappings.items()):
        doc_dir = FEATURES_DOCS_DIR / doc_id
        if not doc_dir.exists():
            result.passed = False
            result.details.append(
                f"docs/features/{doc_id}/ が存在しないためSPEC確認不可"
            )
            continue

        # SPEC-{NNN}-*.md パターンを検索
        spec_number = doc_id.split("-")[0]  # "001", "014" etc.
        spec_pattern = f"SPEC-{spec_number}-*.md"
        spec_files = list(doc_dir.glob(spec_pattern))

        if spec_files:
            result.ok_count += 1
        else:
            result.passed = False
            result.details.append(
                f"docs/features/{doc_id}/ に {spec_pattern} が見つからない"
            )
    return result


def d4_context_json_required_fields(registry: dict) -> CheckResult:
    """D4: 各 CONTEXT.json に必須フィールドが存在すること"""
    result = CheckResult(
        id="D4", name="CONTEXT.json Required Fields",
        severity="MVS", passed=True
    )
    mappings = registry.get("mappings", {})
    result.total = len(mappings)
    result.ok_count = 0

    for src_name, doc_id in sorted(mappings.items()):
        context_path = FEATURES_DOCS_DIR / doc_id / "CONTEXT.json"
        if not context_path.exists():
            result.passed = False
            result.details.append(
                f"docs/features/{doc_id}/CONTEXT.json が存在しない"
            )
            continue

        ctx = load_json(context_path)
        if ctx is None:
            result.passed = False
            result.details.append(
                f"docs/features/{doc_id}/CONTEXT.json のJSON解析に失敗"
            )
            continue

        errors = []
        # schema_version >= 6
        sv = ctx.get("schema_version")
        if sv is None or (isinstance(sv, (int, float)) and sv < 6):
            errors.append(f"schema_version={sv} (>=6 必須)")

        # feature_id
        if not ctx.get("feature_id"):
            errors.append("feature_id が未定義")

        # title
        if not ctx.get("title"):
            errors.append("title が未定義")

        # why (10文字以上)
        why = ctx.get("why", "")
        if not why or len(str(why)) < 10:
            errors.append(f"why が10文字未満 (現在: {len(str(why))}文字)")

        if errors:
            result.passed = False
            result.details.append(
                f"docs/features/{doc_id}/CONTEXT.json: {'; '.join(errors)}"
            )
        else:
            result.ok_count += 1

    return result


def d5_index_md_feature_completeness(registry: dict) -> CheckResult:
    """D5: docs/features/index.md が registry の全エントリを参照していること"""
    result = CheckResult(
        id="D5", name="index.md Feature Completeness",
        severity="MVS", passed=True
    )
    mappings = registry.get("mappings", {})
    result.total = len(mappings)
    result.ok_count = 0

    if not INDEX_MD_PATH.exists():
        result.passed = False
        result.details.append("docs/features/index.md が存在しない")
        return result

    index_content = INDEX_MD_PATH.read_text(encoding="utf-8")

    for src_name, doc_id in sorted(mappings.items()):
        # SPEC番号（例: "014"）または doc_id がindex.mdに含まれているか
        spec_number = doc_id.split("-")[0]
        if doc_id in index_content or spec_number in index_content:
            result.ok_count += 1
        else:
            result.passed = False
            result.details.append(
                f"{doc_id} (SPEC-{spec_number}) が index.md に未参照"
            )
    return result


def d6_spec_minimum_structure(registry: dict) -> CheckResult:
    """D6: 各 SPEC ファイルに §0, §1, §2 セクションが存在すること"""
    result = CheckResult(
        id="D6", name="SPEC Minimum Structure",
        severity="Tier", passed=True
    )
    mappings = registry.get("mappings", {})
    result.total = len(mappings)
    result.ok_count = 0

    for src_name, doc_id in sorted(mappings.items()):
        doc_dir = FEATURES_DOCS_DIR / doc_id
        if not doc_dir.exists():
            continue

        spec_number = doc_id.split("-")[0]
        spec_files = list(doc_dir.glob(f"SPEC-{spec_number}-*.md"))
        if not spec_files:
            continue

        spec_content = spec_files[0].read_text(encoding="utf-8")

        # §0, §1, §2 に相当する "## 0." "## 1." "## 2." を検索
        missing_sections = []
        for section_num in [0, 1, 2]:
            pattern = rf"^##\s+{section_num}\."
            if not re.search(pattern, spec_content, re.MULTILINE):
                missing_sections.append(f"§{section_num}")

        if missing_sections:
            result.passed = False
            result.details.append(
                f"docs/features/{doc_id}/: {', '.join(missing_sections)} セクション不足"
            )
        else:
            result.ok_count += 1

    return result


def d7_related_code_path_validity(registry: dict) -> CheckResult:
    """D7: CONTEXT.json references.related_code のパスがファイルシステムに存在すること"""
    result = CheckResult(
        id="D7", name="Related Code Path Validity",
        severity="Tier", passed=True
    )
    mappings = registry.get("mappings", {})
    total_paths = 0
    valid_paths = 0

    for src_name, doc_id in sorted(mappings.items()):
        context_path = FEATURES_DOCS_DIR / doc_id / "CONTEXT.json"
        if not context_path.exists():
            continue

        ctx = load_json(context_path)
        if ctx is None:
            continue

        related_code = ctx.get("references", {}).get("related_code", {})

        # related_code が dict（カテゴリ別）またはリスト（フラット）の両方に対応
        all_paths = []
        if isinstance(related_code, dict):
            for category, paths in related_code.items():
                if isinstance(paths, list):
                    all_paths.extend(paths)
        elif isinstance(related_code, list):
            all_paths.extend(related_code)

        for p in all_paths:
            if not isinstance(p, str):
                continue
            total_paths += 1
            full_path = PROJECT_ROOT / p
            if full_path.exists():
                valid_paths += 1
            else:
                result.passed = False
                result.details.append(
                    f"docs/features/{doc_id}/: {p} が存在しない"
                )

    result.total = total_paths
    result.ok_count = valid_paths
    return result


def d8_orphan_spec_detection(registry: dict) -> CheckResult:
    """D8: docs/features/ に存在するが src/features/ に対応がないSPECを検出"""
    result = CheckResult(
        id="D8", name="Orphan SPEC Detection",
        severity="Warning", passed=True
    )

    mappings = registry.get("mappings", {})
    registered_doc_ids = set(mappings.values())

    if not FEATURES_DOCS_DIR.exists():
        return result

    orphans = []
    for d in FEATURES_DOCS_DIR.iterdir():
        if not d.is_dir() or d.name in EXCLUDED_DIRS:
            continue
        # 数字で始まるディレクトリのみチェック（feature spec ディレクトリ）
        if not re.match(r"^\d{3}-", d.name):
            continue
        if d.name not in registered_doc_ids:
            orphans.append(d.name)

    result.total = len(orphans) + len(registered_doc_ids)
    result.ok_count = result.total - len(orphans)

    if orphans:
        result.passed = False
        for o in sorted(orphans):
            result.details.append(
                f"docs/features/{o}/ は feature-registry.json に対応なし (orphan)"
            )
    return result


def run_all_checks(registry: dict) -> ValidationReport:
    """全8項目の検証を実行"""
    report = ValidationReport()

    checks = [
        d1_feature_directory_coverage(registry),
        d2_spec_directory_existence(registry),
        d3_spec_file_existence(registry),
        d4_context_json_required_fields(registry),
        d5_index_md_feature_completeness(registry),
        d6_spec_minimum_structure(registry),
        d7_related_code_path_validity(registry),
        d8_orphan_spec_detection(registry),
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


def print_report_text(report: ValidationReport) -> None:
    """テキスト形式でレポート出力"""
    print()
    mvs_count = sum(1 for r in report.results if r.severity == "MVS")
    tier_count = sum(1 for r in report.results if r.severity == "Tier")
    warn_count = sum(1 for r in report.results if r.severity == "Warning")

    mvs_passed = sum(1 for r in report.results if r.severity == "MVS" and r.passed)
    tier_passed = sum(1 for r in report.results if r.severity == "Tier" and r.passed)
    warn_passed = sum(1 for r in report.results if r.severity == "Warning" and r.passed)

    for r in report.results:
        if r.passed:
            icon = "✅ PASS"
        elif r.severity == "Warning":
            icon = "⚠️  WARN"
        else:
            icon = "❌ FAIL"

        count_info = ""
        if r.total > 0:
            count_info = f"  ({r.ok_count}/{r.total})"

        print(f"  {r.id} {r.name:<30s} {icon}{count_info}")

    print()

    # 詳細（失敗項目のみ）
    failed = [r for r in report.results if not r.passed]
    if failed:
        print("  Details:")
        for r in failed:
            for detail in r.details:
                severity_icon = "❌" if r.severity in ("MVS", "Tier") else "⚠️"
                print(f"    {severity_icon} [{r.id}] {detail}")
        print()

    # サマリー
    print(f"  Result: {mvs_passed}/{mvs_count} MVS passed, "
          f"{tier_passed}/{tier_count} Tier passed, "
          f"{warn_passed}/{warn_count} Warning passed")

    if report.exit_code == 0:
        print("\n  ✅ ドキュメント-実装整合性検証 PASSED")
    elif report.exit_code == 1:
        print("\n  ❌ MVS項目の修正が必要です（コミット不可）")
    elif report.exit_code == 2:
        print("\n  ⚠️  Tier項目の修正を推奨します")
    print()


def print_report_json(report: ValidationReport) -> None:
    """JSON形式でレポート出力"""
    output = {
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
                "total": r.total,
                "ok_count": r.ok_count,
                "details": r.details,
            }
            for r in report.results
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ドキュメント-実装整合性を検証します",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python3 scripts/validate_docs_consistency.py
  python3 scripts/validate_docs_consistency.py --json
        """,
    )
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    args = parser.parse_args()

    # feature-registry.json 読み込み
    registry = load_json(REGISTRY_PATH)
    if registry is None:
        print(f"❌ feature-registry.json の読み込みに失敗しました: {REGISTRY_PATH}")
        sys.exit(1)

    # 検証実行
    report = run_all_checks(registry)

    # レポート出力
    if args.json:
        print_report_json(report)
    else:
        print_report_text(report)

    sys.exit(report.exit_code)


if __name__ == "__main__":
    main()
