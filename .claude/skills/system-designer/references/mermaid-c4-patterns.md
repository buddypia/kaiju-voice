# Mermaid C4 パターンガイド

> Mermaid の C4 拡張構文を使用してシステム設計図を生成するためのガイド。
> プロジェクト プロジェクトでの具体的なサンプルを含む。

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

### プロジェクト サンプル: System Context

```mermaid
C4Context
  title System Context diagram for プロジェクト

  Person(player, "プレイヤー", "AI対戦ゲームをプレイするユーザー")

  System(gameSystem, "プロジェクト", "AI駆動のゲーム対戦Webアプリ")

  System_Ext(imagen3, "Imagen 3", "画像生成")
  System_Ext(geminiAI, "Gemini AI", "AI対戦ロジック・コンテンツ生成")
  System_Ext(liveAPI, "Live API", "リアルタイム音声・映像対話")

  Rel(player, gameSystem, "対戦する")
  Rel(gameSystem, imagen3, "画像生成を要求")
  Rel(gameSystem, geminiAI, "AI対戦を要求")
  Rel(gameSystem, liveAPI, "リアルタイム対話")
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
3. **Container** の第3引数に技術スタックを明記する（例: "Next.js/React", "Next.js/TypeScript"）
4. **ContainerDb** をデータベースに使用する（通常の Container と区別）
5. **Rel** の第3引数に通信プロトコルを明記する（例: "HTTPS", "Client SDK"）
6. 第4引数（任意）でより詳細な技術情報を追加可能

### プロジェクト サンプル: Container

```mermaid
C4Container
  title Container diagram for プロジェクト

  Person(player, "プレイヤー")

  Container(webapp, "Next.js Web App", "Next.js/React", "UI表示、状態管理(React Hooks)")
  ContainerDb(db, "データベース", "ゲームデータ", "ユーザーデータ、対戦データ")
  Container(apiRoutes, "API Routes", "Next.js/TypeScript", "AI対戦ロジック、コンテンツ生成")

  System_Ext(imagen3, "Imagen 3")
  System_Ext(geminiAI, "Gemini AI")
  System_Ext(liveAPI, "Live API")

  Rel(player, webapp, "HTTPS")
  Rel(webapp, db, "Client SDK")
  Rel(webapp, apiRoutes, "HTTPS/REST")
  Rel(apiRoutes, geminiAI, "Gemini API")
  Rel(apiRoutes, imagen3, "Imagen API")
  Rel(webapp, liveAPI, "Live API SDK")
```

---

## 4. シーケンス図（データフロー用）

C4 の補助として、主要なデータフローを Mermaid シーケンス図で表現します。

### 基本構造

```mermaid
sequenceDiagram
  actor User as プレイヤー
  participant App as Next.js Web App
  participant DB as データベース
  participant EF as API Routes
  participant AI as Gemini AI

  User->>App: 対戦開始
  App->>DB: 対戦データ取得
  DB-->>App: 対戦データ
  App->>EF: AI コンテンツ要求
  EF->>AI: プロンプト送信
  AI-->>EF: 生成コンテンツ
  EF-->>App: コンテンツ返却
  App-->>User: 対戦画面表示
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
  actor User as プレイヤー
  participant App as Next.js Web App
  participant EF as API Routes
  participant AI as Gemini AI

  User->>App: AIに対戦リクエスト
  App->>EF: 対戦リクエスト
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

  Person(player, "プレイヤー")

  Boundary(b0, "プロジェクト System") {
    Container(webapp, "Next.js Web App", "Next.js/React", "フロントエンド")
    ContainerDb(db, "データベース", "ゲームデータ", "データストア")
    Container(apiRoutes, "API Routes", "Next.js/TypeScript", "サーバーレスAPI")
  }

  Boundary(b1, "External Services") {
    System_Ext(imagen3, "Imagen 3")
    System_Ext(geminiAI, "Gemini AI")
  }

  Rel(player, webapp, "HTTPS")
  Rel(webapp, db, "Client SDK")
  Rel(webapp, apiRoutes, "HTTPS/REST")
  Rel(apiRoutes, geminiAI, "Gemini API")
  Rel(apiRoutes, imagen3, "Imagen API")
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
| Person          | `<role>`                    | `player`, `admin`      |
| System          | `<systemName>` (camelCase)  | `gameSystem`          |
| Container (App) | `<appType>`                 | `webapp`, `mobileApp`   |
| Container (DB)  | `db` or `<dbName>`          | `db`, `cacheDb`         |
| Container (API) | `<apiName>`                 | `apiRoutes`, `authApi`     |
| External System | `<serviceName>` (camelCase) | `imagen3`, `geminiAI` |

---

## 6. 機能別の拡張パターン

新機能を追加する際、標準コンテナ図に追加要素を重ねる方法:

### パターン A: 新しい Edge Function を追加

```mermaid
C4Container
  title Container diagram - Feature: 029-battle-content

  Person(player, "プレイヤー")

  Container(webapp, "Next.js Web App", "Next.js/React", "対戦UI")
  ContainerDb(db, "データベース", "ゲームデータ", "battles テーブル")
  Container(apiRoutes, "API Routes", "Next.js/TypeScript", "既存 API Routes")
  Container(newApiRoute, "generate-battle-content", "Next.js/TypeScript", "対戦コンテンツ生成 (新規)")

  System_Ext(geminiAI, "Gemini AI")

  Rel(player, webapp, "HTTPS")
  Rel(webapp, db, "Client SDK")
  Rel(webapp, newApiRoute, "HTTPS/REST")
  Rel(newApiRoute, geminiAI, "Gemini API")
```

### パターン B: 外部サービスを追加

新しい外部サービス連携が必要な場合:

```mermaid
C4Container
  title Container diagram - Feature: XXX-new-feature

  Person(player, "プレイヤー")

  Container(webapp, "Next.js Web App", "Next.js/React", "フロントエンド")
  ContainerDb(db, "データベース", "ゲームデータ", "データストア")
  Container(apiRoutes, "API Routes", "Next.js/TypeScript", "サーバーレスAPI")

  System_Ext(geminiAI, "Gemini AI")
  System_Ext(newService, "新外部サービス", "新サービスの説明")

  Rel(player, webapp, "HTTPS")
  Rel(webapp, db, "Client SDK")
  Rel(webapp, apiRoutes, "HTTPS/REST")
  Rel(apiRoutes, geminiAI, "Gemini API")
  Rel(apiRoutes, newService, "REST API")
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
