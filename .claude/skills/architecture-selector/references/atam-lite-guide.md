# ATAM Lite 評価ガイド

## 概要

ATAM（Architecture Tradeoff Analysis Method）は、カーネギーメロン大学ソフトウェア工学研究所（SEI/CMU）が開発したアーキテクチャ評価手法です。複数の品質属性間のトレードオフを体系的に分析し、アーキテクチャ決定のリスクを早期に特定します。

> **参考**: Kazman, R., Klein, M., & Clements, P. "ATAM: Method for Architecture Evaluation" (SEI/CMU, 2000)

---

## ATAM Lite とは

ATAM Lite は、フル ATAM プロセスを Hackathon Project プロジェクトの規模に合わせて簡略化したバージョンです。

### フル ATAM との差分

| 項目                 | フル ATAM                                          | ATAM Lite                                          |
| -------------------- | -------------------------------------------------- | -------------------------------------------------- |
| **参加者**           | アーキテクト、開発者、ステークホルダー、評価チーム | AI + 開発者                                        |
| **所要時間**         | 2-3日のワークショップ                              | 1回のスキル実行                                    |
| **品質属性シナリオ** | 完全な 6部構成シナリオ                             | 簡略化シナリオ（刺激→応答→測定）                   |
| **Utility Tree**     | 完全な階層構造                                     | Weight（H/M/L）による優先順位付け                  |
| **分析深度**         | 全アーキテクチャアプローチの詳細分析               | 主要な Options の比較マトリクス                    |
| **成果物**           | 詳細な評価レポート                                 | ADR 内の評価セクション                             |
| **リスク分類**       | Risk、Non-risk、Sensitivity、Tradeoff の4分類      | Sensitivity Points + Tradeoff Points + Risk Themes |

---

## Quality Attribute Scenarios の書き方

### 簡略化シナリオ形式

フル ATAM では6要素（Source、Stimulus、Environment、Artifact、Response、Response Measure）を記述しますが、ATAM Lite では3要素に簡略化します:

```
[刺激(Stimulus)] → [応答(Response)] → [測定基準(Measure)]
```

### 例

| 品質属性        | 刺激                             | 応答                     | 測定基準             |
| --------------- | -------------------------------- | ------------------------ | -------------------- |
| Performance     | 100件の単語リストを要求          | 単語リストを表示         | 200ms 以内           |
| Security        | 未認証ユーザーがデータにアクセス | アクセスを拒否           | 100% ブロック        |
| Reliability     | Edge Function がタイムアウト     | フォールバック処理を実行 | データ損失なし       |
| Maintainability | 新しい学習モードを追加           | 既存コードの変更最小限   | 変更ファイル 5個以内 |

### Hackathon Project プロジェクトでの典型的なシナリオ

1. **オフライン学習**: ネットワーク切断時 → ローカルキャッシュから表示 → 前回同期データの 100% 表示
2. **AI コンテンツ生成**: ユーザーがレッスンを開始 → Edge Function で AI コンテンツ生成 → 3秒以内にコンテンツ表示
3. **データ保護**: RLS ポリシー適用 → 他ユーザーのデータへのアクセスを遮断 → 0件のデータ漏洩

---

## Sensitivity Points の識別方法

### 定義

**Sensitivity Point（感度ポイント）**: アーキテクチャの特定のプロパティが変更された場合、品質属性に大きな影響を与えるポイント。

### 識別手順

1. **各 Option の構成要素を列挙する**
   - データ層の構成（ローカルDB、API、キャッシュ等）
   - 通信パターン（同期、非同期、リアルタイム等）
   - 状態管理の方式

2. **各構成要素について問う**:
   - "この要素を変更したら、品質属性にどの程度影響するか？"
   - 影響が大きい要素 = Sensitivity Point

3. **文書化する**:

   ```markdown
   ### Sensitivity Points

   - **SP-1**: キャッシュ有効期限の設定
     - 短すぎる → Performance 低下（頻繁なAPI呼び出し）
     - 長すぎる → データ鮮度の低下
   - **SP-2**: Edge Function のタイムアウト設定
     - 短すぎる → Reliability 低下（AI生成の中断）
     - 長すぎる → UX 低下（待ち時間増加）
   ```

### Hackathon Project での典型的な Sensitivity Points

| SP                           | 構成要素                            | 影響する品質属性               |
| ---------------------------- | ----------------------------------- | ------------------------------ |
| キャッシュ戦略               | ローカルDB の同期頻度               | Performance vs データ鮮度      |
| AI 応答フォーマット          | Edge Function の JSON Schema 厳密度 | Reliability vs 柔軟性          |
| Riverpod Provider のスコープ | グローバル vs Feature スコープ      | Maintainability vs Performance |
| RLS ポリシーの粒度           | 行レベル vs テーブルレベル          | Security vs Performance        |

---

## Tradeoff Points の識別方法

### 定義

**Tradeoff Point（トレードオフポイント）**: ある品質属性を改善すると、別の品質属性が低下するポイント。複数の Sensitivity Point に影響する構成要素。

### 識別手順

1. **Sensitivity Points の交差を探す**:
   - 同じ構成要素が複数の品質属性に影響する箇所

2. **対立する品質属性のペアを特定する**:

   ```
   Performance ↔ Security    （暗号化によるオーバーヘッド）
   Flexibility ↔ Simplicity   （拡張性 vs 実装コスト）
   Performance ↔ Reliability  （キャッシュ vs データ整合性）
   ```

3. **文書化する**:

   ```markdown
   ### Tradeoff Points

   - **TP-1**: オフラインキャッシュの範囲
     - Performance (+): ローカルデータで高速表示
     - Maintainability (-): 同期ロジックの複雑化
     - Reliability (?): コンフリクト解決の戦略が必要
   ```

### Hackathon Project での典型的な Tradeoff Points

| TP                             | トレードオフ                 | 説明                                             |
| ------------------------------ | ---------------------------- | ------------------------------------------------ |
| AI コンテンツ品質 vs 応答速度  | Quality ↔ Performance        | 高品質な AI 生成にはより多くの処理時間が必要     |
| データ暗号化 vs パフォーマンス | Security ↔ Performance       | ローカルデータの暗号化はアクセス速度を低下させる |
| 機能分離 vs 再利用性           | Maintainability ↔ Efficiency | Feature-First 分離は再利用コードの重複を生む     |
| オフライン対応 vs 実装コスト   | Reliability ↔ Cost           | 完全なオフライン対応は実装工数が大きい           |

---

## 評価マトリクスの作成手順

### ステップ1: 品質属性の選定

[quality-attribute-catalog.md](quality-attribute-catalog.md) から、対象機能に関連する品質属性を選定する（通常 4-8 個）。

### ステップ2: Weight（重要度）の付与

各品質属性に重要度を付与する:

| Weight         | 意味             | 判定基準                                           |
| -------------- | ---------------- | -------------------------------------------------- |
| **H (High)**   | 必須要件         | この品質を満たさないと機能が成立しない             |
| **M (Medium)** | 重要だが妥協可能 | ユーザー体験に影響するが、最低限の水準でも運用可能 |
| **L (Low)**    | あれば良い       | 長期的には重要だが、MVP では低優先                 |

### ステップ3: 各 Option の評価

各 Option が品質属性をどの程度満たすかを評価する:

| 記号  | 評価       | 説明                               |
| ----- | ---------- | ---------------------------------- |
| `+++` | 非常に良好 | 品質属性を完全に満たし、余裕がある |
| `++`  | 良好       | 品質属性を十分に満たす             |
| `+`   | 最低限     | 品質属性の最低要件を満たす         |
| `-`   | 不十分     | 品質属性を満たさない。リスクあり   |

### ステップ4: マトリクス完成

```markdown
| Quality Attribute | Weight | Option A | Option B | Option C |
| ----------------- | ------ | -------- | -------- | -------- |
| Performance       | H      | +++      | ++       | +        |
| Security          | H      | ++       | +++      | +        |
| Maintainability   | M      | +++      | +        | ++       |
| Usability         | M      | ++       | ++       | +++      |
| Reliability       | M      | ++       | +++      | +        |
| Portability       | L      | ++       | ++       | ++       |
```

### ステップ5: 総合評価

1. **Weight が H の属性**: `-` 評価の Option は原則として推奨しない
2. **Weight が M の属性**: `+` 以上であれば許容
3. **Weight が L の属性**: 参考情報として扱う
4. **Sensitivity Points と Tradeoff Points** を考慮して最終判断

---

## Risk Themes の導出

### 定義

**Risk Theme（リスクテーマ）**: 複数の Sensitivity Points や Tradeoff Points から浮かび上がるリスクのパターン。個別のリスクを集約した上位概念。

### 導出手順

1. Sensitivity Points と Tradeoff Points を一覧化する
2. 共通するパターンやカテゴリを探す
3. 1-3個のリスクテーマにまとめる

### 文書化例

```markdown
### Risk Themes

**RT-1: オフライン/オンライン境界の複雑性**
関連: SP-1 (キャッシュ有効期限), TP-1 (オフラインキャッシュ範囲)
リスク: 同期ロジックの複雑化により、バグの温床となる可能性。
軽減策: 同期戦略を最小限に保ち、コンフリクト解決は "last-write-wins" を採用。

**RT-2: AI コンテンツ生成の信頼性**
関連: SP-2 (Edge Function タイムアウト), TP-2 (品質 vs 速度)
リスク: AI サービス障害時のフォールバック戦略が不十分だと UX が著しく低下。
軽減策: 事前生成コンテンツのプールを用意し、リアルタイム生成失敗時に利用。
```
