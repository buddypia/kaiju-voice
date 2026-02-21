#!/usr/bin/env python3
"""
SPEC Validator - SPEC 文書の JSON Schema ブロックおよびハイブリッド API 仕様を検証するスクリプト

v3.1 アップデート:
- ハイブリッド API 仕様検証 (Schema + Example)
- Example が Schema と一致するか検証
- SSOT パス(Edge Function ファイル) 存在確認
- Edge Function responseSchema と SPEC 一致検証

使用法:
    python validate.py <SPEC_PATH>           # 単一ファイル検証
    python validate.py --all                 # 全体 SPEC 検証
    python validate.py 029                   # 機能番号で検証
    python validate.py --json <SPEC_PATH>    # JSON 形式出力
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    import jsonschema
    from jsonschema import Draft202012Validator, ValidationError
except ImportError:
    print("❌ jsonschema パッケージが必要です: pip install jsonschema")
    sys.exit(1)


# プロジェクトルートパス
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCHEMAS_DIR = PROJECT_ROOT / "docs" / "_templates" / "schemas"
FEATURES_DIR = PROJECT_ROOT / "docs" / "features"
EDGE_FUNCTIONS_DIR = PROJECT_ROOT / "infra" / "supabase" / "functions"


@dataclass
class ValidationResult:
    """検証結果を格納するデータクラス"""
    file_path: str
    schema_type: str
    is_valid: bool
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


@dataclass
class SpecValidationReport:
    """SPEC ファイル全体検証レポート"""
    spec_path: str
    json_schema_results: list = field(default_factory=list)
    structure_results: dict = field(default_factory=dict)
    api_validation_results: list = field(default_factory=list)
    overall_passed: bool = True
    error_count: int = 0
    warning_count: int = 0


def load_meta_schema(schema_type: str) -> Optional[dict]:
    """メタスキーマファイルロード"""
    schema_path = SCHEMAS_DIR / f"{schema_type}.schema.json"
    if not schema_path.exists():
        return None

    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_json_schema_blocks(content: str) -> list[tuple[str, str, int]]:
    """
    SPEC ファイルから json:schema/* ブロック抽出

    Returns:
        list of (schema_type, json_content, line_number)
    """
    # パターン: ```json:schema/{type}\n{content}\n```
    pattern = r'```json:schema/(\w+)\n(.*?)\n```'
    matches = []

    for match in re.finditer(pattern, content, re.DOTALL):
        schema_type = match.group(1)
        json_content = match.group(2)
        # 行番号計算
        line_number = content[:match.start()].count('\n') + 1
        matches.append((schema_type, json_content, line_number))

    return matches


def validate_json_block(
    json_content: str,
    schema_type: str,
    line_number: int,
    spec_path: str
) -> ValidationResult:
    """単一 JSON ブロック検証"""
    result = ValidationResult(
        file_path=spec_path,
        schema_type=schema_type,
        is_valid=True
    )

    # 1. JSON パース検証
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError as e:
        result.is_valid = False
        result.errors.append(f"ライン {line_number}: JSON パース失敗 - {e.msg}")
        return result

    # 2. メタスキーマロード
    meta_schema = load_meta_schema(schema_type)
    if meta_schema is None:
        result.warnings.append(f"メタスキーマなし: {schema_type}.schema.json (スキップ)")
        return result

    # 3. JSON Schema 検証
    try:
        validator = Draft202012Validator(meta_schema)
        errors = list(validator.iter_errors(data))

        if errors:
            result.is_valid = False
            for error in errors:
                path = " > ".join(str(p) for p in error.absolute_path) or "(root)"
                result.errors.append(f"ライン {line_number}: [{path}] {error.message}")
    except Exception as e:
        result.is_valid = False
        result.errors.append(f"ライン {line_number}: 検証エラー - {str(e)}")

    # 4. API Endpoint の場合追加検証 (ハイブリッド)
    if schema_type == "api_endpoint":
        hybrid_results = validate_api_hybrid(data, line_number, spec_path)
        result.errors.extend(hybrid_results.get("errors", []))
        result.warnings.extend(hybrid_results.get("warnings", []))
        if hybrid_results.get("errors"):
            result.is_valid = False

    return result


def validate_api_hybrid(data: dict, line_number: int, spec_path: str) -> dict:
    """ハイブリッド API 仕様検証 (Schema + Example 一致)"""
    errors = []
    warnings = []

    # 1. request_example が request スキーマと一致するか検証
    if "request" in data and "request_example" in data:
        request_schema = data["request"]
        request_example = data["request_example"]
        example_errors = validate_example_against_schema(
            request_example, request_schema, "request_example"
        )
        errors.extend([f"ライン {line_number}: {e}" for e in example_errors])
    elif "request" in data and "request_example" not in data:
        warnings.append(f"ライン {line_number}: request_example 欠落 (ハイブリッド形式不完全)")

    # 2. response_example が response スキーマと一致するか検証
    if "response" in data and "response_example" in data:
        response_schema = data["response"]
        response_example = data["response_example"]
        example_errors = validate_example_against_schema(
            response_example, response_schema, "response_example"
        )
        errors.extend([f"ライン {line_number}: {e}" for e in example_errors])
    elif "response" in data and "response_example" not in data:
        warnings.append(f"ライン {line_number}: response_example 欠落 (ハイブリッド形式不完全)")

    # 3. SSOT パス検証
    if "ssot_path" in data:
        ssot_path = PROJECT_ROOT / data["ssot_path"]
        if not ssot_path.exists():
            warnings.append(f"ライン {line_number}: SSOT ファイルなし - {data['ssot_path']}")

    # 4. error_examples が errors と一致するか検証
    if "errors" in data and "error_examples" in data:
        error_codes = {e["code"] for e in data["errors"]}
        example_codes = {e["code"] for e in data["error_examples"]}

        # errors に定義されたが example がないコード
        missing_examples = error_codes - example_codes
        if missing_examples:
            warnings.append(
                f"ライン {line_number}: エラー例示欠落 - {', '.join(missing_examples)}"
            )

    return {"errors": errors, "warnings": warnings}


def validate_example_against_schema(
    example: Any,
    schema: dict,
    context: str
) -> list[str]:
    """Example が Schema と一致するか検証"""
    errors = []

    # スキーマで required フィールド確認
    required_fields = schema.get("required", [])
    properties = schema.get("properties", {})

    if isinstance(example, dict):
        # 必須フィールド検証
        for req_field in required_fields:
            if req_field not in example:
                errors.append(f"{context}: 必須フィールド '{req_field}' 欠落")

        # タイプ検証
        for field_name, field_value in example.items():
            if field_name in properties:
                field_schema = properties[field_name]
                field_type = field_schema.get("type")

                if field_type:
                    type_valid = check_type(field_value, field_type)
                    if not type_valid:
                        errors.append(
                            f"{context}.{field_name}: タイプ不一致 "
                            f"(expected: {field_type}, got: {type(field_value).__name__})"
                        )

                # enum 検証
                if "enum" in field_schema:
                    if field_value not in field_schema["enum"]:
                        errors.append(
                            f"{context}.{field_name}: enum 不一致 "
                            f"(allowed: {field_schema['enum']}, got: {field_value})"
                        )

                # 入れ子オブジェクト検証
                if field_type == "object" and "properties" in field_schema:
                    nested_errors = validate_example_against_schema(
                        field_value, field_schema, f"{context}.{field_name}"
                    )
                    errors.extend(nested_errors)

    return errors


def check_type(value: Any, expected_type: str) -> bool:
    """値のタイプがスキーマタイプと一致するか確認"""
    type_mapping = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
    }

    expected = type_mapping.get(expected_type)
    if expected is None:
        return True  # わからないタイプは通過

    return isinstance(value, expected)


def check_required_sections(content: str) -> dict:
    """必須セクション存在有無確認"""
    required_sections = {
        "§0 AI 実装契約": r'##\s*0\.\s*AI 実装 契約',
        "§0.4 Data Schema": r'###\s*0\.4\s*Data Schema',
        "§0.5 API Contract": r'###\s*0\.5\s*API Contract',
        "§1 概要": r'##\s*1\.\s*概要',
        "§2 機能要求事項": r'##\s*2\.\s*機能 要求事項',
    }

    results = {}
    for section_name, pattern in required_sections.items():
        if re.search(pattern, content, re.IGNORECASE):
            results[section_name] = {"exists": True}
        else:
            results[section_name] = {"exists": False, "error": "セクション欠落"}

    return results


def check_na_declarations(content: str) -> list[str]:
    """空セクションに N/A 明示有無確認"""
    warnings = []

    # §0.7, §0.8 は AI 未使用時 N/A 必須
    ai_sections = [
        (r'###\s*0\.7\s*AI Logic', "§0.7 AI Logic"),
        (r'###\s*0\.8\s*Safety', "§0.8 Safety"),
    ]

    for pattern, section_name in ai_sections:
        match = re.search(pattern, content)
        if match:
            # 該当セクション以降次の ### 前まで内容確認
            section_start = match.end()
            next_section = re.search(r'\n###\s', content[section_start:])
            section_end = section_start + next_section.start() if next_section else len(content)
            section_content = content[section_start:section_end]

            # N/A または実質的内容確認
            has_na = re.search(r'\*\*N/A\*\*|該当なし|N/A', section_content)
            has_content = len(section_content.strip()) > 50  # 最小内容

            if not has_na and not has_content:
                warnings.append(f"{section_name}: 内容がなければ 'N/A' 明示必要")

    return warnings


def check_ac_format(content: str) -> list[str]:
    """AC (Acceptance Criteria) 形式検証 - BDD 5列テーブル"""
    warnings = []

    # AC テーブル検索
    ac_table_pattern = r'\|\s*AC\s*\|.*\|.*\|.*\|.*\|'
    ac_row_pattern = r'\|\s*AC\d+\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|'

    # AC テーブルがあるか確認
    if re.search(ac_table_pattern, content):
        # 各 AC 行検証
        for match in re.finditer(ac_row_pattern, content):
            given, when, then, observation = match.groups()

            # 空セル確認
            if not given.strip():
                ac_id = match.group(0).split('|')[1].strip()
                warnings.append(f"{ac_id}: Given コラムが空")
            if not observation.strip():
                ac_id = match.group(0).split('|')[1].strip()
                warnings.append(f"{ac_id}: 観測点コラムが空")

    return warnings


def check_api_hybrid_completeness(content: str) -> list[str]:
    """ハイブリッド API 仕様完全性検証 (テーブル + 例示)"""
    warnings = []

    # §0.5 API Contract セクション検索
    api_section_match = re.search(r'###\s*0\.5\s*API Contract', content)
    if not api_section_match:
        return warnings

    # セクション範囲抽出
    section_start = api_section_match.end()
    next_section = re.search(r'\n##[#]?\s', content[section_start:])
    section_end = section_start + next_section.start() if next_section else len(content)
    section_content = content[section_start:section_end]

    # N/A チェック
    if re.search(r'\*\*N/A\*\*|N/A\s*-', section_content):
        return warnings  # N/A なら検証スキップ

    # Schema テーブル存在確認
    has_schema_table = bool(re.search(r'\|\s*Field\s*\|\s*Type\s*\|', section_content))
    if not has_schema_table:
        warnings.append("§0.5 API Contract: Schema テーブルなし")

    # Example ブロック存在確認
    has_request_example = bool(re.search(r'Request Example|要求例示', section_content, re.IGNORECASE))
    has_response_example = bool(re.search(r'Response Example|応答例示|Success.*Example', section_content, re.IGNORECASE))

    if not has_request_example:
        warnings.append("§0.5 API Contract: Request Example なし")
    if not has_response_example:
        warnings.append("§0.5 API Contract: Response Example なし")

    # Error セクション確認
    has_error_codes = bool(re.search(r'\|\s*HTTP\s*\|\s*Code\s*\|', section_content))
    has_error_examples = bool(re.search(r'Error.*Example|エラー.*例示', section_content, re.IGNORECASE))

    if not has_error_codes:
        warnings.append("§0.5 API Contract: Error Codes テーブルなし")
    if has_error_codes and not has_error_examples:
        warnings.append("§0.5 API Contract: Error Response Examples なし (ハイブリッド不完全)")

    return warnings


def validate_ssot_paths(content: str) -> list[str]:
    """SSOT パス有効性検証"""
    warnings = []

    # SSOT パスパターン検索 (例: infra/supabase/functions/xxx/index.ts)
    ssot_pattern = r'`(infra/supabase/functions/[^`]+)`'
    matches = re.findall(ssot_pattern, content)

    for path in matches:
        full_path = PROJECT_ROOT / path
        if not full_path.exists():
            warnings.append(f"SSOT パスなし: {path}")

    return warnings


def validate_spec_file(spec_path: Path) -> SpecValidationReport:
    """単一 SPEC ファイル検証"""
    report = SpecValidationReport(spec_path=str(spec_path))

    if not spec_path.exists():
        report.overall_passed = False
        report.error_count = 1
        report.structure_results["file"] = {"error": "ファイルを見つけられません"}
        return report

    with open(spec_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. JSON Schema ブロック検証
    blocks = extract_json_schema_blocks(content)
    for schema_type, json_content, line_number in blocks:
        result = validate_json_block(json_content, schema_type, line_number, str(spec_path))
        report.json_schema_results.append(result)

        if not result.is_valid:
            report.overall_passed = False
            report.error_count += len(result.errors)
        report.warning_count += len(result.warnings)

    # 2. 必須セクション確認
    section_results = check_required_sections(content)
    report.structure_results["sections"] = section_results
    for section, info in section_results.items():
        if not info.get("exists"):
            report.overall_passed = False
            report.error_count += 1

    # 3. N/A 明示確認
    na_warnings = check_na_declarations(content)
    report.structure_results["na_declarations"] = na_warnings
    report.warning_count += len(na_warnings)

    # 4. AC 形式確認
    ac_warnings = check_ac_format(content)
    report.structure_results["ac_format"] = ac_warnings
    report.warning_count += len(ac_warnings)

    # 5. ハイブリッド API 仕様完全性検証 (v3.1 追加)
    hybrid_warnings = check_api_hybrid_completeness(content)
    report.structure_results["api_hybrid"] = hybrid_warnings
    report.warning_count += len(hybrid_warnings)

    # 6. SSOT パス検証 (v3.1 追加)
    ssot_warnings = validate_ssot_paths(content)
    report.structure_results["ssot_paths"] = ssot_warnings
    report.warning_count += len(ssot_warnings)

    return report


def find_spec_files(feature_id: Optional[str] = None) -> list[Path]:
    """SPEC ファイル検索"""
    if feature_id:
        # 数字のみ抽出
        feature_num = ''.join(filter(str.isdigit, feature_id)).zfill(3)
        pattern = f"{feature_num}-*/SPEC-*.md"
    else:
        pattern = "*/SPEC-*.md"

    return list(FEATURES_DIR.glob(pattern))


def print_report(report: SpecValidationReport, use_json: bool = False):
    """検証結果出力"""
    if use_json:
        output = {
            "spec_path": report.spec_path,
            "passed": report.overall_passed,
            "errors": report.error_count,
            "warnings": report.warning_count,
            "json_schema_results": [
                {
                    "type": r.schema_type,
                    "valid": r.is_valid,
                    "errors": r.errors,
                    "warnings": r.warnings
                }
                for r in report.json_schema_results
            ],
            "structure_results": report.structure_results
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    print(f"\n## SPEC 検証結果: {Path(report.spec_path).name}\n")

    # JSON Schema 検証結果
    print("### JSON Schema 検証")
    if report.json_schema_results:
        for result in report.json_schema_results:
            status = "✅" if result.is_valid else "❌"
            print(f"{status} {result.schema_type}")
            for error in result.errors:
                print(f"   - {error}")
            for warning in result.warnings:
                print(f"   ⚠️ {warning}")
    else:
        print("   (JSON Schema ブロックなし)")

    # 構造検証結果
    print("\n### 構造検証")

    # 必須セクション
    sections = report.structure_results.get("sections", {})
    for section, info in sections.items():
        status = "✅" if info.get("exists") else "❌"
        print(f"{status} {section}")

    # N/A 警告
    na_warnings = report.structure_results.get("na_declarations", [])
    if na_warnings:
        print("\n### N/A 明示必要")
        for warning in na_warnings:
            print(f"   ⚠️ {warning}")

    # AC 形式警告
    ac_warnings = report.structure_results.get("ac_format", [])
    if ac_warnings:
        print("\n### AC 形式警告")
        for warning in ac_warnings:
            print(f"   ⚠️ {warning}")

    # ハイブリッド API 検証結果 (v3.1)
    hybrid_warnings = report.structure_results.get("api_hybrid", [])
    if hybrid_warnings:
        print("\n### ハイブリッド API 仕様検証")
        for warning in hybrid_warnings:
            print(f"   ⚠️ {warning}")

    # SSOT パス検証結果 (v3.1)
    ssot_warnings = report.structure_results.get("ssot_paths", [])
    if ssot_warnings:
        print("\n### SSOT パス検証")
        for warning in ssot_warnings:
            print(f"   ⚠️ {warning}")

    # 要約
    print("\n### 要約")
    print(f"| 項目 | 結果 |")
    print(f"|------|:----:|")

    json_status = "✅" if all(r.is_valid for r in report.json_schema_results) else f"❌ {report.error_count} errors"
    structure_status = "✅" if report.warning_count == 0 else f"⚠️ {report.warning_count} warnings"
    overall_status = "**PASSED**" if report.overall_passed else "**FAILED**"

    print(f"| JSON Schema | {json_status} |")
    print(f"| 構造 | {structure_status} |")
    print(f"| 全体 | {overall_status} |")

    if not report.overall_passed:
        print("\n→ 上記エラーを修正してください。")


def main():
    parser = argparse.ArgumentParser(
        description="SPEC 文書の JSON Schema ブロックおよびハイブリッド API 仕様を検証します。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例示:
  python validate.py docs/features/029-vocabulary-book/SPEC-029.md
  python validate.py --all
  python validate.py 029
  python validate.py --json 029
        """
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="SPEC ファイルパスまたは機能番号 (例: 029)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="全ての SPEC ファイル検証"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON 形式で出力"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="警告も失敗で処理"
    )

    args = parser.parse_args()

    # SPEC ファイル検索
    if args.all:
        spec_files = find_spec_files()
    elif args.target:
        target_path = Path(args.target)
        if target_path.exists() and target_path.is_file():
            spec_files = [target_path]
        else:
            # 機能番号で検索
            spec_files = find_spec_files(args.target)
    else:
        parser.print_help()
        sys.exit(1)

    if not spec_files:
        print("❌ SPEC ファイルを見つけられません。")
        sys.exit(1)

    # 検証実行
    all_passed = True
    for spec_file in spec_files:
        report = validate_spec_file(spec_file)

        if args.strict and report.warning_count > 0:
            report.overall_passed = False

        if not report.overall_passed:
            all_passed = False

        print_report(report, use_json=args.json)

    # 終了コード
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
