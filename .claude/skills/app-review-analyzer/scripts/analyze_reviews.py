#!/usr/bin/env python3
"""
アプリストアレビューCSV分析および可視化スクリプト

使用法:
    python3 analyze_reviews.py <csv_path> [output_dir]

出力:
    - rating_distribution.png: 評点分布グラフ
    - monthly_trend.png: 月別レビュートレンド
    - version_rating.png: バージョン別平均評点
    - analysis_report.txt: 分析サマリーレポート
"""

import sys
import os
from pathlib import Path
from collections import Counter
import re

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ハングルフォント設定 (macOS)
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False


def load_and_validate_csv(csv_path: str) -> pd.DataFrame:
    """CSVファイルをロードし、必須カラムを検証する。"""
    required_columns = ['id', 'date', 'user_name', 'title', 'content', 'rating', 'app_version']

    df = pd.read_csv(csv_path)

    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ValueError(f"必須カラム不足: {missing}")

    # 日付パース
    df['date'] = pd.to_datetime(df['date'], utc=True)
    df['year_month'] = df['date'].dt.to_period('M')

    return df


def plot_rating_distribution(df: pd.DataFrame, output_path: str):
    """評点分布バーグラフを生成する。"""
    fig, ax = plt.subplots(figsize=(10, 6))

    rating_counts = df['rating'].value_counts().sort_index()
    colors = ['#ff6b6b', '#ffa94d', '#ffd43b', '#a9e34b', '#69db7c']

    bars = ax.bar(rating_counts.index, rating_counts.values, color=colors)

    for bar, count in zip(bars, rating_counts.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                str(count), ha='center', va='bottom', fontsize=12)

    ax.set_xlabel('評点', fontsize=12)
    ax.set_ylabel('レビュー数', fontsize=12)
    ax.set_title('評点分布', fontsize=14, fontweight='bold')
    ax.set_xticks([1, 2, 3, 4, 5])

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✓ 保存: {output_path}")


def plot_monthly_trend(df: pd.DataFrame, output_path: str):
    """月別レビュートレンドグラフを生成する。"""
    fig, ax1 = plt.subplots(figsize=(12, 6))

    monthly = df.groupby('year_month').agg({
        'id': 'count',
        'rating': 'mean'
    }).rename(columns={'id': 'count', 'rating': 'avg_rating'})

    x = range(len(monthly))
    x_labels = [str(p) for p in monthly.index]

    # レビュー数バーグラフ
    ax1.bar(x, monthly['count'], alpha=0.7, color='#4dabf7', label='レビュー数')
    ax1.set_xlabel('月', fontsize=12)
    ax1.set_ylabel('レビュー数', color='#4dabf7', fontsize=12)
    ax1.tick_params(axis='y', labelcolor='#4dabf7')

    # 平均評点ラインチャート
    ax2 = ax1.twinx()
    ax2.plot(x, monthly['avg_rating'], color='#ff6b6b', marker='o', linewidth=2, label='平均評点')
    ax2.set_ylabel('平均評点', color='#ff6b6b', fontsize=12)
    ax2.tick_params(axis='y', labelcolor='#ff6b6b')
    ax2.set_ylim(1, 5)

    ax1.set_xticks(x)
    ax1.set_xticklabels(x_labels, rotation=45, ha='right')

    plt.title('月別レビュートレンド', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✓ 保存: {output_path}")


def plot_version_rating(df: pd.DataFrame, output_path: str):
    """バージョン別平均評点グラフを生成する。"""
    # 最新10バージョンのみ表示
    version_stats = df.groupby('app_version').agg({
        'id': 'count',
        'rating': 'mean'
    }).rename(columns={'id': 'count', 'rating': 'avg_rating'})

    # レビュー数が3件以上のバージョンのみフィルタリング
    version_stats = version_stats[version_stats['count'] >= 3]
    version_stats = version_stats.tail(10)

    if len(version_stats) == 0:
        print("⚠ バージョン別分析: 十分なデータなし")
        return

    fig, ax = plt.subplots(figsize=(12, 6))

    x = range(len(version_stats))
    colors = ['#ff6b6b' if r < 3 else '#69db7c' if r >= 4 else '#ffd43b'
              for r in version_stats['avg_rating']]

    bars = ax.bar(x, version_stats['avg_rating'], color=colors)

    for bar, (_, row) in zip(bars, version_stats.iterrows()):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f"{row['avg_rating']:.1f}\n({int(row['count'])}件)",
                ha='center', va='bottom', fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(version_stats.index, rotation=45, ha='right')
    ax.set_xlabel('アプリバージョン', fontsize=12)
    ax.set_ylabel('平均評点', fontsize=12)
    ax.set_title('バージョン別平均評点 (最新10バージョン、3件以上)', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 5.5)
    ax.axhline(y=3, color='gray', linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✓ 保存: {output_path}")


def extract_keywords(texts: pd.Series, top_n: int = 10) -> list:
    """テキストから主要キーワードを抽出する。"""
    # ストップワード (ハングル)
    stopwords = {'アプリ', 'アップリ', 'これ', 'が', 'を', 'は', 'に', 'の', 'で', 'として',
                 'と', 'や', 'も', 'だけ', 'から', 'として', 'して', 'その', 'あの', 'それ', 'こと', '等',
                 'もっと', 'ちょっと', 'とても', '本当に', '本当', 'あ', 'うん', '何', 'なぜ', 'どう', 'ない', 'できない',
                 '良い', '悪い', 'いまいち', 'ただ', 'でも', 'ある', 'ない', 'なる', 'する', 'です', 'だ', 'される'}

    all_text = ' '.join(texts.dropna().astype(str))

    # ハングル単語抽出 (2文字以上)
    words = re.findall(r'[が-힣]{2,}', all_text)

    # ストップワード除去
    words = [w for w in words if w not in stopwords]

    counter = Counter(words)
    return counter.most_common(top_n)


def generate_report(df: pd.DataFrame, output_path: str):
    """分析レポートを生成する。"""
    total = len(df)
    avg_rating = df['rating'].mean()
    rating_dist = df['rating'].value_counts().sort_index()

    # ネガティブ/ポジティブレビュー分離
    negative = df[df['rating'] <= 2]
    positive = df[df['rating'] >= 4]

    # キーワード抽出
    neg_keywords = extract_keywords(negative['content'].astype(str) + ' ' + negative['title'].astype(str))
    pos_keywords = extract_keywords(positive['content'].astype(str) + ' ' + positive['title'].astype(str))

    report = f"""
================================================================================
                        アプリストアレビュー分析レポート
================================================================================

📊 基本統計
--------------------------------------------------------------------------------
総レビュー数: {total}件
平均評点: {avg_rating:.2f}点

📈 評点分布
--------------------------------------------------------------------------------
"""
    for rating in range(5, 0, -1):
        count = rating_dist.get(rating, 0)
        pct = count / total * 100
        bar = '█' * int(pct / 2)
        report += f"  {rating}点: {bar} {count}件 ({pct:.1f}%)\n"

    report += f"""
😞 ネガティブレビュー分析 (1-2点: {len(negative)}件)
--------------------------------------------------------------------------------
主要キーワード: {', '.join([f'{w}({c})' for w, c in neg_keywords[:10]])}

😊 ポジティブレビュー分析 (4-5点: {len(positive)}件)
--------------------------------------------------------------------------------
主要キーワード: {', '.join([f'{w}({c})' for w, c in pos_keywords[:10]])}

📅 期間
--------------------------------------------------------------------------------
最初のレビュー: {df['date'].min().strftime('%Y-%m-%d')}
最後のレビュー: {df['date'].max().strftime('%Y-%m-%d')}

================================================================================
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✓ 保存: {output_path}")
    print(report)


def main():
    if len(sys.argv) < 2:
        print("使用法: python3 analyze_reviews.py <csv_path> [output_dir]")
        sys.exit(1)

    csv_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else str(Path(csv_path).parent)

    if not os.path.exists(csv_path):
        print(f"エラー: ファイルが見つかりません - {csv_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print(f"\n📂 CSVファイル: {csv_path}")
    print(f"📁 出力ディレクトリ: {output_dir}\n")

    # データロード
    df = load_and_validate_csv(csv_path)
    print(f"✓ データロード完了: {len(df)}件のレビュー\n")

    # グラフ生成
    plot_rating_distribution(df, os.path.join(output_dir, 'rating_distribution.png'))
    plot_monthly_trend(df, os.path.join(output_dir, 'monthly_trend.png'))
    plot_version_rating(df, os.path.join(output_dir, 'version_rating.png'))

    # レポート生成
    generate_report(df, os.path.join(output_dir, 'analysis_report.txt'))


if __name__ == '__main__':
    main()
