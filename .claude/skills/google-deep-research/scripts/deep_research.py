#!/usr/bin/env python3
"""
Google Gemini Deep Research API を使用したディープリサーチスクリプト。

使用法:
    python deep_research.py "リサーチ主題"
    python deep_research.py "リサーチ主題" --language korean
    python deep_research.py "リサーチ主題" --output result.md
"""

import argparse
import os
import sys
import time
from datetime import datetime


def check_dependencies():
    """必須パッケージのインストール確認。"""
    try:
        from google import genai
        return True
    except ImportError:
        print("Error: google-genai パッケージがインストールされていません。")
        print("インストールコマンド: pip install google-genai")
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


def run_deep_research(query: str, language: str = None, output_file: str = None):
    """
    Deep Research API を実行して結果を返す。

    Args:
        query: リサーチ主題
        language: 結果言語 (korean, english, japanese, chinese)
        output_file: 結果保存ファイルパス
    """
    from google import genai

    # API キー確認
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY 環境変数が設定されていません。")
        print("設定方法: export GEMINI_API_KEY='your-api-key'")
        sys.exit(1)

    # クライアント初期化
    client = genai.Client(api_key=api_key)

    # 言語指示文追加
    full_query = query
    if language:
        lang_instruction = get_language_instruction(language)
        if lang_instruction:
            full_query = f"{query}\n\n{lang_instruction}"

    print(f"=" * 60)
    print(f"Deep Research 開始")
    print(f"=" * 60)
    print(f"主題: {query}")
    if language:
        print(f"結果言語: {language}")
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"-" * 60)

    try:
        # Deep Research 開始 (バックグラウンド実行)
        interaction = client.interactions.create(
            input=full_query,
            agent='deep-research-pro-preview-12-2025',
            background=True
        )

        print(f"リサーチ ID: {interaction.id}")
        print(f"状態: 進行中...")
        print(f"-" * 60)

        # 結果ポーリング
        poll_count = 0
        while True:
            interaction = client.interactions.get(interaction.id)
            poll_count += 1

            elapsed_minutes = poll_count * 10 / 60

            if interaction.status == "completed":
                print(f"\n状態: 完了!")
                print(f"所要時間: 約 {elapsed_minutes:.1f}分")
                print(f"=" * 60)

                # 結果抽出
                result = ""
                if hasattr(interaction, 'outputs') and interaction.outputs:
                    result = interaction.outputs[-1].text
                else:
                    result = str(interaction)

                # 結果出力
                print("\n### リサーチ結果 ###\n")
                print(result)

                # ファイル保存
                if output_file:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(f"# Deep Research 結果\n\n")
                        f.write(f"**主題**: {query}\n\n")
                        f.write(f"**生成日**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        f.write(f"---\n\n")
                        f.write(result)
                    print(f"\n結果が {output_file} に保存されました。")

                return result

            elif interaction.status == "failed":
                error_msg = getattr(interaction, 'error', 'Unknown error')
                print(f"\n状態: 失敗")
                print(f"エラー: {error_msg}")
                sys.exit(1)

            else:
                # 進行状態表示
                status_msg = f"進行中... ({elapsed_minutes:.1f}分経過)"

                # 進行情報があれば表示
                if hasattr(interaction, 'progress'):
                    status_msg += f" - {interaction.progress}"

                print(f"\r{status_msg}", end="", flush=True)

            time.sleep(10)  # 10秒ごとにポーリング

    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Google Gemini Deep Research API を使用したディープリサーチ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python deep_research.py "2025年 AI 技術トレンド"
  python deep_research.py "韓国語学習アプリ市場分析" --language korean
  python deep_research.py "LLM 研究動向" --output research.md
        """
    )

    parser.add_argument(
        "query",
        help="リサーチ主題"
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

    args = parser.parse_args()

    # 依存性確認
    if not check_dependencies():
        sys.exit(1)

    # リサーチ実行
    run_deep_research(args.query, args.language, args.output)


if __name__ == "__main__":
    main()
