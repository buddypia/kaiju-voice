#!/usr/bin/env python3
"""
check_pipeline_golden.py - パイプラインデータ整合性ゴールデンテスト

Market Intelligence → Feature Architect パイプラインの成果物が
scan-status.jsonと一致するかを交差検証します。

Exit Codes:
  0 - すべての検証に合格
  1 - エラー発生（ファイルなし、JSONパース失敗など）
  2 - 整合性違反を検出（警告）

Usage:
  python check_pipeline_golden.py [--json] [--verbose]

Options:
  --json     JSON形式で出力
  --verbose  詳細な検証ログを出力
"""

import json
import sys
import argparse
import re
from datetime import datetime, timezone
from pathlib import Path


SCAN_STATUS_PATH = Path(".claude/skills/market-intelligence-scanner/assets/scan-status.json")
FEATURES_DIR = Path("docs/features")
CANDIDATES_DIR = Path("docs/features/candidates/market")


def check_pipeline_golden(verbose: bool = False) -> dict:
    """
    パイプラインデータの整合性を検証します。

    Returns:
        検証結果の辞書
    """
    errors = []
    warnings = []
    info = []

    # 1. scan-status.json の存在確認
    if not SCAN_STATUS_PATH.exists():
        return {"status": "error", "errors": ["scan-status.json ファイルが見つかりません"], "warnings": [], "info": []}

    try:
        with open(SCAN_STATUS_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {"status": "error", "errors": [f"JSONパース失敗: {e}"], "warnings": [], "info": []}

    candidates = data.get("candidates", [])

    # 2. converted 候補の検証
    converted_count = 0
    for candidate in candidates:
        cid = candidate.get("candidate_id", "unknown")
        status = candidate.get("status")

        if status == "converted":
            converted_count += 1
            converted_to = candidate.get("converted_to")

            if not converted_to:
                errors.append(f"candidate[{cid}]: converted 状態だが converted_to がありません")
                continue

            # Feature ディレクトリの存在確認
            feature_dir = FEATURES_DIR / converted_to
            if not feature_dir.exists():
                errors.append(f"candidate[{cid}]: converted_to={converted_to} ディレクトリなし ({feature_dir})")
                continue

            if verbose:
                info.append(f"candidate[{cid}]: {converted_to} ディレクトリ存在 ✓")

            # BRIEF.md の存在確認
            brief_path = feature_dir / "BRIEF.md"
            if not brief_path.exists():
                errors.append(f"candidate[{cid}]: {converted_to}/BRIEF.md なし")
            elif verbose:
                info.append(f"candidate[{cid}]: {converted_to}/BRIEF.md 存在 ✓")

            # CONTEXT.json の存在確認
            context_path = feature_dir / "CONTEXT.json"
            if not context_path.exists():
                warnings.append(f"candidate[{cid}]: {converted_to}/CONTEXT.json なし")
            elif verbose:
                info.append(f"candidate[{cid}]: {converted_to}/CONTEXT.json 存在 ✓")

    # 3. merged 候補の検証
    merged_count = 0
    for candidate in candidates:
        cid = candidate.get("candidate_id", "unknown")
        status = candidate.get("status")

        if status == "merged":
            merged_count += 1
            merged_into = candidate.get("merged_into")

            if not merged_into:
                errors.append(f"candidate[{cid}]: merged 状態だが merged_into がありません")
                continue

            # merged_into Feature ディレクトリの存在確認
            feature_dir = FEATURES_DIR / merged_into
            if not feature_dir.exists():
                warnings.append(f"candidate[{cid}]: merged_into={merged_into} ディレクトリなし ({feature_dir})")
            elif verbose:
                info.append(f"candidate[{cid}]: merged_into={merged_into} ディレクトリ存在 ✓")

    # 4. ICE Score 交差検証 (scan-status.json vs 候補ドキュメント)
    ice_checked = 0
    for candidate in candidates:
        cid = candidate.get("candidate_id", "unknown")
        scan_ice = candidate.get("ice_score")

        if scan_ice is None:
            continue

        # 候補ドキュメントパス: doc_path フィールド優先、フォールバックとして candidate_id 基準で推定
        candidate_doc_path = None
        doc_path_val = candidate.get("doc_path")
        if doc_path_val:
            candidate_doc_path = Path(doc_path_val)

        if candidate_doc_path is None or not candidate_doc_path.exists():
            # フォールバック: ファイル名パターンで試行 (candidate_id 基準)
            possible_path = CANDIDATES_DIR / f"{cid}.md"
            if possible_path.exists():
                candidate_doc_path = possible_path

        if candidate_doc_path and candidate_doc_path.exists():
            try:
                content = candidate_doc_path.read_text(encoding="utf-8")
                # ICE Score 抽出: 3種類のドキュメント形式に対応
                # 1) "ICE Score: X.X" または "ICE 平均: X.X" (インライン)
                # 2) "| **総点** | 9.3 → **正規化 8.2** |" (正規化を含むテーブル)
                # 3) "| **総点** | **8.5** |" または "| **ICE Total** | **7.3** |" (テーブル)
                doc_ice = None
                m = re.search(r"ICE\s*(?:Score|平均)[*]*[:\s]*(\d+\.?\d*)", content)
                if m:
                    doc_ice = float(m.group(1))
                else:
                    m = re.search(r"正規化\s*\**\s*(\d+\.?\d+)", content)
                    if m:
                        doc_ice = float(m.group(1))
                    else:
                        m = re.search(r"(?:総点|ICE\s*Total)\**\s*\|\s*\**\s*(\d+\.?\d+)", content)
                        if m:
                            doc_ice = float(m.group(1))

                if doc_ice is not None:
                    try:
                        scan_ice_val = float(scan_ice)
                    except (ValueError, TypeError):
                        warnings.append(f"candidate[{cid}]: scan-status.json の ice_score 変換失敗 ({scan_ice!r})")
                        scan_ice_val = None
                    if scan_ice_val is not None:
                        ice_checked += 1
                        if abs(doc_ice - scan_ice_val) > 0.1:
                            warnings.append(
                                f"candidate[{cid}]: ICE Score 不一致 "
                                f"(scan-status: {scan_ice_val}, ドキュメント: {doc_ice}). "
                                f"scan-status.json が SSOT"
                            )
                        elif verbose:
                            info.append(f"candidate[{cid}]: ICE Score 一致 ({scan_ice_val}) ✓")
            except IOError:
                pass  # ファイル読み取り失敗は無視

    # 5. 双方向参照検証: BRIEF.md → 候補ドキュメントの存在
    brief_checked = 0
    for candidate in candidates:
        cid = candidate.get("candidate_id", "unknown")
        status = candidate.get("status")
        converted_to = candidate.get("converted_to")

        if status == "converted" and converted_to:
            brief_path = FEATURES_DIR / converted_to / "BRIEF.md"
            if brief_path.exists():
                brief_checked += 1
                try:
                    brief_content = brief_path.read_text(encoding="utf-8")
                    # Source セクションで元の候補ドキュメント参照を確認
                    if "candidates/market/" in brief_content:
                        # 参照されたファイルが実際に存在するか確認
                        ref_match = re.search(r"\(.*?(candidates/market/[^)]+\.md)\)", brief_content)
                        if ref_match:
                            ref_path = CANDIDATES_DIR / Path(ref_match.group(1)).name
                            if not ref_path.exists():
                                warnings.append(
                                    f"candidate[{cid}]: BRIEF.md で参照している "
                                    f"候補ドキュメントなし ({ref_match.group(1)})"
                                )
                            elif verbose:
                                info.append(f"candidate[{cid}]: BRIEF → 候補ドキュメント逆参照 ✓")
                    elif verbose:
                        info.append(f"candidate[{cid}]: BRIEF.md に Source 参照なし（候補入力モードでない場合は正常）")
                except IOError:
                    pass

    # 6. reverted 候補の検証（追加セーフティネット）
    reverted_count = 0
    for candidate in candidates:
        cid = candidate.get("candidate_id", "unknown")
        status = candidate.get("status")

        if status == "reverted":
            reverted_count += 1
            converted_to = candidate.get("converted_to")

            if converted_to:
                feature_dir = FEATURES_DIR / converted_to
                if feature_dir.exists():
                    warnings.append(
                        f"candidate[{cid}]: reverted 状態だが {converted_to} "
                        f"ディレクトリがまだ存在しています（手動クリーンアップが必要）"
                    )

    return {
        "status": "error" if errors else ("warning" if warnings else "ok"),
        "errors": errors,
        "warnings": warnings,
        "info": info if verbose else [],
        "summary": {
            "total_candidates": len(candidates),
            "converted": converted_count,
            "merged": merged_count,
            "reverted": reverted_count,
            "ice_cross_checked": ice_checked,
            "brief_back_referenced": brief_checked,
        }
    }


def main():
    parser = argparse.ArgumentParser(description="パイプラインデータ整合性ゴールデンテスト")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    parser.add_argument("--verbose", action="store_true", help="詳細な検証ログを出力")
    args = parser.parse_args()

    result = check_pipeline_golden(verbose=args.verbose)

    if args.json:
        result["checked_at"] = datetime.now(timezone.utc).isoformat()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        summary = result["summary"]
        print(f"\n🔍 パイプラインゴールデンテスト")
        print(f"   candidates: {summary['total_candidates']}件")
        print(f"   converted: {summary['converted']}件, merged: {summary['merged']}件, reverted: {summary['reverted']}件")
        print(f"   ICE 交差検証: {summary['ice_cross_checked']}件, BRIEF 逆参照: {summary['brief_back_referenced']}件")

        if result.get("info"):
            print(f"\nℹ️  詳細 ({len(result['info'])}件):")
            for i in result["info"]:
                print(f"   • {i}")

        if result["errors"]:
            print(f"\n❌ エラー {len(result['errors'])}件:")
            for e in result["errors"]:
                print(f"   • {e}")

        if result["warnings"]:
            print(f"\n⚠️  警告 {len(result['warnings'])}件:")
            for w in result["warnings"]:
                print(f"   • {w}")

        if not result["errors"] and not result["warnings"]:
            print("\n✅ すべての整合性検証に合格")
        print()

    # Exit code
    if result["errors"]:
        sys.exit(1)
    elif result["warnings"]:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
