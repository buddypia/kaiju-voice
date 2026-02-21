# {NNN}: {機能名}

> **状態**: {STATUS} ({PROGRESS}%) | **優先度**: {PRIORITY} | **修正日**: {DATE}
> **SPEC バージョン**: v3.5 (2026-01-28) - §0.2 状態 & アーキテクチャの再編 (処方的→原則基盤)、AI 設計自律性の強化
> **Tier**: {1/2/3} - {高/中/低 リスク} | **機能タイプ**: {UI のみ/API 連携/AI 使用/決済}
>
> ⚡ **クイックリファレンス**: Tier/機能タイプ別必須セクションは [文書下部マトリックス](#tier-選択-基準) を参照

---

## 0. AI 実装契約 (必須)

> **目的**: AI が実装開始前に把握すべき核心情報を一目で提供
> **原則**: AI が "推測" すべき情報 = 0

### 0.0 プロジェクトコンテキスト (v3.1 軽量化)

> **SSOT**: [docs/technical/project-context.md](../../technical/project-context.md)
> **原則**: 共通規約は上記文書参照、この SPEC には **差分(この機能固有事項)のみ**記述

#### 0.0.1 共通規約適用確認

<!-- 下記チェックリストで共通規約参照確認後作成 -->

- [ ] Naming: [project-context.md §1](../../technical/project-context.md#1-naming-conventions-名命規則) 準拠
- [ ] Provider: [project-context.md §2](../../technical/project-context.md#2-provider-specifications-共通) 参照
- [ ] Error Handling: [project-context.md §3](../../technical/project-context.md#3-error-handling-共通-政策) 基盤
- [ ] Design Tokens: [project-context.md §4](../../technical/project-context.md#4-design-tokens-共通) 使用

#### 0.0.2 この機能の差分 (Feature-Specific Overrides)

<!-- 共通規約と異なる部分のみ記述。なければ "共通規約そのまま適用" 明記 -->

| 項目   | 共通規約対比差分 | 理由           |
| ------ | ---------------- | -------------- |
| {項目} | {差分内容}       | {なぜ異なるか} |

**共通規約そのまま適用**: {該当なければこの行のみ残し上テーブル削除}

#### 0.0.3 この機能固有用語 (Feature-Specific Glossary)

> **全体用語集**: [docs/glossary.md](../glossary.md)
> 下記はこの機能で **新たに定義または特別に使用**する用語のみ記述

| 用語    | 定義   | コード表現    |
| ------- | ------ | ------------- |
| {Term1} | {定義} | `{ClassName}` |

<!-- 固有用語がなければ "該当なし - 共通用語集参照" 明記 -->

> ℹ️ 用語追加時: glossary.mdに先に登録 → SPEC で参照

### 0.1 ターゲットファイル (v3.1 範囲ベース)

> **v3.1 変更**: 具体的ファイルパスの代わりに **Glob パターン** 使用
> **SSOT**: CONTEXT.jsonの `references.related_code` が実際のファイルリスト管理
> **目的**: 柔軟な範囲定義 + 条件付きファイルサポート

| レイヤー  | 範囲 (Glob)                            | 作業 | 条件      | 備考                                |
| --------- | -------------------------------------- | :--: | --------- | ----------------------------------- |
| Type      | `src/features/{feature}/types/**`      |  🆕  | -         | TypeScript interface + Zod スキーマ |
| Hook      | `src/features/{feature}/hooks/**`      |  🆕  | -         | React Custom Hook (状態管理)        |
| API       | `src/features/{feature}/api/**`        |  🆕  | -         | データフェッチ/API呼び出し          |
| Component | `src/features/{feature}/components/**` |  🆕  | -         | UI コンポーネント (.tsx)            |
| Test      | `tests/unit/features/{feature}/**`     |  🆕  | -         | 単体テスト (Vitest)                 |
| API Route | `src/app/api/{name}/**`                |  ⚡  | API必要時 | 条件付き                            |

**作業タイプ**: 🆕 新規作成 / 🔄 既存修正 / ⚡ 条件付き

#### 0.1.1 トレース可能性マトリクス (Traceability Matrix)

> **検証方法**: すべての FR-ID が最低 1 つの実装ファイルと 1 つのテストに接続されている必要がある
> **実装後作成**: 実装完了時に CONTEXT.json の references から自動抽出推奨

|   FR-ID    | 実装ファイル (Glob内)        | テストファイル | 検証状態 |
| :--------: | ---------------------------- | -------------- | :------: |
| FR-{NNN}01 | `{ファイル1}`, `{ファイル2}` | `{テスト1}`    |    ⬜    |
| FR-{NNN}02 | `{ファイル3}`                | `{テスト2}`    |    ⬜    |

<!--
トレース可能性規則:
- すべての FR は最低 1 つの実装ファイルに接続
- すべての FR は最低 1 つのテストに接続 (Tier 3 除外)
- 実装ファイル変更時に関連 FR-ID 注釈必須: // FR-{NNN}XX
- 具体的ファイルリストは CONTEXT.json references で管理 (SSOT)
-->

### 0.2 状態 & アーキテクチャ (v3.5 改編)

> **v3.5 変更**: 処方的 Provider リスト → 原則に基づくガイドライン
> **参照**: [spec-sections.md §0.2](../_templates/../.claude/skills/feature-spec-generator/references/spec-sections.md)

#### 0.2.1 コア状態 (必須)

> **目的**: AI が管理すべき核心状態要素定義
> **原則**: 状態構造は明示するが、実装ファイル数は AI が SRP 基準で決定

| 状態要素   | タイプ                 | 必須 | 用途                          | 初期値   |
| ---------- | ---------------------- | :--: | ----------------------------- | -------- |
| `items`    | `{Entity}[]`           |  ✅  | データ一覧                    | `[]`     |
| `status`   | `ScreenStatus`         |  ✅  | Idle/Loading/Data/Empty/Error | `'idle'` |
| `error`    | `Error \| null`        |  ⚪  | エラー情報                    | `null`   |
| `{filter}` | `{FilterType} \| null` |  ⚪  | フィルター条件                | `null`   |

**状態 type 定義**:

```typescript
type ScreenStatus = 'idle' | 'loading' | 'data' | 'empty' | 'error';
```

**派生状態 (該当時)**:
| 派生状態 | 計算式 | 用途 |
|----------|--------|------|
| `hasData` | `status == data && items.isNotEmpty` | データ表示条件 |
| `filteredItems` | `filter?.apply(items) ?? items` | フィルタリングされた一覧 |

#### 0.2.2 アーキテクチャガイダンス (ガイドライン)

> **目的**: AI が SRP 原則に従って自律的にファイル分離できるよう案内
> **核心**: 具体的ファイルリストの代わりに分離基準とネーミング規則を提供

**Custom Hook 分離基準** (詳細: spec-sections.md §0.2.2):

| 条件                  | 推奨行動                          |
| --------------------- | --------------------------------- |
| 画面 1個、単純 CRUD   | 単一 Custom Hook                  |
| 画面 2個+ (一覧/詳細) | 画面別 Custom Hook 分離           |
| 複雑なフォーム検証    | 別途 Form Custom Hook             |
| 複数画面で状態共有    | React Context + Provider パターン |

**Service 分離基準**:

| 条件                         | 推奨行動                 |
| ---------------------------- | ------------------------ |
| 単純 DB CRUD                 | Service 1個              |
| 外部 API 統合 (TTS, AI など) | 外部 API 別 Service 分離 |
| 複雑なビジネスロジック       | ドメイン Service 分離    |

**ネーミング規則 (必須遵守)**:

| 対象           | パターン             | 例              |
| -------------- | -------------------- | --------------- |
| Hook (一覧)    | `use{Feature}List`   | `useQuizList`   |
| Hook (詳細)    | `use{Feature}Detail` | `useQuizDetail` |
| Hook (単一)    | `use{Feature}`       | `useQuiz`       |
| API関数        | `{feature}-api.ts`   | `quiz-api.ts`   |
| コンポーネント | `{Feature}Panel.tsx` | `QuizPanel.tsx` |

**React Hooks ガイドライン**:

| 状況                              | 推奨パターン                         |
| --------------------------------- | ------------------------------------ |
| 画面別状態 (デフォルト)           | `useState` / `useReducer` (ローカル) |
| アプリ全域状態 (フィルター、設定) | React Context + Provider パターン    |
| 詳細画面 (パラメータ付き)         | `useParams` + カスタムフック         |

<!-- Tier 3 の場合下記に置き換え:
**§0.2 State & Architecture**: 既存 `use{Feature}` 再利用, {レイヤー}のみ変更 (単一 Hook 維持)
-->

#### 0.2.3 状態遷移 (v3.0 新規)

```
┌─────────┐     {イベント}     ┌─────────┐
│ 初期    │ ───────────────> │ ローディング│
└─────────┘                  └────┬────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │ 成功               │ 失敗              │ キャンセル
              ▼                   ▼                   ▼
        ┌─────────┐         ┌─────────┐         ┌─────────┐
        │  データ  │         │  エラー │         │ 初期    │
        └─────────┘         └─────────┘         └─────────┘
```

<!-- Tier 3 の場合下記に置き換え:
**N/A** - Tier 3 機能として状態遷移ダイアグラム省略
-->

### 0.3 エラーハンドリングポリシー (v3.0 強化)

#### 0.3.1 エラー分類

| エラータイプ      | コード | HTTP | 原因                  |
| ----------------- | ------ | :--: | --------------------- |
| `NetworkError`    | `E001` |  -   | 接続失敗/タイムアウト |
| `AuthError`       | `E002` | 401  | JWT 有効期限切れ/無効 |
| `ValidationError` | `E003` | 400  | 入力値検証失敗        |
| `NotFoundError`   | `E004` | 404  | リソースがありません  |
| `RateLimitError`  | `E005` | 429  | リクエスト過多        |
| `ServerError`     | `E006` | 500  | サーバー内部エラー    |

#### 0.3.2 ユーザー向けメッセージ

| エラータイプ      | UI表示方法                | メッセージ (メッセージキー) |    再試行    |
| ----------------- | ------------------------- | --------------------------- | :----------: |
| `NetworkError`    | SnackBar + Retry          | `error_networkRetry`        |      ✅      |
| `AuthError`       | ダイアログ → LoginPage    | `error_sessionExpired`      |      ❌      |
| `ValidationError` | インライン (フィールド下) | `error_invalidInput`        |      ❌      |
| `NotFoundError`   | EmptyStateコンポーネント  | `error_notFound`            |      ❌      |
| `RateLimitError`  | SnackBar                  | `error_tooManyRequests`     | ✅ (30秒後)  |
| `ServerError`     | SnackBar + Retry          | `error_serverError`         | ✅ (最大2回) |

#### 0.3.3 回復パス

| エラータイプ      | 回復パス                              | 状態保持 |
| ----------------- | ------------------------------------- | :------: |
| `NetworkError`    | 再試行ボタン → 同じAPI再呼び出し      |    ✅    |
| `AuthError`       | LoginPageに移動                       |    ❌    |
| `ValidationError` | 対象フィールドフォーカス + エラー表示 |    ✅    |

#### 0.3.4 ロギングルール

| 項目                    | ロギング | マスキング | 備考             |
| ----------------------- | :------: | :--------: | ---------------- |
| エラーコード/メッセージ |    ✅    |     ❌     |                  |
| リクエストパラメータ    |    ✅    |    部分    | 敏感情報除外     |
| `access_token`          |    ❌    |     -      | 絶対ロギング禁止 |
| `email`, `phone`        |    ❌    |     -      | PII              |
| `user_id`               |    ✅    |     ❌     |                  |

### 0.4 データスキーマ & セキュリティ (必須)

> **SSOT**: `src/app/api/` が真実の源であり、このセクションは要約 + 意図の記録です。

#### 0.4.1 TypeScript型定義 + Zod

> **人用要約** (クイックリファレンス)

| モデル    | フィールド/型     | Nullable | 備考   |
| --------- | ----------------- | :------: | ------ |
| `{Model}` | `id: string`      |    ❌    | UUID   |
|           | `{field}: {type}` |  ⭕/❌   | {説明} |

**機械検証用JSONスキーマ** (spec-validator対象):

<!-- 以下のjson:schemaブロックはspec-validatorが自動抽出して検証します -->

```json:schema/typescript_type
{
  "name": "{Model}",
  "description": "{モデルの説明}",
  "file_path": "src/features/{feature}/types/{model}.ts",
  "fields": [
    {
      "name": "id",
      "type": "string",
      "nullable": false,
      "comment": "UUID識別子"
    },
    {
      "name": "{field}",
      "type": "{Type}",
      "nullable": false,
      "json_key": "{snake_case_key}",
      "comment": "{説明}"
    }
  ],
  "zod_schema": true
}
```

> ℹ️ **メタスキーマ**: [schemas/typescript_type.schema.json](./schemas/typescript_type.schema.json)

#### 0.4.2 バックエンドスキーマ

> **人用要約** (クイックリファレンス)

##### エンティティ: `{entity_name}`

| フィールド  | 型     | Nullable | デフォルト | 制約          |
| ----------- | ------ | :------: | ---------- | ------------- |
| `id`        | string |    ❌    | UUID       | PK            |
| `userId`    | string |    ❌    | -          | FK, INDEX     |
| `{field}`   | {type} |  ⭕/❌   | {default}  | {constraints} |
| `createdAt` | Date   |    ❌    | `now()`    | INDEX         |
| `updatedAt` | Date   |    ❌    | `now()`    |               |

**機械検証用JSONスキーマ** (spec-validator対象):

<!-- 以下のjson:schemaブロックはspec-validatorが自動抽出して検証します -->

```json:schema/backend_entity
{
  "entity": "{entity_name}",
  "description": "{エンティティの説明}",
  "fields": [
    {
      "name": "id",
      "type": "string",
      "nullable": false,
      "default": "UUID",
      "constraints": ["PK"]
    },
    {
      "name": "userId",
      "type": "string",
      "nullable": false,
      "constraints": ["FK", "INDEX"]
    },
    {
      "name": "{field}",
      "type": "{type}",
      "nullable": false,
      "default": "{default}",
      "constraints": ["{constraint}"],
      "comment": "{説明}"
    },
    {
      "name": "createdAt",
      "type": "Date",
      "nullable": false,
      "default": "now()",
      "constraints": ["INDEX"]
    },
    {
      "name": "updatedAt",
      "type": "Date",
      "nullable": false,
      "default": "now()"
    }
  ]
}
```

> ℹ️ **メタスキーマ**: [schemas/backend_entity.schema.json](./schemas/backend_entity.schema.json)

#### 0.4.3 認可ポリシー

##### 認可: `{entity_name}`

| 操作   | ポリシー名            | 条件                               | 備考             |
| ------ | --------------------- | ---------------------------------- | ---------------- |
| READ   | `user_can_read_own`   | `session.userId === record.userId` | 自分のデータのみ |
| CREATE | `user_can_create_own` | `session.userId === input.userId`  |                  |
| UPDATE | `user_can_update_own` | `session.userId === record.userId` |                  |
| DELETE | `user_can_delete_own` | `session.userId === record.userId` |                  |

**セキュリティ考慮事項**:

- PIIを含むか: ❌ なし / ⭕ あり → {暗号化方針}

### 0.4.5 書き込み操作 (v3.4 新規)

> **目的**: 各API/イベントがデータをどのように変更するかを仕様化 (CQRS Commandの観点)
> **SSOT**: §0.5 API契約 + §0.4.2 DBスキーマの接続

<!-- 書き込み操作がないUI-Only機能は以下の1行に置き換え:
**N/A** - 読み取り専用機能 (書き込み操作なし)
-->

#### 0.4.5.1 操作マッピング (API → DB変更)| API/イベント | 操作 | テーブル | 変更フィールド | 条件 | 副作用 |

|-----------|:----:|--------|----------|------|--------|
| `{API endpoint}` | INSERT | `{table}` | `{fields}` | - | {副作用} |
| `{API endpoint}` | UPDATE | `{table}` | `{fields}` | RLS通過 | - |
| `{API endpoint}` | SOFT DELETE | `{table}` | `deleted_at` | RLS通過 | {整理作業} |

**操作タイプの範例**:
| 操作 | 説明 |
|:----:|------|
| INSERT | 新しいレコードの作成 |
| UPDATE | 既存レコードの修正 |
| UPSERT | あれば修正、なければ作成 |
| SOFT DELETE | 論理削除 (`deleted_at`設定) |
| HARD DELETE | 物理削除 |

#### 0.4.5.2 トランザクション境界 (トランザクション境界)

| 操作グループ      | 含まれる操作 |   トランザクション範囲   | 隔離レベル     |
| ----------------- | ------------ | :----------------------: | -------------- |
| {操作1}           | {操作リスト} |      単一 / バッチ       | READ COMMITTED |
| {操作2} + {操作3} | {操作リスト} | **単一トランザクション** | {隔離レベル}   |

**ロールバック条件**:

| トランザクション | ロールバックトリガー | ロールバック範囲 | ユーザーメッセージ               |
| ---------------- | -------------------- | ---------------- | -------------------------------- |
| {操作グループ}   | {条件}               | 全体 / 部分      | {メッセージまたはメッセージキー} |

**部分失敗戦略**:

- [ ] All-or-Nothing: 1つでも失敗した場合は全体ロールバック
- [ ] Best-Effort: 成功したものはコミット、失敗したものだけロールバック
- [ ] Compensating: 補償トランザクションで回復

#### 0.4.5.3 アイデンポテンス (アイデンポテンス保証)

| API                 |   アイデンポテンス    | 戦略                 | キー                  |
| ------------------- | :-------------------: | -------------------- | --------------------- |
| `GET {endpoint}`    |        ✅ 自然        | -                    | -                     |
| `POST {endpoint}`   | ⚠️ 非アイデンポテンス | アイデンポテンスキー | `X-Idempotency-Key`   |
| `PATCH {endpoint}`  |  ✅ アイデンポテンス  | -                    | `id` (パスパラメータ) |
| `DELETE {endpoint}` |  ✅ アイデンポテンス  | -                    | `id` (パスパラメータ) |

#### 0.4.5.4 監査ポリシー (監査ポリシー)

| 操作タイプ | 監査ログ | 保存情報                                     | 保存期間 |
| ---------- | :------: | -------------------------------------------- | -------- |
| CREATE     |  ⭕/❌   | `user_id`, `table`, `record_id`, `new_value` | {期間}   |
| UPDATE     |  ⭕/❌   | 上記 + `old_value`                           | {期間}   |
| DELETE     |  ⭕/❌   | 上記 + `deletion_reason`                     | {期間}   |

**敏感データ処理**:
| フィールドタイプ | 処理方法 |
|----------|----------|
| PII (個人情報) | マスキング: `j***@example.com` |
| パスワード/トークン | 保存しない: `[REDACTED]` |
| 一般データ | 元のまま保存 |

**機械検証用 JSON Schema** (spec-validator 対象):

```json:schema/write_operations
{
  "feature_id": "{NNN}",
  "operations": [
    {
      "api": "{METHOD} {path}",
      "action": "{INSERT|UPDATE|UPSERT|SOFT_DELETE|HARD_DELETE}",
      "table": "{table_name}",
      "fields": ["{field1}", "{field2}"],
      "condition": "{RLS条件またはnull}",
      "side_effects": ["{副作用1}", "{副作用2}"]
    }
  ],
  "transactions": [
    {
      "name": "{トランザクショングループ名}",
      "operations": ["{op1}", "{op2}"],
      "isolation_level": "READ_COMMITTED",
      "rollback_triggers": ["{条件1}"],
      "rollback_scope": "ALL|PARTIAL",
      "partial_failure_strategy": "ALL_OR_NOTHING|BEST_EFFORT|COMPENSATING"
    }
  ],
  "idempotency": {
    "non_idempotent_apis": ["{POST endpoint}"],
    "strategy": "IDEMPOTENCY_KEY|UPSERT|NONE",
    "key_header": "X-Idempotency-Key",
    "ttl_hours": 24
  },
  "audit": {
    "enabled": true,
    "operations": ["CREATE", "UPDATE", "DELETE"],
    "retention_days": 90,
    "pii_masking": true
  }
}
```

> ℹ️ **メタスキーマ**: [schemas/write_operations.schema.json](./schemas/write_operations.schema.json)

### 0.5 API Contract (必須)

> **SSOT**: `src/app/api/{name}/route.ts`の `responseSchema`が真実の源
> **分離基準**: エンドポイント 3つ+ またはこのセクション 100行+ → 別途 `API-{NNN}.md` 分離

#### エンドポイント一覧 (人間用要約)

| ID           | Method | Path          | Auth | 説明   |
| ------------ | ------ | ------------- | :--: | ------ |
| API-{NNN}-01 | POST   | `/api/{name}` |  ✅  | {説明} |

#### API-{NNN}-01: {name}

**Request Schema**:

```json
{
  "type": "object",
  "required": ["field1"],
  "properties": {
    "field1": { "type": "string", "description": "{説明}" },
    "field2": { "type": "integer", "description": "{説明}" }
  }
}
```

**Response Schema**:

```json
{
  "type": "object",
  "required": ["status"],
  "properties": {
    "status": { "type": "string", "enum": ["ok", "error"] },
    "data": { "type": "object", "description": "{説明}" },
    "error": {
      "type": "object",
      "properties": {
        "code": { "type": "string" },
        "message": { "type": "string" }
      }
    }
  }
}
```

**Error Codes**:

| HTTP | Code              | 条件               | クライアント対応   |
| :--: | ----------------- | ------------------ | ------------------ |
| 400  | `INVALID_INPUT`   | 必須フィールド欠落 | 入力検証表示       |
| 401  | `UNAUTHENTICATED` | JWTなし/期限切れ   | 再ログイン誘導     |
| 403  | `FORBIDDEN`       | RLS違反            | 権限エラー表示     |
| 429  | `RATE_LIMITED`    | リクエスト過多     | バックオフ後再試行 |
| 500  | `INTERNAL_ERROR`  | サーバーエラー     | 再試行 (最大 2 回) |

**機械検証用 JSON Schema** (spec-validator 対象):

```json:schema/api_endpoint
{
  "id": "API-{NNN}-01",
  "method": "POST",
  "path": "/api/{name}",
  "description": "{API 説明}",
  "auth": true,
  "request": {
    "type": "object",
    "required": ["field1"],
    "properties": {
      "field1": { "type": "string", "description": "{説明}" },
      "field2": { "type": "integer", "description": "{説明}" }
    }
  },
  "response": {
    "type": "object",
    "required": ["status"],
    "properties": {
      "status": { "type": "string", "enum": ["ok", "error"] },
      "data": { "type": "object" },
      "error": {
        "type": "object",
        "properties": {
          "code": { "type": "string" },
          "message": { "type": "string" }
        }
      }
    }
  },
  "errors": [
    { "http": 400, "code": "INVALID_INPUT", "condition": "必須フィールドの欠落", "client_action": "入力検証表示" },
    { "http": 401, "code": "UNAUTHENTICATED", "condition": "JWTなし/期限切れ", "client_action": "再ログイン促進" },
    { "http": 403, "code": "FORBIDDEN", "condition": "RLS違反", "client_action": "権限エラー表示" },
    { "http": 429, "code": "RATE_LIMITED", "condition": "リクエスト過多", "client_action": "バックオフ後再試行" },
    { "http": 500, "code": "INTERNAL_ERROR", "condition": "サーバーエラー", "client_action": "再試行 (最大2回)" }
  ],
  "rate_limit": {
    "requests_per_minute": 30,
    "requests_per_day": 1000,
    "tier": "all"
  }
}
```

> ℹ️ **メタスキーマ**: [schemas/api_endpoint.schema.json](./schemas/api_endpoint.schema.json)
> ℹ️ **API Route 必須**: `responseMimeType: "application/json"` + `responseSchema` 使用

### 0.6 NFR (非機能要件) - 必須

> **目的**: AI が品質基準を満たす実装を行えるように明確な目標提示

#### 性能 (Performance)

| 指標                   | 目標         | 測定方法                        |
| ---------------------- | ------------ | ------------------------------- |
| **初回応答時間**       | < {N}ms      | API 呼び出し → 初バイト         |
| **全体応答時間**       | < {N}s (P95) | API 呼び出し → 完了             |
| **ストリーミング開始** | < {N}s       | (ストリーミングのみ) 初チャンク |

#### 同時性 (Concurrency)

| 項目                   | 予想値       | 備考   |
| ---------------------- | ------------ | ------ |
| **同時ユーザー**       | ~{N}名       | {基準} |
| **ユーザー当たり頻度** | {N}回/{時間} | 平均   |

#### 信頼性 (Reliability)

| 項目       | 政策               | 備考   |
| ---------- | ------------------ | ------ | --- | ---------------- | ----- | -------------- |
| **再試行** | 最大 {N}回, {戦略} | {対象} |     | **タイムアウト** | {N}秒 | クライアント側 |

#### コスト (Cost) - AI 使用機能のみ

| 項目             | 上限                 | 備考             |
| ---------------- | -------------------- | ---------------- |
| **LLM 呼び出し** | {N}回/ユーザー/日    | {プラン}         |
| **トークン**     | 入力 {N}K, 出力 {N}K | リクエスト当たり |
| **月コスト**     | ${N}                 | 全体合計         |

<!-- AI 未使用の場合は下記に置き換え:
**N/A** - AI/LLM 未使用
-->

#### 観測性 (Observability)

| 項目           | 内容                                              |
| -------------- | ------------------------------------------------- |
| **ログ項目**   | `{フィールド1}`, `{フィールド2}`, `{フィールド3}` |
| **メトリクス** | `{metric_name}`                                   |
| **通知条件**   | {条件}                                            |

<!-- 基本ロギングのみ必要な場合は:
**標準ロギング適用** - LogUtils 基本設定
-->

### 0.7 AI Logic & Prompts (AI 機能必須)

> **目的**: AI が LLM 呼び出しロジックを正確に実装できるようにプロンプトとスキーマ仕様
> **適用**: API Route で LLM 呼び出しする機能のみ作成 (AI 未使用時は "N/A" 明示)

<!-- AI 未使用の場合は下記 1 行に置き換え:
**N/A** - この機能は LLM/AI 呼び出しを使用していません
-->

#### 0.7.1 AI 役割定義

| 役割          | 目的       | モデル       |
| ------------- | ---------- | ------------ |
| `{role_name}` | {役割説明} | {model_name} |

#### 0.7.2 System Prompt

**役割: {role_name}**

```
あなたは {役割定義}。

## コンテキスト
- ユーザー L1: {{l1_language}}
- 学習レベル: {{topik_level}}
- {追加コンテキスト}

## ルール
1. {ルール1}
2. {ルール2}
3. {ルール3}

## 出力形式
JSONのみで応答。説明テキスト禁止。
```

#### 0.7.3 Response Schema (JSON Schema)

```json
{
  "type": "object",
  "required": ["field1", "field2"],
  "properties": {
    "field1": {
      "type": "string",
      "description": "{フィールド説明}"
    },
    "field2": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "sub_field": { "type": "string" }
        }
      }
    }
  }
}
```

#### 0.7.4 変数注入 (Variable Injection)

| 変数              | ソース               | 例                     |
| ----------------- | -------------------- | ---------------------- |
| `{{l1_language}}` | ユーザープロファイル | `"ja"`, `"en"`         |
| `{{topik_level}}` | ユーザー設定         | `"TOPIK1"`, `"TOPIK3"` |
| `{{user_input}}`  | リクエストパラメータ | ユーザー入力値         |

### 0.8 Safety & Guardrails (AI 機能必須)

> **目的**: AI 出力の品質と安全性を保証するための検証ルール
> **適用**: §0.7 AI Logic がある機能のみ作成 (AI 未使用時は "N/A" 明示)

<!-- AI 未使用の場合は下記 1 行に置き換え:
**N/A** - この機能は AI/LLM を使用していません
-->

#### 0.8.1 入力検証 (Input Validation)

| 検証項目       | ルール                | 失敗時動作              |
| -------------- | --------------------- | ----------------------- |
| 入力長さ       | 最大 {N}文字          | 400 エラー + メッセージ |
| 禁止語フィルタ | {パターン/リスト}     | リクエスト拒否          |
| Rate Limit     | {N}回/{時間}/ユーザー | 429 エラー              |

#### 0.8.2 出力検証 (Output Validation)

| 検証項目           | ルール             | 失敗時動作                          |
| ------------------ | ------------------ | ----------------------------------- |
| JSON 解析          | スキーマ遵守       | 再試行 (最大 2 回) → フォールバック |
| 必須フィールド     | {フィールドリスト} | フォールバック応答                  |
| コンテンツフィルタ | {禁止パターン}     | フィルタリング後返却                |

#### 0.8.3 フォールバック戦略

| 失敗タイプ       | フォールバック | ユーザーメッセージ |
| ---------------- | -------------- | ------------------ |
| LLM タイムアウト | {代替ロジック} | {メッセージ}       |
| 解析失敗         | {代替応答}     | {メッセージ}       |
| Rate Limit       | {キュー/拒否}  | {メッセージ}       |

#### 0.8.4 コスト制御

| 項目         | 限定                 | 超過時         |
| ------------ | -------------------- | -------------- |
| 日次呼び出し | {N}回/ユーザー       | {動作}         |
| トークン上限 | 入力 {N}K, 出力 {N}K | リクエスト拒否 |
| 月予算       | ${N}                 | 通知 + {動作}  |

### 0.9 Design Tokens (v3.0 必須)

> **SSOT**: `src/app/globals.css` (Tailwind CSS 4), `docs/development/base-ui-theme-guide.md`
> **原則**: ハードコーディングされた色値, 数字直接使用禁止 → 常にTailwindトークン参照

#### 0.9.1 Color References

| 用途     | Tailwindクラス     | 直接使用禁止     |
| -------- | ------------------ | ---------------- |
| 基本背景 | `bg-background`    | `bg-[#0b1120]`   |
| 基本文字 | `text-foreground`  | `text-[#e2e8f0]` |
| エラー   | `text-destructive` | `text-red-500`   |
| Primary  | `text-primary`     | `text-[#3b82f6]` |
| Surface  | `bg-card`          | `bg-[rgba(...)]` |

#### 0.9.2 Typography

| 用途         | Tailwindクラス           | サイズ |
| ------------ | ------------------------ | ------ |
| タイトル     | `text-2xl font-semibold` | 24px   |
| 本文         | `text-base`              | 16px   |
| キャプション | `text-sm`                | 14px   |
| ボタン       | `text-sm font-medium`    | 14px   |

#### 0.9.3 Spacing

| Tailwindクラス |  値  | 用途                    |
| -------------- | :--: | ----------------------- |
| `p-1`          | 4px  | アイコン-テキスト間距離 |
| `p-2`          | 8px  | 要素内部パディング      |
| `p-3`          | 12px | カードパディング        |
| `p-4`          | 16px | セクション間距離        |
| `p-6`          | 24px | ページパディング        |

#### 0.9.4 Common Components

| コンポーネント    | 使用             | 例               |
| ----------------- | ---------------- | ---------------- |
| `PrimaryButton`   | 主要アクション   | 提出, 開始       |
| `SecondaryButton` | 補助アクション   | キャンセル, 戻る |
| `ErrorText`       | エラーメッセージ | フィールド下     |
| `LoadingSpinner`  | ローディング     | 中央配置         |

### 0.10 Eventing & Async Processing (v3.5 新規, Tier 2+ 必須)

> **目的**: 機能で発生するイベント、非同期処理の流れ、配達保証戦略を明示化
> **適用**: Tier 2 以上の機能の中でDBトリガー、API Route チェーン、オフライン同期が含まれる機能

<!-- イベント/非同期処理がない場合は以下の1行に置き換え:
**N/A** - 同期処理のみ使用 (DBトリガー/API Route チェーンなし)
-->

#### 0.10.1 DB Event Sources (PostgreSQL Trigger/Function)

| トリガー名       | テーブル  | イベント                 | 呼び出し関数        | 発生時点 |
| ---------------- | --------- | ------------------------ | ------------------- | -------- |
| `{trigger_name}` | `{table}` | `{INSERT/UPDATE/DELETE}` | `{function_name}()` | `{条件}` |

> **参照**: バックエンドのトリガー定義

#### 0.10.2 Event Payload 定義

| フィールド | タイプ   | 必須 | 説明        |
| ---------- | -------- | :--: | ----------- |
| `user_id`  | `UUID`   |  ✓   | ユーザー ID |
| `{field}`  | `{type}` | ✓/-  | {説明}      |

**JSON スキーマ**:

```json
{
  "type": "object",
  "required": ["{field1}", "{field2}"],
  "properties": {
    "{field1}": { "type": "string", "format": "uuid" },
    "{field2}": { "type": "string", "format": "date-time" }
  }
}
```

#### 0.10.3 API Route Call Chain

```
┌────────┐     ┌──────────────┐     ┌──────────────┐     ┌────────┐
│ Client │────>│ API Route 1  │────>│ API Route 2  │────>│   DB   │
└────────┘     └──────────────┘     └──────────────┘     └────────┘
```

| 順序 | 呼び出し元 | 被呼び出し先 | メソッド | 目的 ||:----:|--------|----------|--------|------|
| 1 | {呼び出し元} | `{被呼び出し先}` | {POST/GET} | {目的} |

#### 0.10.4 配信保証戦略 (Delivery Guarantee)

| 処理区間                 | 保証レベル    | 実装方式           | 失敗時動作     |
| ------------------------ | ------------- | ------------------ | -------------- |
| クライアント → API Route | 少なくとも1回 | クライアント再試行 | エラー UI 表示 |
| API Route → データベース | 正確に1回     | トランザクション   | ロールバック   |
| トリガー → Webhook       | 少なくとも1回 | Webhook 再試行     | DLQ 格納       |

**冪等性保証**:

- `idempotency_key` ヘッダーサポート: ⭕/❌
- 重複リクエスト判別基準: `{基準}`

#### 0.10.5 オフライン同期 & 衝突解決 (Offline Sync & Conflict Resolution)

**同期アーキテクチャ**: サーバー主導 / クライアント主導

| データタイプ | 同期方向                | 衝突解決戦略                                         |
| ------------ | ----------------------- | ---------------------------------------------------- |
| {タイプ}     | クライアント → サーバー | 最後の書き込み勝ち / サーバー勝ち / クライアント勝ち |

<!-- オフラインサポートがない場合は以下に置き換え:
**N/A** - オンライン必須機能
-->

#### 0.10.6 リアルタイムサブスクリプション (Realtime Subscriptions)

| チャンネル名 | 購読対象  | イベントタイプ         | フィルター条件 |
| ------------ | --------- | ---------------------- | -------------- |
| `{channel}`  | `{table}` | {INSERT/UPDATE/DELETE} | `{条件}`       |

**現在の状態**: [ ] リアルタイム使用 / [✓] ポーリング使用 ({N}秒間隔)

#### 0.10.7 デッドレターキュー & 回復 (Dead Letter Queue & Recovery)

| DLQ 対象 | 保存位置  | 保管期間 | 再処理方法 |
| -------- | --------- | -------- | ---------- |
| {対象}   | `{table}` | {N}日    | {方法}     |

<!-- DLQ 不要の場合は以下に置き換え:
**N/A** - MVP 範囲で DLQ 未実装
-->

---

## 1. 概要

### 1.1 目標 (WHY)

{1-2文でビジネス根拠とユーザー価値}

### 1.2 ユーザーストーリー

```
AS A プログラミング学習者
I WANT TO {望むもの}
SO THAT {得られる価値}
```

### 1.3 MVP 範囲

| 含む       | 除外            |
| ---------- | --------------- |
| {必須機能} | {Post-MVP 機能} |

### 1.4 目的 / 非目的 (必須)

> **目的**: AIが実装範囲を正確に理解し範囲の逸脱を防ぐ

#### 目的 (このSPECで達成すること)

1. **{Goal 1}**: {具体的説明}
2. **{Goal 2}**: {具体的説明}
3. **{Goal 3}**: {具体的説明}

#### 非目的 (このSPECで行わないこと)

| 項目         | 理由       | 代替/時期            |
| ------------ | ---------- | -------------------- |
| {Non-Goal 1} | {除外理由} | {Post-MVP / 別SPEC}  |
| {Non-Goal 2} | {除外理由} | {代替または将来計画} |
| {Non-Goal 3} | {除外理由} | {該当なし / 不要}    |

> ⚠️ **AI注意**: Non-Goalsに記載された機能を実装しないでください。関連リクエスト時はこのセクションを引用してください。

### 1.5 UI Flow Contract (v4.0 改修, Tier 1-2 必須)

> **目的**: SPA状態駆動パネル表示の契約を宣言し、`docs/ui-flow/ui-flow.json` (SSOT) との整合性を保証
>
> **SSOT参照**: `docs/ui-flow/ui-flow.json` — 全パネル・状態・SSEマッピングの定義元

<!-- Tier 3 (backend_feature) の場合は以下に置き換え:
**N/A** - Backend-only 機能で UI Flow Contract 省略
-->

#### 1.5.1 パネル宣言

> この機能が追加・変更するパネルを宣言

| パネル名         | 操作 | feature      | visibility 種別 | visibility 条件                  |
| ---------------- | ---- | ------------ | --------------- | -------------------------------- |
| {PanelName}Panel | 新規 | {feature-id} | state_based     | `status === '{state}'`           |
| {PanelName}Panel | 変更 | {feature-id} | data_based      | `{data} !== null && {condition}` |

操作: `新規` = ui-flow.json に新パネル追加 / `変更` = 既存パネルの条件変更 / `参照` = 変更なし（依存のみ）

#### 1.5.2 SSE イベントマッピング

> この機能が使用する SSE イベントの一覧

| SSE Event | → SessionStatus | Target Panel     | 状態変更 |
| --------- | --------------- | ---------------- | :------: |
| {event}   | {status}        | {PanelName}Panel |   Yes    |

#### 1.5.3 フェーズ統合

> パネルがどのフェーズで表示されるか

| Phase   | 追加パネル       | Layout    | Auto Scroll |
| ------- | ---------------- | --------- | ----------- |
| {phase} | {PanelName}Panel | grid-2col | {scrollRef} |

#### 1.5.4 状態遷移（この機能に関連する範囲）

```
{fromState} ──{EVENT}──▶ {toState}
```

<!-- json:schema/ui_flow_contract — 機械可読ブロック（readiness_gate 検証対象） -->

```json
{
  "$schema": "ui_flow_contract",
  "panels": [
    {
      "name": "{PanelName}Panel",
      "operation": "new|modify|reference",
      "feature": "{feature-id}",
      "visibility": {
        "type": "state_based|data_based|flag_based",
        "condition": "{condition expression}"
      }
    }
  ],
  "sse_events": [
    {
      "event": "{event-name}",
      "target_status": "{SessionStatus}",
      "target_panel": "{PanelName}Panel",
      "changes_status": true
    }
  ],
  "phases": [
    {
      "phase": "{phase-name}",
      "added_panels": ["{PanelName}Panel"],
      "auto_scroll_ref": "{refName|null}"
    }
  ]
}
```

> **AI注意**: `json:schema/ui_flow_contract` ブロックの `panels[].name` は `docs/ui-flow/ui-flow.json` の `panels` キーと一致すること。`operation: "new"` の場合、実装完了時に `ui-flow.json` への追加が必須（feature-wiring Phase 2.3 で検証）。

---

## 2. 機能要件 (WHAT)

> 💡 **シングルソースオブトゥルース**: 実装ファイル、状態、テストはここにのみ記録

### FR-{NNN}01: {機能名}

| 項目             | 内容                                                |
| ---------------- | --------------------------------------------------- |
| **説明**         | {機能説明}                                          |
| **実装ファイル** | `src/features/{feature}/components/{Name}Panel.tsx` |
| **テスト**       | `tests/unit/features/{feature}/{name}.test.ts`      |
| **状態変化**     | {例: Loading → Data, Error → Retry}                 |
| **状態**         | ⬜ 未開始 / 🔄 実行中 / ✅ 完了                     |

**受け入れ基準 (AC)** - BDD 6-column (v3.1 定量化強化):

> ⚠️ **定量化必須**: Thenカラムには必ず **測定可能な数値/閾値** を含める
> 例: "表示される" ❌ → "500ms以内に表示される" ✅

| AC  | Given (前提条件) | When (行動) | Then (期待結果 + 定量基準)                | 観測点     | テストID  |
| :-: | ---------------- | ----------- | ----------------------------------------- | ---------- | :-------: |
| AC1 | {前提条件}       | {行動}      | {期待結果} **[{N}ms以内/{N}個/{N}%以上]** | {検証変数} | T-{NNN}01 |
| AC2 | {前提条件}       | {行動}      | {期待結果} **[定量基準]**                 | {検証変数} | T-{NNN}02 |

<!--
定量化ガイド:
- 時間: "< 500ms", "3秒以内"
- 個数: "最大 10個", "正確に 5個"
- 割合: "90% 以上", "エラー率 < 1%"
- 状態: "isLoading = false", "items.length > 0"
- 定性的 → 定量的変換例:
  - "速く" → "< 1秒"
  - "多くの" → "> 100個"
  - "正確に" → "100% 一致"
-->

**エッジケース (EC)**:

- EC1: {例外状況} → {処理方法}
- EC2: {例外状況} → {処理方法}

**例外フロー (EF)**:

| EF  | トリガー       | システム動作                | ユーザーフィードバック | 復旧経路                 |
| :-: | -------------- | --------------------------- | ---------------------- | ------------------------ |
| EF1 | {エラー条件}   | {ロギング/状態変更}         | {トースト/ダイアログ}  | {再試行/キャンセル/移動} |
| EF2 | {タイムアウト} | {キャンセル/フォールバック} | {メッセージ}           | {再試行ボタン}           |

**ロジック (v3.0, Tier 1-2 必須)** - pseudocode/数式:

<!-- Tier 3の場合は以下に置き換え:
**N/A** - 単純CRUDでロジック詳細省略
-->

```pseudocode
FUNCTION {functionName}(param1: Type, param2: Type) -> ReturnType:
    # 1. 入力検証
    IF param1 is invalid:
        THROW ValidationError

    # 2. ビジネスロジック
    result = {計算/処理}

    # 3. 保存/返却
    RETURN result
```

**数式 (該当する場合)**:

- `{変数} = {公式}`

**境界値**:
| 条件 | 結果 |
|------|------|
| {条件1} | {結果1} |
| {条件2} | {結果2} |

**AI 実装ヒント**:

```typescript
// 参考パターン: src/features/{feature}/components/SimilarPanel.tsx
// 使用するHook: React.FC + use{Feature}() Hook
```

---

### FR-{NNN}02: {機能名}

| 項目             | 内容                                               |
| ---------------- | -------------------------------------------------- | ----------------------------------- |
| **説明**         | {機能説明}                                         |
| **実装ファイル** | `src/features/{feature}/api/{name}-api.ts`         |
| **テスト**       | `tests/unit/features/{feature}/{name}-api.test.ts` |
| **状態変化**     | {例: Loading → Data, Error → Retry}                |
| **状態**         | ⬜ 未開始                                          | **受け入れ基準 (AC)** - 定量化必須: |

| AC  | Given (前提条件) | When (行動) | Then (期待結果 + 定量基準) | 観測点     | テストID  |
| :-: | ---------------- | ----------- | -------------------------- | ---------- | :-------: |
| AC1 | {前提条件}       | {行動}      | {期待結果} **[定量基準]**  | {検証変数} | T-{NNN}XX |

**エッジケース (EC)**:

- EC1: {例外状況} → {処理方法}**例外フロー (EF)**:

| EF  | トリガー     | システム動作 | ユーザーフィードバック | 回復ルート |
| :-: | ------------ | ------------ | ---------------------- | ---------- |
| EF1 | {エラー条件} | {動作}       | {フィードバック}       | {回復}     |

---

### 2.X ビジネスルール (v3.0 新規)

> **目的**: 複雑なビジネスロジックを集中して仕様化

#### BR-01: {ビジネスルール名}

| 項目           | 内容                   |
| -------------- | ---------------------- |
| **適用対象**   | {どのFRに適用されるか} |
| **ルール説明** | {自然言語での説明}     |

**ロジック (擬似コード)**:

```pseudocode
FUNCTION {ruleName}(inputs) -> output:
    # {段階別ロジック}
```

**数式**:

- `{出力} = {公式}`

**境界値**:
| 入力範囲 | 出力 |
|----------|------|
| {範囲1} | {結果1} |
| {範囲2} | {結果2} |

---

## 3. 依存性 & リスク (HOW)

### 3.1 前提依存性

| 依存対象    | 必要項目       |  状態   |
| ----------- | -------------- | :-----: |
| SPEC-{XXX}  | {機能}         | ✅ / ⏳ |
| DB テーブル | `{table_name}` | ✅ / ⏳ |

### 3.2 トップ 3 リスク

| リスク    |   影響   | 対応       |
| --------- | :------: | ---------- |
| {リスク1} | 高/中/低 | {対応戦略} |
| {リスク2} | 高/中/低 | {対応戦略} |
| {リスク3} | 高/中/低 | {対応戦略} |

### 3.3 外部依存性 (v3.0 新規)

> **目的**: 外部システム連携の詳細仕様

| 外部システム | 用途   | API/SDK                     | 失敗時           |
| ------------ | ------ | --------------------------- | ---------------- |
| {システム1}  | {用途} | {バージョン/エンドポイント} | {フォールバック} |

### 3.4 シーケンス図 (Tier 1-2 必須)

> **目的**: コンポーネント間の呼び出しフローを可視化し、AIが正確な統合を実装
> **適用**: Tier 1-2 の機能必須、Tier 3 は選択

<!-- Tier 3の場合、以下に置き換え:
**N/A** - Tier 3 の機能によりシーケンス図は省略
-->

#### 3.4.1 {主要フロー名} (例: AI チュータの対話)

```
┌──────────┐     ┌──────────┐     ┌───────────┐     ┌────────┐
│   User   │     │   Hook   │     │ API Route │     │   LLM  │
└────┬─────┘     └────┬─────┘     └─────┬─────┘     └───┬────┘
     │                 │                  │                │
     │  1. {アクション} │                  │                │
     │────────────────>│                  │                │
     │                 │                  │                │
     │                 │  2. {API 呼び出し} │                │
     │                 │─────────────────>│                │
     │                 │                  │                │
     │                 │                  │  3. {LLM リクエスト} │
     │                 │                  │───────────────>│
     │                 │                  │                │
     │                 │                  │  4. {応答}     │
     │                 │                  │<───────────────│
     │                 │                  │                │
     │                 │  5. {結果 返却}  │                │
     │                 │<─────────────────│                │
     │                 │                  │                │
     │  6. {UI 更新}  │                  │                │
     │<────────────────│                  │                │
     │                 │                  │                │
```

**段階説明**:

|  #  | コンポーネント | 動作   | データ       |
| :-: | -------------- | ------ | ------------ |
|  1  | User → Hook    | {説明} | `{データ}`   |
|  2  | Hook → API     | {説明} | `{Request}`  |
|  3  | API → LLM      | {説明} | `{Prompt}`   |
|  4  | LLM → API      | {説明} | `{Response}` |
|  5  | API → Hook     | {説明} | `{Result}`   |
|  6  | Hook → User    | {説明} | `{UI State}` |

#### 3.4.2 {エラーフローネーム} (選択)

```
{エラーシナリオダイアグラム}
```

---

## 4. 画面文書

> UI の詳細は別途 Screen 文書を参照

| 画面 ID       | 画面名   | 文書                                     | 状態 |
| ------------- | -------- | ---------------------------------------- | :--: |
| SCR-{NNN}-001 | {画面名} | [screens/{name}.md](./screens/{name}.md) |  ⬜  |

---

## 4.5 ランブック (運用, 条件付き)

<!-- 運用手順が不要な場合、このセクションは削除可能 -->

- 運用文書: [RUNBOOK-{NNN}-{name}.md](./RUNBOOK-{NNN}-{name}.md)
- 適用対象: 障害対応/運用手順が必要な機能のみ記載

---

## 5. 検証 & テスト (v3.0 新規)

> **目的**: AI が現実的なテストデータで正確なテストを作成

### 5.1 テスト戦略

| レイヤー    | テストタイプ       | カバレッジ目標 |
| ----------- | ------------------ | :------------: |
| Custom Hook | ユニット           |      80%+      |
| サービス    | ユニット           |      90%+      |
| UI          | コンポーネント     |   主要フロー   |
| 統合        | インテグレーション |  ハッピーパス  |

### 5.2 テストフィクスチャ

> **目的**: モックデータの標準化でテストの一貫性を確保

#### API 応答サンプル: `{API endpoint}`

**成功 (200)**:

```json
{
  "status": "ok",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "field1": "value1",
    "createdAt": "2026-01-28T00:00:00Z"
  }
}
```

**エラー (401)**:

```json
{
  "status": "error",
  "error": {
    "code": "UNAUTHENTICATED",
    "message": "JWT expired"
  }
}
```

#### 境界値テストデータ

| ケース          | 入力               | 期待結果        |
| --------------- | ------------------ | --------------- |
| 空応答          | `items: []`        | EmptyState 表示 |
| 最大長          | `title: "A" * 200` | 省略処理        |
| null フィールド | `field: null`      | 基本値使用      |

### 5.3 受け入れチェックリスト

- [ ] すべての AC の Then 条件を満たす
- [ ] すべての EF の回復ルート動作
- [ ] エラー時に敏感情報が漏れない
- [ ] オフライン時に適切なフォールバック
- [ ] メッセージ定数の欠落なし

---

## 6. メッセージ定数 (v3.0 新規)

> **目的**: 文字列のハードコーディング防止, メッセージキーの一貫性を確保
> **SSOT**: `src/shared/constants/messages.ts`

### 6.1 メッセージキー命名ルール

| パターン                   | 例                   | 用途              |
| -------------------------- | -------------------- | ----------------- |
| `{feature}_{element}`      | `lesson_title`       | 画面要素          |
| `{feature}_{action}Button` | `lesson_startButton` | ボタン/アクション |
| `error_{type}`             | `error_networkRetry` | エラーメッセージ  |
| `common_{element}`         | `common_cancel`      | 共通要素          |

### 6.2 この機能に必要なキー

| メッセージキー         | テキスト | 用途   |
| ---------------------- | -------- | ------ |
| `{feature}_{element1}` | {日本語} | {用途} |
| `{feature}_{element2}` | {日本語} | {用途} |
| `error_{type}`         | {日本語} | {用途} |

> **ルール**: 上記キーが `messages.ts` にない場合、実装前に追加必須

---

## 7. 変更履歴

| 日付   | バージョン | 変更内容 | 根拠       |
| ------ | ---------- | -------- | ---------- |
| {DATE} | v1.0       | 初稿     | BRIEF 基盤 |

---

<!--
状態レジェンド: ✅ 完了 | 🔄 進行中 | ⬜ 未開始 | ❌ ブロック
優先順位: P0 (MVP) | P1 (MVP 支援) | P2 (Post-MVP)

═══════════════════════════════════════════════════════════════
Tier 選定基準 (v3.0 必須 - AI/作成者全員参照)
═══════════════════════════════════════════════════════════════

## Tier 分類基準表

| Tier | リスクレベル | 該当機能タイプ | 例 |
|:----:|------------|---------------|------|| **1** | 高リスク | AI/LLM 呼び出し, 決済/サブスクリプション, 認証/権限, 複雑なアルゴリズム, 外部 API 連携 | AI チュータ, サブスクリプション決済, SRS アルゴリズム, OAuth |
| **2** | 中リスク | 一般 CRUD, 標準 UI フロー, DB 連携, 状態管理 | 単語帳管理, プロフィール編集, 学習記録 |
| **3** | 低リスク | 静的コンテンツ, 設定トグル, シンプル表示, 情報ページ | FAQ, About, アプリ設定, お知らせ |

## Tier 選定意思決定ツリー

```
Q1: AI/LLM 呼び出しがあるか？
├─ YES → Tier 1
└─ NO → Q2

Q2: 決済/認証/外部 API 連携があるか？
├─ YES → Tier 1
└─ NO → Q3

Q3: 複雑なビジネスロジック（アルゴリズム、数式）があるか？
├─ YES → Tier 1
└─ NO → Q4

Q4: DB CRUD または状態管理があるか？
├─ YES → Tier 2
└─ NO → Q5

Q5: 画面遷移が 2 つ以上か？
├─ YES → Tier 2
└─ NO → Tier 3
```

## 機能タイプ別必須セクションマトリックス

| セクション | UI のみ | API 連携 | AI 使用 | 決済 |
|------|:-------:|:--------:|:-------:|:----:|
| §0.0 プロジェクトコンテキスト | ✅ | ✅ | ✅ | ✅ |
| §0.2.2 プロバイダ仕様 | ⚪選択 | ✅基本 | ✅詳細 | ✅詳細 |
| §0.3 エラー処理 | ⚪基本 | ✅主要 | ✅全体 | ✅全体 |
| §0.4 データスキーマ | ❌ | ✅ | ✅ | ✅ |
| §0.5 API 契約 | ❌ | ✅ | ✅ | ✅ |
| §0.6 NFR | ⚪基本 | ✅ | ✅詳細 | ✅詳細 |
| §0.7 AI ロジック | ❌ | ❌ | ✅必須 | ❌ |
| §0.8 安全性 | ❌ | ⚪選択 | ✅必須 | ✅必須 |
| §0.9 デザイントークン | ✅ | ✅ | ✅ | ✅ |
| §0.10 イベント & 非同期 | ❌ | ✅該当時 | ✅ | ✅ |
| §1.5 画面フロー | ⚪選択 | ✅ | ✅ | ✅ |
| §2.X ビジネスルール | ❌ | ⚪複雑時 | ✅ | ✅ |
| §3.4 シーケンス図 | ❌ | ✅ | ✅ | ✅ |
| §5 テストフィクスチャ | ⚪選択 | ✅主要 | ✅全体 | ✅全体 |
| §6 メッセージ定数 | ✅ | ✅ | ✅ | ✅ |

═══════════════════════════════════════════════════════════════

SPEC v3.5 必須セクション (2026-01-28):
- §0.0 プロジェクトコンテキスト: 命名 + 用語集参照 (必須)
- §0.2.1 コアステート: コアステート要素定義 (必須)
- §0.2.2 アーキテクチャガイダンス: SRP 基盤の分離基準 + 命名規則 (ガイドライン)
- §0.3 エラー処理: 分類 + UX + 回復 + ロギング (強化)
- §0.4 データスキーマ & セキュリティ: TypeScript型定義 + Zod + 認可ポリシー (必須)
- §0.5 API契約: 必須 (APIがなければ "N/A" を明示)
- §0.6 NFR: 必須 (該当しない項目は "N/A" を明示)
- §0.7 AIロジック & プロンプト: AI機能必須 (AI未使用の場合は "N/A" を明示)
- §0.8 安全性 & ガードレール: AI機能必須 (AI未使用の場合は "N/A" を明示)
- §0.9 デザイントークン: UIスタイル参照規則 (必須)
- §0.10 イベント処理 & 非同期: DBトリガー + API Routeチェーン + 提供保証 (v3.5新規, Tier 2+ 必須)
- §1.4 目標 / 非目標: すべての機能必須
- §1.5 画面フロー: 画面遷移ダイアグラム (Tier 1-2 必須)
- §2 FRロジック: 疑似コード/数式 (Tier 1-2 必須)
- §2.X ビジネスルール: 複雑なビジネスロジック (必要に応じて)
- §3.4 シーケンス図: Tier 1-2 必須 (Tier 3 任意)
- §5 検証 & テスト: テストフィクスチャ + チェックリスト (Tier 1-2 必須)
- §6 メッセージ定数: メッセージキー規則 + 必須キーリスト (必須)

Tierベースの適用マトリックス:
| セクション | Tier 1 | Tier 2 | Tier 3 |
|------|:------:|:------:|:------:|
| §0.0 プロジェクトコンテキスト | ✅ | ✅ | ✅ |
| §0.2.2 プロバイダー仕様 | ✅詳細 | ✅基本 | ⚪選択 |
| §0.3 エラーハンドリング | ✅全体 | ✅主要 | ⚪基本 |
| §0.9 デザイントークン | ✅ | ✅ | ⚪参照 |
| §0.10 イベント処理 & 非同期 | ✅ | ✅該当時 | ❌ |
| §1.5 画面フロー | ✅全体 | ✅主要 | ⚪選択 |
| §2.X ロジック疑似コード | ✅ | ⚪複雑なもの | ❌ |
| §3.4 シーケンス図 | ✅ | ✅ | ⚪選択 |
| §5 テストフィクスチャ | ✅全体 | ✅主要 | ⚪選択 |
| §6 メッセージ定数 | ✅ | ✅ | ✅ |

═══════════════════════════════════════════════════════════════
MVS (Minimum Viable SPEC) ゲート - AI実装前に必須確認
═══════════════════════════════════════════════════════════════

## MVS チェックリスト (5つの項目すべて ✅ 必須)

[ ] §0.0.2 命名規則 - ファイル/クラス/変数の命名規則定義
[ ] §0.1 ターゲットファイル - 範囲(Glob) + 条件付きファイルの明示
[ ] §1.4 目標 / 非目標 - 実装範囲と除外項目の明確化
[ ] §2 FR with AC (最低1つ) - 機能要件 + 受け入れ基準
[ ] §6.2 必要なメッセージ定数 - 必要なメッセージキーリスト

## MVS未達成時のポリシー

| 状況 | 許可される作業 | 禁止される作業 |
|------|----------|----------|
| MVS未達成 | スパイク/探索コード | プロダクション実装 |
| MVS達成、Tier未達成 | 該当Tierの必須のみ実装 | Tier上位要素 |
| 完全達成 | 全体実装 | - |

> ⚠️ **AI実装ゲート**: MVS未達成SPECに対して実装リクエストがあった場合、
> AIは「MVSチェックリスト未達成のため実装不可。次の項目補完が必要: [未達成項目]」と応答すべきです。

## MVS検証コマンド

```bash
# SPECバリデータ実行 (P2で実装予定)
make spec.validate SPEC=docs/features/XXX/SPEC-XXX.md
```

═══════════════════════════════════════════════════════════════

SSOT原則:
- API: src/app/api/*/route.tsのresponseSchema
- 用語集: docs/glossary.md
- テーマ: src/app/globals.css + docs/development/base-ui-theme-guide.md
- SPECはこれらを要約 + 意図を記録

AI実装時のチェックリスト:
1. §0.0 確認 → 命名規則遵守
2. 目標確認 → 範囲内作業のみ実施
3. 非目標確認 → 明示された項目は実装禁止
4. §0.7 確認 → System Prompt + Response Schemaを正確にコピー
5. §0.8 確認 → 入出力検証 + Fallback実装
6. §0.9 確認 → デザイントークン使用、ハードコーディング禁止
7. EF確認 → すべての例外フロー処理
8. シーケンス図確認 → 呼び出し順序遵守
9. §6 確認 → 必要なメッセージキーすべて存在確認
