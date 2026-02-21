# ADR テンプレートガイド

## 概要

ADR（Architecture Decision Record）は、アーキテクチャ上の重要な設計決定を記録する軽量ドキュメントです。Michael Nygard が2011年に提唱した形式が業界標準として広く採用されています。

> **参考**: Michael Nygard, "Documenting Architecture Decisions" (2011)

---

## Nygard 形式 ADR の構造

### 各セクションの解説

#### 1. Title（タイトル）

```markdown
# ADR-{feature_id}: {Decision Title}
```

- `feature_id`: 機能 ID（例: `029`）
- `Decision Title`: 決定内容を簡潔に表す（例: "単語データのローカルキャッシュ戦略"）
- 命名規則: `ADR-<feature_id>.md`

**良い例**: `ADR-029: Hive を使用したオフラインファースト単語キャッシュ`
**悪い例**: `ADR-029: データベース` （曖昧すぎる）

#### 2. Status（ステータス）

```markdown
## Status

Proposed
```

ADR のライフサイクル状態を示す。

#### 3. Context（コンテキスト）

```markdown
## Context

{この決定が必要になった背景・状況を記述}
```

- なぜこの決定が必要なのか
- どのような問題や要件があるのか
- 関連する技術的・ビジネス的制約
- 利害関係者の懸念事項

**書き方のポイント**:

- 事実に基づいて記述する（意見ではなく状況を述べる）
- 決定を正当化するのではなく、決定が必要な理由を述べる
- 技術的背景と非技術的背景の両方を含める

#### 4. Architecture Drivers（アーキテクチャドライバー）

```markdown
## Architecture Drivers

### Functional Drivers

### Quality Attribute Drivers

### Technical Constraints

### Business Constraints
```

- **Functional Drivers**: 機能要件からアーキテクチャに課される制約
- **Quality Attribute Drivers**: 性能、セキュリティ、可用性等の品質要件
- **Technical Constraints**: 既存スタック、フレームワーク等の技術的制約
- **Business Constraints**: コスト、スケジュール、チーム規模等のビジネス制約

#### 5. Alternatives Considered（検討した代替案）

```markdown
## Alternatives Considered

### Option A: {名前}（推奨）

- **Description**: アプローチの概要
- **Pros**: メリット一覧
- **Cons**: デメリット一覧
- **Risk**: リスク要因
```

- 最低3つの代替案を提示する
- 各案の違いが明確に分かるように記述する
- 推奨案には `（推奨）` を付記する

#### 6. ATAM Lite Evaluation（ATAM Lite 評価）

```markdown
## ATAM Lite Evaluation

| Quality Attribute | Weight | Option A | Option B | Option C |
| ----------------- | ------ | -------- | -------- | -------- |
```

- 品質属性ごとの比較マトリクス
- Sensitivity Points、Tradeoff Points、Risk Themes を含む

#### 7. Decision（決定）

```markdown
## Decision

Option {X} を選択する。

{選択の理由を1-3文で簡潔に述べる}
```

- 選択した案を明記する
- ATAM Lite 評価の結果に基づいた根拠を述べる
- 能動態で記述する（"...を選択する"）

#### 8. Consequences（結果）

```markdown
## Consequences

### Positive

### Negative

### Risks
```

- **Positive**: この決定により得られるメリット
- **Negative**: この決定により受け入れるデメリット
- **Risks**: この決定に伴うリスクと軽減策

#### 9. Platform Deviation Justification（Platform 制約逸脱の正当化）（条件付き）

```markdown
## Platform Deviation Justification

### Deviating from

- {PC-NNN}: {制約名}

### Justification

{なぜこの機能では Platform 制約から逸脱する必要があるのか}

### ATAM Lite Evidence

{逸脱の正当性を品質属性比較で証明}
```

- **条件**: Feature ADR が `docs/architecture/constraints.json` の制約から逸脱する場合のみ必須
- `constraints.json` の `deviation_policy` に従い、逸脱には ATAM Lite 評価による正当化が必要
- 逸脱対象の `PC-NNN` ID を明記し、トレードオフを定量的に示すこと
- `constraints.json` が存在しない場合はこのセクション不要

#### 10. References（参照）

```markdown
## References

- BRIEF: {path}
- Domain Model: {path} (if exists)
- Platform Constraints: docs/architecture/constraints.json (if exists)
```

- 関連する BRIEF、Domain Model、SPEC 等への参照
- Platform 制約逸脱がある場合、constraints.json への参照を含める

---

## ステータスライフサイクル

```
Proposed → Accepted → [Deprecated | Superseded]
```

| ステータス     | 意味                        | 遷移条件                    |
| -------------- | --------------------------- | --------------------------- |
| **Proposed**   | 提案中。レビュー待ち        | ADR 生成時の初期状態        |
| **Accepted**   | 承認済み。実装に進む        | レビュー完了、合意形成後    |
| **Deprecated** | 非推奨。もはや適用されない  | 要件変更、技術的陳腐化      |
| **Superseded** | 後続の ADR で置き換えられた | 新しい ADR が作成された場合 |

**Superseded の場合の記法**:

```markdown
## Status

Superseded by [ADR-035](./ADR-035.md)
```

---

## Hackathon Project プロジェクトでの ADR 運用ルール

### ファイル配置

```
docs/features/<id>-<name>/
├── BRIEF.md
├── CONTEXT.json
├── ADR-<id>.md          ← ここに配置
├── DOMAIN-MODEL.md      (任意)
└── SPEC-<id>-<name>.md
```

### ADR が必要な場合

| 条件                         | ADR 必要 | 例                                   |
| ---------------------------- | :------: | ------------------------------------ |
| Tier L/XL の新機能           |    ✅    | 新しいドメインモデル、複雑な状態管理 |
| 既存アーキテクチャからの逸脱 |    ✅    | Riverpod 以外の状態管理の検討        |
| 新しい外部サービス導入       |    ✅    | 新しい AI API、決済サービス          |
| Tier S/M の単純機能          |    ❌    | UI 調整、既存パターンの踏襲          |
| バグ修正                     |    ❌    | 既存設計の範囲内                     |

### Hackathon Project 固有の制約

以下は ADR の Technical Constraints に必ず含める:

1. **Feature-First + Simplified Clean Architecture**: `presentation/ → domain/ → data/`
2. **Riverpod 3.1+**: `@riverpod` Notifier 使用必須
3. **Freezed**: 不変データモデル
4. **Supabase**: PostgreSQL + Edge Functions

---

## 良い ADR の例

```markdown
# ADR-029: Hive を使用したオフラインファースト単語キャッシュ

## Status

Proposed

## Context

単語帳機能では、ユーザーが学習した単語をオフラインでも閲覧・復習できる必要がある。
現在のアプリはネットワーク接続を前提としており、オフライン対応のキャッシュ戦略が未定義である。
Supabase からのデータ取得は平均 200ms だが、地下鉄等の通信環境では 5 秒以上のタイムアウトが発生する。

## Architecture Drivers

### Functional Drivers

- オフライン時に最新100件の単語を表示可能
- オンライン復帰時に自動同期

### Quality Attribute Drivers

- Performance: オフライン時の表示は 50ms 以内
- Reliability: データ損失なし

### Technical Constraints

- Riverpod による状態管理
- Freezed による不変モデル

### Business Constraints

- MVP フェーズ: 最小工数で実装

## Decision

Option A（Hive ローカルキャッシュ）を選択する。
Flutter エコシステムでの実績と、Freezed との親和性が決め手となった。
```

## 悪い ADR の例

```markdown
# ADR-029: データベース

## Status

Accepted

## Context

データを保存する必要がある。

## Decision

SQLite を使う。
```

**問題点**:

- タイトルが曖昧（何の決定か不明）
- Context が不十分（なぜその決定が必要か不明）
- Alternatives がない（他の選択肢を検討していない）
- Consequences がない（決定の影響が不明）
- Architecture Drivers がない（制約条件が不明）
- ATAM Lite 評価がない（客観的根拠なし）
