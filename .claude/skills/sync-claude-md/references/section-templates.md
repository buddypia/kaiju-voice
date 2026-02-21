# CLAUDE.md セクション別テンプレート

> Hackathon Project プロジェクトの CLAUDE.md 各セクション作成標準テンプレート

## プロジェクト識別情報

```markdown
## 🎯 プロジェクト識別情報

| 項目                 | 値                                                            |
| -------------------- | ------------------------------------------------------------- |
| **プロジェクト名**   | Hackathon Project                                                 |
| **プラットフォーム** | Flutter (iOS/Android)                                         |
| **アーキテクチャ**   | Feature-First + Simplified Clean Architecture + Riverpod 2.6+ |
| **バックエンド**     | Supabase (PostgreSQL)                                         |
| **状態管理**         | Riverpod (コード生成)                                         |
| **データモデル**     | Freezed (不変)                                                |
| **Dart SDK**         | >=3.8.0 <4.0.0                                                |
| **サポート言語**     | 日本語(ja, デフォルト), 英語(en), 韓国語(ko)                  |

**核心特徴**: AI 生成コンテンツ基盤の韓国語学習アプリ、音声中心学習、オフラインファースト
```

## 主要ライブラリバージョン

```markdown
### 主要ライブラリバージョン

| カテゴリ                     | ライブラリ                     | バージョン |
| ---------------------------- | ------------------------------ | ---------- |
| **状態管理**                 | flutter_riverpod               | X.X.X      |
| **不変モデル**               | freezed                        | X.X.X      |
| **JSONシリアライゼーション** | json_serializable              | X.X.X      |
| **バックエンド**             | supabase_flutter               | X.X.X      |
| **収益化**                   | purchases_flutter (RevenueCat) | X.X.X      |
| **認証**                     | google_sign_in                 | X.X.X      |
| **オーディオ**               | audioplayers                   | X.X.X      |
| **TTS**                      | flutter_tts                    | X.X.X      |
| **音声認識**                 | speech_to_text                 | X.X.X      |
| **UIテキスト管理**           | messages.ts (自前定義)         | -          |

> 全体リスト: [tech-stack-rules.md](./docs/technical/tech-stack-rules.md)
```

## 準拠事項

````markdown
## ✅ 準拠事項 (Rules to Follow)

### 必須ルール (MUST)

1. **ルール名**: 説明
2. **ルール名**: 説明

### 品質チェック

```bash
flutter analyze          # 静的分析 (エラー 0 必須)
flutter test             # テスト実行
flutter pub run build_runner build --delete-conflicting-outputs  # コード生成
```
````

### 推奨事項 (SHOULD)

1. **ルール名**: 説明

### 禁止事項 (MUST NOT)

| パターン     | 理由     | 代替     |
| ------------ | -------- | -------- |
| `パターン名` | 禁止理由 | 推奨代替 |

````

## Supabase バックエンド

```markdown
## ☁️ Supabase バックエンド

### プロジェクト情報

| 項目 | 値 |
|------|-----|
| **Project ID** | `lwbmgbapiqsrlixtogqu` |
| **Region** | `ap-northeast-1` (Tokyo) |
| **API URL** | https://lwbmgbapiqsrlixtogqu.supabase.co |

### Edge Functions

| 関数名 | 用途 |
|--------|------|
| `function-name` | 機能説明 |

### 主要ドメインテーブル

| ドメイン | テーブル |
|--------|--------|
| ドメイン名 | `table1`, `table2` |

詳細: **[Supabase Overview](./docs/supabase-overview.md)**, **[データベーススキーマ](./docs/database-schema/README.md)**
````

## 言語設定

```markdown
## 言語設定

| 言語   | コード | 役割               |
| ------ | ------ | ------------------ |
| 日本語 | `ja`   | **唯一の対応言語** |

### 主要ファイル

| ファイル                           | 役割                    |
| ---------------------------------- | ----------------------- |
| `src/shared/constants/messages.ts` | UIテキスト定義 (日本語) |

### ルール

- UIテキストは `messages.ts` で一元管理
- 日本語専用プロジェクト
```

## 特殊設定

````markdown
## ⚙️ 特殊設定および注意事項

### Dependency Overrides

> **⚠️ 重要**: `pubspec.yaml`に `dependency_overrides` が設定されています。

```yaml
dependency_overrides:
  package_name:
    git:
      url: https://github.com/...
      ref: branch_name
```
````

- **背景**: 設定理由の説明
- **注意**: アップグレード時に検討必要

### 環境変数

| 変数名     | 説明     |
| ---------- | -------- |
| `VAR_NAME` | 変数説明 |

- `.env.local` (開発用), `.env.production` (プロダクション用) - すべて git 無視

````

## ドキュメントリンクセクション

```markdown
## 📚 主要ドキュメントリンク

### 必須参照

| ドキュメント | 内容 |
|------|------|
| **[ドキュメント名](パス)** | 説明 |

### 開発ガイド

| ドキュメント | 内容 |
|------|------|
| **[ドキュメント名](パス)** | 説明 |
````

## スタイルガイド

### 絵文字使用

| セクション           | 絵文字 |
| -------------------- | ------ |
| プロジェクト識別情報 | 🎯     |
| 準拠事項             | ✅     |
| エージェント運用     | 🤖     |
| アーキテクチャ       | 🏗️     |
| プロジェクト構造     | 📁     |
| 開発ワークフロー     | 🛠️     |
| コードスタイル       | 🎨     |
| Supabase             | ☁️     |
| 言語設定             | 🌐     |
| ビジネスコンテキスト | 👤     |
| ドキュメントリンク   | 📚     |
| 特殊設定             | ⚙️     |
| Git/GitHub           | 🔀     |

### テーブル整列

```markdown
| 項目         | 値  |
| ------------ | --- |
| **太字キー** | 値  |
```

### コードブロック

言語指定必須:

````markdown
```bash
コマンド
```
````

```dart
コード
```

```yaml
設定
```

```

```
