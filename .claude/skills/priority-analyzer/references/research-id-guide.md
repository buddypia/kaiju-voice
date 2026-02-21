# Research ID ガイド

## Overview

priority-analyzer v2.0 では Research 文書を**明示的 ID**で連結します。
このガイドは Research ID 付与および管理方法を説明します。

---

## ID 形式

```
R-YYYYMMDD-NNN
```

| 部分       | 説明              | 例示     |
| ---------- | ----------------- | -------- |
| `R-`       | 接頭辞 (Research) | 固定     |
| `YYYYMMDD` | 生成日            | 20260125 |
| `NNN`      | 連番 (001-999)    | 001      |

### 正規表現

```regex
^R-\d{8}-\d{3}$
```

### 例示

- `R-20260125-001`
- `R-20260120-042`
- `R-20251231-999`

---

## ファイル名規則

```
docs/research/{ID}__{description}.md
```

| 部分            | 説明                           |
| --------------- | ------------------------------ |
| `{ID}`          | Research ID (R-YYYYMMDD-NNN)   |
| `__`            | 区切り文字 (アンダースコア2個) |
| `{description}` | 内容説明 (kebab-case)          |

### 例示

```
docs/research/R-20260125-001__user-interview-summary.md
docs/research/R-20260120-002__competitor-analysis-duolingo.md
docs/research/R-20260115-003__japan-market-pricing.md
```

---

## 既存 Research ファイルのマイグレーション

### マイグレーション方法

既存ファイルに ID を付与する2つの方式:

#### 方式 1: ファイル名変更 (推奨)

```bash
# Before
docs/research/gamification-retention-research-2025.md

# After
docs/research/R-20250115-001__gamification-retention-research.md
```

#### 方式 2: ファイル内メタデータ追加

```markdown
---
research_id: R-20250115-001
title: Gamification Retention Research
created: 2025-01-15
---

# Gamification Retention Research

...
```

### 連番付与規則

1. 同一日付に生成されたファイルは 001 から順次付与
2. 既存ファイルは原本生成日基準 (可能な場合)
3. 生成日不明時はマイグレーション日付を使用

---

## CONTEXT.json での使用

### research_links セクション

```json
{
  "priority": {
    "research_links": {
      "research_ids": ["R-20260110-001", "R-20260120-002"],
      "id_format": "R-YYYYMMDD-NNN"
    }
  }
}
```

### EQS sources での参照

```json
{
  "confidence": {
    "eqs": {
      "factors": {
        "user_problem_validation": {
          "value": true,
          "sources": ["R-20260110-001"],
          "notes": "ユーザーインタビュー10件分析"
        },
        "market_or_competitor_data": {
          "value": true,
          "sources": ["R-20260120-002", "R-20260115-003"],
          "notes": "競合社3社比較分析"
        }
      }
    }
  }
}
```

---

## 検証規則

### ID 検証

- 形式: `^R-\d{8}-\d{3}$` 正規表現マッチング
- 日付: 有効な日付 (YYYYMMDD)
- 重複: プロジェクト内唯一

### ファイル存在検証

```
priority-analyzer 実行時:
1. research_ids の各 ID 抽出
2. docs/research/{ID}*.md パターンで検索
3. ファイルなければ warning (処理続行)
4. ID 形式エラーなら error (中断)
```

---

## FAQ

### Q: 既存 Research ファイルをすべてマイグレーションする必要がありますか？

A: いいえ。priority-analyzer で**連結が必要なファイルのみ** ID を付与すれば十分です。

### Q: ID は誰が付与しますか？

A: 現在は手動付与です。今後自動化スクリプト開発予定。

### Q: 1つの Research が複数の Feature に連結できますか？

A: はい。research_ids は Feature ごとに独立しています。同一 ID が複数の Feature に現れることができます。

### Q: 日付を変更すると ID が変わりますか？

A: ID は**最初の生成日基準**で固定されます。内容修正時にも ID は維持します。

---

## 変更履歴

| 日付       | 変更内容                                     |
| ---------- | -------------------------------------------- |
| 2026-01-25 | 初期バージョン - v2.0 設計に基づくガイド作成 |
