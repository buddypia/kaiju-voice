#!/usr/bin/env python3
"""
brief_regenerator.py — BRIEF.mdをTemplate v2.0形式で再生成する。

auto-migratedされたBRIEF（### Core Goal サブセクション形式）をインライン形式（- **Core Goal**: text）に変換し、
欠落セクションはCONTEXT.jsonから抽出して補完する。

Usage:
    python3 brief_regenerator.py                # dry-run（全体）
    python3 brief_regenerator.py --apply        # 全体適用
    python3 brief_regenerator.py --feature 001  # 特定Featureのみ
    python3 brief_regenerator.py --verbose       # 詳細出力
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ── Project Root ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURES_DIR = PROJECT_ROOT / "docs" / "features"
EXCLUDE_DIRS = {"_templates", "candidates", "priority"}

# ── Template v2.0 §0-§7 ──────────────────────────────────────────────────
TEMPLATE_SECTIONS = [
    "0. Original Request",
    "1. Problem & Why",
    "2. User Stories",
    "3. User Journey",
    "4. Acceptance Criteria",
    "5. Scope Boundaries",
    "6. Constraints",
    "7. Business Metrics",
]


def detect_brief_format(brief_text: str) -> str:
    """BRIEF.mdの形式を検出する。"""
    if "- **Core Goal**:" in brief_text:
        return "v2.0"
    if "[auto-migrated]" in brief_text or "### Core Goal" in brief_text:
        return "auto-migrated"
    if brief_text.startswith("#") and "## 0." in brief_text:
        return "candidate-derived"
    return "legacy"


def _load_context(feature_dir: Path) -> dict | None:
    """CONTEXT.jsonを読み込む。"""
    ctx_path = feature_dir / "CONTEXT.json"
    if not ctx_path.exists():
        return None
    try:
        with ctx_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _parse_sections(text: str) -> dict[str, str]:
    """BRIEF.mdを## N. セクション名 を基準にパースする。"""
    sections: dict[str, str] = {}
    # ## 0. ~ ## 9. 形式のセクションヘッダーにマッチ
    pattern = re.compile(r"^## (\d+\.\s+.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        key = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        # セクション間の区切り線(---)を除去
        body = re.sub(r"\n---\s*$", "", body).strip()
        sections[key] = body
    return sections


def _extract_header(text: str) -> str:
    """§0より前のヘッダー部分（# Feature Brief: ... ~ 最初の ---）を抽出する。"""
    # ## 0. より前のすべてのテキスト
    match = re.search(r"^## 0\.", text, re.MULTILINE)
    if match:
        return text[: match.start()].rstrip()
    return ""


def _convert_subsection_to_inline(section_body: str) -> str:
    """### Core Goal / ### User Value / ### Business Metric(s) 形式を
    - **Core Goal**: text インライン形式に変換する。"""
    lines = section_body.split("\n")
    result_parts: dict[str, str] = {}
    current_key = None
    current_lines: list[str] = []
    preamble_lines: list[str] = []  # サブヘッディング前のテキスト

    for line in lines:
        sub_match = re.match(r"^###\s+(.+)$", line)
        if sub_match:
            if current_key:
                result_parts[current_key] = "\n".join(current_lines).strip()
            current_key = sub_match.group(1).strip()
            current_lines = []
        elif current_key:
            current_lines.append(line)
        else:
            preamble_lines.append(line)

    if current_key:
        result_parts[current_key] = "\n".join(current_lines).strip()

    # マッピング: ### Key → - **Key**: value
    output_lines: list[str] = []

    # Core Goal
    core_goal_keys = ["Core Goal"]
    for k in core_goal_keys:
        if k in result_parts:
            val = _clean_value(result_parts[k])
            output_lines.append(f"- **Core Goal**: {val}")
            break

    # User Value
    user_value_keys = ["User Value", "Value"]
    for k in user_value_keys:
        if k in result_parts:
            val = _clean_value(result_parts[k])
            output_lines.append(f"- **User Value**: {val}")
            break

    # Business Metric
    biz_keys = ["Business Metric", "Business Metrics"]
    for k in biz_keys:
        if k in result_parts:
            val = _clean_value(result_parts[k])
            output_lines.append(f"- **Business Metric**: {val}")
            break

    if output_lines:
        return "\n".join(output_lines)

    # サブヘッディングがない場合は原文を返す
    return section_body


def _clean_value(text: str) -> str:
    """複数行テキストから核心的な値を抽出する。

    - ボールド(**...**）、引用("...")のラッピングを除去
    - コードブロック(```)を除去
    - リスト項目(- ...)はセミコロンで結合
    - 複数行の説明は最初の意味のある行（段落）のみ抽出
    """
    text = text.strip()

    # コードブロックを除去
    text = re.sub(r"```[\s\S]*?```", "", text).strip()

    # ボールド+引用のラッピングを除去
    if text.startswith("**") and "**" in text[2:]:
        # **"..."** または **text** から最初の行のみ抽出
        end_idx = text.index("**", 2)
        inner = text[2:end_idx].strip().strip('"').strip()
        # 残りのテキストがあれば最初の行に結合
        rest = text[end_idx + 2 :].strip()
        if rest:
            # 残りが説明であればカンマで連結
            first_rest_line = rest.split("\n")[0].strip()
            if first_rest_line and not first_rest_line.startswith("-"):
                text = f"{inner}. {first_rest_line}"
            else:
                text = inner
        else:
            text = inner

    # "..." のラッピングを除去
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()

    # 複数行の処理
    if "\n" in text:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        # すべてリスト項目(- ...)であればセミコロンで結合
        if all(l.startswith("- ") for l in lines):
            return "; ".join(l[2:] for l in lines)
        # 混在の場合は最初の意味のある行を返す
        return lines[0] if lines else text

    return text


def _build_section1_from_context(ctx: dict) -> str | None:
    """CONTEXT.jsonから§1 Problem & Why の内容を抽出する。"""
    parts: list[str] = []
    bc = ctx.get("brief_context", {})
    why = ctx.get("why", "")

    core_goal = bc.get("core_goal", "") or why
    user_value = bc.get("user_value", "")
    biz_metrics = bc.get("business_metrics", [])

    if core_goal:
        parts.append(f"- **Core Goal**: {core_goal}")
    else:
        parts.append("- **Core Goal**: [TBD]")

    if user_value:
        parts.append(f"- **User Value**: {user_value}")
    else:
        parts.append("- **User Value**: [TBD]")

    if biz_metrics:
        if isinstance(biz_metrics, list):
            parts.append(f"- **Business Metric**: {'; '.join(biz_metrics)}")
        else:
            parts.append(f"- **Business Metric**: {biz_metrics}")
    else:
        parts.append("- **Business Metric**: [TBD]")

    return "\n".join(parts)


def _build_section2_from_context(ctx: dict) -> str | None:
    """CONTEXT.jsonから§2 User Stories の内容を抽出する。"""
    bc = ctx.get("brief_context", {})
    story = bc.get("user_story", "")
    if story:
        return f"- {story}"
    return None


def _build_section6_from_context(ctx: dict) -> str | None:
    """CONTEXT.jsonから§6 Constraints の内容を抽出する。"""
    constraints = ctx.get("constraints", [])
    if constraints:
        return "\n".join(f"- {c}" for c in constraints)
    return None


def _build_section7_from_context(ctx: dict) -> str | None:
    """CONTEXT.jsonから§7 Business Metrics の内容を抽出する。"""
    bc = ctx.get("brief_context", {})
    biz_metrics = bc.get("business_metrics", [])
    success = ctx.get("success_criteria", [])

    items = biz_metrics or success
    if items:
        if isinstance(items, list):
            return "\n".join(f"- {item}" for item in items if item)
        return f"- {items}"
    return None


def _semantic_match(section_key: str, target: str) -> bool:
    """セクションキーがtargetの意味とマッチするか検査する。番号に依存せず、タイトルキーワードに基づく。"""
    key_lower = section_key.lower()
    matchers = {
        "original_request": ["original request"],
        "problem_why": ["problem", "why", "value", "goal"],
        "user_stories": ["user stor", "user story"],
        "user_journey": ["user journey", "journey"],
        "acceptance": ["acceptance", "criteria", "bdd"],
        "scope": ["scope", "boundaries"],
        "constraints": ["constraint"],
        "metrics": ["metric", "success contract", "success criteria", "kpi"],
    }
    keywords = matchers.get(target, [])
    return any(kw in key_lower for kw in keywords)


def _find_semantic_section(
    sections: dict[str, str], target: str, claimed: set[str] | None = None
) -> str | None:
    """意味ベースでセクションを検索する。既に他のtargetに割り当てられたキーは除外する。"""
    if claimed is None:
        claimed = set()

    # 1次: 意味マッチング（claimed除外）
    for key in sections:
        if key not in claimed and _semantic_match(key, target):
            return key

    # 2次: 番号ベースのフォールバック（claimed除外、v2.0標準番号のみ）
    prefix_map = {
        "original_request": "0.",
        "problem_why": "1.",
        "user_stories": "2.",
        "user_journey": "3.",
        "acceptance": "4.",
        "scope": "5.",
        "constraints": "6.",
        "metrics": "7.",
    }
    prefix = prefix_map.get(target, "")
    if prefix:
        for key in sections:
            if key not in claimed and key.startswith(prefix):
                # 番号フォールバック時の意味衝突検査: このキーが他のtargetに意味マッチする場合はスキップ
                has_other_match = False
                for other_target in prefix_map:
                    if other_target != target and _semantic_match(key, other_target):
                        has_other_match = True
                        break
                if not has_other_match:
                    return key
    return None


def regenerate_brief(feature_dir: Path, apply: bool, verbose: bool) -> dict:
    """単一FeatureのBRIEF.mdを再生成する。

    Returns:
        dict with keys: feature_id, current_format, action, sections_updated
    """
    feature_id = feature_dir.name
    brief_path = feature_dir / "BRIEF.md"
    result = {
        "feature_id": feature_id,
        "current_format": "missing",
        "action": "skip",
        "sections_updated": [],
    }

    # Lifecycleフィルター: Archived/Failed FeatureはBRIEF再生成の対象外
    from feature_lifecycle import load_context, is_active
    ctx = load_context(feature_dir)
    if ctx and not is_active(ctx):
        result["action"] = "skipped_inactive"
        return result

    if not brief_path.exists():
        result["action"] = "skip (no BRIEF.md)"
        return result

    text = brief_path.read_text(encoding="utf-8")
    fmt = detect_brief_format(text)
    result["current_format"] = fmt

    # v2.0形式ならスキップ
    if fmt == "v2.0":
        result["action"] = "skip"
        if verbose:
            print(f"  [SKIP] {feature_id}: already v2.0")
        return result

    ctx = _load_context(feature_dir)
    sections = _parse_sections(text)
    header = _extract_header(text)
    updated_sections: list[str] = []
    new_sections: dict[str, str] = {}
    claimed: set[str] = set()  # 既に割り当て済みのセクションキーを追跡

    def _claim(key: str | None) -> str | None:
        if key:
            claimed.add(key)
        return key

    # §0 Original Request — NEVER modify
    s0_key = _claim(_find_semantic_section(sections, "original_request", claimed))
    if s0_key:
        new_sections["0. Original Request"] = sections[s0_key]

    # §1 Problem & Why — ### サブセクションをインラインに変換
    s1_key = _claim(_find_semantic_section(sections, "problem_why", claimed))
    if s1_key:
        original_body = sections[s1_key]
        if "### Core Goal" in original_body or "### User Value" in original_body:
            converted = _convert_subsection_to_inline(original_body)
            new_sections["1. Problem & Why"] = converted
            updated_sections.append("§1")
        elif "- **Core Goal**:" in original_body:
            new_sections["1. Problem & Why"] = original_body
        else:
            if ctx:
                from_ctx = _build_section1_from_context(ctx)
                if from_ctx:
                    new_sections["1. Problem & Why"] = from_ctx
                    updated_sections.append("§1")
                else:
                    new_sections["1. Problem & Why"] = original_body
            else:
                new_sections["1. Problem & Why"] = original_body
    elif ctx:
        from_ctx = _build_section1_from_context(ctx)
        new_sections["1. Problem & Why"] = from_ctx or "- **Core Goal**: [TBD]\n- **User Value**: [TBD]\n- **Business Metric**: [TBD]"
        updated_sections.append("§1")

    # §2 User Stories
    s2_key = _claim(_find_semantic_section(sections, "user_stories", claimed))
    if s2_key:
        new_sections["2. User Stories"] = sections[s2_key]
    elif ctx:
        from_ctx = _build_section2_from_context(ctx)
        new_sections["2. User Stories"] = from_ctx or "[TBD]"
        if from_ctx:
            updated_sections.append("§2")
    else:
        new_sections["2. User Stories"] = "[TBD]"

    # §3 User Journey
    s3_key = _claim(_find_semantic_section(sections, "user_journey", claimed))
    if s3_key:
        new_sections["3. User Journey"] = sections[s3_key]
    else:
        new_sections["3. User Journey"] = "[TBD]"

    # §4 Acceptance Criteria
    s4_key = _claim(_find_semantic_section(sections, "acceptance", claimed))
    if s4_key:
        new_sections["4. Acceptance Criteria"] = sections[s4_key]
    else:
        new_sections["4. Acceptance Criteria"] = "[TBD]"

    # §5 Scope Boundaries
    s5_key = _claim(_find_semantic_section(sections, "scope", claimed))
    if s5_key:
        new_sections["5. Scope Boundaries"] = sections[s5_key]
    else:
        new_sections["5. Scope Boundaries"] = "[TBD]"

    # §6 Constraints
    s6_key = _claim(_find_semantic_section(sections, "constraints", claimed))
    if s6_key:
        new_sections["6. Constraints"] = sections[s6_key]
    elif ctx:
        from_ctx = _build_section6_from_context(ctx)
        new_sections["6. Constraints"] = from_ctx or "[TBD]"
        if from_ctx:
            updated_sections.append("§6")

    # §7 Business Metrics
    s7_key = _claim(_find_semantic_section(sections, "metrics", claimed))
    if s7_key:
        new_sections["7. Business Metrics"] = sections[s7_key]
    elif ctx:
        from_ctx = _build_section7_from_context(ctx)
        new_sections["7. Business Metrics"] = from_ctx or "[TBD]"
        if from_ctx:
            updated_sections.append("§7")

    # 変換するものがなければスキップ（auto-migratedだが### Core Goalがない場合など）
    if not updated_sections and fmt not in ("auto-migrated", "legacy"):
        result["action"] = "skip (no changes needed)"
        if verbose:
            print(f"  [SKIP] {feature_id}: no changes needed ({fmt})")
        return result

    # 再構成
    brief_lines: list[str] = []

    # ヘッダーを保持（# Feature Brief: ... など）
    if header:
        # ヘッダー末尾の重複 --- を除去
        clean_header = header.rstrip()
        while clean_header.endswith("\n---"):
            clean_header = clean_header[:-4].rstrip()
        if clean_header.endswith("---"):
            clean_header = clean_header[:-3].rstrip()
        brief_lines.append(clean_header)
        brief_lines.append("")

    for section_name in TEMPLATE_SECTIONS:
        brief_lines.append("---")
        brief_lines.append("")
        brief_lines.append(f"## {section_name}")
        brief_lines.append("")
        body = new_sections.get(section_name, "[TBD]")
        brief_lines.append(body)
        brief_lines.append("")

    new_text = "\n".join(brief_lines).rstrip() + "\n"

    if apply:
        brief_path.write_text(new_text, encoding="utf-8")
        # CONTEXT.json の artifacts.brief_format_version も v2.0 に更新
        ctx_path = feature_dir / "CONTEXT.json"
        if ctx_path.exists():
            try:
                ctx_data = json.loads(ctx_path.read_text(encoding="utf-8"))
                if "artifacts" in ctx_data:
                    ctx_data["artifacts"]["brief_format_version"] = "v2.0"
                    ctx_path.write_text(
                        json.dumps(ctx_data, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
            except (json.JSONDecodeError, KeyError):
                pass  # CONTEXT.json破損時は無視（BRIEF再生成が主目的）
        result["action"] = "regenerate"
    else:
        result["action"] = "regenerate (dry-run)"

    result["sections_updated"] = updated_sections

    if verbose:
        action_label = "APPLY" if apply else "DRY-RUN"
        print(f"  [{action_label}] {feature_id}: {fmt} → v2.0, updated: {', '.join(updated_sections) or 'structure only'}")

    return result


def _find_section_key(sections: dict[str, str], prefix: str) -> str | None:
    """sectionsのdictからprefixで始まるキーを検索する。"""
    for key in sections:
        if key.startswith(prefix):
            return key
    return None


def _discover_features(feature_filter: str | None) -> list[Path]:
    """Featureディレクトリを探索する。"""
    if not FEATURES_DIR.exists():
        return []

    dirs = sorted(
        d
        for d in FEATURES_DIR.iterdir()
        if d.is_dir() and d.name not in EXCLUDE_DIRS and re.match(r"\d{3}-", d.name)
    )

    if feature_filter:
        dirs = [d for d in dirs if d.name.startswith(feature_filter)]

    return dirs


def main() -> None:
    parser = argparse.ArgumentParser(description="BRIEF.md Template v2.0 再生成")
    parser.add_argument("--apply", action="store_true", help="実際のファイルに適用")
    parser.add_argument("--feature", type=str, help="特定のFeature ID（例: 001）")
    parser.add_argument("--verbose", action="store_true", help="詳細出力")
    args = parser.parse_args()

    feature_filter = args.feature
    if feature_filter and not feature_filter.endswith("-"):
        # "001" → "001-" にマッチさせる
        feature_filter = feature_filter if "-" in feature_filter else f"{feature_filter}-"

    dirs = _discover_features(feature_filter)
    if not dirs:
        print("対象のFeatureがありません。")
        sys.exit(0)

    results: list[dict] = []
    for d in dirs:
        r = regenerate_brief(d, apply=args.apply, verbose=args.verbose)
        results.append(r)

    # Summary table
    print()
    print(f"{'Feature':<40} {'Format':<18} {'Action':<28} {'Sections Updated'}")
    print("-" * 110)
    skip_count = 0
    regen_count = 0
    for r in results:
        sections_str = ", ".join(r["sections_updated"]) if r["sections_updated"] else "-"
        print(f"{r['feature_id']:<40} {r['current_format']:<18} {r['action']:<28} {sections_str}")
        if "skip" in r["action"]:
            skip_count += 1
        else:
            regen_count += 1

    print("-" * 110)
    mode_label = "APPLIED" if args.apply else "DRY-RUN"
    print(f"Total: {len(results)} | Regenerated: {regen_count} | Skipped: {skip_count} | Mode: {mode_label}")


if __name__ == "__main__":
    main()
