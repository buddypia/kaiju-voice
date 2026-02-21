#!/usr/bin/env python3
"""
check_scan_status.py - scan-status.json 整合性検証スクリプト

scan-status.json のスキーマ規則の準拠状況を検証します。

Exit Codes:
  0 - すべての検証に合格
  1 - エラー発生（ファイルなし、JSONパース失敗など）
  2 - 整合性違反を検出（警告）

Usage:
  python check_scan_status.py [--json] [--fix]

Options:
  --json  JSON形式で出力
  --fix   自動修復を試行（欠落した history 配列の追加など）
"""

import json
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path


SCAN_STATUS_PATH = Path(".claude/skills/market-intelligence-scanner/assets/scan-status.json")
SCHEMA_PATH = Path(".claude/skills/market-intelligence-scanner/references/scan-status-schema.json")
SUPPORTED_VERSIONS = {1, 2, 3}

# WIP 制限
MAX_PENDING_REVIEW = 10

# ── ハードコーディング Fallback（スキーマファイル読み込み失敗時のみ使用） ──
_FALLBACK_STATUSES = {"pending_review", "approved", "rejected", "converted", "merged", "deferred", "reverted"}
_FALLBACK_PHASES = {"pending", "scanning", "completed", "failed"}
_FALLBACK_CONDITIONAL_REQUIRED = {
    "converted": ["converted_to"],
    "rejected": ["rejection_reason"],
    "merged": ["merged_into"],
    "deferred": ["deferred_reason"],
    "reverted": ["reverted_from", "revert_reason"],
}
_FALLBACK_TRANSITIONS = {
    "pending_review": {"approved", "rejected", "merged", "deferred"},
    "approved": {"converted", "rejected"},
    "converted": {"reverted"},
    "rejected": {"pending_review"},
    "merged": set(),
    "deferred": {"pending_review", "rejected"},
    "reverted": {"pending_review"},
}


def _load_from_schema() -> tuple[set, set, dict, dict, list]:
    """
    scan-status-schema.json から SSOT 定義をランタイムで読み込みます。

    Returns:
        (statuses, phases, conditional_required, transitions, load_warnings)
        読み込み失敗時は fallback 値と警告メッセージを返します。
    """
    load_warnings = []

    if not SCHEMA_PATH.exists():
        load_warnings.append(f"スキーマファイルなし ({SCHEMA_PATH}), fallback を使用")
        return _FALLBACK_STATUSES, _FALLBACK_PHASES, _FALLBACK_CONDITIONAL_REQUIRED, _FALLBACK_TRANSITIONS, load_warnings

    try:
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        load_warnings.append(f"スキーマパース失敗 ({e}), fallback を使用")
        return _FALLBACK_STATUSES, _FALLBACK_PHASES, _FALLBACK_CONDITIONAL_REQUIRED, _FALLBACK_TRANSITIONS, load_warnings

    defs = schema.get("$defs", {})

    # 1. candidate_status enum
    statuses = set(defs.get("candidate_status", {}).get("enum", []))
    if not statuses:
        load_warnings.append("スキーマから candidate_status enum の抽出に失敗, fallback を使用")
        statuses = _FALLBACK_STATUSES

    # 2. scan_phase enum
    phases = set(defs.get("scan_phase", {}).get("enum", []))
    if not phases:
        load_warnings.append("スキーマから scan_phase enum の抽出に失敗, fallback を使用")
        phases = _FALLBACK_PHASES

    # 3. valid_transitions (標準 JSON Schema 形式: default オブジェクトから直接読み取り)
    transitions = {}
    vt_def = defs.get("valid_transitions", {})
    vt_default = vt_def.get("default", {})
    if vt_default:
        for status_key, next_list in vt_default.items():
            if isinstance(next_list, list):
                transitions[status_key] = set(next_list)
    if not transitions:
        load_warnings.append("スキーマから valid_transitions の抽出に失敗, fallback を使用")
        transitions = _FALLBACK_TRANSITIONS

    # 4. conditional_required (allOf 条件付き必須フィールド)
    conditional_required = {}
    candidates_schema = schema.get("properties", {}).get("candidates", {})
    items_allof = candidates_schema.get("items", {}).get("allOf", [])
    for rule in items_allof:
        if_clause = rule.get("if", {}).get("properties", {}).get("status", {})
        then_clause = rule.get("then", {})
        status_val = if_clause.get("const")
        required_fields = then_clause.get("required", [])
        if status_val and required_fields:
            conditional_required[status_val] = required_fields
    if not conditional_required:
        load_warnings.append("スキーマから conditional_required の抽出に失敗, fallback を使用")
        conditional_required = _FALLBACK_CONDITIONAL_REQUIRED

    return statuses, phases, conditional_required, transitions, load_warnings


# ── スキーマからランタイム読み込み（SSOT 準拠） ──
VALID_STATUSES, VALID_PHASES, CONDITIONAL_REQUIRED, VALID_TRANSITIONS, _SCHEMA_LOAD_WARNINGS = _load_from_schema()


def parse_iso_datetime(dt_str: str) -> datetime:
    """ISO 8601 形式の datetime 文字列をパースします。"""
    dt_str = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(dt_str)


def check_scan_status(fix: bool = False) -> dict:
    """
    scan-status.json を検証します。

    Returns:
        検証結果の辞書
    """
    errors = []
    warnings = list(_SCHEMA_LOAD_WARNINGS)  # スキーマ読み込み警告を含む
    fixes_applied = []

    # 1. ファイルの存在確認
    if not SCAN_STATUS_PATH.exists():
        return {"status": "error", "errors": ["scan-status.json ファイルが見つかりません"], "warnings": [], "fixes": []}

    # 2. JSONパース（原本保持: --fix バックアップ用）
    try:
        with open(SCAN_STATUS_PATH, encoding="utf-8") as f:
            raw_content = f.read()
        data = json.loads(raw_content)
    except json.JSONDecodeError as e:
        return {"status": "error", "errors": [f"JSONパース失敗: {e}"], "warnings": [], "fixes": []}

    # 3. schema_version の確認
    version = data.get("schema_version")
    if version not in SUPPORTED_VERSIONS:
        errors.append(f"schema_version が無効です: {version} (サポート: {SUPPORTED_VERSIONS})")

    # 4. 必須トップレベルフィールドの確認
    for field in ["schema_version", "scans", "candidates"]:
        if field not in data:
            errors.append(f"必須フィールドが欠落: {field}")

    if "scans" not in data or "candidates" not in data:
        return {"status": "error", "errors": errors, "warnings": warnings, "fixes": fixes_applied}

    # 5. scans の検証
    valid_scan_ids = set()
    for i, scan in enumerate(data.get("scans", [])):
        scan_id = scan.get("scan_id", f"<index:{i}>")
        valid_scan_ids.add(scan_id)
        for field in ["scan_id", "phase", "created_at"]:
            if field not in scan:
                errors.append(f"scan[{scan_id}]: 必須フィールドが欠落 - {field}")
        phase = scan.get("phase")
        if phase and phase not in VALID_PHASES:
            errors.append(f"scan[{scan_id}]: 無効な phase - {phase}")
        if phase == "completed":
            for field in ["completed_at", "scanned_docs_count"]:
                if field not in scan:
                    warnings.append(f"scan[{scan_id}]: completed 状態だが {field} が欠落")

    # 6. candidates の検証
    candidate_ids = []
    pending_review_count = 0

    for i, candidate in enumerate(data.get("candidates", [])):
        cid = candidate.get("candidate_id", f"<index:{i}>")
        candidate_ids.append(cid)

        # 必須フィールド
        for field in ["candidate_id", "name", "status", "scan_id", "created_at"]:
            if field not in candidate:
                errors.append(f"candidate[{cid}]: 必須フィールドが欠落 - {field}")

        # scan_id 参照整合性: candidate.scan_id が scans[] に存在するか確認
        candidate_scan_id = candidate.get("scan_id")
        if candidate_scan_id and candidate_scan_id not in valid_scan_ids:
            warnings.append(f"candidate[{cid}]: scan_id '{candidate_scan_id}' が scans 配列に存在しません")

        # 有効な status
        status = candidate.get("status")
        if status and status not in VALID_STATUSES:
            errors.append(f"candidate[{cid}]: 無効な status - {status}")

        # WIP カウント
        if status == "pending_review":
            pending_review_count += 1

        # 条件付き必須フィールド（明示的な None/空文字列チェックで 0, False の誤検出を防止）
        if status in CONDITIONAL_REQUIRED:
            for field in CONDITIONAL_REQUIRED[status]:
                val = candidate.get(field)
                if val is None or val == "":
                    errors.append(f"candidate[{cid}]: {status} 状態では {field} が必須")

        # ── [v3 新規ルール 3] ice_score 範囲検証 (0-10) ──
        ice_score = candidate.get("ice_score")
        if ice_score is not None:
            if not isinstance(ice_score, (int, float)) or ice_score < 0 or ice_score > 10:
                errors.append(f"candidate[{cid}]: ice_score 範囲超過 - {ice_score} (有効: 0-10)")

        # ── [v3 新規ルール 4] japan_fit 範囲検証 (0-10) ──
        japan_fit = candidate.get("japan_fit")
        if japan_fit is not None:
            if not isinstance(japan_fit, (int, float)) or japan_fit < 0 or japan_fit > 10:
                errors.append(f"candidate[{cid}]: japan_fit 範囲超過 - {japan_fit} (有効: 0-10)")

        # ── [v3 新規ルール 6] source_docs ファイル存在検証 ──
        source_docs = candidate.get("source_docs", [])
        if isinstance(source_docs, list):
            for doc_name in source_docs:
                if isinstance(doc_name, str) and doc_name:
                    doc_full_path = Path(f"docs/research/{doc_name}")
                    if not doc_full_path.exists():
                        warnings.append(f"candidate[{cid}]: source_docs '{doc_name}' ファイルが存在しません")

        # ── [v3 新規ルール 7] doc_path ファイル存在検証 ──
        doc_path = candidate.get("doc_path")
        if doc_path and isinstance(doc_path, str):
            if not Path(doc_path).exists():
                errors.append(f"candidate[{cid}]: doc_path '{doc_path}' ファイルが存在しません")

        # history 配列の検証 (v2+ 専用)
        if version and version >= 2:
            if "history" not in candidate:
                warnings.append(f"candidate[{cid}]: v{version} だが history 配列がありません")
                if fix:
                    candidate["history"] = []
                    fixes_applied.append(f"candidate[{cid}]: history 配列を追加")
            else:
                history = candidate["history"]
                if not isinstance(history, list):
                    errors.append(f"candidate[{cid}]: history が配列ではありません")
                else:
                    # 時系列ソートおよびチェーン連続性の確認
                    prev_time = None
                    prev_to_status = None
                    for j, entry in enumerate(history):
                        # from_status は history[0] でのみ null を許可
                        from_st = entry.get("from_status")
                        to_st = entry.get("to_status")

                        # 必須フィールドの検証（from_status は null 許可のため別途処理）
                        for field in ["at", "to_status", "triggered_by"]:
                            if field not in entry:
                                errors.append(f"candidate[{cid}].history[{j}]: 必須フィールドが欠落 - {field}")

                        if "from_status" not in entry:
                            errors.append(f"candidate[{cid}].history[{j}]: 必須フィールドが欠落 - from_status")

                        # ── [v3 新規ルール 1] from_status: null は history[0] でのみ許可 ──
                        if from_st is None and j > 0:
                            errors.append(
                                f"candidate[{cid}].history[{j}]: from_status が null — "
                                f"null は history[0]（初期生成）でのみ許可"
                            )

                        # ── [v3 新規ルール 2] history[0].to_status は必ず pending_review ──
                        if j == 0 and to_st and to_st != "pending_review":
                            warnings.append(
                                f"candidate[{cid}].history[0]: to_status が '{to_st}' — "
                                f"初期生成は pending_review であるべき"
                            )

                        # 遷移有効性の検査
                        if from_st is not None and to_st:
                            if from_st not in VALID_STATUSES:
                                errors.append(f"candidate[{cid}].history[{j}]: 無効な from_status - {from_st}")
                            if to_st not in VALID_STATUSES:
                                errors.append(f"candidate[{cid}].history[{j}]: 無効な to_status - {to_st}")
                            if from_st in VALID_TRANSITIONS and to_st not in VALID_TRANSITIONS.get(from_st, set()):
                                warnings.append(f"candidate[{cid}].history[{j}]: 許可されない遷移 {from_st} → {to_st}")
                        elif from_st is None and to_st:
                            # from_status が null の場合（初期生成） — to_status のみ検証
                            if to_st not in VALID_STATUSES:
                                errors.append(f"candidate[{cid}].history[{j}]: 無効な to_status - {to_st}")

                        # チェーン連続性の検証: history[i].to_status == history[i+1].from_status
                        if prev_to_status is not None and from_st is not None:
                            if prev_to_status != from_st:
                                errors.append(
                                    f"candidate[{cid}].history[{j}]: チェーン断絶 — "
                                    f"前回の to_status({prev_to_status}) ≠ 今回の from_status({from_st})"
                                )
                        prev_to_status = to_st

                        # 時系列の検証
                        at_str = entry.get("at")
                        if at_str:
                            try:
                                at_time = parse_iso_datetime(at_str)
                                if prev_time and at_time < prev_time:
                                    warnings.append(f"candidate[{cid}].history[{j}]: 時系列違反（前回: {prev_time}, 今回: {at_time}）")
                                prev_time = at_time
                            except ValueError:
                                errors.append(f"candidate[{cid}].history[{j}]: at の日付形式エラー - {at_str}")

                    # history の最終状態と candidate.status の一貫性検証
                    if len(history) > 0:
                        last_entry = history[-1]
                        last_to = last_entry.get("to_status")
                        if last_to and last_to != status:
                            errors.append(
                                f"candidate[{cid}]: history の最終状態({last_to})と "
                                f"candidate status({status}) が不一致 — "
                                f"Safe Write 中の status 更新漏れの可能性"
                            )

    # 7. candidate_id の一意性
    seen = set()
    for cid in candidate_ids:
        if cid in seen:
            errors.append(f"candidate_id 重複: {cid}")
        seen.add(cid)

    # ── [v3 新規ルール 5] WIP 制限: pending_review > 10 で警告 ──
    if pending_review_count > MAX_PENDING_REVIEW:
        warnings.append(
            f"⚠️ pending_review {pending_review_count}件 (制限: {MAX_PENDING_REVIEW}). "
            f"--triage で整理してください。"
        )

    # fix モード: 変更を保存（原本 raw_content でバックアップ → TOCTOU 防止）
    if fix and fixes_applied:
        backup_path = SCAN_STATUS_PATH.with_suffix(".json.check-bak")
        backup_path.write_text(raw_content, encoding="utf-8")
        with open(SCAN_STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

    # 8. ステータス別カウント集計（main() での二重読み取り防止）
    status_counts = {}
    for c in data.get("candidates", []):
        st = c.get("status", "unknown")
        status_counts[st] = status_counts.get(st, 0) + 1

    return {
        "status": "error" if errors else ("warning" if warnings else "ok"),
        "errors": errors,
        "warnings": warnings,
        "fixes": fixes_applied,
        "summary": {
            "schema_version": version,
            "total_scans": len(data.get("scans", [])),
            "total_candidates": len(data.get("candidates", [])),
            "status_counts": status_counts,
            "pending_review_count": pending_review_count,
            "wip_limit": MAX_PENDING_REVIEW,
            "ssot_source": "schema" if not _SCHEMA_LOAD_WARNINGS else "fallback",
        }
    }


def main():
    parser = argparse.ArgumentParser(description="scan-status.json 整合性検証")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    parser.add_argument("--fix", action="store_true", help="自動修復を試行")
    args = parser.parse_args()

    result = check_scan_status(fix=args.fix)

    if args.json:
        result["checked_at"] = datetime.now(timezone.utc).isoformat()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        summary = result["summary"]
        ssot = summary.get("ssot_source", "unknown")
        ssot_label = "📋 スキーマ SSOT" if ssot == "schema" else "⚠️ fallback"
        print(f"\n🔍 scan-status.json 検証 (v{summary.get('schema_version', '?')}, {ssot_label})")
        print(f"   scans: {summary.get('total_scans', 0)}件, candidates: {summary.get('total_candidates', 0)}件")

        counts = summary.get("status_counts", {})
        if counts:
            parts = [f"{k}: {v}" for k, v in sorted(counts.items())]
            print(f"   ステータス分布: {', '.join(parts)}")

        # WIP 状態の表示
        pr_count = summary.get("pending_review_count", 0)
        wip_limit = summary.get("wip_limit", MAX_PENDING_REVIEW)
        wip_icon = "🟢" if pr_count <= wip_limit else "🔴"
        print(f"   WIP: {wip_icon} pending_review {pr_count}/{wip_limit}")

        if result["errors"]:
            print(f"\n❌ エラー {len(result['errors'])}件:")
            for e in result["errors"]:
                print(f"   • {e}")

        if result["warnings"]:
            print(f"\n⚠️  警告 {len(result['warnings'])}件:")
            for w in result["warnings"]:
                print(f"   • {w}")

        if result["fixes"]:
            print(f"\n🔧 修正 {len(result['fixes'])}件:")
            for fix_item in result["fixes"]:
                print(f"   • {fix_item}")

        if not result["errors"] and not result["warnings"]:
            print("\n✅ すべての検証に合格")
        print()

    # Exit code
    if result["errors"]:
        sys.exit(1)
    elif result["warnings"]:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
