# ギャップ分析ルール

> **SSOT 原則**: このファイルは分析**方法論**のみを定義します。
>
> - KPI/Feature マッピング → `kpi-targets.md`
> - 現在のギャップリスト → `critical-gaps.md`
> - パターンマッチング → ランタイムスキャン (ハードコーディング禁止)

---

## 1. ギャップ識別基準

### 1.1 ギャップ状態定義

| 状態         | アイコン | 判断基準                         |
| ------------ | :------: | -------------------------------- |
| **なし**     |    🔴    | 該当テーマのファイル0個          |
| **概念のみ** |    🟡    | ファイルありだがAction Itemsなし |
| **完了**     |    ✅    | ファイル + 実行計画 + 定量データ |
| **更新必要** |    ⚪    | 修正日 > 180日                   |

### 1.2 品質チェックリスト

リサーチが「完了」状態として認められるには:

```markdown
□ Executive Summary 存在 (100単語以内)
□ 定量的データ含む (% 数値、ベンチマーク)
□ Action Items 具体的 (誰が、何を、いつ)
□ Japan-First 戦略と一致
```

**実行可能基準**:

- 実装複雑度: 1週間以内に着手可能
- コスト: 無料または月$100以下
- 自動化: 繰り返し作業最小化

---

## 2. 優先順位決定ルール

### 2.1 基本優先順位

| 優先順位 | 基準                | 例                             |
| :------: | ------------------- | ------------------------------ |
|  **P0**  | 収益/生存に直接影響 | Churn 防止、LTV 改善、価格戦略 |
|  **P1**  | 6ヶ月以内に必要     | 差別化、最適化、競合対応       |
|  **P2**  | 1年以内に必要       | グローバル展開、高度機能       |
|  **P3**  | 長期競争力          | 市場トレンド、技術動向         |

### 2.2 ROI 重み付け

```
最終スコア = (KPI 影響度 × 3) + (実装容易性 × 2) + (Japan-First 適合性 × 1)
```

| 要素        | 重み | 評価基準                    |
| ----------- | :--: | --------------------------- |
| KPI 影響度  |  ×3  | 直接(3)、間接(2)、微小(1)   |
| 実装容易性  |  ×2  | 容易(3)、普通(2)、困難(1)   |
| Japan-First |  ×1  | 適合(3)、中立(2)、不適合(1) |

---

## 3. ランタイムスキャンルール

### 3.1 リサーチファイルスキャン

```python
# スキャン対象
research_files = glob("docs/research/*.md")

# 品質評価
for file in research_files:
    content = read(file)
    quality = evaluate(content, checklist)
```

### 3.2 品質評価ロジック

```python
def evaluate(content: str) -> str:
    """リサーチ品質評価"""
    has_summary = "## Executive Summary" in content or "## 要約" in content
    has_data = re.search(r'\d+%', content) is not None
    has_actions = "Action" in content or "実行" in content

    if has_summary and has_data and has_actions:
        return "完了"
    elif has_summary or has_actions:
        return "概念のみ"
    else:
        return "なし"
```

### 3.3 KPI マッピング

**ハードコーディング禁止**: `kpi-targets.md`をランタイムにパースしてKPI-Feature-Researchマッピングを構成する。

```python
# 正しい方式
kpi_targets = parse_yaml("references/kpi-targets.md")
for kpi, config in kpi_targets.items():
    required = config["required_research"]

# 禁止された方式
REQUIRED_RESEARCH = {
    "d7_retention": [...]  # ハードコーディング禁止!
}
```

---

## 4. リサーチ要請テンプレート

### 4.1 ディープリサーチ要請

```markdown
## リサーチ要請: {gap_topic}

### 目標

Hackathon Project アプリの {kpi_target} 達成

### コンテキスト

- Japan-First 戦略 (日本市場優先)
- 効率性重視 (自動化/低コスト必須)
- AI コンテンツ 100% (著作権Free)

### 必須含有内容

1. 定量的データ (% 数値、ベンチマーク)
2. 競合比較 (Duolingo, Speak, ELSA)
3. 実行可能な Action Items
4. 日本市場特殊性反映

### 出力形式

- 言語: 日本語
- 形式: マークダウン
- 長さ: 1500-3000 単語
```

### 4.2 ファイル命名規則

```
{topic}-{subtopic}-{year}.md
例: churn-prevention-program-design-2026.md
```

### 4.3 必須セクション

```markdown
1. Executive Summary (100単語以内)
2. 核心インサイト (3-5個、定量データ含む)
3. 競合ベンチマーク
4. Action Items (優先順位 + 予想工数)
5. 出典 (信頼度表示: A/B/C級)
```

---

## 5. 注意事項

1. **ランタイム優先**: ハードコーディングされたリストの代わりに常に最新ファイル構造をスキャン
2. **SSOT 遵守**: データ重複保存禁止
3. **品質 > 量**: 概念のみのリサーチは「未完成」処理
4. **PRD 連携**: リサーチは必ずPRDと明示的に連携

---

## Changelog

| バージョン |    日付    | 変更内容                                                                           |
| :--------: | :--------: | :--------------------------------------------------------------------------------- |
|    2.0     | 2026-01-19 | **簡素化**: パターンマッチングハードコーディング除去、ランタイムスキャンルール追加 |
|    1.0     | 2026-01-15 | 初期バージョン                                                                     |
