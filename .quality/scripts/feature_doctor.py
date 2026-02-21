#!/usr/bin/env python3
"""
feature_doctor.py - CONTEXT.json状態診断および自動復旧スクリプト

目標:
- CONTEXT.json破損/欠落によるパイプライン停止を防止
- スキーマ/テンプレート基盤で最小限の安全復旧を実行
- 危険な自動修正は避け、復旧が必要な箇所を明確に表示

Exit Codes:
  0 - 正常 (問題なし)
  1 - エラー (致命的問題)
  2 - 警告 (復旧が必要または部分的問題)

Usage:
  python3 feature_doctor.py [--fix] [--json] [--feature <id>] [--no-sync]

Options:
  --fix       自動復旧を試行 (テンプレート基盤の補完、欠落CONTEXT.jsonの生成)
  --json      JSON形式で出力
  --feature   特定のfeature IDのみ検査 (部分一致許可)
  --no-sync   related_code/FR状態の自動整理(verify_feature_status)をスキップ
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURES_DIR = Path("docs/features")
TEMPLATE_PATH = Path("docs/_templates/context_template.json")
SCHEMA_PATH = Path("docs/_templates/context_schema.json")
VERIFY_STATUS_DART = Path("scripts/sync_feature_status/bin/verify_feature_status.dart")

EXCLUDE_DIRS = {"_templates", "candidates", "priority"}


# ----------------------------
# Utilities
# ----------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _strip_comments(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: _strip_comments(v)
            for k, v in value.items()
            if not (isinstance(k, str) and k.startswith("$comment"))
        }
    if isinstance(value, list):
        return [_strip_comments(v) for v in value]
    return value


def _deep_merge_missing(target: dict, defaults: dict) -> bool:
    """Fill missing keys in target using defaults. Returns True if modified."""
    modified = False
    for key, default_val in defaults.items():
        if key not in target or target[key] is None:
            target[key] = deepcopy(default_val)
            modified = True
            continue
        if isinstance(default_val, dict) and isinstance(target.get(key), dict):
            if _deep_merge_missing(target[key], default_val):
                modified = True
    return modified


def _safe_write_json(path: Path, data: dict) -> None:
    encoder = json.JSONEncoder(indent=2, ensure_ascii=False)
    content = encoder.encode(data)
    path.write_text(content + "\n", encoding="utf-8")


def _find_spec_path(feature_dir: Path) -> str | None:
    specs = sorted(feature_dir.glob("SPEC-*.md"))
    return str(specs[0]) if specs else None


def _find_brief_path(feature_dir: Path) -> str | None:
    brief = feature_dir / "BRIEF.md"
    return str(brief) if brief.exists() else None


def _find_index_path(feature_dir: Path) -> str:
    return str(feature_dir / "index.md")


def _load_schema_required(schema: dict) -> tuple[list[str], list[str], list[str], set[str], set[int]]:
    required_root = schema.get("required", [])
    quick_required = (
        schema.get("properties", {})
        .get("quick_resume", {})
        .get("required", [])
    )
    artifact_required = (
        schema.get("properties", {})
        .get("artifacts", {})
        .get("required", [])
    )
    states = set(
        schema.get("properties", {})
        .get("quick_resume", {})
        .get("properties", {})
        .get("current_state", {})
        .get("enum", [])
    )
    versions = set(schema.get("properties", {}).get("schema_version", {}).get("enum", []))
    return required_root, quick_required, artifact_required, states, versions


def _contains_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return "{" in value and "}" in value or "TODO" in value
    return False


# ----------------------------
# Core logic
# ----------------------------

def _feature_dirs(feature_filter: str | None) -> list[Path]:
    if not FEATURES_DIR.exists():
        return []

    dirs = []
    for entry in FEATURES_DIR.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith("_") or entry.name in EXCLUDE_DIRS:
            continue
        if feature_filter and feature_filter not in entry.name:
            continue
        dirs.append(entry)
    return sorted(dirs)


def _create_stub_context(
    feature_dir: Path,
    template: dict,
    reason: str,
    backup_path: str | None = None,
) -> dict:
    context = deepcopy(template)
    feature_id = feature_dir.name

    context["feature_id"] = feature_id
    context["title"] = feature_id  # Placeholder (manual update required)
    context["why"] = f"TODO: {feature_id} 機能のWhyを入力してください (feature-doctor 自動生成)"

    qr = context.get("quick_resume", {})
    qr["current_state"] = "AwaitingUser"
    qr["current_task"] = "CONTEXT.json復旧が必要 (feature-doctor)"
    qr["last_updated_at"] = _now_iso()
    qr["next_actions"] = [
        "BRIEF.md確認",
        "Why/Success Criteriaを入力",
        "feature-spec-generatorの再実行要否を検討",
    ]
    blockers = qr.get("blockers", []) or []
    blockers.append(reason)
    if backup_path:
        blockers.append(f"backup: {backup_path}")
    qr["blockers"] = blockers
    context["quick_resume"] = qr

    artifacts = context.get("artifacts", {})
    artifacts["index"] = _find_index_path(feature_dir)
    brief_path = _find_brief_path(feature_dir)
    if brief_path:
        artifacts["brief"] = brief_path
    spec_path = _find_spec_path(feature_dir)
    if spec_path:
        artifacts["spec"] = spec_path
    context["artifacts"] = artifacts

    return context


def _validate_priority(
    context: dict,
    fix: bool,
    defaults: dict,
) -> tuple[list[str], list[str], bool]:
    """priorityセクションの検証 (rice_inputs範囲, confidence.score, calculated.rice_score)。"""
    warnings: list[str] = []
    errors: list[str] = []
    modified = False

    priority = context.get("priority")
    if priority is None:
        warnings.append("priorityセクション欠落")
        if fix and "priority" in defaults:
            context["priority"] = deepcopy(defaults["priority"])
            modified = True
        return warnings, errors, modified

    if not isinstance(priority, dict):
        errors.append("priorityがオブジェクトではありません")
        return warnings, errors, modified

    # rice_inputs 範囲チェック
    rice_inputs = priority.get("rice_inputs")
    if isinstance(rice_inputs, dict):
        reach = rice_inputs.get("reach", {})
        if isinstance(reach, dict):
            score = reach.get("score")
            if score is not None and isinstance(score, (int, float)) and not (1 <= score <= 10):
                warnings.append(
                    f"priority.rice_inputs.reach.score 範囲超過: {score} (許容: 1-10)"
                )
        impact = rice_inputs.get("impact", {})
        if isinstance(impact, dict):
            score = impact.get("score")
            if score is not None and isinstance(score, (int, float)) and score not in (0.25, 0.5, 1, 2, 3):
                warnings.append(
                    f"priority.rice_inputs.impact.score 許容値外: {score} (許容: 0.25, 0.5, 1, 2, 3)"
                )
        effort = rice_inputs.get("effort", {})
        if isinstance(effort, dict):
            score = effort.get("score")
            if score is not None and isinstance(score, (int, float)) and not (0.5 <= score <= 20):
                warnings.append(
                    f"priority.rice_inputs.effort.score 範囲超過: {score} (許容: 0.5-20)"
                )
    else:
        warnings.append("priority.rice_inputs 欠落またはフォーマットエラー")

    # confidence.score 範囲
    confidence = priority.get("confidence")
    if isinstance(confidence, dict):
        score = confidence.get("score")
        if score is not None and isinstance(score, (int, float)) and not (0 <= score <= 1):
            warnings.append(
                f"priority.confidence.score 範囲超過: {score} (許容: 0-1)"
            )

    # calculated.rice_score の存在および型確認
    calculated = priority.get("calculated")
    if isinstance(calculated, dict):
        rice_score = calculated.get("rice_score")
        if rice_score is None:
            warnings.append("priority.calculated.rice_score 欠落")
        elif not isinstance(rice_score, (int, float)):
            warnings.append(
                f"priority.calculated.rice_score 型エラー: {type(rice_score).__name__}"
            )
    else:
        warnings.append("priority.calculated 欠落")

    # last_updated ISO 8601 形式確認
    last_updated = priority.get("last_updated")
    if last_updated and isinstance(last_updated, str):
        try:
            datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        except ValueError:
            warnings.append("priority.last_updated ISO 8601 形式エラー")

    return warnings, errors, modified


def _validate_brief_context(context: dict) -> tuple[list[str], list[str]]:
    """brief_contextセクションの検証 (null許容、存在する場合core_goal/user_valueの最小長)。"""
    warnings: list[str] = []
    errors: list[str] = []

    brief_context = context.get("brief_context")
    if brief_context is None:
        # nullは許容 (Briefing段階前)
        return warnings, errors

    if not isinstance(brief_context, dict):
        errors.append("brief_contextがオブジェクトではありません")
        return warnings, errors

    core_goal = brief_context.get("core_goal")
    if not core_goal or (isinstance(core_goal, str) and len(core_goal.strip()) < 10):
        warnings.append("brief_context.core_goal 未記入または短すぎます (最小10文字)")

    user_value = brief_context.get("user_value")
    if not user_value or (isinstance(user_value, str) and len(user_value.strip()) < 10):
        warnings.append("brief_context.user_value 未記入または短すぎます (最小10文字)")

    return warnings, errors


def _validate_progress_details(context: dict) -> tuple[list[str], list[str]]:
    """progress.detailsの値の型/enum検証 (string/object両パターン許容)。"""
    warnings: list[str] = []
    errors: list[str] = []
    valid_statuses = {"pending", "in_progress", "completed", "not_started", "partial"}

    progress = context.get("progress")
    if not isinstance(progress, dict):
        return warnings, errors

    details = progress.get("details")
    if not isinstance(details, dict):
        return warnings, errors

    for key, val in details.items():
        if isinstance(key, str) and key.startswith("$"):
            continue  # $comment等のメタキーをスキップ
        if isinstance(val, str):
            if val not in valid_statuses:
                warnings.append(
                    f"progress.details.{key}: 非標準ステータス値 '{val}'"
                )
        elif isinstance(val, dict):
            status = val.get("status")
            if status is not None and status not in valid_statuses:
                warnings.append(
                    f"progress.details.{key}.status: 非標準ステータス値 '{status}'"
                )
        else:
            errors.append(
                f"progress.details.{key}: 型エラー {type(val).__name__} (stringまたはobjectが必要)"
            )

    return warnings, errors


def _validate_and_fix_context(
    context_path: Path,
    feature_dir: Path,
    defaults: dict,
    required_root: list[str],
    quick_required: list[str],
    artifact_required: list[str],
    state_enum: set[str],
    version_enum: set[int],
    fix: bool,
) -> tuple[dict | None, list[str], list[str], bool]:
    """Returns (context, warnings, errors, modified)."""
    warnings: list[str] = []
    errors: list[str] = []
    modified = False

    try:
        context = _load_json(context_path)
        if not isinstance(context, dict):
            errors.append("CONTEXT.jsonのトップレベルがオブジェクトではありません")
            return None, warnings, errors, False
    except json.JSONDecodeError as e:
        errors.append(f"JSONパース失敗: {e}")
        return None, warnings, errors, False
    except IOError as e:
        errors.append(f"ファイル読み取り失敗: {e}")
        return None, warnings, errors, False

    # 基本キー欠落の補正 (テンプレート基盤)
    if fix:
        if _deep_merge_missing(context, defaults):
            modified = True

    # required root check
    for key in required_root:
        if key not in context:
            errors.append(f"必須フィールド欠落: {key}")

    # schema_version
    version = context.get("schema_version")
    if version is None:
        warnings.append("schema_version 欠落")
        if fix:
            context["schema_version"] = max(version_enum) if version_enum else 3
            modified = True
    elif isinstance(version, int) and version_enum and version not in version_enum:
        warnings.append(f"schema_version 値が異常: {version} (許容: {sorted(version_enum)})")
        if fix:
            context["schema_version"] = max(version_enum)
            modified = True

    # feature_id
    feature_id = context.get("feature_id")
    if not feature_id:
        warnings.append("feature_id 欠落")
        if fix:
            context["feature_id"] = feature_dir.name
            modified = True
    elif feature_id != feature_dir.name:
        warnings.append(f"feature_id 不一致: {feature_id} != {feature_dir.name}")

    # title
    title = context.get("title")
    if not title or _contains_placeholder(title):
        warnings.append("title 未記入またはplaceholder")
        if fix and not title:
            context["title"] = feature_dir.name
            modified = True

    # quick_resume
    qr = context.get("quick_resume")
    if not isinstance(qr, dict):
        warnings.append("quick_resume 欠落またはフォーマットエラー")
        if fix:
            context["quick_resume"] = deepcopy(defaults.get("quick_resume", {}))
            context["quick_resume"]["last_updated_at"] = _now_iso()
            modified = True
        qr = context.get("quick_resume", {})

    if isinstance(qr, dict):
        for key in quick_required:
            if key not in qr:
                warnings.append(f"quick_resume 必須フィールド欠落: {key}")
                if fix:
                    qr[key] = deepcopy(defaults.get("quick_resume", {}).get(key))
                    modified = True

        current_state = qr.get("current_state")
        if current_state and state_enum and current_state not in state_enum:
            warnings.append(f"current_state 異常: {current_state}")
            if fix:
                qr["current_state"] = "Idle"
                modified = True

        last_updated = qr.get("last_updated_at")
        if not last_updated:
            warnings.append("quick_resume.last_updated_at 欠落")
            if fix:
                qr["last_updated_at"] = _now_iso()
                modified = True
        else:
            try:
                datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            except ValueError:
                warnings.append("quick_resume.last_updated_at 形式エラー")
                if fix:
                    qr["last_updated_at"] = _now_iso()
                    modified = True

        context["quick_resume"] = qr

    # artifacts
    artifacts = context.get("artifacts")
    if not isinstance(artifacts, dict):
        warnings.append("artifacts 欠落またはフォーマットエラー")
        if fix:
            context["artifacts"] = deepcopy(defaults.get("artifacts", {}))
            modified = True
        artifacts = context.get("artifacts", {})

    if isinstance(artifacts, dict):
        for key in artifact_required:
            if key not in artifacts:
                warnings.append(f"artifacts 必須フィールド欠落: {key}")
                if fix:
                    artifacts[key] = deepcopy(defaults.get("artifacts", {}).get(key))
                    modified = True

        # index/spec 自動補完
        if fix:
            if not artifacts.get("index"):
                artifacts["index"] = _find_index_path(feature_dir)
                modified = True
            if not artifacts.get("spec"):
                spec_path = _find_spec_path(feature_dir)
                if spec_path:
                    artifacts["spec"] = spec_path
                    modified = True
            if "brief" not in artifacts:
                brief_path = _find_brief_path(feature_dir)
                if brief_path:
                    artifacts["brief"] = brief_path
                    modified = True

        context["artifacts"] = artifacts

    # placeholder detection for why
    why = context.get("why")
    if not why or _contains_placeholder(why):
        warnings.append("why 未記入またはplaceholder")

    # priorityセクション検証
    p_warnings, p_errors, p_modified = _validate_priority(context, fix, defaults)
    warnings.extend(p_warnings)
    errors.extend(p_errors)
    if p_modified:
        modified = True

    # brief_contextセクション検証
    bc_warnings, bc_errors = _validate_brief_context(context)
    warnings.extend(bc_warnings)
    errors.extend(bc_errors)

    # progress.detailsの型/enum検証
    pd_warnings, pd_errors = _validate_progress_details(context)
    warnings.extend(pd_warnings)
    errors.extend(pd_errors)

    return context, warnings, errors, modified


def _repair_invalid_json(
    context_path: Path,
    feature_dir: Path,
    template: dict,
    fix: bool,
) -> tuple[dict | None, list[str], list[str], bool]:
    warnings = ["JSON破損 - 復旧が必要"]
    errors: list[str] = []

    if not fix:
        errors.append("CONTEXT.jsonパース失敗")
        return None, warnings, errors, False

    backup_path = context_path.with_suffix(
        f".bak.{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    )
    try:
        shutil.move(str(context_path), str(backup_path))
    except IOError as e:
        errors.append(f"バックアップ失敗: {e}")
        return None, warnings, errors, False

    stub = _create_stub_context(
        feature_dir,
        template,
        reason="CONTEXT.json破損の復旧が必要",
        backup_path=str(backup_path),
    )
    _safe_write_json(context_path, stub)
    warnings.append(f"バックアップ生成: {backup_path}")
    return stub, warnings, errors, True


def _run_verify_status(fix: bool, feature_filter: str | None) -> tuple[bool, str]:
    if not VERIFY_STATUS_DART.exists():
        return False, "verify_feature_status.dart なし (スキップ)"

    cmd = ["dart", "run", str(VERIFY_STATUS_DART)]
    if fix:
        cmd.append("--fix")
    if feature_filter:
        cmd.extend(["--feature", feature_filter])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as e:
        return False, f"dart実行失敗: {e}"

    if result.returncode == 0:
        return True, "verify_feature_status 完了"

    # verify_feature_statusはイシューがある場合1を返すため警告として処理
    return False, result.stderr.strip() or result.stdout.strip() or "verify_feature_status 失敗"


def main() -> None:
    parser = argparse.ArgumentParser(description="CONTEXT.json状態診断および復旧")
    parser.add_argument("--fix", action="store_true", help="自動復旧を試行")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    parser.add_argument("--feature", help="特定のfeature IDのみ検査")
    parser.add_argument("--no-sync", action="store_true", help="verify_feature_statusをスキップ")
    args = parser.parse_args()

    if not TEMPLATE_PATH.exists():
        print("❌ context_template.json なし", file=sys.stderr)
        sys.exit(1)
    if not SCHEMA_PATH.exists():
        print("❌ context_schema.json なし", file=sys.stderr)
        sys.exit(1)

    raw_template = _strip_comments(_load_json(TEMPLATE_PATH))
    schema = _load_json(SCHEMA_PATH)

    required_root, quick_required, artifact_required, state_enum, version_enum = _load_schema_required(schema)

    # placeholderフィールドはテンプレートデフォルト値として使用しない
    template_defaults = deepcopy(raw_template)
    for key in ["feature_id", "title", "why", "success_criteria"]:
        if key in template_defaults:
            template_defaults.pop(key)

    summary = {
        "checked": 0,
        "fixed": 0,
        "warnings": 0,
        "errors": 0,
        "items": [],
    }

    for feature_dir in _feature_dirs(args.feature):
        summary["checked"] += 1
        context_path = feature_dir / "CONTEXT.json"

        if not context_path.exists():
            if args.fix:
                stub = _create_stub_context(
                    feature_dir,
                    raw_template,
                    reason="CONTEXT.json なし",
                )
                _safe_write_json(context_path, stub)
                summary["fixed"] += 1
                summary["warnings"] += 1
                summary["items"].append(
                    {
                        "feature": feature_dir.name,
                        "status": "created",
                        "warnings": ["CONTEXT.json なし → テンプレート生成"],
                        "errors": [],
                    }
                )
                continue

            summary["errors"] += 1
            summary["items"].append(
                {
                    "feature": feature_dir.name,
                    "status": "missing",
                    "warnings": [],
                    "errors": ["CONTEXT.json なし"],
                }
            )
            continue

        # JSON破損復旧
        try:
            _load_json(context_path)
        except json.JSONDecodeError:
            context, warnings, errors, modified = _repair_invalid_json(
                context_path,
                feature_dir,
                raw_template,
                args.fix,
            )
            summary["warnings"] += len(warnings)
            summary["errors"] += len(errors)
            if modified:
                summary["fixed"] += 1
            summary["items"].append(
                {
                    "feature": feature_dir.name,
                    "status": "repaired" if modified else "corrupt",
                    "warnings": warnings,
                    "errors": errors,
                }
            )
            continue

        # 正常JSON
        context, warnings, errors, modified = _validate_and_fix_context(
            context_path,
            feature_dir,
            template_defaults,
            required_root,
            quick_required,
            artifact_required,
            state_enum,
            version_enum,
            args.fix,
        )

        if context is not None and modified:
            _safe_write_json(context_path, context)
            summary["fixed"] += 1

        summary["warnings"] += len(warnings)
        summary["errors"] += len(errors)
        summary["items"].append(
            {
                "feature": feature_dir.name,
                "status": "fixed" if modified else "ok",
                "warnings": warnings,
                "errors": errors,
            }
        )

    # related_code/FR状態の整理
    sync_note = None
    if not args.no_sync:
        ok, note = _run_verify_status(args.fix, args.feature)
        sync_note = note
        if not ok:
            summary["warnings"] += 1

    if args.json:
        if sync_note:
            summary["verify_feature_status"] = sync_note
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print("\n🩺 Feature Doctor 結果")
        print("=" * 60)
        for item in summary["items"]:
            if item["status"] == "ok":
                continue
            print(f"- {item['feature']}: {item['status']}")
            for w in item.get("warnings", []):
                print(f"  ⚠️  {w}")
            for e in item.get("errors", []):
                print(f"  ❌ {e}")
        print("=" * 60)
        print(
            f"検査: {summary['checked']} | 修正: {summary['fixed']} | 警告: {summary['warnings']} | エラー: {summary['errors']}"
        )
        if sync_note:
            print(f"verify_feature_status: {sync_note}")

    if summary["errors"] > 0:
        sys.exit(1)
    if summary["warnings"] > 0:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
