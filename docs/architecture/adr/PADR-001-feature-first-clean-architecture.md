# PADR-001: Feature-First + Simplified Clean Architecture

## Status

Accepted (遡及作成: 2026-02-11)

## Context

Web Project Templateは、多数の独立した機能を持つWebアプリケーションとして設計される。各機能は独自のデータモデル、ビジネスロジック、UIを持ち、機能間の依存関係は明確に管理される必要がある。

プロジェクトはAI主導開発で、小規模チーム（1-2名 + AIエージェント）による運用を前提とする。アーキテクチャは以下の要件を満たす必要があった:

1. 機能単位での独立した開発・テストが可能
2. 依存方向が明確で循環依存を防止
3. 小規模チームでも管理可能な複雑さ
4. React/Next.js エコシステムとの親和性

## Architecture Drivers

### Functional Drivers

- 機能ごとの独立したライフサイクル管理
- 機能間の疎結合と明示的な依存関係
- データアクセス層とUI層の明確な分離

### Quality Attribute Drivers

- **Maintainability (H)**: 機能追加・変更時の影響範囲の局所化
- **Testability (H)**: 各レイヤーの独立テスト
- **Modularity (H)**: 機能単位のカプセル化

### Technical Constraints

- Next.js 14+ / React 18+
- TypeScript 5.0+
- Zod 3.0+ によるバリデーション

### Business Constraints

- 小規模チーム（AI主導開発）
- MVP優先のスケジュール
- 過剰な抽象化の回避

## Alternatives Considered

### Option A: Feature-First + Simplified Clean Architecture（採用）

- **Description**: 機能をトップレベルのフォルダ構造とし、各機能内部をcomponents/hooks/api/types に分離。
- **Pros**: 機能の独立性、依存方向の明確さ、小規模チームでの管理容易性
- **Cons**: 機能間のコード重複リスク
- **Risk**: 機能間の共通ロジックが増大した場合の shared レイヤー肥大化

### Option B: Layered Architecture（不採用）

- **Description**: 従来型のレイヤードアーキテクチャ（components/hooks/api がトップレベル）
- **Pros**: シンプルで理解しやすい
- **Cons**: 機能が増えるとレイヤー内が肥大化、機能間の境界が曖昧
- **Risk**: モノリシック化のリスク

### Option C: Full Clean Architecture + DDD Tactical（不採用）

- **Description**: Aggregate、Value Object、Domain Event等のDDD戦術パターンをフル適用
- **Pros**: ドメインロジックの完全なカプセル化
- **Cons**: 小規模プロジェクトには過剰な抽象化、学習コスト高
- **Risk**: 過剰設計（Over-Engineering）

## ATAM Lite Evaluation

| Quality Attribute | Weight | Option A | Option B | Option C |
| ----------------- | ------ | -------- | -------- | -------- |
| Maintainability   | H      | +++      | +        | +++      |
| Testability       | H      | +++      | ++       | +++      |
| Modularity        | H      | +++      | +        | +++      |
| Simplicity        | H      | ++       | +++      | +        |
| Initial Cost      | M      | ++       | +++      | +        |

### Sensitivity Points

- バレルファイルの適切な管理が機能カプセル化の鍵
- shared レイヤーの肥大化はモジュール性を損なう

### Tradeoff Points

- 完全なドメイン分離（Option C）vs 実装速度（Option A）
- 機能独立性 vs コード重複

## Decision

Option A（Feature-First + Simplified Clean Architecture）を選択する。

小規模チーム・AI主導開発において、保守性と実装速度のバランスが最も優れている。

## Consequences

### Positive

- 機能単位の独立開発・テストが可能
- 新規機能追加時のテンプレートが明確
- 依存方向（components → hooks → api）が強制される

### Negative

- 機能間で類似コードの重複が発生しうる
- バレルファイルの管理コスト

### Risks

- shared レイヤーの肥大化 → 定期的なリファクタリングで緩和
- バレルファイルの管理漏れ → lint ルールで緩和

## References

- [Feature-First Architecture ガイド](../../technical/feature-first-architecture.md)
- [CLAUDE.md アーキテクチャ概要](../../../CLAUDE.md)
- [tech-stack-rules.md セクション3](../../technical/tech-stack-rules.md)
