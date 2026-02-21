# PADR-006: CONTEXT.json SSOT パターン

## Status

Accepted (遡及作成: 2026-02-11)

## Context

Hackathon ProjectはAI主導開発を採用しており、複数のAIスキル（feature-architect, feature-spec-generator, feature-implementer 等）が協調して機能を開発する。各スキルはセッション間でコンテキストを共有する必要があり、従来のJiraやNotionのような外部ツールではAIエージェントからの直接読み書きが困難である。

プロジェクトの開発パイプライン（feature-pilot）では、機能の全ライフサイクル（Briefing → SpecDrafting → Implementing → Done）を追跡し、中断・再開が頻繁に発生するAIセッション間でコンテキストを完全に保存する必要がある。

## Architecture Drivers

### Functional Drivers

- 機能開発の全ライフサイクル追跡
- セッション中断・再開時のコンテキスト完全保存
- 複数AIスキル間でのメタデータ共有
- FR（機能要件）ベースの進捗管理

### Quality Attribute Drivers

- **AI Readability (H)**: AIエージェントがJSON を直接読み書き可能
- **Traceability (H)**: 状態遷移とデシジョンの追跡
- **Reliability (H)**: VCS（Git）管理下での変更追跡
- **Consistency (H)**: 単一ファイルによる一貫性保証

### Technical Constraints

- Git リポジトリ内での管理（VCS 追跡）
- JSON フォーマット（AIパース容易）
- ファイルベースのロック機構

### Business Constraints

- 外部ツール依存の排除（Jira, Notion 等不使用）
- AI主導開発でのセッション中断・再開の頻繁な発生

## Alternatives Considered

### Option A: CONTEXT.json SSOT パターン（採用）

- **Description**: 機能ごとに `docs/features/<id>/CONTEXT.json` を配置し、全メタデータ（状態、進捗、決定履歴、参照文書）を単一JSONファイルで管理。状態マシンベースのライフサイクル管理。
- **Pros**: AI直接読み書き、VCS追跡、単一ファイルの一貫性、外部依存なし
- **Cons**: JSON の手動編集の困難さ、並行編集のロックの必要性
- **Risk**: CONTEXT.json の破損リスク（feature-doctor スキルで緩和）

### Option B: 外部プロジェクト管理ツール（不採用）

- **Description**: Jira, Linear, Notion 等の外部ツールでメタデータを管理
- **Pros**: UI による視覚的管理、チーム協業機能
- **Cons**: AIからのAPI経由アクセスの制約、コスト、VCS外
- **Risk**: API変更やサービス停止リスク

### Option C: 分散ファイル管理（不採用）

- **Description**: RUN_LOG.json, context_manifest.json 等を複数ファイルで分散管理
- **Pros**: 各ファイルが小さく、関心の分離
- **Cons**: ファイル間の整合性管理コスト、quick_resume 困難
- **Risk**: ファイル間の不整合（実際にv4.0以前で発生した問題）

## ATAM Lite Evaluation

| Quality Attribute   | Weight | Option A | Option B | Option C |
| ------------------- | ------ | -------- | -------- | -------- |
| AI Readability      | H      | +++      | +        | ++       |
| Traceability        | H      | +++      | +++      | +        |
| Consistency         | H      | +++      | ++       | +        |
| VCS Integration     | H      | +++      | +        | +++      |
| Visual Management   | L      | +        | +++      | +        |
| External Dependency | M      | +++      | +        | +++      |

## Decision

Option A（CONTEXT.json SSOT パターン）を選択する。

AI主導開発において、AIエージェントがメタデータを直接JSON形式で読み書きできることが最重要。VCS管理下での変更追跡と、単一ファイルによる一貫性保証がプロジェクトの信頼性を支える。enhanced-pipeline-proposal でもこのパターンの優位性が確認されている。

## Consequences

### Positive

- AIエージェントが3秒以内にコンテキストを把握（quick_resume セクション）
- 状態マシンベースの厳密なライフサイクル管理
- Git での変更履歴追跡による監査可能性
- feature-doctor による自動復旧メカニズム

### Negative

- JSON 手動編集の困難さ（人間向けではない）
- 並行編集のロック管理が必要

### Risks

- CONTEXT.json の破損 → feature-doctor スキルによる自動復旧
- 状態不整合 → バリデーションスキーマ（context_schema.json）で防止

## References

- [feature-pilot SKILL.md](../../../.claude/skills/feature-pilot/SKILL.md)
- [enhanced-pipeline-proposal.md](../../development/enhanced-pipeline-proposal.md)
- [CLAUDE.md プロジェクト構造](../../../CLAUDE.md)
