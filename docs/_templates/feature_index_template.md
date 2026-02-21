# {NNN} {フィーチャー名}

> **状態**: {STATUS_EMOJI} {STATUS_TEXT} ({PROGRESS}%)
> **優先度**: {PRIORITY}
> **最終修正**: {DATE}

---

## 📌 概要

{機能に関する1-3文の核心説明}

### ユーザー価値

```
AS A 韓国語学習者
I WANT TO {ユーザーが欲しいもの}
SO THAT {得たい価値}
```

---

## 📚 文書一覧

|   タイプ   | 文書                                       | 説明                                               |   状態   |
| :--------: | ------------------------------------------ | -------------------------------------------------- | :------: |
|    SPEC    | [SPEC-{NNN}](./SPEC-{NNN}-{name}.md)       | 統合仕様 - WHY/WHAT/HOW                            | {STATUS} |
|    API     | [API-{NNN}](./API-{NNN}-{name}.md)         | 契約仕様 - リクエスト/レスポンス/エラー (条件付き) | {STATUS} |
|  Runbook   | [RUNBOOK-{NNN}](./RUNBOOK-{NNN}-{name}.md) | 運用/障害対応 (条件付き)                           | {STATUS} |
|   Screen   | [screens/](./screens/)                     | 画面別UI仕様                                       | {STATUS} |
| Legacy-PRD | [PRD-{NNN}](./PRD-{NNN}-{name}.md)         | (任意) 過去PRD                                     | {STATUS} |
| Legacy-FRD | [FRD-{NNN}](./FRD-{NNN}-{name}.md)         | (任意) 過去FRD                                     | {STATUS} |

### Screen一覧

| 画面ID        | 画面名   | 文書                                     |   状態   |
| ------------- | -------- | ---------------------------------------- | :------: |
| SCR-{NNN}-001 | {画面名} | [screens/{name}.md](./screens/{name}.md) | {STATUS} |

---

## 🔗 トレーサビリティマトリックス (Traceability Matrix)

> API → SPEC → Screen → Code → Test トレースチェーン

```
API-{NNN} (契約/スキーマ)
    │
    ▼
SPEC-{NNN} (ポリシー/フロー)
    │
    ▼
screens/{name}.md (UI仕様)
    ├── UI要素 → FR-{NNN}01
    │       └── lib/features/{feature}/presentation/pages/{name}_page.dart
    │
    ├── UI要素 → FR-{NNN}02
    │       └── lib/features/{feature}/data/repositories/{name}_repository.dart
    │
    └── API: {endpoint} (API文書参照)
    │
    ▼
テスト
    └── test/{name}_test.dart
```

---

## 📊 実装状況

### レイヤー別進捗率

| レイヤー        | ファイル                                                                |   状態   | 備考 |
| --------------- | ----------------------------------------------------------------------- | :------: | ---- |
| **UI**          |                                                                         |          |      |
| └ Page          | `lib/features/{feature}/presentation/pages/{name}_page.dart`            | {STATUS} |      |
| └ Widget        | `lib/features/{feature}/presentation/widgets/`                          | {STATUS} |      |
| **State**       |                                                                         |          |      |
| └ ViewModel     | `lib/features/{feature}/presentation/viewmodels/{name}_viewmodel.dart`  | {STATUS} |      |
| └ Provider      | `lib/features/{feature}/di/providers.dart`                              | {STATUS} |      |
| **Data**        |                                                                         |          |      |
| └ Model         | `lib/features/{feature}/data/models/{name}_model.dart`                  | {STATUS} |      |
| └ Repository    | `lib/features/{feature}/data/repositories/{name}_repository.dart`       | {STATUS} |      |
| **Test**        |                                                                         |          |      |
| └ Unit          | `test/features/{feature}/data/repositories/{name}_repository_test.dart` | {STATUS} |      |
| └ Widget        | `test/features/{feature}/presentation/pages/{name}_page_test.dart`      | {STATUS} |      |
| **Infra**       |                                                                         |          |      |
| └ Edge Function | `infra/supabase/functions/{name}/`                                      | {STATUS} |      |
| └ Migration     | `infra/supabase/migrations/{timestamp}_{name}.sql`                      | {STATUS} |      |

### FR別実装状況

| FR番号     | 機能説明   |   実装   |  テスト  |   文書   |
| ---------- | ---------- | :------: | :------: | :------: |
| FR-{NNN}01 | {機能説明} | {STATUS} | {STATUS} | {STATUS} |
| FR-{NNN}02 | {機能説明} | {STATUS} | {STATUS} | {STATUS} |
| FR-{NNN}03 | {機能説明} | {STATUS} | {STATUS} | {STATUS} |

**凡例**: ✅ 完了 | 🔄 進行中 | ⬜ 未開始 | ❌ 該当なし

---

## 🔗 関連文書

### 内部文書

| 文書       | リンク                                     | 役割                  |
| ---------- | ------------------------------------------ | --------------------- |
| DBスキーマ | [database-schema/](../../database-schema/) | テーブル定義          |
| API文書    | [API-{NNN}](./API-{NNN}-{name}.md)         | Edge Function/API契約 |

### 外部依存性

| FRD                           | 機能     | 依存タイプ |   状態   |
| ----------------------------- | -------- | ---------- | :------: |
| [FRD-{XXX}](../{XXX}-{name}/) | {機能名} | 前提依存   | {STATUS} |
| [FRD-{YYY}](../{YYY}-{name}/) | {機能名} | 後続依存   | {STATUS} |

---

## ♻️ 公共化候補 / 重複

| 項目                  | 現在位置 | 公共化提案                     | 備考   |
| --------------------- | -------- | ------------------------------ | ------ |
| {規則/コンポーネント} | {path}   | docs/shared または docs/common | {理由} |

---

## 🏷️ メタデータ

| 項目           | 値                            |
| -------------- | ----------------------------- |
| **作成日**     | {DATE}                        |
| **最終修正**   | {DATE}                        |
| **バージョン** | v1.0                          |
| **タグ**       | `#{tag1}` `#{tag2}` `#{tag3}` |

---

## 変更履歴

| 日付   | バージョン | 変更内容 |
| ------ | ---------- | -------- |
| {DATE} | v1.0       | 草案作成 |

---

<!--
状態絵文字凡例:
✅ 実装完了 (100%)
🔄 実装中 (1-99%)
⬜ 未開始 (0%)
🚫 保留/キャンセル

優先度:
P0 - MVP必須
P1 - MVPサポート
P2 - Post-MVP
-->
