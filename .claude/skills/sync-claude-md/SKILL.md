---
name: sync-claude-md
description: Hackathon Project プロジェクトの CLAUDE.md 文書をプロジェクト変更事項と同期するスキル。新しいライブラリ追加、Edge Function 変更、DB スキーマ更新後に CLAUDE.md 更新が必要か確認して案内する。「CLAUDE.md 更新」、「文書同期」、「プロジェクト指針更新」等のリクエストでトリガーされる。
doc_contract:
  review_interval_days: 90
---

# CLAUDE.md Updater

## Overview

Hackathon Project プロジェクトの `CLAUDE.md` は AI コーディングアシスタントの唯一の Source of Truth である。このスキルはプロジェクト変更事項が発生した時に CLAUDE.md を同期し、最新状態を維持する方法を案内する。

## トリガー条件

次の状況でこのスキル使用を提案する:

1. **ライブラリ追加/更新**: `pubspec.yaml` 変更後
2. **Edge Function 追加/修正**: `infra/supabase/functions/` 変更後
3. **DB スキーマ変更**: 新しいマイグレーション追加後
4. **アーキテクチャ変更**: 新しいパターンや規則導入時
5. **明示的リクエスト**: 「CLAUDE.md 更新」、「文書同期」

## CLAUDE.md 構造

| セクション                   | 内容                           | 更新トリガー         |
| ---------------------------- | ------------------------------ | -------------------- |
| **プロジェクト識別情報**     | SDK バージョン、サポート言語   | SDK 変更、言語追加   |
| **主要ライブラリバージョン** | 核心パッケージバージョン       | pubspec.yaml 変更    |
| **遵守事項**                 | MUST/SHOULD/MUST NOT 規則      | コーディング規則変更 |
| **アーキテクチャ概要**       | Feature-First ダイアグラム     | アーキテクチャ変更   |
| **プロジェクト構造**         | フォルダ構造                   | 新フォルダ追加       |
| **Supabase バックエンド**    | Edge Functions、テーブル       | バックエンド変更     |
| **言語設定**                 | プロジェクト言語設定           | 言語設定変更         |
| **ビジネスコンテキスト**     | 目標、L1 ブリッジ戦略          | 戦略変更             |
| **特殊設定**                 | dependency_overrides、環境変数 | 設定変更             |

## ワークフロー

### 1. 変更事項検出

```
# ライブラリ変更検出
Read pubspec.yaml (dependencies セクション)

# Edge Function 変更検出
Glob infra/supabase/functions/*/index.ts

# マイグレーション変更検出
Read infra/supabase/migrations/_migrations_list.json
```

### 2. CLAUDE.md 現在状態確認

```
Read CLAUDE.md

# 主要セクション確認
- ライブラリバージョンテーブル
- Edge Functions リスト
- 主要ドメインテーブル
```

### 3. 不一致項目識別

```
## CLAUDE.md 同期必要項目

### ライブラリバージョン
| パッケージ | CLAUDE.md | pubspec.yaml | 措置 |
|--------|-----------|--------------|------|
| flutter_riverpod | 2.6.1 | 2.6.1 | ✅ 一致 |
| supabase_flutter | 2.9.0 | 2.9.1 | ❌ 更新必要 |

### Edge Functions
| 関数名 | CLAUDE.md | 実際フォルダ | 措置 |
|--------|-----------|-----------|------|
| ai-tutor-chat | ✅ | ✅ | 一致 |
| new-function | ❌ | ✅ | 追加必要 |
```

### 4. 更新実行

各セクション別更新方法:

#### A. ライブラリバージョン更新

```markdown
### 主要ライブラリバージョン

| カテゴリー       | ライブラリ       | バージョン |
| ---------------- | ---------------- | ---------- | ------ |
| **状態管理**     | flutter_riverpod | 2.6.1      |
| **バックエンド** | supabase_flutter | 2.9.1      | ← 更新 |
```

#### B. Edge Functions リスト更新

```markdown
### Edge Functions

| 関数名          | 用途                      |
| --------------- | ------------------------- | ------ |
| `ai-tutor-chat` | Gemini 基盤 AI チューター |
| `new-function`  | 新機能説明                | ← 追加 |
```

#### C. ドメインテーブル更新

```markdown
### 主要ドメインテーブル

| ドメイン      | テーブル                                      |
| ------------- | --------------------------------------------- | ------ |
| AI チューター | `ai_tutor_conversations`, `ai_tutor_messages` |
| 新ドメイン    | `new_table`                                   | ← 追加 |
```

### 5. 結果報告

```
## CLAUDE.md 同期結果

### 更新された項目
✅ supabase_flutter バージョン: 2.9.0 → 2.9.1
✅ Edge Function 追加: new-function
✅ テーブル追加: new_table

### 確認必要項目
⚠️ dependency_overrides セクション検討必要

### 未変更項目
- プロジェクト識別情報
- 遵守事項
- アーキテクチャ概要
```

## セクション別更新規則

### 主要ライブラリバージョン (核心のみ)

次のパッケージのみ CLAUDE.md に記録:

```
flutter_riverpod, freezed, json_serializable,
supabase_flutter, purchases_flutter, google_sign_in,
audioplayers, flutter_tts, speech_to_text, intl
```

その他パッケージは `tech-stack-rules.md` 参照で代替。

### Edge Functions

全ての Edge Function をテーブルに含むが、必須シークレット情報も一緒に記録:

```markdown
| 関数名          | 用途          | 必須シークレット |
| --------------- | ------------- | ---------------- |
| `ai-tutor-chat` | AI チューター | `GEMINI_API_KEY` |
```

### 遵守事項変更

新規則追加時次の様式使用:

```markdown
### 必須規則 (MUST)

N. **規則名**: 説明
```

## 自動化検査項目

| 検査                 | 方法                           | 不一致時           |
| -------------------- | ------------------------------ | ------------------ |
| ライブラリバージョン | pubspec.yaml vs CLAUDE.md 比較 | バージョン更新     |
| Edge Functions       | フォルダ vs CLAUDE.md 比較     | 関数追加/削除      |
| 言語設定             | CLAUDE.md 確認                 | 言語設定更新       |
| Dart SDK             | pubspec.yaml vs CLAUDE.md 比較 | SDK バージョン更新 |

## 注意事項

- **一貫性維持**: テーブル形式、絵文字使用等既存スタイル維持
- **最小変更**: 変更された項目のみ更新、不要なフォーマット変更禁止
- **リンク検証**: 文書リンク追加/変更時有効性確認
- **目次同期化**: セクション追加/削除時目次も更新

## Resources

### references/

- `section-templates.md`: CLAUDE.md セクション別作成テンプレート

このスキルは別途実行スクリプトが必要ない。ファイル比較と編集ツールで同期化を実行する。
