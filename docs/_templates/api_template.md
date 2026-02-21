# API-{NNN}: {機能名} API コントラクト

> **状態**: {STATUS} | **バージョン**: v{N} | **最終更新日**: {DATE}
> **SPEC バージョン**: v3.1 (ハイブリッド形式)

---

## 1. 概要

### 1.1 範囲

{この文書が扱うAPI/Edge Functionの範囲の概要}

### 1.2 SSOT (Single Source of Truth)

| 項目                          | SSOT の位置                                | 役割                  |
| ----------------------------- | ------------------------------------------ | --------------------- |
| **Request/Response スキーマ** | この文書のスキーマテーブル                 | タイプ/制約条件の定義 |
| **実際の実装**                | `infra/supabase/functions/{name}/index.ts` | responseSchema コード |
| **Example**                   | この文書のExampleセクション                | 参考用 (検証対象)     |

> **衝突時の優先順位**: コード > スキーマテーブル > Example
>
> スキーマテーブルはコードを反映し、Exampleはスキーマを反映します。
> 不一致が発見された場合、`spec-validator`が警告します。

---

## 2. エンドポイント一覧

| ID           | メソッド | パス                   | 認証 | 再現性 | 説明   |
| ------------ | -------- | ---------------------- | :--: | :----: | ------ |
| API-{NNN}-01 | POST     | `/functions/v1/{name}` |  ✅  |   ❌   | {説明} |
| API-{NNN}-02 | GET      | `/functions/v1/{name}` |  ✅  |   ✅   | {説明} |

---

## 3. API-{NNN}-01: {エンドポイント名}

> **SSOT**: `infra/supabase/functions/{name}/index.ts`

### 3.1 リクエスト

#### リクエス スキーマ (SSOT)

| フィールド     | タイプ  | 必須 | 制約条件                        | 説明               | 例                                 |
| -------------- | ------- | :--: | ------------------------------- | ------------------ | ---------------------------------- |
| `action`       | string  |  ✅  | enum: `add`, `update`, `delete` | 実行するアクション | `"add"`                            |
| `data`         | object  |  ✅  | -                               | アクションデータ   | `{}`                               |
| `data.word`    | string  |  ✅  | minLength: 1, maxLength: 100    | 韓国語の単語       | `"annyeonghaseyo"`                 |
| `data.meaning` | string  |  ✅  | maxLength: 500                  | L1 翻訳            | `"こんにちは"`                     |
| `data.level`   | integer |  ⚪  | min: 1, max: 6, default: 1      | TOPIK レベル       | `1`                                |
| `data.example` | string  |  ⚪  | maxLength: 1000                 | 例文               | `"annyeonghaseyo, bangapseumnida"` |

#### リクエスト例

```json
{
  "action": "add",
  "data": {
    "word": "annyeonghaseyo",
    "meaning": "こんにちは",
    "level": 1,
    "example": "annyeonghaseyo, bangapseumnida"
  }
}
```

### 3.2 レスポンス

#### レスポンススキーマ (SSOT)

| フィールド        | タイプ | 必須 | 制約条件                     | 説明                   | 例                                       |
| ----------------- | ------ | :--: | ---------------------------- | ---------------------- | ---------------------------------------- |
| `status`          | string |  ✅  | enum: `ok`, `error`          | 処理結果               | `"ok"`                                   |
| `data`            | object |  ⚪  | -                            | 成功時の結果データ     | `{}`                                     |
| `data.id`         | string |  ⚪  | format: uuid                 | 作成/修正された項目 ID | `"550e8400-e29b-41d4-a716-446655440000"` |
| `data.created_at` | string |  ⚪  | format: date-time (ISO 8601) | 作成時間               | `"2026-01-28T10:30:00Z"`                 |
| `error`           | object |  ⚪  | status=error の場合は必須    | エラー情報             | `{}`                                     |
| `error.code`      | string |  ⚪  | UPPER_SNAKE_CASE             | エラーコード           | `"INVALID_INPUT"`                        |
| `error.message`   | string |  ⚪  | -                            | 人間が読めるメッセージ | `"単語は必須です"`                       |
| `error.details`   | object |  ⚪  | -                            | 追加エラー情報         | `{}`                                     |

#### 成功レスポンス例 (200 OK)

```json
{
  "status": "ok",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2026-01-28T10:30:00Z"
  }
}
```

### 3.3 エラー応答

#### エラーコード

| HTTP | コード                | 条件                                     | ユーザーメッセージ (ja)                | クライアントアクション   |
| :--: | --------------------- | ---------------------------------------- | -------------------------------------- | ------------------------ |
| 400  | `INVALID_INPUT`       | 必須フィールドの欠落または形式のエラー   | "入力内容を確認してください"           | インラインエラー表示     |
| 400  | `DUPLICATE_ENTRY`     | 重複データの存在                         | "すでに登録されています"               | 重複通知表示             |
| 401  | `UNAUTHENTICATED`     | JWTなしまたは有効期限切れ                | "再ログインが必要です"                 | ログイン画面へ移動       |
| 403  | `FORBIDDEN`           | RLSポリシー違反 (他者データへのアクセス) | "アクセス権限がありません"             | ホームへ移動             |
| 429  | `RATE_LIMITED`        | リクエスト制限超過                       | "しばらく待ってから再試行してください" | 指数バックオフ後に再試行 |
| 500  | `INTERNAL_ERROR`      | サーバ内部エラー                         | "エラーが発生しました"                 | 再試行 (最大2回)         |
| 503  | `SERVICE_UNAVAILABLE` | 外部サービス障害                         | "現在サービスを利用できません"         | 後で再試行の案内         |

#### エラー応答例

**400 Bad Request - INVALID_INPUT**

```json
{
  "status": "error",
  "error": {
    "code": "INVALID_INPUT",
    "message": "単語は必須です",
    "details": {
      "field": "data.word",
      "reason": "required"
    }
  }
}
```

**400 Bad Request - DUPLICATE_ENTRY**

```json
{
  "status": "error",
  "error": {
    "code": "DUPLICATE_ENTRY",
    "message": "すでに登録されています",
    "details": {
      "existing_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  }
}
```

**401 Unauthorized**

```json
{
  "status": "error",
  "error": {
    "code": "UNAUTHENTICATED",
    "message": "再ログインが必要です"
  }
}
```

**429 Too Many Requests**

```json
{
  "status": "error",
  "error": {
    "code": "RATE_LIMITED",
    "message": "しばらく待ってから再試行してください",
    "details": {
      "retry_after_seconds": 60
    }
  }
}
```

**500 Internal Server Error**

```json
{
  "status": "error",
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "エラーが発生しました"
  }
}
```

---

## 4. レート制限 (選択)

> レート制限のないAPIはこのセクションを"N/A"と表示

| ティア     | リクエスト/分 | リクエスト/日 | バースト制限 |
| ---------- | :-----------: | :-----------: | :----------: |
| 無料       |      10       |      100      |      5       |
| プレミアム |      60       |    10,000     |      20      |

**超過時の動作**:

- 429応答を返す
- `Retry-After`ヘッダーに待機時間（秒）を含む
- クライアントは指数バックオフを適用

---

## 5. 互換性ポリシー

| 変更タイプ            |   互換性    | 処理方法                 |
| --------------------- | :---------: | ------------------------ |
| フィールド追加 (任意) | ✅ 互換あり | バージョン維持           |
| フィールド削除        |  ❌ 非互換  | メジャーバージョンアップ |
| タイプ変更            |  ❌ 非互換  | メジャーバージョンアップ |
| enum 値追加           |   ⚠️ 注意   | クライアント更新を推奨   |
| 制約条件緩和          | ✅ 互換あり | バージョン維持           |
| 制約条件強化          |  ❌ 非互換  | メジャーバージョンアップ |

**非推奨ポリシー**:

- フィールド削除前に最低2週間の警告期間
- `@deprecated`タグで文書に明記
- 応答に`X-Deprecated-Fields`ヘッダーを含む (任意)

---

## 6. 変更履歴

| 日付   | バージョン | 変更内容 | 根拠               |
| ------ | ---------- | -------- | ------------------ |
| {DATE} | v1.0       | 草案作成 | SPEC-{NNN}に基づく |

---

## Appendix A: JSON スキーマ (機械検証用)

> `spec-validator`がこのブロックを自動抽出して検証します。

```json:schema/api_endpoint
{
  "id": "API-{NNN}-01",
  "method": "POST",
  "path": "/functions/v1/{name}",
  "auth": true,
  "request": {
    "type": "object",
    "required": ["action", "data"],
    "properties": {
      "action": {
        "type": "string",
        "enum": ["add", "update", "delete"]
      },
      "data": {
        "type": "object",
        "required": ["word", "meaning"],
        "properties": {
          "word": { "type": "string", "minLength": 1, "maxLength": 100 },
          "meaning": { "type": "string", "maxLength": 500 },
          "level": { "type": "integer", "minimum": 1, "maximum": 6, "default": 1 },
          "example": { "type": "string", "maxLength": 1000 }
        }
      }
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
          "message": { "type": "string" },
          "details": { "type": "object" }
        }
      }
    }
  },
  "request_example": {
    "action": "add",
    "data": {
      "word": "annyeonghaseyo",
      "meaning": "こんにちは",
      "level": 1
    }
  },
  "response_example": {
    "status": "ok",
    "data": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2026-01-28T10:30:00Z"
    }
  },
  "errors": [
    {
      "http": 400,
      "code": "INVALID_INPUT",
      "condition": "必須フィールドが欠落または形式エラー",
      "client_action": "入力検証メッセージを表示"
    },
    {
      "http": 401,
      "code": "UNAUTHENTICATED",
      "condition": "JWTがないまたは期限切れ",
      "client_action": "再ログインを促す"
    },
    {
      "http": 429,
      "code": "RATE_LIMITED",
      "condition": "リクエストの制限を超えた",
      "client_action": "バックオフ後再試行"
    },
    {
      "http": 500,
      "code": "INTERNAL_ERROR",
      "condition": "サーバ内部エラー",
      "client_action": "再試行（最大2回）"
    }
  ]
}
```

---

## Appendix B: 検証チェックリスト

> プルリクエスト前確認事項

- [ ] **スキーマテーブルの完全性**
  - [ ] すべてのフィールドにタイプ、必須、例が記載されている - [ ] 制約条件にmin/max/enumなどが明記されている
- [ ] **Example一致**
  - [ ] リクエストExampleがリクエストスキーマと一致
  - [ ] レスポンスExampleがレスポンススキーマと一致
  - [ ] エラーExampleがエラーコードテーブルと一致
- [ ] **SSOT一致**
  - [ ] Edge FunctionのresponseSchemaとこの文書が一致
  - [ ] `spec-validator`を通過
- [ ] **エラーの完全性**
  - [ ] すべてのエラーコードにユーザーメッセージが存在
  - [ ] クライアントアクションが具体的
