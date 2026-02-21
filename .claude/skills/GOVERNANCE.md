# Skill System Governance

> **目的**: Hackathon Project プロジェクトのスキルシステムを**長期運用**可能に管理するためのガバナンスフレームワーク

---

## 1. スキルライフサイクル (Lifecycle)

### 1.1 状態定義

```
┌──────────┐    承認     ┌──────────┐   安定化    ┌──────────┐
│  Draft   │ ─────────→ │  Active  │ ─────────→ │  Stable  │
└──────────┘            └──────────┘            └──────────┘
     │                       │                       │
     │ 拒否                  │ 問題発生             │ 代替スキル登場
     ↓                       ↓                       ↓
┌──────────┐            ┌──────────┐            ┌──────────┐
│ Rejected │            │Maintenance│ ─────────→│Deprecated│
└──────────┘            └──────────┘   3ヶ月    └──────────┘
                                        未使用         │
                                                       │ 6ヶ月後
                                                       ↓
                                                ┌──────────┐
                                                │ Archived │
                                                └──────────┘
```

| 状態            | 説明                  | SKILL.md表示         |
| --------------- | --------------------- | -------------------- |
| **Draft**       | 開発中、使用不可      | `> 🚧 DRAFT`         |
| **Active**      | 正常運用中            | (表示なし)           |
| **Stable**      | 6ヶ月以上無修正で安定 | `> ✅ STABLE`        |
| **Maintenance** | 問題あり、修正中      | `> 🔧 MAINTENANCE`   |
| **Deprecated**  | 代替済み、使用非推奨  | `> ⚠️ DEPRECATED`    |
| **Archived**    | 削除済み              | (スキルフォルダ削除) |

### 1.2 状態遷移ルール

| 現在の状態  | 遷移条件                       | 次の状態    |
| ----------- | ------------------------------ | ----------- |
| Draft       | コードレビュー通過、テスト完了 | Active      |
| Draft       | 設計問題、重複発見             | Rejected    |
| Active      | 6ヶ月間バグ0件                 | Stable      |
| Active      | バグ/問題発生                  | Maintenance |
| Stable      | 代替スキル登場                 | Deprecated  |
| Maintenance | 修正完了                       | Active      |
| Maintenance | 3ヶ月以上未解決                | Deprecated  |
| Deprecated  | 6ヶ月経過                      | Archived    |

---

## 2. バージョン管理 (Versioning)

### 2.1 バージョンスキーマ

**形式**: `vMAJOR.MINOR.PATCH` (例: v2.1.0)

| タイプ    | 変更時点                           | 例                                     |
| --------- | ---------------------------------- | -------------------------------------- |
| **MAJOR** | 互換性を壊す変更、コアロジック変更 | v1.0 → v2.0 (turbo-mode実行エンジン化) |
| **MINOR** | 機能追加、下位互換維持             | v2.0 → v2.1 (新バッチアルゴリズム)     |
| **PATCH** | バグ修正、文書改善                 | v2.1 → v2.1.1 (タイポ修正)             |

### 2.2 バージョン記録

各スキルのSKILL.md下部に変更履歴セクション必須:

```markdown
## 変更履歴

| 日付       | バージョン | 変更内容                  |
| ---------- | ---------- | ------------------------- |
| 2026-02-01 | v2.0       | 大幅強化 - 実行エンジン化 |
| 2026-01-15 | v1.0       | 新規作成                  |
```

### 2.3 MANIFEST.jsonバージョンフィールド

```json
{
  "skill_version": "2.0.0",
  "min_compatible_version": "1.0.0"
}
```

### 2.4 Schema Version (MANIFEST.json)

| Schema Version | 導入日  | 必須フィールド                                                                           | 説明                   |
| :------------: | :-----: | ---------------------------------------------------------------------------------------- | ---------------------- |
|     **1**      | 2026-01 | tier, public_api, calls, called_by                                                       | 基本メタデータ         |
|     **2**      | 2026-02 | + enforced_protocol, model_routing, evidence_policy, preflight_checks, postflight_checks | Enforced Skill Pattern |

**マイグレーションガイド**:

- 新規スキル: schema_version 2必須
- 既存スキル: 段階的マイグレーション (コアスキル優先)

---

## 2.5 Enforced Skill Pattern (ESP) v2.0

> **目的**: "ガイドラインの文書化のみ"から"実行時の強制"への転換

### ESP核心要素

| 要素                      | 必須 | 説明                                      |
| ------------------------- | :--: | ----------------------------------------- |
| **Pre-flight Checklist**  |  ✅  | スキル実行前に出力 + 検証必須             |
| **Model Routing Policy**  |  ✅  | Task ツール呼び出し時model パラメータ必須 |
| **Evidence Policy**       |  ⚠️  | 検証結果キャッシング (選択的)             |
| **Post-flight Checklist** |  ✅  | スキル完了前に出力 + 検証必須             |
| **Violation Protocol**    |  ✅  | 違反時の処理ポリシー                      |

### Pre-flight Checklist標準形式

```markdown
## ✈️ Pre-flight Checklist

|  #  | 項目                   | 状態 | 備考 |
| :-: | ---------------------- | :--: | ---- |
|  1  | (スキル別チェック項目) |  ⬜  |      |
|  2  | ...                    |  ⬜  |      |

→ すべての項目 ✅ 確認後に実行進行
→ 一つでも ❌ の場合は即座に中断 + 理由報告
```

### Model Routing Policy標準

| 作業複雑度                 | 推奨モデル | 例                               |
| -------------------------- | :--------: | -------------------------------- |
| 読み取り/検索/単純チェック |   haiku    | ファイル検索、状態確認           |
| コード分析/単一修正        |   sonnet   | バグ分析、機能実装               |
| アーキテクチャ/複合問題    |    opus    | 設計決定、複雑なリファクタリング |

**フォールバックチェーン**: haiku失敗 → sonnet → opus

### Evidence Policy (検証キャッシュ)

> **⚠️ 設計原則 (2026-02-02修正)**:
> `cache_location`は技術的に自動化不可能なため**削除**。
> Evidence Freshnessは**CLAUDE.mdのAI行動指針**で処理。
> スキルはキャッシング実装の代わりに"推奨再検査時点"のみを文書化。

```json
{
  "evidence_policy": {
    "note": "Evidence FreshnessはCLAUDE.md AI行動指針で処理。別途キャッシュ実装なし",
    "recommended_freshness": [
      { "type": "flutter_analyze", "minutes": 30, "invalidation": "lib/**/*.dart変更時" },
      { "type": "flutter_test", "minutes": 30, "invalidation": "test/**/*.dart変更時" }
    ]
  }
}
```

### Violation Protocol標準

| 違反タイプ             |  深刻度  | 処理                     |
| ---------------------- | :------: | ------------------------ |
| Pre-flight未出力       | CRITICAL | 即座に中断、最初から再開 |
| Modelパラメータ欠落    |   HIGH   | 該当Task再実行           |
| Post-flight未検証      |   HIGH   | 完了報告前に検証実行     |
| Evidenceキャッシュ無視 |  MEDIUM  | 警告後に進行             |

### ESP適用スキル一覧

| スキル          | Schema | ESP Version |    状態     |
| --------------- | :----: | :---------: | :---------: |
| turbo-mode      |   2    |    v2.0     |   ✅ v3.0   |
| persistent-mode |   2    |    v2.0     |   ✅ v3.0   |
| flutter-qa      |   2    |    v2.0     |   ✅ v3.0   |
| security-scan   | **2**  |  **v2.0**   | ✅ **v2.0** |
| feature-pilot   | **2**  |  **v2.0**   | ✅ **v9.0** |

---

## 3. 依存性管理 (Dependencies)

### 3.1 依存性タイプ

| タイプ                 | 説明                           | MANIFESTフィールド      |
| ---------------------- | ------------------------------ | ----------------------- |
| **必須 (Required)**    | なければスキル実行不可         | `dependencies.required` |
| **選択 (Optional)**    | あれば機能向上                 | `dependencies.optional` |
| **逆方向 (Called By)** | このスキルを呼び出す上位スキル | `called_by`             |

### 3.2 循環依存性禁止

```
❌ 禁止:
A → B → C → A

✅ 許可:
A → B → C
A → D
```

### 3.3 依存性変更時の影響分析

スキルAが変更される時:

1. `A.calls`にある下位スキルの影響確認
2. `A.called_by`にある上位スキルに通知
3. 変更履歴に影響範囲を記録

---

## 4. 効果測定 (Metrics Framework)

> **目的**: スキルシステムのROIを測定し継続的改善のためのデータ基盤意思決定

### 4.1 核心測定項目 (KPIs)

#### Primary Metrics (必須測定)

| メトリック   | 説明                  | 測定方法                   | 目標  |
| ------------ | --------------------- | -------------------------- | :---: |
| **実行時間** | スキル開始 → 完了時間 | タイムスタンプ差分         |   -   |
| **成功率**   | 成功/失敗比率         | 完了状態追跡               | ≥ 90% |
| **再作業率** | 手動修正必要回数      | スキル完了後の修正コミット | ≤ 10% |

#### Secondary Metrics (選択測定)

| メトリック           | 説明                     | 測定方法              | 備考                          |
| -------------------- | ------------------------ | --------------------- | ----------------------------- |
| **トークン推定値**   | スキル当たり消費トークン | 3-Tierモデル推定      | Haiku 1x, Sonnet 3x, Opus 10x |
| **並列効率**         | turbo-mode活性化率       | 並列バッチ数 / 総作業 | 目標 ≥ 50%                    |
| **パイプライン深度** | スキル呼び出しチェーン長 | calls追跡             | 情報                          |

### 4.2 測定ログフォーマット (標準)

**CRITICAL**: すべてのスキル実行完了時に以下のフォーマットでログを出力する必要があります。

#### 単一スキルログ

```markdown
## 📊 スキル実行完了

| 項目               | 値                                                               |
| ------------------ | ---------------------------------------------------------------- |
| スキル             | `feature-pilot v5.0`                                             |
| 作業タイプ         | NEW_FEATURE                                                      |
| 対象               | `046-insight-dashboard`                                          |
| 開始               | 2026-02-01T10:30:00+09:00                                        |
| 終了               | 2026-02-01T10:45:00+09:00                                        |
| 所要時間           | **15分**                                                         |
| 結果               | ✅ 成功                                                          |
| 下位スキル呼び出し | feature-architect → feature-spec-generator → feature-implementer |
| 生成ファイル       | 12個                                                             |
| 修正ファイル       | 3個                                                              |
```

#### turbo-mode並列実行ログ

```markdown
## 📊 Turbo Mode バッチ実行完了

| 項目       | 値                  |
| ---------- | ------------------- |
| モード     | `turbo-mode v2.0`   |
| 総作業数   | 10                  |
| バッチ構成 | 4 (3+2+3+2)         |
| 並列効率   | **70%** (7/10 同時) |

### バッチ別結果

| バッチ | 作業数 | ティア | 所要時間 | 状態 |
| :----: | :----: | :----: | :------: | :--: |
|   B1   |   3    | Haiku  |   45秒   |  ✅  |
|   B2   |   2    | Sonnet |   2分    |  ✅  |
|   B3   |   3    | Sonnet |   3分    |  ✅  |
|   B4   |   2    | Sonnet | 2分30秒  |  ✅  |

**総所要時間**: 8分15秒
**順次実行予想時間**: 20分
**節約**: **60%** ⚡
```

### 4.3 メトリック収集プロトコル

#### スキル別測定責任

|          ティア           | 責任                           | ログ出力時点       |
| :-----------------------: | ------------------------------ | ------------------ |
| **Tier 1** (Orchestrator) | 全体パイプラインメトリック集計 | パイプライン完了時 |
|   **Tier 2** (Pipeline)   | 個別スキルメトリック           | スキル完了時       |
|   **Tier 3** (Utility)    | 必要時のみ (簡単な作業除外)    | 選択的             |

#### 自動測定トリガー

```
スキル呼び出し
   ↓
開始タイムスタンプ記録
   ↓
スキル実行 (下位スキル呼び出し時に再帰的測定)
   ↓
終了タイムスタンプ記録
   ↓
メトリックログ出力 (4.2フォーマット)
   ↓
CONTEXT.json progressセクションに記録 (選択的)
```

### 4.4 トークンコスト推定モデル

> **注意**: 実際のトークン自動測定は不可能、以下は推定値

| 作業タイプ         | 予想入力 | 予想出力 |  Tier  | 推定コスト (相対) |
| ------------------ | :------: | :------: | :----: | :---------------: |
| ファイル検索       |   100    |   500    | Haiku  |        1x         |
| パターン分析       |  2,000   |  1,000   | Haiku  |        5x         |
| CONTEXT生成        |  3,000   |  2,000   | Sonnet |        30x        |
| SPEC生成           |  5,000   |  8,000   | Sonnet |        60x        |
| コード実装         |  10,000  |  15,000  | Sonnet |       100x        |
| アーキテクチャ分析 |  15,000  |  5,000   |  Opus  |       300x        |

**コスト最適化原則**:

- 可能な限りHaiku使用 (読み取り/検索作業)
- 並列実行でSonnet待機時間短縮
- Opusは本当に必要な時のみ (アーキテクチャ/セキュリティ)

### 4.5 メトリック保存場所

| メトリックタイプ | 保存場所                                | 形式                         |
| ---------------- | --------------------------------------- | ---------------------------- |
| **実行別ログ**   | 対話内出力                              | Markdownテーブル             |
| **機能別累積**   | `docs/features/*/CONTEXT.json`          | `progress.metrics`セクション |
| **全体集計**     | `docs/metrics/skill-metrics-YYYY-QN.md` | 四半期レポート               |

#### CONTEXT.json metricsスキーマ

```json
{
  "progress": {
    "metrics": {
      "skill_runs": [
        {
          "skill": "feature-pilot",
          "version": "5.0",
          "timestamp": "2026-02-01T10:45:00+09:00",
          "duration_seconds": 900,
          "result": "success",
          "sub_skills": ["feature-architect", "feature-spec-generator", "feature-implementer"],
          "turbo_enabled": true,
          "parallel_batches": 3
        }
      ],
      "totals": {
        "total_runs": 5,
        "success_rate": 0.8,
        "avg_duration_seconds": 720,
        "turbo_usage_rate": 0.6
      }
    }
  }
}
```

### 4.6 四半期メトリックレビュー

#### レビュー時点

- **月間 (1日)**: ヘルスチェックスクリプト自動実行
- **四半期 (1, 4, 7, 10月)**: 全体メトリックレビューミーティング

#### 分析項目

| 分析         | 指標                            | アクショントリガー              |
| ------------ | ------------------------------- | ------------------------------- |
| スキル活用度 | 呼び出し回数 Top 10 / Bottom 10 | Bottom 10 → Deprecated検討      |
| 成功率       | スキル別成功/失敗率             | < 80% → Maintenance転換         |
| 実行時間     | 平均/P90実行時間推移            | 20%以上増加 → 最適化必要        |
| 並列効率     | turbo-mode活用率                | < 30% → 並列化機会発掘          |
| コスト効率   | Haiku:Sonnet:Opus比率           | Opus > 10% → ダウングレード検討 |

#### 四半期レポートテンプレート

```markdown
# スキルメトリックレポート - 2026 Q1

> **期間**: 2026-01-01 ~ 2026-03-31
> **作成者**: AI Assistant
> **作成日**: 2026-04-01

## Executive Summary

| 指標             | 今四半期 | 前四半期 | 変化  |
| ---------------- | :------: | :------: | :---: |
| 総スキル実行数   |   150    |   120    | ↑ 25% |
| 全体成功率       |   92%    |   88%    | ↑ 4p  |
| 平均実行時間     |   12分   |   15分   | ↓ 20% |
| turbo-mode活用率 |   65%    |   40%    | ↑ 25p |

## Top 5 Most Used Skills

| 順位 | スキル                 | 呼び出し数 | 成功率 |
| :--: | ---------------------- | :--------: | :----: |
|  1   | feature-pilot          |     45     |  95%   |
|  2   | bug-fix                |     30     |  90%   |
|  3   | feature-implementer    |     28     |  88%   |
|  4   | feature-spec-generator |     25     |  96%   |
|  5   | turbo-mode             |     20     |  100%  |

## Issues & Recommendations

### 🔴 Critical

- (例: legacy-migration成功率60% - 検討必要)

### 🟡 Warning

- (例: priority-analyzer未使用3ヶ月 - Deprecated検討)

### ✅ Achievements

- turbo-mode v2.0導入後の並列効率25p向上
- 全体実行時間20%短縮

## Next Quarter Goals

1. MANIFEST未保有スキル50%補完
2. 全体成功率95%達成
3. turbo-mode活用率75%達成
```

---

## 5. レビュー/承認プロセス (Review)

### 5.1 変更タイプ別プロセス

| 変更タイプ          | レビュー必要 | 承認基準             |
| ------------------- | :----------: | -------------------- |
| 新スキル作成        |   ✅ 必須    | 重複なし、Tier適合   |
| MAJORバージョン変更 |   ✅ 必須    | 互換性検討、影響分析 |
| MINORバージョン変更 |   ⚠️ 推奨    | テスト通過           |
| PATCHバージョン変更 |   ❌ 選択    | -                    |
| スキル廃止          |   ✅ 必須    | 代替スキル案内       |

### 5.2 レビューチェックリスト

**新スキル作成時**:

- [ ] 既存スキルと重複していないか？
- [ ] Tierが適切か？
- [ ] MANIFEST.jsonスキーマ準拠？
- [ ] 依存性グラフに循環がないか？
- [ ] 使用例を含んでいるか？

**スキル変更時**:

- [ ] 変更履歴更新？
- [ ] バージョン番号増加？
- [ ] 影響を受けるスキルリスト確認？
- [ ] 下位互換性維持？

---

## 6. 定期監査 (Audit)

### 6.1 月間ヘルスチェック

毎月1日自動実行:

1. すべてのMANIFEST.jsonスキーマ検証
2. 依存性一貫性確認
3. Deprecatedスキルの経過時間確認

### 6.2 四半期全体監査

毎四半期手動実行:

1. スキルインベントリ更新
2. 未使用スキル識別 (3ヶ月以上未呼び出し)
3. メトリックレビューおよび改善点導出
4. スキル統合/分離検討

### 6.3 監査報告書テンプレート

```markdown
# スキルシステム監査報告書

> **期間**: 2026-Q1 (1月-3月)
> **作成日**: 2026-04-01

## 要約

- 総スキル数: 37個
- Active: 30個, Deprecated: 5個, Maintenance: 2個

## 主要発見

1. turbo-mode v2.0導入後のコンテキスト収集時間60%削減
2. feature-data-wiring, feature-navigation-wiring廃止予定

## 推奨措置

1. [ ] 未使用スキル3個のDeprecated転換
2. [ ] hardcoded-\*スキル統合検討
```

---

## 7. スキルカタログ

### 7.1 ガバナンスヘルス要約

> **監査日**: 2026-02-01 (更新)

| 指標           |     数値      |             状態             |
| -------------- | :-----------: | :--------------------------: |
| 総スキル数     |     37個      |              -               |
| MANIFEST保有   |  19個 (51%)   |         🟢 Improving         |
| MANIFEST未保有 |  18個 (49%)   |      🟡 Action Required      |
| Active         |     35個      |              ✅              |
| Deprecated     |      2個      |   ✅ 整理中 (MANIFEST完了)   |
| Archived       |      0個      |              -               |
| テンプレート   | ✅ 標準化完了 | `_templates/skill-template/` |

### 7.2 現在のスキルインベントリ (全体40個)

#### Tier 1: Orchestrator (4個)

| スキル                      |  状態  | バージョン | Schema | MANIFEST |  ESP   | 説明                                           |
| --------------------------- | :----: | :--------: | :----: | :------: | :----: | ---------------------------------------------- |
| feature-pilot               | Active |  **v9.0**  | **2**  |    ✅    | **✅** | 開発リクエスト統合エントリーポイント (ESP適用) |
| research-gap-analyzer       | Active |    v1.0    |   1    |    ✅    |   -    | リサーチギャップ分析                           |
| market-intelligence-scanner | Active |    v1.0    |   1    |    ✅    |   -    | 市場/競合分析                                  |
| turbo-mode                  | Active |  **v3.0**  | **2**  |    ✅    | **✅** | 並列実行エンジン (ESP適用)                     |

#### Tier 2: Pipeline (19個)

| スキル                 |  状態  | バージョン | MANIFEST | 説明                                |
| ---------------------- | :----: | :--------: | :------: | ----------------------------------- |
| domain-modeler         | Active |    v1.0    |    ✅    | DDD Strategic + Event Storming Lite |
| architecture-selector  | Active |    v1.0    |    ✅    | ADR + ATAM Lite アーキテクチャ選定  |
| system-designer        | Active |    v1.0    |    ✅    | C4 Model L1-L2 システム設計         |
| feature-architect      | Active |    v1.0    |    ✅    | CONTEXT.json生成                    |
| feature-spec-generator | Active |    v1.0    |    ✅    | SPEC.md生成                         |
| feature-implementer    | Active |    v1.0    |    ✅    | TDD実装                             |
| feature-wiring         | Active |    v1.0    |    ✅    | データ+ナビ統合連携                 |
| ui-approval-gate       | Active |    v1.0    |    ✅    | UI承認ゲート                        |
| bug-fix                | Active |    v1.0    |    ✅    | バグ分析/修正                       |
| feature-spec-updater   | Active |    v1.0    |    ✅    | SPEC修正                            |
| feature-status-sync    | Active |    v1.0    |    ✅    | 状態同期                            |
| priority-analyzer      | Active |    v1.0    |    ✅    | 優先順位分析                        |
| pre-quality-gate       | Active |    v1.0    |    ✅    | 品質検証                            |
| spec-validator         | Active |    v1.0    |    ❌    | SPECスキーマ検証                    |
| feature-doctor         | Active |    v1.0    |    ❌    | 状態自動復旧                        |
| legacy-migration       | Active |    v1.0    |    ❌    | PRD→CONTEXTマイグレーション         |
| hardcoded-scan         | Active |    v1.0    |    ❌    | ハードコーディング統合スキャン      |
| wireframe-manager      | Active |    v1.0    |    ❌    | ワイヤーフレーム管理                |

#### Tier 3: Utility (15個)

| スキル                  |    状態    | バージョン | Schema |            MANIFEST            |  ESP   | 説明                         |
| ----------------------- | :--------: | :--------: | :----: | :----------------------------: | :----: | ---------------------------- |
| flutter-qa              |   Active   |  **v3.0**  | **2**  |               ✅               | **✅** | QAサイクル (ESP適用)         |
| security-scan           |   Active   |  **v2.0**  | **2**  |               ✅               | **✅** | セキュリティ検査 (ESP適用)   |
| persistent-mode         |   Active   |  **v3.0**  | **2**  |               ✅               | **✅** | 完了まで自動持続 (ESP適用)   |
| skill-health-check      |   Active   |  **v2.0**  | **2**  |               ✅               | **✅** | ガバナンス自動監査 + ESP検証 |
| arb-sync                | Deprecated |    v1.0    |   ❌   |     (日本語専用のため廃止)     |
| edge-function-validator |   Active   |    v1.0    |   ❌   |       Edge Function検証        |
| test-coverage-check     |   Active   |    v1.0    |   ❌   |        テストカバレッジ        |
| sync-claude-md          |   Active   |    v1.0    |   ❌   |         CLAUDE.md同期          |
| glossary-updater        |   Active   |    v1.0    |   ❌   |           用語集更新           |
| hardcoded-text-finder   |   Active   |    v1.0    |   ❌   | ハードコーディングテキスト検出 |
| hardcoded-color-finder  |   Active   |    v1.0    |   ❌   |    ハードコーディング色検出    |
| migration-sync          |   Active   |    v1.0    |   ❌   |      マイグレーション同期      |
| supabase-sync           |   Active   |    v1.0    |   ❌   |          Supabase同期          |
| gemini                  |   Active   |    v1.0    |   ❌   |         Gemini CLI連携         |
| openai-deep-research    |   Active   |    v1.0    |   ❌   |     OpenAIディープリサーチ     |
| google-deep-research    |   Active   |    v1.0    |   ❌   |     Googleディープリサーチ     |
| app-review-analyzer     |   Active   |    v1.0    |   ❌   |    アプリストアレビュー分析    |

#### Deprecated (2個) - 整理予定

| スキル                    |    状態    | MANIFEST | 代替スキル     | Deprecated日付 | Archive予定 |
| ------------------------- | :--------: | :------: | -------------- | :------------: | :---------: |
| feature-data-wiring       | Deprecated |    ✅    | feature-wiring |   2026-01-25   | 2026-07-25  |
| feature-navigation-wiring | Deprecated |    ✅    | feature-wiring |   2026-01-25   | 2026-07-25  |

### 7.3 MANIFEST未保有スキル優先整備対象

> **長期運用リスク**: MANIFESTなしでは依存性/バージョン/状態追跡不可

| 優先順位 | スキル                 | 理由                         | 措置期限  |
| :------: | ---------------------- | ---------------------------- | :-------: |
|  ~~P0~~  | ~~turbo-mode~~         | ✅ **完了** (2026-02-01)     |     -     |
|  ~~P1~~  | ~~flutter-qa~~         | ✅ **完了** (2026-02-01)     |     -     |
|  ~~P1~~  | ~~security-scan~~      | ✅ **完了** (2026-02-01)     |     -     |
|  ~~P1~~  | ~~persistent-mode~~    | ✅ **完了** (2026-02-01)     |     -     |
|  ~~P1~~  | ~~skill-health-check~~ | ✅ **新規作成** (2026-02-01) |     -     |
|    P2    | spec-validator         | SPEC品質ゲート               | 2週間以内 |
|    P2    | feature-doctor         | 状態復旧のコア               | 2週間以内 |
|    P3    | 残り14個               | 補助ユーティリティ           | 1ヶ月以内 |

### 7.4 依存性マトリクス

```
                    呼び出される (Called By)
呼び出す (Calls)   pilot  arch   spec   impl   wiring  turbo
───────────────────────────────────────────────────────────
feature-pilot     -      ✓      ✓      ✓       ✓       -
feature-architect -      -      ✓      -       -       ✓
feature-spec-gen  -      -      -      -       -       -
feature-impl      -      -      -      -       ✓       ✓
feature-wiring    -      -      -      -       -       -
turbo-mode        ✓      ✓      -      ✓       -       -
research-gap      -      -      -      -       -       -
market-intel      -      ✓      -      -       -       -
ui-approval       -      -      -      -       -       -
```

### 7.5 ヘルスチェック発見事項

#### 🔴 Critical Issues

1. **MANIFEST未保有率65%**: 長期運用に深刻なリスク
   - バージョン管理不可
   - 依存性追跡不可
   - 状態遷移検証不可

2. **turbo-mode v2.0 MANIFEST不在**: Tier 1コアスキルであるにもかかわらずガバナンス外

#### 🟡 Medium Issues

1. ~~**Deprecatedスキル未整理**~~: ✅ **解決済み** (2026-02-01)
   - feature-data-wiring, feature-navigation-wiringにMANIFEST.json生成完了
   - 明確なsunset_date(2026-07-25)とリダイレクション情報を含む

2. **重複機能疑い**:
   - hardcoded-scan ↔ hardcoded-text-finder + hardcoded-color-finder (上位互換)

#### ✅ 推奨措置

1. ~~**即時**: turbo-mode MANIFEST.json生成~~ ✅ **完了** (2026-02-01)
2. ~~**即時**: Deprecatedスキル MANIFEST.json生成~~ ✅ **完了** (2026-02-01)
3. **1週間以内**: flutter-qa, security-scan, persistent-mode MANIFEST生成
4. **1ヶ月以内**: 残りのスキルMANIFEST補完
5. **四半期**: Deprecatedスキル整理状態レビュー

---

## 8. 緊急対応 (Incident Response)

### 8.1 スキル障害等級

| 等級 | 説明                  | 対応時間 |
| :--: | --------------------- | :------: |
|  P0  | feature-pilot完全障害 |   即時   |
|  P1  | Tier 2コアスキル障害  |  4時間   |
|  P2  | Tier 3スキル障害      |  24時間  |
|  P3  | 文書/タイポエラー     |  1週間   |

### 8.2 ロールバックプロトコル

スキル変更後に問題発生時:

1. SKILL.mdを以前のバージョンにロールバック (git revert)
2. 変更履歴にロールバック理由を記録
3. 原因分析後に修正バージョンを再デプロイ

---

## 9. スキルテンプレート (Templates)

### 9.1 標準テンプレート位置

```
.claude/skills/_templates/
├── README.md               # テンプレート使用ガイド
└── skill-template/
    ├── SKILL.md            # スキル定義文書テンプレート
    └── MANIFEST.json       # メタデータテンプレート
```

### 9.2 新スキル作成プロトコル

**MUST**: 新スキル作成時は必ずテンプレートを使用

```bash
# 1. テンプレートコピー
cp -r .claude/skills/_templates/skill-template .claude/skills/{{new-skill-name}}

# 2. プレースホルダー置換
# すべての{{PLACEHOLDER}}を実際の値に置換

# 3. チェックリスト検証
- [ ] SKILL.md生成済み
- [ ] MANIFEST.json生成済み
- [ ] tierが1, 2, 3のいずれか
- [ ] calls ↔ called_by双方向参照一致
- [ ] trigger_keywordsが2個以上
```

### 9.3 テンプレート効果

| 項目             |   Before   |        After         |
| ---------------- | :--------: | :------------------: |
| MANIFEST欠落発生 | 頻発 (62%) |     根本的に防止     |
| スキーマ不一致   |    頻発    |        標準化        |
| 依存性欠落       |    発生    | チェックリストで防止 |

---

## 変更履歴

| 日付       | 変更内容                                                                                                                                                                                                                   |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-02-02 | v2.3 - **願望文書化の根源除去**: Evidence Policyからcache_location削除、"AI行動指針で処理"原則明示。スキルMANIFESTで参照していた未実装フィールドの原因除去                                                                 |
| 2026-02-01 | v2.2 - **MANIFEST.json実際アップグレード**: skill-health-check v2.0 ESP適用 (文書-実態不一致解消), security-scan v2.0 ESP適用 (セキュリティスキル強制化完了)                                                               |
| 2026-02-01 | v2.1 - **ESP Enforcement Layer 3-Tier実装**: Runtime(esp_execution_log), Post-hoc(skill-health-check v2.0), Audit(GOVERNANCEメトリクス). feature-pilot v9.0 ESP適用, context_template.json esp_execution_logセクション追加 |
| 2026-02-01 | v2.0 - **Enforced Skill Pattern (ESP) v2.0導入**, schema_version 2定義, turbo-mode/persistent-mode/flutter-qa v3.0アップグレード (ESP適用), スキルテンプレートv2追加 (`_templates/skill-template-v2/`)                     |
| 2026-02-01 | v1.4 - P1スキルMANIFEST完了 (flutter-qa, security-scan, persistent-mode), skill-health-check新規作成, スキルテンプレート標準化 (`_templates/`), MANIFEST保有率51%達成                                                      |
| 2026-02-01 | v1.3 - Deprecatedスキル(feature-data-wiring, feature-navigation-wiring) MANIFEST.json生成, ヘルス状態改善 (38%→43%), Medium Issue解決                                                                                      |
| 2026-02-01 | v1.2 - 効果測定フレームワーク大幅拡張 (KPI定義, ログフォーマット, トークンコストモデル, 四半期レポートテンプレート)                                                                                                        |
| 2026-02-01 | v1.1 - スキルインベントリヘルスチェック完了, 全体37個スキル分類, MANIFESTギャップ分析, turbo-mode MANIFEST生成                                                                                                             |
| 2026-02-01 | v1.0 - 初期ガバナンスフレームワーク作成                                                                                                                                                                                    |
