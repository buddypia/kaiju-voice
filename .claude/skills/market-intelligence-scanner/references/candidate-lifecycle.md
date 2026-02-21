# 候補状態管理 (Candidate Lifecycle)

> **状態定義 SSOT**: [scan-status-schema.json](scan-status-schema.json)の `$defs.candidate_status`
> この文書は可読性参考用であり、スキーマが正式定義です。

---

## 候補状態遷移

```
pending_review → approved → converted (Featureに転換)
              ↘ rejected (却下)        ↘ reverted (変換取消)
              ↘ merged   (既存Featureに統合)
              ↘ deferred (保留 - 条件付き再検討)

reverted → pending_review (再検討)
rejected → pending_review (再検討)
deferred → pending_review / rejected
```

### 遷移マトリクス (SSOT: スキーマ `$defs.valid_transitions`)

|    現在の状態    | 遷移可能な状態                               |
| :--------------: | -------------------------------------------- |
| `pending_review` | `approved`, `rejected`, `merged`, `deferred` |
|    `approved`    | `converted`, `rejected`                      |
|   `converted`    | `reverted`                                   |
|    `rejected`    | `pending_review`                             |
|     `merged`     | _(Terminal State - 遷移不可)_                |
|    `deferred`    | `pending_review`, `rejected`                 |
|    `reverted`    | `pending_review`                             |

> **mergedはTerminal State**: 誤ったmergeは対象Featureから関連内容を削除して解決します。

### --force 強制遷移

> **v5.2 新規**: `--force` フラグを使用すると一般遷移規則を迂回して状態を強制変更できます。

**許可範囲**: `merged`(Terminal State)を除く**すべての状態**から対象状態へ遷移可能

**制約条件**:

1. `merged`からの強制遷移は不可 (Terminal State)
2. 同一状態への遷移は不可 (no-op 防止)
3. ユーザー確認を必ず経る必要あり (AskUserQuestion)

**History 記録**: `note`に `[FORCE]` 接頭辞必須

```json
{
  "at": "{時間}",
  "from_status": "converted",
  "to_status": "deferred",
  "triggered_by": "market-intelligence-scanner",
  "note": "[FORCE] バッチ保留: {事由}"
}
```

---

## History 記録規則

> **すべての状態変更時に必ず `history` 配列に append する必要があります。**

```json
{
  "history": [
    {
      "at": "{ISO 8601 時間}",
      "from_status": null,
      "to_status": "pending_review",
      "triggered_by": "market-intelligence-scanner",
      "note": "初期生成"
    }
  ]
}
```

### フィールド規則

| フィールド     | 必須 | 説明                                                     |
| -------------- | :--: | -------------------------------------------------------- |
| `at`           |  ✅  | ISO 8601 時間                                            |
| `from_status`  |  -   | 以前の状態。`null`は **history[0]にのみ許可** (初期生成) |
| `to_status`    |  ✅  | 新しい状態                                               |
| `triggered_by` |  ✅  | 実行主体                                                 |
| `note`         |  -   | 変更事由 (任意)                                          |

### `triggered_by` 値規則

| 実行主体                   | 値                              |
| -------------------------- | ------------------------------- |
| スキャン自動生成           | `"market-intelligence-scanner"` |
| ユーザー手動承認/却下      | `"manual"`                      |
| feature-architect 変換     | `"feature-architect"`           |
| feature-pilot revert       | `"feature-pilot"`               |
| マイグレーションスクリプト | `"migrate_scan_status.py"`      |

### チェーン連続性

- `history[i].to_status == history[i+1].from_status` (連続性保証)
- 時間順ソート: `history[i].at <= history[i+1].at`
- `history[-1].to_status == candidate.status` (最終状態一貫性)

---

## 状態別 JSON 例示

### 初期生成 (Phase 5)

```json
{
  "candidate_id": "2026-01-26-feature-name",
  "name": "Feature Name",
  "status": "pending_review",
  "doc_path": "docs/features/candidates/market/2026-01-26-feature-name.md",
  "scan_id": "scan-2026-01-26",
  "ice_score": 7.5,
  "japan_fit": 8,
  "source_docs": ["research-doc-1.md", "research-doc-2.md"],
  "created_at": "2026-01-26T10:00:00Z",
  "history": [
    {
      "at": "2026-01-26T10:00:00Z",
      "from_status": null,
      "to_status": "pending_review",
      "triggered_by": "market-intelligence-scanner",
      "note": "scan-2026-01-26: 初期生成"
    }
  ]
}
```

### 承認 (--accept)

```json
{
  "status": "approved",
  "reviewed_at": "{検討時間}",
  "history": [
    "...(既存項目維持)...",
    {
      "at": "{検討時間}",
      "from_status": "pending_review",
      "to_status": "approved",
      "triggered_by": "manual",
      "note": "ユーザー承認"
    }
  ]
}
```

### Feature 転換 (--accept 後自動)

```json
{
  "status": "converted",
  "converted_to": "030-new-feature-name",
  "history": [
    "...(既存項目維持)...",
    {
      "at": "{変換時間}",
      "from_status": "approved",
      "to_status": "converted",
      "triggered_by": "feature-architect",
      "note": "converted_to=030-new-feature-name"
    }
  ]
}
```

### 却下 (--reject)

```json
{
  "status": "rejected",
  "reviewed_at": "{検討時間}",
  "rejection_reason": "Japan-Fit 低い / 実装複雑度過大 / 優先順位低い",
  "history": [
    "...",
    {
      "at": "{検討時間}",
      "from_status": "pending_review",
      "to_status": "rejected",
      "triggered_by": "manual",
      "note": "{rejection_reason}"
    }
  ]
}
```

### 統合 (--merge)

```json
{
  "status": "merged",
  "reviewed_at": "{検討時間}",
  "merged_into": "015-gamification-system",
  "merge_note": "既存ゲーミフィケーションシステムにサブ機能として統合",
  "history": [
    "...",
    {
      "at": "{検討時間}",
      "from_status": "pending_review",
      "to_status": "merged",
      "triggered_by": "manual",
      "note": "merged_into=015-gamification-system"
    }
  ]
}
```

### 保留 (--defer)

```json
{
  "status": "deferred",
  "reviewed_at": "{検討時間}",
  "deferred_reason": "MVP 後検討 / 依存機能未実装",
  "deferred_until": "2026-06-01",
  "history": [
    "...",
    {
      "at": "{検討時間}",
      "from_status": "pending_review",
      "to_status": "deferred",
      "triggered_by": "manual",
      "note": "{deferred_reason}"
    }
  ]
}
```

### 変換取消 (Revert)

```json
{
  "status": "reverted",
  "reverted_from": "converted",
  "revert_reason": "{取消事由}",
  "history": [
    "...",
    {
      "at": "{取消時間}",
      "from_status": "converted",
      "to_status": "reverted",
      "triggered_by": "feature-pilot",
      "note": "{revert_reason}"
    }
  ]
}
```

---

## 条件付き必須フィールド (SSOT: スキーマ allOf)

|    状態     | 必須フィールド                   |
| :---------: | -------------------------------- |
| `converted` | `converted_to`                   |
| `rejected`  | `rejection_reason`               |
|  `merged`   | `merged_into`                    |
| `deferred`  | `deferred_reason`                |
| `reverted`  | `reverted_from`, `revert_reason` |

---

## 検証

状態変更後の整合性確認:

```bash
python3 .quality/scripts/check_scan_status.py
```
