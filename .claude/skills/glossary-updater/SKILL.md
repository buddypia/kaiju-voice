---
name: glossary-updater
description: Hackathon Project プロジェクトの glossary.md 用語集を更新するスキル。PRD/FRD 文書変更、新機能追加、コードベース変更後に用語集同期が必要なときにこのスキルを使用する。「用語集更新」、「glossary 同期」、「新用語追加」などの要求でトリガーされる。
doc_contract:
  review_interval_days: 90
---

# Glossary Updater

## Overview

Hackathon Project プロジェクトのドメイン用語集（`docs/glossary.md`）を最新状態に保つスキル。PRD/FRD 文書、コードベース（enum、モデル）、データベーススキーマから新用語を発見して用語集に追加する。

## トリガー条件

次の状況でこのスキル使用を提案する:

1. **PRD/FRD 文書変更後**: `docs/features/` フォルダの文書が修正されたとき
2. **明示的要求**: 「用語集更新」、「glossary 同期」、「新用語追加」
3. **新機能実装完了後**: 新 enum、モデル、サービスが追加されたとき

## ワークフロー

### 1. 現在の用語集分析

```
Read docs/glossary.md
```

用語集の現在のセクション構造と既存用語リストを把握する。セクション構造は `references/glossary-structure.md` を参照。

### 2. ソース分析（変更タイプに応じて選択）

#### A. 文書ベース分析（PRD/FRD 変更時）

```
# 変更された PRD/FRD 文書を読む
Read docs/features/{feature-number}/PRD-*.md
Read docs/features/{feature-number}/FRD-*.md

# 新用語抽出: 太字(**term**)、テーブル定義、新概念
```

#### B. コードベース分析（コード変更時） - Feature-First 構造

```
# 新しく追加された enum/モデル確認（Feature-First）
Glob lib/features/**/data/models/*.dart
Grep "enum " lib/features/**/data/models/
Grep "@freezed" lib/features/**/data/models/

# 新 Repository/ViewModel 確認（Feature-First）
Glob lib/features/**/data/repositories/*.dart
Glob lib/features/**/presentation/viewmodels/*.dart
```

#### C. データベース分析（スキーマ変更時）

```
# マイグレーションファイル確認
Read infra/supabase/migrations/_migrations_list.json
Glob infra/supabase/migrations/*.sql
```

### 3. 欠落用語識別

既存用語集とソースを比較して欠落した用語を識別する:

- 新 enum 値（例: `LessonPhase`, `DirectorMode`）
- 新データモデル（例: `WrongNote`, `StreakModel`）
- 新 DB テーブル
- PRD/FRD で定義された新概念

### 4. 用語追加

#### 用語追加形式

各セクションに適したテーブル形式で追加:

**ビジネス/学習システム用語:**

```markdown
| **Term** | 韓国語 | 説明 | 実装例 |
```

**技術用語:**

```markdown
| **Term** | 説明 | 実装 |
```

**データベーステーブル:**

```markdown
| **table_name** | 用途 | 備考 |
```

#### セクション選択基準

`references/glossary-structure.md` のセクション分類基準に従う。

### 5. 検証および完了

1. 目次と本文のセクション番号一致確認
2. マークダウンテーブル形式検証
3. 改訂履歴更新（バージョン番号増加）

## 注意事項

- **重複防止**: 既に存在する用語は追加しない
- **一貫した形式**: 既存テーブル形式と同じように維持
- **韓国語説明**: すべての説明は韓国語で作成
- **実装例**: 可能であれば実際のファイル名/テーブル名を明示

## Resources

### references/

- `glossary-structure.md`: 用語集セクション構造および分類基準
