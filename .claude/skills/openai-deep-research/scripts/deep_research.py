#!/usr/bin/env python3
"""
OpenAI Deep Research API を使用したディープリサーチスクリプト。

使用法:
    python deep_research.py "リサーチ主題"
    python deep_research.py "リサーチ主題" --model mini
    python deep_research.py "リサーチ主題" --language korean
    python deep_research.py "リサーチ主題" --output result.md
    python deep_research.py "リサーチ主題" --stream
"""

import argparse
import os
import sys
from datetime import datetime


def check_dependencies():
    """必須パッケージのインストール確認。"""
    try:
        import openai
        return True
    except ImportError:
        print("Error: openai パッケージがインストールされていません。")
        print("インストールコマンド: pip install openai")
        return False


def get_language_instruction(language: str) -> str:
    """言語設定に応じた指示文を返す。"""
    instructions = {
        "korean": "Please write the research report in Korean .",
        "english": "Please write the research report in English.",
        "japanese": "Please write the research report in Japanese (日本語で作成してください).",
        "chinese": "Please write the research report in Chinese (请用中文撰写研究报告).",
    }
    return instructions.get(language.lower(), "")


def get_model_name(model_type: str) -> str:
    """モデルタイプに応じた完全なモデル名を返す。"""
    models = {
        "o3": "o3-deep-research",
        "mini": "o4-mini-deep-research",
        "o4-mini": "o4-mini-deep-research",
    }
    return models.get(model_type.lower(), "o3-deep-research")


def run_deep_research_streaming(client, model: str, full_query: str):
    """ストリーミングモードで Deep Research を実行。"""
    print("ストリーミングモードで実行中...")
    print("-" * 60)

    result_text = ""
    reasoning_summary = ""

    try:
        stream = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": full_query}]
                }
            ],
            reasoning={"summary": "auto"},
            tools=[{"type": "web_search_preview"}],
            stream=True
        )

        for event in stream:
            event_type = event.type

            if event_type == "response.reasoning_summary_text.delta":
                # 推論要約デルタ
                if hasattr(event, 'delta'):
                    reasoning_summary += event.delta
                    print(f"\r[推論中] {len(reasoning_summary)} chars...", end="", flush=True)

            elif event_type == "response.output_text.delta":
                # 出力テキストデルタ
                if hasattr(event, 'delta'):
                    result_text += event.delta
                    print(f"\r[応答中] {len(result_text)} chars...", end="", flush=True)

            elif event_type == "response.completed":
                print("\n" + "=" * 60)
                print("リサーチ完了!")

        return result_text, reasoning_summary

    except Exception as e:
        print(f"\nストリーミングエラー: {str(e)}")
        raise


def run_deep_research(
    query: str,
    model_type: str = "o3",
    language: str = None,
    output_file: str = None,
    stream: bool = False
):
    """
    Deep Research API を実行して結果を返す。

    Args:
        query: リサーチ主題
        model_type: モデルタイプ（o3 または mini）
        language: 結果言語（korean, english, japanese, chinese）
        output_file: 結果保存ファイルパス
        stream: ストリーミングモード使用有無
    """
    from openai import OpenAI

    # API キー確認
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY 環境変数が設定されていません。")
        print("設定方法: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)

    # クライアント初期化
    client = OpenAI(api_key=api_key)

    # モデル選択
    model = get_model_name(model_type)

    # 言語指示文追加
    full_query = query
    if language:
        lang_instruction = get_language_instruction(language)
        if lang_instruction:
            full_query = f"{query}\n\n{lang_instruction}"

    print("=" * 60)
    print("OpenAI Deep Research 開始")
    print("=" * 60)
    print(f"主題: {query}")
    print(f"モデル: {model}")
    if language:
        print(f"結果言語: {language}")
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)

    try:
        if stream:
            result_text, reasoning_summary = run_deep_research_streaming(
                client, model, full_query
            )
        else:
            print("リサーチ進行中...（完了まで時間がかかる場合があります）")

            response = client.responses.create(
                model=model,
                input=[
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": full_query}]
                    }
                ],
                reasoning={"summary": "auto"},
                tools=[{"type": "web_search_preview"}]
            )

            print("=" * 60)
            print("リサーチ完了!")
            print(f"完了時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)

            # 結果抽出
            result_text = ""
            reasoning_summary = ""

            # output からテキスト抽出
            if hasattr(response, 'output') and response.output:
                for output_item in response.output:
                    if hasattr(output_item, 'content'):
                        for content_item in output_item.content:
                            if hasattr(content_item, 'text'):
                                result_text += content_item.text
                    # 推論要約抽出
                    if hasattr(output_item, 'summary'):
                        for summary_item in output_item.summary:
                            if hasattr(summary_item, 'text'):
                                reasoning_summary += summary_item.text

        # 結果出力
        if reasoning_summary:
            print("\n### 推論要約 ###\n")
            print(reasoning_summary)
            print("\n" + "-" * 60)

        print("\n### リサーチ結果 ###\n")
        print(result_text if result_text else "（結果なし）")

        # ファイル保存
        if output_file and result_text:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# OpenAI Deep Research 結果\n\n")
                f.write(f"**主題**: {query}\n\n")
                f.write(f"**モデル**: {model}\n\n")
                f.write(f"**生成日**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"---\n\n")
                if reasoning_summary:
                    f.write(f"## 推論要約\n\n{reasoning_summary}\n\n---\n\n")
                f.write(f"## リサーチ結果\n\n{result_text}")
            print(f"\n結果が {output_file} に保存されました。")

        return result_text

    except Exception as e:
        error_msg = str(e)
        print(f"\nError: {error_msg}")

        # 一般的なエラー案内
        if "AuthenticationError" in error_msg or "401" in error_msg:
            print("\n解決策: OPENAI_API_KEY が正しいか確認してください。")
        elif "RateLimitError" in error_msg or "429" in error_msg:
            print("\n解決策: API リクエスト制限を超過しました。しばらくしてから再試行してください。")
        elif "NotFoundError" in error_msg or "404" in error_msg:
            print("\n解決策: モデル名を確認してください。または API アクセス権限があるか確認してください。")

        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="OpenAI Deep Research API を使用したディープリサーチ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python deep_research.py "2025年 AI 技術トレンド"
  python deep_research.py "AIゲームアプリ市場分析" --language korean
  python deep_research.py "LLM 研究動向" --model mini --output research.md
  python deep_research.py "Next.js 最新動向" --stream
        """
    )

    parser.add_argument(
        "query",
        help="リサーチ主題"
    )

    parser.add_argument(
        "--model", "-m",
        choices=["o3", "mini", "o4-mini"],
        default="o3",
        help="使用するモデル（o3: 高品質、mini: 高速応答）（デフォルト: o3）"
    )

    parser.add_argument(
        "--language", "-l",
        choices=["korean", "english", "japanese", "chinese"],
        help="結果言語（デフォルト: クエリ言語自動検出）"
    )

    parser.add_argument(
        "--output", "-o",
        help="結果を保存するファイルパス（例: result.md）"
    )

    parser.add_argument(
        "--stream", "-s",
        action="store_true",
        help="ストリーミングモード使用（リアルタイム進行状況確認）"
    )

    args = parser.parse_args()

    # 依存性確認
    if not check_dependencies():
        sys.exit(1)

    # リサーチ実行
    run_deep_research(
        args.query,
        args.model,
        args.language,
        args.output,
        args.stream
    )


if __name__ == "__main__":
    main()
