#!/usr/bin/env python3
"""
Deep Research CLI v2.0 - Subcommand Architecture.

根本的欠陥解決:
- Bash タイムアウト(10分) vs リサーチ実行時間(最大60分) → start/poll 分離
- Crash recovery → State ファイルでセッション間状態共有
- 両 Provider background mode → ネットワーク切断時もサーバー側で継続実行

Subcommands:
    start   - バックグラウンドリサーチ開始 (即座に戻る)
    status  - リサーチ状態確認 (1回クエリ)
    poll    - 完了までポーリング (timeout 含む)
    result  - 完了したリサーチ結果取得
    list    - 全リサーチセッションリスト
    run     - レガシーモード (start + poll inline)

Usage:
    python deep_research.py start "query" --provider openai
    python deep_research.py poll dr-20260208-143022
    python deep_research.py status dr-20260208-143022
    python deep_research.py result dr-20260208-143022
    python deep_research.py list
    python deep_research.py run "query" --provider google
    python deep_research.py "query" --provider openai  # legacy (= run)
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
import unicodedata
import yaml
from collections import Counter
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional


# ============================================================
# パス定数
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
STATE_DIR = os.path.join(SKILL_DIR, "state")
LOG_DIR = os.path.join(SKILL_DIR, "logs")
CONFIG_PATH = os.path.join(SKILL_DIR, "config.yaml")

SUBCOMMANDS = {"start", "status", "poll", "result", "list", "run"}

os.makedirs(STATE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)


# ============================================================
# ロギング
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(LOG_DIR, f"deep_research_{datetime.now().strftime('%Y%m%d')}.log")
        ),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("deep_research")


# ============================================================
# Retry (指数バックオフ)
# ============================================================


def retry_with_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    errors_to_retry: tuple = (Exception,),
) -> Callable:
    """業界標準指数バックオフRetryデコレーター。"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            for attempt in range(max_retries + 1):
                try:
                    logger.info(f"[Attempt {attempt + 1}/{max_retries + 1}] {func.__name__}")
                    return func(*args, **kwargs)
                except errors_to_retry as e:
                    if attempt == max_retries:
                        logger.error(f"[Failed] {func.__name__} after {max_retries} retries: {e}")
                        raise
                    error_msg = str(e).lower()
                    retryable = any(
                        kw in error_msg
                        for kw in ["timeout", "connection", "rate limit", "429", "503", "500"]
                    )
                    if retryable:
                        logger.warning(f"[Retry {attempt + 1}] {func.__name__}: {e}. Wait {delay}s")
                        time.sleep(delay)
                        delay = min(delay * exponential_base, max_delay)
                    else:
                        logger.error(f"[Non-retryable] {func.__name__}: {e}")
                        raise

        return wrapper

    return decorator


# ============================================================
# エラーヒストリー
# ============================================================


class ErrorHistory:
    """エラーヒストリーをJSONで記録 (最新100件)。"""

    def __init__(self):
        self.log_file = os.path.join(LOG_DIR, "error_history.json")

    def log_error(self, provider: str, error_type: str, error_msg: str, query: str, context: Optional[dict] = None):
        history = []
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []

        history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "provider": provider,
                "error_type": error_type,
                "error_message": error_msg,
                "query": query,
                "context": context or {},
            }
        )
        history = history[-100:]

        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)


error_history = ErrorHistory()


# ============================================================
# Config & Smart Provider Selection
# ============================================================


class Config:
    """設定ファイルローダー。"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or CONFIG_PATH
        self.config = self._load()

    def _load(self) -> Dict:
        if not os.path.exists(self.config_path):
            return self._defaults()
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or self._defaults()
        except Exception:
            return self._defaults()

    @staticmethod
    def _defaults() -> Dict:
        return {
            "strategy": {"mode": "auto"},
            "keyword_rules": {
                "openai": ["深層", "分析", "研究", "レポート"],
                "google": ["最新", "トレンド", "市場", "速い"],
            },
            "defaults": {"provider": "openai", "enable_fallback": False},
            "polling": {
                "openai": {"interval": 15, "max_iterations": 120},
                "google": {"interval": 30, "max_iterations": 60},
            },
        }

    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value if value is not None else default


class UsagePatternLearner:
    """使用パターン学習および推奨。"""

    def __init__(self, data_file: str):
        self.data_file = data_file
        os.makedirs(os.path.dirname(data_file), exist_ok=True)

    def record_usage(self, query: str, provider: str, success: bool, response_time: float):
        history = self._load_history()
        history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "provider": provider,
                "success": success,
                "response_time": response_time,
            }
        )
        history = history[-100:]
        self._save_history(history)

    def recommend_provider(self, query: str) -> Optional[str]:
        history = self._load_history()
        if not history:
            return None
        recent = history[-20:]
        successful = [r for r in recent if r.get("success")]
        if not successful:
            return None
        providers = [r["provider"] for r in successful]
        counter = Counter(providers)
        most_common = counter.most_common(1)
        return most_common[0][0] if most_common else None

    def _load_history(self) -> List:
        if not os.path.exists(self.data_file):
            return []
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_history(self, history: List):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)


class SmartSelector:
    """Smart Provider 選択エンジン。"""

    def __init__(self, config: Config):
        self.config = config
        self.openai_keywords = config.get("keyword_rules.openai", [])
        self.google_keywords = config.get("keyword_rules.google", [])
        data_file = config.get("learning.data_file", os.path.join(LOG_DIR, "usage_patterns.json"))
        self.learner = UsagePatternLearner(data_file)

    def select_provider(
        self,
        query: str,
        manual_provider: Optional[str] = None,
        strategy_override: Optional[str] = None,
    ) -> str:
        if manual_provider:
            return manual_provider

        strategy = strategy_override or self.config.get("strategy.mode", "auto")
        if strategy == "manual":
            return self.config.get("defaults.provider", "openai")

        query_lower = query.lower()
        openai_score = sum(1 for kw in self.openai_keywords if kw in query_lower)
        google_score = sum(1 for kw in self.google_keywords if kw in query_lower)

        if strategy == "quality":
            return "openai" if openai_score > 0 or google_score == 0 else "google"
        elif strategy == "cost":
            return "google" if google_score > 0 or openai_score == 0 else "openai"
        else:  # auto
            if openai_score > google_score:
                return "openai"
            elif google_score > openai_score:
                return "google"
            else:
                learned = self.learner.recommend_provider(query)
                return learned or self.config.get("defaults.provider", "openai")

    def record_result(self, query: str, provider: str, success: bool, response_time: float):
        if self.config.get("learning.enabled", True):
            self.learner.record_usage(query, provider, success, response_time)


# ============================================================
# ユーティリティ関数
# ============================================================


def get_project_root() -> str:
    """プロジェクトルートパス検出 (git基盤、fallbackで相対パス)。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        # .claude/skills/deep-research/scripts/ → 4段階上位
        return os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))


def generate_slug(query: str, max_length: int = 50) -> str:
    """クエリからファイル名用slug生成。ハングル/日本語/英文サポート。"""
    slug = unicodedata.normalize("NFKC", query.lower())
    # アルファベット、数字、ハングル、日本語、ハイフン、スペースのみ保持
    slug = re.sub(r"[^\w\sが-힣ぁ-んァ-ヶ一-龯a-z0-9-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug or "research"


def generate_output_path(query: str, provider: str, explicit_output: Optional[str] = None) -> str:
    """結果ファイル保存パス生成。"""
    if explicit_output:
        return os.path.abspath(explicit_output)

    project_root = get_project_root()
    research_dir = os.path.join(project_root, "docs", "research")
    os.makedirs(research_dir, exist_ok=True)

    slug = generate_slug(query)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{slug}-{provider}-{date_str}.md"
    path = os.path.join(research_dir, filename)

    # 重複防止: 同名存在時にカウンター追加
    if os.path.exists(path):
        base, ext = os.path.splitext(path)
        counter = 1
        while os.path.exists(f"{base}-{counter}{ext}"):
            counter += 1
        path = f"{base}-{counter}{ext}"

    return path


def get_language_instruction(language: str) -> str:
    """言語設定に応じた指示文。"""
    instructions = {
        "korean": "Please write the research report in Korean.",
        "english": "Please write the research report in English.",
        "japanese": "Please write the research report in Japanese (日本語で作成してください).",
        "chinese": "Please write the research report in Chinese (请用中文撰写研究报告).",
    }
    return instructions.get(language.lower(), "")


def get_openai_model_name(model_type: str) -> str:
    """OpenAI モデルタイプ → 完全なモデル名。"""
    models = {
        "o3": "o3-deep-research",
        "mini": "o4-mini-deep-research",
        "o4-mini": "o4-mini-deep-research",
    }
    return models.get(model_type.lower(), "o3-deep-research")


# ============================================================
# ResearchState - 状態ファイル CRUD
# ============================================================


class ResearchState:
    """リサーチセッション状態管理。Stateファイルでcrash recovery サポート。"""

    @staticmethod
    def generate_id() -> str:
        return f"dr-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    @staticmethod
    def create(
        research_id: str,
        provider: str,
        query: str,
        provider_resource_id: str,
        output_path: str,
        model: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict:
        """新しいリサーチ状態生成。"""
        state = {
            "id": research_id,
            "provider": provider,
            "provider_resource_id": provider_resource_id,
            "query": query,
            "model": model,
            "language": language,
            "status": "in_progress",
            "output_path": output_path,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "poll_count": 0,
            "last_polled_at": None,
            "error": None,
            "result_saved": False,
        }
        ResearchState._save(research_id, state)
        logger.info(f"State created: {research_id}")
        return state

    @staticmethod
    def load(research_id: str) -> Optional[Dict]:
        """状態ファイルロード。"""
        path = os.path.join(STATE_DIR, f"{research_id}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load state {research_id}: {e}")
            return None

    @staticmethod
    def update(research_id: str, **kwargs) -> Optional[Dict]:
        """状態更新（部分）。"""
        state = ResearchState.load(research_id)
        if state is None:
            logger.error(f"State not found: {research_id}")
            return None
        state.update(kwargs)
        ResearchState._save(research_id, state)
        return state

    @staticmethod
    def list_all() -> List[Dict]:
        """全てのリサーチセッションリスト（最新順）。"""
        states = []
        if not os.path.exists(STATE_DIR):
            return states
        for filename in sorted(os.listdir(STATE_DIR), reverse=True):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(STATE_DIR, filename), "r", encoding="utf-8") as f:
                        states.append(json.load(f))
                except Exception:
                    continue
        return states

    @staticmethod
    def _save(research_id: str, state: Dict):
        """アトミック保存（temp → rename）。"""
        path = os.path.join(STATE_DIR, f"{research_id}.json")
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)


# ============================================================
# Providerバックエンド: Start
# ============================================================


@retry_with_exponential_backoff(max_retries=2)
def start_openai(query: str, model_type: str = "o3", language: Optional[str] = None) -> Dict:
    """OpenAI Deep Researchをbackgroundモードで開始。即座に返す。"""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 環境変数が設定されていません。")

    client = OpenAI(api_key=api_key)
    model = get_openai_model_name(model_type)

    full_query = query
    if language:
        lang_inst = get_language_instruction(language)
        if lang_inst:
            full_query = f"{query}\n\n{lang_inst}"

    logger.info(f"Starting OpenAI background research: model={model}")

    response = client.responses.create(
        model=model,
        input=[{"role": "user", "content": [{"type": "input_text", "text": full_query}]}],
        reasoning={"summary": "auto"},
        tools=[{"type": "web_search_preview"}],
        background=True,
    )

    return {
        "provider_resource_id": response.id,
        "status": getattr(response, "status", "in_progress"),
        "model": model,
    }


@retry_with_exponential_backoff(max_retries=2)
def start_google(query: str, language: Optional[str] = None) -> Dict:
    """Google Deep Researchをbackgroundモードで開始。即座に返す。"""
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 環境変数が設定されていません。")

    client = genai.Client(api_key=api_key)

    full_query = query
    if language:
        lang_inst = get_language_instruction(language)
        if lang_inst:
            full_query = f"{query}\n\n{lang_inst}"

    logger.info("Starting Google background research")

    interaction = client.interactions.create(
        input=full_query,
        agent="deep-research-pro-preview-12-2025",
        background=True,
    )

    return {
        "provider_resource_id": interaction.id,
        "status": getattr(interaction, "status", "in_progress"),
        "model": "deep-research-pro-preview-12-2025",
    }


# ============================================================
# Providerバックエンド: Poll（1回照会）
# ============================================================


def poll_openai_once(provider_resource_id: str) -> Dict:
    """OpenAI リサーチ状態を1回照会。"""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 環境変数が設定されていません。")

    client = OpenAI(api_key=api_key)
    response = client.responses.retrieve(provider_resource_id)
    status = getattr(response, "status", "unknown")

    result = {"status": status, "result_text": None, "reasoning_summary": None}

    if status == "completed":
        text_parts = []
        summary_parts = []
        if hasattr(response, "output") and response.output:
            for output_item in response.output:
                if hasattr(output_item, "content"):
                    for content_item in output_item.content:
                        if hasattr(content_item, "text"):
                            text_parts.append(content_item.text)
                if hasattr(output_item, "summary"):
                    for summary_item in output_item.summary:
                        if hasattr(summary_item, "text"):
                            summary_parts.append(summary_item.text)
        result["result_text"] = "".join(text_parts)
        result["reasoning_summary"] = "".join(summary_parts) if summary_parts else None

    return result


def poll_google_once(provider_resource_id: str) -> Dict:
    """Google リサーチ状態を1回照会。"""
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 環境変数が設定されていません。")

    client = genai.Client(api_key=api_key)
    interaction = client.interactions.get(provider_resource_id)
    status = getattr(interaction, "status", "unknown")

    result = {"status": status, "result_text": None, "reasoning_summary": None}

    if status == "completed":
        if hasattr(interaction, "outputs") and interaction.outputs:
            result["result_text"] = interaction.outputs[-1].text
        else:
            result["result_text"] = str(interaction)

    if status == "failed":
        result["error"] = getattr(interaction, "error", "Unknown error")

    return result


# ============================================================
# 結果保存
# ============================================================


def save_result(
    output_path: str,
    query: str,
    provider: str,
    model: Optional[str],
    result_text: str,
    reasoning_summary: Optional[str] = None,
    started_at: Optional[str] = None,
):
    """リサーチ結果をマークダウンファイルに保存。"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Deep Research Result\n\n")
        f.write(f"**Query**: {query}\n\n")
        f.write(f"**Provider**: {provider}\n\n")
        if model:
            f.write(f"**Model**: {model}\n\n")
        if started_at:
            f.write(f"**Started**: {started_at}\n\n")
        f.write(f"**Completed**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        if reasoning_summary:
            f.write(f"## Reasoning Summary\n\n{reasoning_summary}\n\n---\n\n")
        f.write(f"## Research Result\n\n{result_text}\n")

    logger.info(f"Result saved to: {output_path}")


# ============================================================
# Subcommand: start
# ============================================================


def cmd_start(args) -> int:
    """バックグラウンドリサーチ開始。即座に返す。"""
    config = Config()
    selector = SmartSelector(config)

    # Provider 決定
    provider = args.provider
    if args.auto or args.strategy:
        if not provider or provider == "openai":
            provider = selector.select_provider(
                args.query, manual_provider=None, strategy_override=args.strategy
            )
            print(f"Smart Selection: {provider.upper()}")
    provider = provider or "openai"

    # 出力 パス 決定
    output_path = generate_output_path(args.query, provider, getattr(args, "output", None))

    # リサーチ 開始
    research_id = ResearchState.generate_id()
    print(f"Research ID: {research_id}")
    print(f"Provider: {provider.upper()}")
    print(f"Output: {output_path}")
    print(f"Starting...")

    try:
        if provider == "openai":
            model_type = getattr(args, "model", "o3") or "o3"
            result = start_openai(args.query, model_type, getattr(args, "language", None))
        elif provider == "google":
            result = start_google(args.query, getattr(args, "language", None))
        else:
            print(f"Error: Unknown provider '{provider}'")
            return 1
    except Exception as e:
        error_history.log_error(provider, type(e).__name__, str(e), args.query)
        print(f"Error: {e}")
        return 1

    # State 保存
    state = ResearchState.create(
        research_id=research_id,
        provider=provider,
        query=args.query,
        provider_resource_id=result["provider_resource_id"],
        output_path=output_path,
        model=result.get("model"),
        language=getattr(args, "language", None),
    )

    print(f"Status: {result['status']}")
    print(f"Provider Resource ID: {result['provider_resource_id']}")
    print()
    print(f"次のコマンドで状態確認:")
    print(f"  python {os.path.basename(__file__)} status {research_id}")
    print(f"  python {os.path.basename(__file__)} poll {research_id}")

    return 0


# ============================================================
# Subcommand: status
# ============================================================


def cmd_status(args) -> int:
    """リサーチ状態を1回照会して更新。"""
    state = ResearchState.load(args.research_id)
    if state is None:
        print(f"Error: Research '{args.research_id}' not found")
        return 1

    # 既に 完了した 場合
    if state["status"] in ("completed", "failed", "cancelled"):
        _print_state_summary(state)
        return 0

    # Providerに 1回 取得
    try:
        if state["provider"] == "openai":
            poll_result = poll_openai_once(state["provider_resource_id"])
        elif state["provider"] == "google":
            poll_result = poll_google_once(state["provider_resource_id"])
        else:
            print(f"Error: Unknown provider '{state['provider']}'")
            return 1
    except Exception as e:
        print(f"Poll error: {e}")
        return 1

    # State 更新
    update_data = {
        "status": poll_result["status"],
        "poll_count": state["poll_count"] + 1,
        "last_polled_at": datetime.now().isoformat(),
    }

    if poll_result["status"] == "completed" and poll_result["result_text"]:
        update_data["completed_at"] = datetime.now().isoformat()
        # 結果 保存
        save_result(
            output_path=state["output_path"],
            query=state["query"],
            provider=state["provider"],
            model=state.get("model"),
            result_text=poll_result["result_text"],
            reasoning_summary=poll_result.get("reasoning_summary"),
            started_at=state.get("started_at"),
        )
        update_data["result_saved"] = True

    if poll_result["status"] == "failed":
        update_data["error"] = poll_result.get("error", "Unknown error")
        update_data["completed_at"] = datetime.now().isoformat()

    state = ResearchState.update(args.research_id, **update_data)
    _print_state_summary(state)
    return 0


# ============================================================
# Subcommand: poll
# ============================================================


def cmd_poll(args) -> int:
    """完了までポーリング。timeoutとzombie guard含む。"""
    state = ResearchState.load(args.research_id)
    if state is None:
        print(f"Error: Research '{args.research_id}' not found")
        return 1

    # 既に 完了した 場合
    if state["status"] == "completed":
        print(f"Already completed. Result: {state['output_path']}")
        return 0
    if state["status"] in ("failed", "cancelled"):
        print(f"Research {state['status']}: {state.get('error', 'N/A')}")
        return 1

    config = Config()
    provider = state["provider"]

    # ポーリング 設定
    interval = config.get(f"polling.{provider}.interval", 15 if provider == "openai" else 30)
    max_iter = config.get(f"polling.{provider}.max_iterations", 120 if provider == "openai" else 60)
    timeout = getattr(args, "timeout", None)

    if timeout:
        # timeout(秒)から max_iterations 計算
        max_iter = min(max_iter, int(timeout / interval) + 1)

    print(f"Polling {state['id']} ({provider.upper()})")
    print(f"Interval: {interval}s, Max iterations: {max_iter}")
    print(f"Max wait: ~{max_iter * interval / 60:.0f} min")
    print("-" * 50)

    start_time = time.time()
    selector = SmartSelector(config)

    for iteration in range(1, max_iter + 1):
        try:
            if provider == "openai":
                poll_result = poll_openai_once(state["provider_resource_id"])
            elif provider == "google":
                poll_result = poll_google_once(state["provider_resource_id"])
            else:
                print(f"Error: Unknown provider '{provider}'")
                return 1
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n[{iteration}/{max_iter}] Poll error ({elapsed:.0f}s): {e}")
            # エラー 時 次の ポーリング 続ける (ネットワーク 一時 障害 等)
            time.sleep(interval)
            continue

        status = poll_result["status"]
        elapsed = time.time() - start_time

        # State 更新
        ResearchState.update(
            state["id"],
            status=status,
            poll_count=state["poll_count"] + iteration,
            last_polled_at=datetime.now().isoformat(),
        )

        if status == "completed" and poll_result["result_text"]:
            print(f"\n[COMPLETED] ({elapsed:.0f}s, {iteration} polls)")

            # 結果 保存
            save_result(
                output_path=state["output_path"],
                query=state["query"],
                provider=state["provider"],
                model=state.get("model"),
                result_text=poll_result["result_text"],
                reasoning_summary=poll_result.get("reasoning_summary"),
                started_at=state.get("started_at"),
            )
            ResearchState.update(
                state["id"],
                completed_at=datetime.now().isoformat(),
                result_saved=True,
            )

            # 学習 記録
            selector.record_result(state["query"], provider, True, elapsed)

            print(f"Result saved: {state['output_path']}")

            # 結果 内容 出力 (stdout)
            print("\n" + "=" * 60)
            print("RESEARCH RESULT")
            print("=" * 60)
            if poll_result.get("reasoning_summary"):
                print(f"\n### Reasoning Summary ###\n")
                print(poll_result["reasoning_summary"])
                print("\n" + "-" * 60)
            print(f"\n### Result ###\n")
            print(poll_result["result_text"])

            return 0

        if status in ("failed", "cancelled"):
            error_msg = poll_result.get("error", "Unknown")
            ResearchState.update(
                state["id"],
                error=error_msg,
                completed_at=datetime.now().isoformat(),
            )
            selector.record_result(state["query"], provider, False, elapsed)
            print(f"\n[{status.upper()}] ({elapsed:.0f}s): {error_msg}")
            return 1

        # 進行 中 - 状態 表示
        minutes = elapsed / 60
        print(f"  [{iteration}/{max_iter}] {status} ({minutes:.1f}min elapsed)", flush=True)
        time.sleep(interval)

    # Zombie guard: max iterations 到達
    elapsed = time.time() - start_time
    ResearchState.update(
        state["id"],
        error=f"Zombie guard: exceeded {max_iter} iterations ({elapsed:.0f}s)",
    )
    selector.record_result(state["query"], provider, False, elapsed)
    print(f"\n[TIMEOUT] Max iterations ({max_iter}) reached after {elapsed / 60:.1f} min")
    print(f"リサーチがサーバーで継続実行中の可能性があります。")
    print(f"後で確認: python {os.path.basename(__file__)} status {state['id']}")
    return 1


# ============================================================
# Subcommand: result
# ============================================================


def cmd_result(args) -> int:
    """完了したリサーチ結果照会。"""
    state = ResearchState.load(args.research_id)
    if state is None:
        print(f"Error: Research '{args.research_id}' not found")
        return 1

    if state["status"] != "completed":
        print(f"Research status: {state['status']} (not completed)")
        if state["status"] == "in_progress":
            print(f"Use 'poll {args.research_id}' to wait for completion")
        return 1

    if state.get("result_saved") and os.path.exists(state["output_path"]):
        with open(state["output_path"], "r", encoding="utf-8") as f:
            print(f.read())
        return 0
    else:
        # 結果 ファイル なし - 再度 poll 試行
        print("Result file not found. Attempting to retrieve from provider...")
        try:
            if state["provider"] == "openai":
                poll_result = poll_openai_once(state["provider_resource_id"])
            else:
                poll_result = poll_google_once(state["provider_resource_id"])

            if poll_result["status"] == "completed" and poll_result["result_text"]:
                save_result(
                    output_path=state["output_path"],
                    query=state["query"],
                    provider=state["provider"],
                    model=state.get("model"),
                    result_text=poll_result["result_text"],
                    reasoning_summary=poll_result.get("reasoning_summary"),
                    started_at=state.get("started_at"),
                )
                ResearchState.update(state["id"], result_saved=True)
                print(f"Result recovered and saved: {state['output_path']}")
                print()
                print(poll_result["result_text"])
                return 0
        except Exception as e:
            print(f"Recovery failed: {e}")
            return 1

    return 1


# ============================================================
# Subcommand: list
# ============================================================


def cmd_list(args) -> int:
    """全てのリサーチセッションリスト。"""
    states = ResearchState.list_all()
    if not states:
        print("No research sessions found.")
        return 0

    print(f"{'ID':<25} {'Status':<12} {'Provider':<8} {'Started':<20} {'Query'}")
    print("-" * 100)
    for s in states:
        query_preview = s["query"][:40] + "..." if len(s["query"]) > 40 else s["query"]
        started = s.get("started_at", "N/A")[:19]
        print(f"{s['id']:<25} {s['status']:<12} {s['provider']:<8} {started:<20} {query_preview}")

    return 0


# ============================================================
# Subcommand: run (レガシー互換)
# ============================================================


def cmd_run(args) -> int:
    """レガシーモード: start + pollインライン実行。--streamは同期ストリーミング。"""
    config = Config()
    selector = SmartSelector(config)
    start_time = time.time()

    # Provider 決定
    provider = args.provider or "openai"
    if args.auto or args.strategy:
        provider = selector.select_provider(
            args.query, manual_provider=None, strategy_override=args.strategy
        )
        print(f"Smart Selection: {provider.upper()}")

    # ストリーミング モード (OpenAI 前用) - 同期 方式として 実行
    if getattr(args, "stream", False) and provider == "openai":
        return _run_streaming(args, provider, config, selector, start_time)

    # Background モード: start → poll
    output_path = generate_output_path(args.query, provider, getattr(args, "output", None))
    research_id = ResearchState.generate_id()

    print("=" * 60)
    print(f"Deep Research ({provider.upper()})")
    print("=" * 60)
    print(f"Query: {args.query}")
    print(f"Research ID: {research_id}")
    print(f"Output: {output_path}")
    print("-" * 60)

    # Start
    try:
        if provider == "openai":
            model_type = getattr(args, "model", "o3") or "o3"
            start_result = start_openai(args.query, model_type, getattr(args, "language", None))
        elif provider == "google":
            start_result = start_google(args.query, getattr(args, "language", None))
        else:
            print(f"Error: Unknown provider '{provider}'")
            return 1
    except Exception as e:
        error_history.log_error(provider, type(e).__name__, str(e), args.query)
        selector.record_result(args.query, provider, False, time.time() - start_time)
        _print_error_help(e, provider, args)
        return 1

    # State 生成
    ResearchState.create(
        research_id=research_id,
        provider=provider,
        query=args.query,
        provider_resource_id=start_result["provider_resource_id"],
        output_path=output_path,
        model=start_result.get("model"),
        language=getattr(args, "language", None),
    )

    # Poll (inline)
    poll_args = argparse.Namespace(research_id=research_id, timeout=None)
    return cmd_poll(poll_args)


def _run_streaming(args, provider: str, config: Config, selector: SmartSelector, start_time: float) -> int:
    """OpenAI ストリーミングモード（同期、リアルタイム出力）。"""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY 環境変数が設定されていません。")
        return 1

    client = OpenAI(api_key=api_key)
    model = get_openai_model_name(getattr(args, "model", "o3") or "o3")

    full_query = args.query
    language = getattr(args, "language", None)
    if language:
        lang_inst = get_language_instruction(language)
        if lang_inst:
            full_query = f"{args.query}\n\n{lang_inst}"

    output_path = generate_output_path(args.query, provider, getattr(args, "output", None))

    print("=" * 60)
    print(f"Deep Research STREAMING ({provider.upper()})")
    print("=" * 60)
    print(f"Query: {args.query}")
    print(f"Model: {model}")
    print("-" * 60)

    try:
        stream = client.responses.create(
            model=model,
            input=[{"role": "user", "content": [{"type": "input_text", "text": full_query}]}],
            reasoning={"summary": "auto"},
            tools=[{"type": "web_search_preview"}],
            stream=True,
        )

        result_text = ""
        reasoning_summary = ""

        for event in stream:
            event_type = event.type
            if event_type == "response.reasoning_summary_text.delta":
                if hasattr(event, "delta"):
                    reasoning_summary += event.delta
                    print(f"\r[Reasoning] {len(reasoning_summary)} chars...", end="", flush=True)
            elif event_type == "response.output_text.delta":
                if hasattr(event, "delta"):
                    result_text += event.delta
                    print(f"\r[Output] {len(result_text)} chars...", end="", flush=True)
            elif event_type == "response.completed":
                print()

        elapsed = time.time() - start_time
        print("=" * 60)
        print(f"Completed! ({elapsed:.0f}s)")
        print("=" * 60)

        # 結果 保存
        if result_text:
            save_result(
                output_path=output_path,
                query=args.query,
                provider=provider,
                model=model,
                result_text=result_text,
                reasoning_summary=reasoning_summary or None,
            )
            selector.record_result(args.query, provider, True, elapsed)
            print(f"Result saved: {output_path}")

            if reasoning_summary:
                print(f"\n### Reasoning Summary ###\n")
                print(reasoning_summary)
                print("\n" + "-" * 60)
            print(f"\n### Result ###\n")
            print(result_text)
        else:
            print("No result received.")
            selector.record_result(args.query, provider, False, elapsed)

        return 0

    except Exception as e:
        elapsed = time.time() - start_time
        error_history.log_error(provider, type(e).__name__, str(e), args.query)
        selector.record_result(args.query, provider, False, elapsed)
        _print_error_help(e, provider, args)
        return 1


# ============================================================
# 出力 ヘルパー
# ============================================================


def _print_state_summary(state: Dict):
    """状態サマリー出力。"""
    print(f"ID:       {state['id']}")
    print(f"Status:   {state['status']}")
    print(f"Provider: {state['provider']}")
    print(f"Query:    {state['query']}")
    print(f"Started:  {state.get('started_at', 'N/A')}")
    if state.get("completed_at"):
        print(f"Completed: {state['completed_at']}")
    print(f"Polls:    {state.get('poll_count', 0)}")
    if state.get("output_path"):
        print(f"Output:   {state['output_path']}")
    if state.get("result_saved"):
        print(f"Result:   Saved")
    if state.get("error"):
        print(f"Error:    {state['error']}")


def _print_error_help(error: Exception, provider: str, args):
    """ユーザーフレンドリーなエラーメッセージ。"""
    error_msg = str(error).lower()
    error_type = type(error).__name__

    print(f"\nError: {error}")
    print(f"Type: {error_type}")
    print()

    if "authentication" in error_type.lower() or "401" in error_msg:
        key_name = "OPENAI_API_KEY" if provider == "openai" else "GEMINI_API_KEY"
        print(f"解決: {key_name} 環境変数が正しいか確認してください。")
    elif "ratelimit" in error_type.lower() or "429" in error_msg:
        print("解決: API リクエスト制限超過。しばらくしてから再試行してください。")
        print("ヒント: --enable-fallback オプションで他のProviderを自動使用")
    elif "timeout" in error_msg or "connection" in error_msg:
        print("解決: ネットワーク接続を確認してください。")
    elif "notfound" in error_type.lower() or "404" in error_msg:
        print("解決: モデル名またはAPIアクセス権限を確認してください。")
    else:
        print(f"ログ 確認: {os.path.join(LOG_DIR, 'error_history.json')}")


# ============================================================
# Argument Parsing & Main
# ============================================================


def _add_common_args(parser):
    """共通 引数 追加."""
    parser.add_argument(
        "--provider", "-p", choices=["openai", "google"], default=None, help="Provider (基本: openai)"
    )
    parser.add_argument(
        "--model", "-m", choices=["o3", "mini", "o4-mini"], default="o3", help="[OpenAI] モデル (基本: o3)"
    )
    parser.add_argument(
        "--language", "-l", choices=["korean", "english", "japanese", "chinese"], help="結果 言語"
    )
    parser.add_argument("--output", "-o", help="結果 ファイル パス (基本: docs/research/)")
    parser.add_argument("--auto", "-a", action="store_true", help="Smart Provider Selection")
    parser.add_argument("--strategy", choices=["auto", "quality", "cost", "manual"], help="選択 戦略")
    parser.add_argument("--enable-fallback", "-f", action="store_true", help="Provider フォールバック")


def build_parser() -> argparse.ArgumentParser:
    """argparse 構成."""
    parser = argparse.ArgumentParser(
        description="Deep Research CLI v2.0 - Subcommand Architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # start
    p_start = subparsers.add_parser("start", help="バックグラウンド リサーチ 開始 (即座に返却)")
    p_start.add_argument("query", help="リサーチ テーマ")
    _add_common_args(p_start)

    # status
    p_status = subparsers.add_parser("status", help="リサーチ 状態 確認 (1回)")
    p_status.add_argument("research_id", help="Research ID")

    # poll
    p_poll = subparsers.add_parser("poll", help="完了まで ポーリング")
    p_poll.add_argument("research_id", help="Research ID")
    p_poll.add_argument("--timeout", "-t", type=int, help="最大 待機時間 (秒)")

    # result
    p_result = subparsers.add_parser("result", help="完了した 結果 取得")
    p_result.add_argument("research_id", help="Research ID")

    # list
    subparsers.add_parser("list", help="全ての リサーチ セッション 一覧")

    # run (legacy)
    p_run = subparsers.add_parser("run", help="レガシー モード (start + poll)")
    p_run.add_argument("query", help="リサーチ テーマ")
    p_run.add_argument("--stream", "-s", action="store_true", help="[OpenAI] ストリーミング モード")
    _add_common_args(p_run)

    return parser


def main():
    # レガシー 互換: 最初の 引数が subcommandで なければ "run"として みなす
    args = sys.argv[1:]
    if args and args[0] not in SUBCOMMANDS and not args[0].startswith("-"):
        # 最初の 引数が クエリ 文字列 → run モード
        args = ["run"] + args

    parser = build_parser()
    parsed = parser.parse_args(args)

    if parsed.command is None:
        parser.print_help()
        return 0

    handlers = {
        "start": cmd_start,
        "status": cmd_status,
        "poll": cmd_poll,
        "result": cmd_result,
        "list": cmd_list,
        "run": cmd_run,
    }

    handler = handlers.get(parsed.command)
    if handler:
        return handler(parsed)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
