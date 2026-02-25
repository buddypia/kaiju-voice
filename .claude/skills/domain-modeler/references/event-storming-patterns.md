# Event Storming Lite パターンガイド

> **用途**: `domain-modeler` スキルの2段階（Event Storming Lite）で参照するパターンリファレンス。
> Alberto Brandolini の Event Storming メソッドを プロジェクト プロジェクト向けに簡略化したガイドです。

---

## 1. Event Storming 概要

### 1.1 Event Storming とは

Event Storming は Alberto Brandolini が考案したワークショップ手法で、ドメインの振る舞いをイベント中心に可視化する手法です。ドメインエキスパートと開発者が協力してビジネスプロセスを探索し、ドメインの全体像を把握します。

### 1.2 フルバージョン vs Lite バージョン

| 要素             |          フルバージョン           |   Lite バージョン（本スキル）    |
| ---------------- | :-------------------------------: | :------------------------------: |
| 参加者           | ドメインエキスパート + 開発チーム | AI エージェント（BRIEF.md 基盤） |
| 所要時間         |           数時間〜数日            |               数分               |
| 入力ソース       |            対話・議論             |     BRIEF.md のテキスト分析      |
| Domain Events    |          全プロセス網羅           |     対象機能のスコープ内のみ     |
| Commands         |       全ユーザーアクション        |        主要アクションのみ        |
| Aggregates       |          詳細設計レベル           |       戦略レベルの識別のみ       |
| Read Models      |               含む                |               省略               |
| Policies         |               含む                |          主要ルールのみ          |
| External Systems |               含む                |         関連するもののみ         |

### 1.3 Lite 版の簡略化ポイント

1. **スコープ限定**: 対象機能（BRIEF.md）の範囲内のみ分析
2. **テキストベース**: 対話ではなく文書分析によるイベント抽出
3. **戦略レベル**: 実装詳細には踏み込まず、ドメインの構造理解に注力
4. **主要パス重視**: Happy Path + 主要な異常系のみカバー
5. **Aggregate 簡略化**: エンティティの詳細属性は定義しない

---

## 2. 変換パターン: Events → Commands → Aggregates

### 2.1 ドメインイベント（Domain Events）の抽出

**定義**: ドメイン内で発生した事実を表す。過去形で命名する。

**抽出手順**:

1. BRIEF.md の User Stories から動詞を抽出
2. 各動詞を「完了した状態」に変換
3. ビジネス上意味のあるイベントのみ残す

**命名規則**:

- 英語 PascalCase + 過去形
- `{Entity}{Action}ed` 形式
- 例: `ActionSubmitted`, `BattleCompleted`, `RankEvaluated`

**抽出テーブル**:

| User Story の動詞    | Domain Event      | 説明                                 |
| -------------------- | ----------------- | ------------------------------------ |
| アクションを提出する | `ActionSubmitted` | 新しいアクションがバトルに提出された |
| バトルを完了する     | `BattleCompleted` | バトルセッションが完了した           |
| ランク評価を受ける   | `RankEvaluated`   | ランク評価が実施された               |

### 2.2 コマンド（Commands）の識別

**定義**: イベントを発生させるユーザーの意図・アクション。命令形で命名する。

**抽出手順**:

1. 各 Domain Event に対して「何がこのイベントを引き起こしたか」を問う
2. ユーザーの直接アクション → Command
3. システムの自動処理 → Policy（Lite 版では主要なもののみ）

**命名規則**:

- 英語 PascalCase + 命令形
- `{Action}{Entity}` 形式
- 例: `SubmitAction`, `StartBattle`, `ExecuteMove`

**変換テーブル**:

| Domain Event      | Command          | Actor   | トリガー           |
| ----------------- | ---------------- | ------- | ------------------ |
| `ActionSubmitted` | `SubmitAction`   | Learner | ユーザーアクション |
| `BattleCompleted` | `CompleteBattle` | System  | セッション終了時   |
| `RankEvaluated`   | `EvaluateRank`   | System  | テスト回答送信時   |

### 2.3 アグリゲート（Aggregates）の識別

**定義**: 関連するエンティティの集合で、整合性の境界を形成する。

**抽出手順**:

1. 各 Command/Event ペアに対して「どのエンティティが責任を持つか」を問う
2. 同じライフサイクルを共有するエンティティをグループ化
3. Aggregate Root を識別

**命名規則**:

- 英語 PascalCase + 単数形
- 例: `BattleAction`, `BattleSession`, `RankTest`

**識別テーブル**:

| Aggregate       | Root Entity  | 関連エンティティ | 主要インバリアント               |
| --------------- | ------------ | ---------------- | -------------------------------- |
| `BattleAction`  | BattleAction | Effect, Target   | 同一ターンでの重複アクション不可 |
| `BattleSession` | Session      | TurnItem, Answer | セッション内のターン数上限       |

---

## 3. Mermaid での表現パターン

### 3.1 イベントフロー図（Sequence Diagram）

```mermaid
sequenceDiagram
    actor Learner as 学習者
    participant Cmd as Command
    participant Agg as Aggregate
    participant Evt as Domain Event
    participant Ext as External System

    Note over Learner,Ext: 単語追加フロー
    Learner->>Cmd: SubmitAction(word, meaning)
    Cmd->>Agg: BattleAction
    Agg-->>Agg: 重複チェック (BR-01)
    Agg->>Evt: ActionSubmitted
    Evt->>Ext: SRS Schedule (初回スケジュール登録)

    Note over Learner,Ext: レビューフロー
    Learner->>Cmd: StartBattle()
    Cmd->>Agg: BattleSession
    Agg->>Evt: BattleStarted
    Learner->>Cmd: ExecuteMove(answer)
    Cmd->>Agg: BattleSession
    Agg-->>Agg: 正誤判定 (BR-02)
    Agg->>Evt: MoveExecuted
    Agg->>Evt: BattleCompleted
```

### 3.2 Aggregate 関係図（Flowchart）

```mermaid
flowchart TD
    subgraph BattleActionContext["Battle Action Context"]
        V[BattleAction] --> E[Example]
        V --> T[Tag]
    end

    subgraph ReviewContext["Battle Context"]
        RS[BattleSession] --> RI[TurnItem]
        RS --> A[Answer]
    end

    BattleActionContext -->|provides actions| ReviewContext
```

### 3.3 コマンド-イベントフロー（Flowchart）

```mermaid
flowchart LR
    C1[SubmitAction] -->|triggers| E1[ActionSubmitted]
    C2[StartBattle] -->|triggers| E2[BattleStarted]
    C3[ExecuteMove] -->|triggers| E3[MoveExecuted]
    E3 -->|policy: all items done| E4[BattleCompleted]

    style C1 fill:#4169E1,color:#fff
    style C2 fill:#4169E1,color:#fff
    style C3 fill:#4169E1,color:#fff
    style E1 fill:#FF8C00,color:#fff
    style E2 fill:#FF8C00,color:#fff
    style E3 fill:#FF8C00,color:#fff
    style E4 fill:#FF8C00,color:#fff
```

---

## 4. プロジェクト プロジェクトでの適用ガイドライン

### 4.1 ドメイン固有の考慮事項

プロジェクトは AI ゲーム対戦 Web サービスであり、以下のドメイン特性を考慮する必要があります。

| 特性                  | 影響                             | Event Storming での対応                     |
| --------------------- | -------------------------------- | ------------------------------------------- |
| **AI 生成コンテンツ** | コンテンツ生成は非同期・外部依存 | External System として API Route を明示 |
| **リアルタイム対戦**  | 対戦マッチングとターン管理が中核 | 対戦関連イベントを独立カテゴリとして扱う    |
| **AI 対戦ロジック**   | AI の行動決定が自動計算          | Policy として AI エンジンを明示             |
| **API バックエンド**  | API Routes + 認証                | 認証・認可イベントを考慮                    |

### 4.2 よく出現するドメインパターン

**対戦セッション系**:

```
StartBattle → BattleStarted → SubmitAction → ActionEvaluated → CompleteBattle → BattleCompleted
```

**コンテンツ生成系**:

```
RequestContent → ContentRequested → (AI Processing) → ContentGenerated → ContentPublished
```

**進捗管理系**:

```
CompleteBattle → BattleCompleted → UpdateRanking → RankingUpdated → (Policy) → RankUpAchieved
```

### 4.3 既存 Bounded Context との整合

新機能の Event Storming 実施時には、以下の既存 BC との境界・関係を確認してください:

| 既存 BC（推定） | 主要 Aggregate            | 関連 Edge Function    |
| --------------- | ------------------------- | --------------------- |
| Battle          | BattleSession, Turn       | `generate-content`    |
| Ranking         | PlayerRank, MatchResult   | -                     |
| Matchmaking     | MatchQueue, MatchRule     | `match-evaluate`      |
| AI Opponent     | AIStrategy, AIAction      | `ai-opponent`         |
| Commentary      | Commentary, Narration     | `generate-commentary` |
| User            | UserProfile, Subscription | -                     |

### 4.4 イベント命名の統一規則

プロジェクト プロジェクトでのイベント命名は以下の規則に従ってください:

1. **ドメイン接頭辞なし**: `Learning.SessionStarted` ではなく `SessionStarted`（BC 内で一意であれば十分）
2. **ビジネス用語使用**: 技術用語（`RowInserted`）ではなくビジネス用語（`ActionSubmitted`）
3. **粒度の目安**: ユーザーが認識できる単位（`ButtonClicked` は細かすぎ、`EverythingDone` は粗すぎ）

---

## 5. 出力テンプレート

### 2段階の出力セクション

```markdown
## 2. Event Storming

### 2.1 Domain Events

|  #  | Event       | Trigger              | Result                   | Aggregate        |
| :-: | ----------- | -------------------- | ------------------------ | ---------------- |
|  1  | {EventName} | {何がトリガーするか} | {結果として何が起きるか} | {所属 Aggregate} |

### 2.2 Commands & Aggregates

|  #  | Command       | Actor    | Aggregate        | Pre-conditions |
| :-: | ------------- | -------- | ---------------- | -------------- |
|  1  | {CommandName} | {実行者} | {対象 Aggregate} | {事前条件}     |

### 2.3 Event Flow

(Mermaid sequence diagram - 上記パターン3.1参照)
```

---

## 変更履歴

| 日付       | バージョン | 変更内容                                      |
| ---------- | ---------- | --------------------------------------------- |
| 2026-02-11 | v1.0       | 新規生成 - Event Storming Lite パターンガイド |
