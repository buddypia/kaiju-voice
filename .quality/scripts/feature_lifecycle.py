#!/usr/bin/env python3
"""
feature_lifecycle.py — Feature ライフサイクル管理 共有ユーティリティ

すべてのパイプラインスクリプトが Archived/Failed 等の非アクティブ Feature を
一貫してフィルタリングするための Single Source of Truth.

Usage:
    from feature_lifecycle import load_context, is_active, get_lifecycle_state

    ctx = load_context(feature_dir)
    if ctx and not is_active(ctx):
        # Archived/Failed Feature → スキップ
        continue
"""

import json
from pathlib import Path
from typing import Optional

# 非アクティブなライフサイクル状態 (この状態の Feature はパイプライン処理対象から除外)
INACTIVE_STATES = frozenset({"Archived", "Failed"})


def load_context(feature_dir: Path) -> Optional[dict]:
    """Feature ディレクトリから CONTEXT.json をロードする。

    Args:
        feature_dir: Feature ディレクトリパス (例: docs/features/032-text-adventure-mode/)

    Returns:
        パース済み CONTEXT.json dict、または None (ファイルなし/パース失敗)
    """
    ctx_path = feature_dir / "CONTEXT.json"
    if not ctx_path.exists():
        return None
    try:
        with open(ctx_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def get_lifecycle_state(context: dict) -> str:
    """CONTEXT.json から現在のライフサイクル状態を抽出する。

    Args:
        context: パース済み CONTEXT.json dict

    Returns:
        current_state 文字列 (なければ "unknown")
    """
    return context.get("quick_resume", {}).get("current_state", "unknown")


def is_active(context: dict) -> bool:
    """Feature がアクティブなライフサイクル状態かどうかを確認する。

    Archived、Failed 状態の Feature は非アクティブと判定される。
    パイプラインスクリプトはこの関数で処理対象かどうかを決定する。

    Args:
        context: パース済み CONTEXT.json dict

    Returns:
        True = アクティブ (処理対象)、False = 非アクティブ (スキップ対象)
    """
    return get_lifecycle_state(context) not in INACTIVE_STATES


def get_archived_reason(context: dict) -> Optional[str]:
    """Archived Feature の理由を返す。

    Args:
        context: パース済み CONTEXT.json dict

    Returns:
        archived_reason 文字列 (なければ None)
    """
    return context.get("archived_reason")


def get_archived_ref(context: dict) -> Optional[str]:
    """Archived Feature の参照先(統合/置換された Feature ID)を返す。

    Args:
        context: パース済み CONTEXT.json dict

    Returns:
        archived_ref 文字列 (なければ None)
    """
    return context.get("archived_ref")
