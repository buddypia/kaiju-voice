# Mermaid C4 パターンガイド

> Mermaid の C4 拡張構文を使用してシステム設計図を生成するためのガイド。
> Hackathon Project プロジェクトでの具体的なサンプルを含む。

---

## 1. Mermaid C4 拡張構文の基本

Mermaid は C4 Model の図を直接サポートしています。以下の図タイプが利用可能です:

| 図タイプ       | Mermaid キーワード | C4 レベル                |
| -------------- | ------------------ | ------------------------ |
| System Context | `C4Context`        | Level 1                  |
| Container      | `C4Container`      | Level 2                  |
| Component      | `C4Component`      | Level 3 (Phase 0 不使用) |
| Dynamic        | `C4Dynamic`        | 動的図 (任意)            |

### 共通要素

| 要素          | 構文                                           | 説明                 |
| ------------- | ---------------------------------------------- | -------------------- |
| Person        | `Person(alias, "名前", "説明")`                | ユーザー/アクター    |
| Person_Ext    | `Person_Ext(alias, "名前", "説明")`            | 外部ユーザー         |
| System        | `System(alias, "名前", "説明")`                | 構築対象システム     |
| System_Ext    | `System_Ext(alias, "名前", "説明")`            | 外部システム         |
| SystemDb      | `SystemDb(alias, "名前", "説明")`              | 外部データベース     |
| SystemDb_Ext  | `SystemDb_Ext(alias, "名前", "説明")`          | 外部データベース     |
| Container     | `Container(alias, "名前", "技術", "説明")`     | コンテナ             |
| ContainerDb   | `ContainerDb(alias, "名前", "技術", "説明")`   | データベースコンテナ |
| Container_Ext | `Container_Ext(alias, "名前", "技術", "説明")` | 外部コンテナ         |
| Relationship  | `Rel(from, to, "ラベル")`                      | 関係線               |
| Relationship  | `Rel(from, to, "ラベル", "技術")`              | 技術付き関係線       |

---

## 2. C4Context Diagram の書き方

### 基本構造

```mermaid
C4Context
  title システムコンテキスト図のタイトル

  Person(alias1, "ユーザー名", "ユーザーの説明")

  System(alias2, "システム名", "システムの説明")

  System_Ext(alias3, "外部システム名", "外部システムの説明")

  Rel(alias1, alias2, "関係の説明")
  Rel(alias2, alias3, "関係の説明")
```

### 記述ルール

1. **title** は必ず先頭に記述する
2. **Person** → **System** → **System_Ext** の順に定義する
3. **Rel** は要素定義の後にまとめて記述する
4. **alias** はキャメルケースまたはスネークケースで一意に命名する
5. **説明文** は日本語で簡潔に記述する（50文字以内目安）

### Hackathon Project サンプル: System Context

```mermaid
C4Context
  title System Context diagram for Hackathon Project

  Person(learner, "学習者", "韓国語を学ぶユーザー")

  System(vibeMentorAI, "Hackathon Project", "AI駆動の韓国語学習Webアプリ")

  System_Ext(googleTTS, "Google Cloud TTS", "テキスト音声変換")
  System_Ext(geminiAI, "Gemini AI", "AIコンテンツ生成・チュータリング")
  System_Ext(revenueCat, "RevenueCat", "サブスクリプション管理")

  Rel(learner, vibeMentorAI, "学習する")
  Rel(vibeMentorAI, googleTTS, "音声を要求")
  Rel(vibeMentorAI, geminiAI, "AI処理を要求")
  Rel(vibeMentorAI, revenueCat, "課金を管理")
```

---

## 3. C4Container Diagram の書き方

### 基本構造

```mermaid
C4Container
  title コンテナ図のタイトル

  Person(alias1, "ユーザー名")

  Container(alias2, "コンテナ名", "技術スタック", "責務の説明")
  ContainerDb(alias3, "DB名", "技術", "データの説明")
  Container(alias4, "API名", "技術", "API の説明")

  System_Ext(alias5, "外部システム名")

  Rel(alias1, alias2, "プロトコル")
  Rel(alias2, alias3, "プロトコル")
  Rel(alias4, alias5, "API名")
```

### 記述ルール

1. **title** は必ず先頭に記述する
2. 定義順序: **Person** → **Container/ContainerDb** → **System_Ext** → **Rel**
3. **Container** の第3引数に技術スタックを明記する（例: "Flutter/Dart", "Deno/TypeScript"）
4. **ContainerDb** をデータベースに使用する（通常の Container と区別）
5. **Rel** の第3引数に通信プロトコルを明記する（例: "HTTPS", "Supabase Client SDK"）
6. 第4引数（任意）でより詳細な技術情報を追加可能

### Hackathon Project サンプル: Container

```mermaid
C4Container
  title Container diagram for Hackathon Project

  Person(learner, "学習者")

  Container(webapp, "Flutter Web App", "Flutter/Dart", "UI表示、状態管理(Riverpod)")
  ContainerDb(db, "Supabase PostgreSQL", "PostgreSQL", "ユーザーデータ、学習データ")
  Container(edgeFn, "Edge Functions", "Deno/TypeScript", "AIチュータ、コンテンツ生成")

  System_Ext(googleTTS, "Google Cloud TTS")
  System_Ext(geminiAI, "Gemini AI")
  System_Ext(revenueCat, "RevenueCat")

  Rel(learner, webapp, "HTTPS")
  Rel(webapp, db, "Supabase Client SDK")
  Rel(webapp, edgeFn, "HTTPS/REST")
  Rel(edgeFn, geminiAI, "Gemini API")
  Rel(edgeFn, googleTTS, "Cloud TTS API")
  Rel(webapp, revenueCat, "RevenueCat SDK")
```

---

## 4. シーケンス図（データフロー用）

C4 の補助として、主要なデータフローを Mermaid シーケンス図で表現します。

### 基本構造

```mermaid
sequenceDiagram
  actor User as 学習者
  participant App as Flutter Web App
  participant DB as Supabase PostgreSQL
  participant EF as Edge Functions
  participant AI as Gemini AI

  User->>App: 学習開始
  App->>DB: 学習データ取得
  DB-->>App: 学習データ
  App->>EF: AI コンテンツ要求
  EF->>AI: プロンプト送信
  AI-->>EF: 生成コンテンツ
  EF-->>App: コンテンツ返却
  App-->>User: 学習画面表示
```

### 記述ルール

1. **actor** を人間のユーザーに使用する
2. **participant** をシステムコンポーネントに使用する
3. `->>` は同期リクエスト、`-->>` はレスポンスに使用する
4. 日本語のラベルで動作を説明する
5. エラーフローは `alt` / `else` ブロックで表現する

### エラーフローの例

```mermaid
sequenceDiagram
  actor User as 学習者
  participant App as Flutter Web App
  participant EF as Edge Functions
  participant AI as Gemini AI

  User->>App: AI チュータに質問
  App->>EF: チャットリクエスト
  EF->>AI: プロンプト送信

  alt 成功
    AI-->>EF: AI 応答
    EF-->>App: 応答返却
    App-->>User: 回答表示
  else AI エラー
    AI-->>EF: エラー応答
    EF-->>App: エラー (500)
    App-->>User: エラーメッセージ表示 + リトライボタン
  else タイムアウト
    EF-->>App: タイムアウト (504)
    App-->>User: タイムアウトメッセージ + リトライボタン
  end
```

---

## 5. スタイリングとレイアウトの Tips

### Boundary（境界線）の使用

システムの境界を視覚的に明示するために `Boundary` を使用できます:

```mermaid
C4Container
  title Container diagram with Boundaries

  Person(learner, "学習者")

  Boundary(b0, "Hackathon Project System") {
    Container(webapp, "Flutter Web App", "Flutter/Dart", "フロントエンド")
    ContainerDb(db, "Supabase PostgreSQL", "PostgreSQL", "データストア")
    Container(edgeFn, "Edge Functions", "Deno/TypeScript", "サーバーレスAPI")
  }

  Boundary(b1, "External Services") {
    System_Ext(googleTTS, "Google Cloud TTS")
    System_Ext(geminiAI, "Gemini AI")
  }

  Rel(learner, webapp, "HTTPS")
  Rel(webapp, db, "Supabase Client SDK")
  Rel(webapp, edgeFn, "HTTPS/REST")
  Rel(edgeFn, geminiAI, "Gemini API")
  Rel(edgeFn, googleTTS, "Cloud TTS API")
```

### レイアウトのベストプラクティス

1. **要素数の制限**: 1つの図に15個以上の要素を入れない
2. **左から右への流れ**: ユーザー → フロントエンド → バックエンド → 外部サービスの順
3. **Boundary の活用**: 論理的なグループ化で見やすさを向上
4. **一貫した alias 命名**: 図をまたいで同じ要素には同じ alias を使用
5. **説明の簡潔さ**: 各要素の説明は1-2行以内に収める

### alias 命名規則

| 要素タイプ      | 命名パターン                | 例                      |
| --------------- | --------------------------- | ----------------------- |
| Person          | `<role>`                    | `learner`, `admin`      |
| System          | `<systemName>` (camelCase)  | `vibeMentorAI`          |
| Container (App) | `<appType>`                 | `webapp`, `mobileApp`   |
| Container (DB)  | `db` or `<dbName>`          | `db`, `cacheDb`         |
| Container (API) | `<apiName>`                 | `edgeFn`, `authApi`     |
| External System | `<serviceName>` (camelCase) | `googleTTS`, `geminiAI` |

---

## 6. 機能別の拡張パターン

新機能を追加する際、標準コンテナ図に追加要素を重ねる方法:

### パターン A: 新しい Edge Function を追加

```mermaid
C4Container
  title Container diagram - Feature: 029-vocabulary-book

  Person(learner, "学習者")

  Container(webapp, "Flutter Web App", "Flutter/Dart", "単語帳UI")
  ContainerDb(db, "Supabase PostgreSQL", "PostgreSQL", "vocabularies テーブル")
  Container(edgeFn, "Edge Functions", "Deno/TypeScript", "既存 Edge Functions")
  Container(newEdgeFn, "generate-vocab-quiz", "Deno/TypeScript", "単語クイズ生成 (新規)")

  System_Ext(geminiAI, "Gemini AI")

  Rel(learner, webapp, "HTTPS")
  Rel(webapp, db, "Supabase Client SDK")
  Rel(webapp, newEdgeFn, "HTTPS/REST")
  Rel(newEdgeFn, geminiAI, "Gemini API")
```

### パターン B: 外部サービスを追加

新しい外部サービス連携が必要な場合:

```mermaid
C4Container
  title Container diagram - Feature: XXX-new-feature

  Person(learner, "学習者")

  Container(webapp, "Flutter Web App", "Flutter/Dart", "フロントエンド")
  ContainerDb(db, "Supabase PostgreSQL", "PostgreSQL", "データストア")
  Container(edgeFn, "Edge Functions", "Deno/TypeScript", "サーバーレスAPI")

  System_Ext(geminiAI, "Gemini AI")
  System_Ext(newService, "新外部サービス", "新サービスの説明")

  Rel(learner, webapp, "HTTPS")
  Rel(webapp, db, "Supabase Client SDK")
  Rel(webapp, edgeFn, "HTTPS/REST")
  Rel(edgeFn, geminiAI, "Gemini API")
  Rel(edgeFn, newService, "REST API")
```

---

## 7. よくある間違いと対策

| 間違い               | 問題点                   | 対策                                     |
| -------------------- | ------------------------ | ---------------------------------------- |
| `Rel` にラベルなし   | 何が流れているか不明     | 必ず通信プロトコルまたはデータ種別を記載 |
| Person に技術を記載  | Level 1 では不要         | Person は名前と説明のみ                  |
| Container に実装詳細 | Level 2 の抽象度を超える | 技術スタック名のみ記載                   |
| alias の重複         | レンダリングエラー       | 図全体で一意の alias を使用              |
| 日本語 alias         | 一部レンダラーで問題     | alias は英語、説明文は日本語             |
| 要素の過多           | 読みにくい               | 1図15要素以下に制限                      |

---

## 8. 参考資料

- [Mermaid C4 公式ドキュメント](https://mermaid.js.org/syntax/c4.html)
- [C4 Model 公式サイト](https://c4model.com/)
- [C4モデルガイド](./c4-model-guide.md) - 本プロジェクトでの C4 適用方針
