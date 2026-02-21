# Feature-Research マッピングガイド

> 各 Feature と関連するリサーチファイルおよび核心インサイト抽出ガイド

---

## マッピングテーブル

### P0 (MVP 必須) Features

| ID  | Feature               | 関連リサーチ                                                              | 核心インサイトキーワード        |
| :-: | --------------------- | ------------------------------------------------------------------------- | ------------------------------- |
| 001 | Bridge Grammar Engine | `japanese-korean-l1-interference-*.md`, `korean-honorific-*.md`           | L1 干渉パターン、文法マッピング |
| 002 | Nunchi AI Coach       | `ai-tutor-*.md`, `llm-korean-*.md`                                        | フィードバック品質、語用論      |
| 003 | AI Content Pipeline   | `ai-content-*.md`, `ai-app-launch-cost-*.md`                              | コンテンツ自動化、コスト最適化  |
| 004 | Onboarding Level Test | `irt-adaptive-testing-*.md`, `mobile-app-onboarding-*.md`                 | IRT、オンボーディングUX         |
| 005 | Core Learning Session | `language-learning-activities-*.md`                                       | 学習効果、アクティビティ        |
| 006 | SRS Review System     | `sm2-srs-*.md`, `user-retention-*.md`                                     | SM-2 アルゴリズム、復習効果     |
| 007 | Visual Pronunciation  | `korean-speech-recognition-*.md`, `l1-japanese-korean-pronunciation-*.md` | 発音ASR、L1特化                 |
| 008 | Monetization          | `monetization-*.md`, `pricing-*.md`, `arpu-*.md`, `subscription-*.md`     | 収益モデル、価格戦略            |

### P0.5 (MVP 推奨) Features

| ID  | Feature      | 関連リサーチ                                         | 核心インサイトキーワード     |
| :-: | ------------ | ---------------------------------------------------- | ---------------------------- |
| 015 | Gamification | `gamification-retention-*.md`, `user-retention-*.md` | XP、ストリーク、リテンション |

### P1 (MVP 直後) Features

| ID  | Feature            | 関連リサーチ                                                                          | 核心インサイトキーワード |
| :-: | ------------------ | ------------------------------------------------------------------------------------- | ------------------------ |
| 010 | Push Notification  | `push-notification-*.md`, `retention-*.md`                                            | プッシュ最適化、DAU      |
| 017 | Settings & Account | `ai-language-app-legal-*.md`, `mvp-legal-*.md`                                        | GDPR、アプリストア規定   |
| 019 | Retention Strategy | `retention-*.md`, `language-app-user-retention-*.md`, `language-app-user-cohort-*.md` | D1/D7/D30 リテンション   |
| 022 | Home Screen        | `user-retention-*.md`, `mobile-app-onboarding-*.md`                                   | CTA階層、ホームUX        |

### P2 (Phase 2) Features

| ID  | Feature              | 関連リサーチ                                            | 核心インサイトキーワード       |
| :-: | -------------------- | ------------------------------------------------------- | ------------------------------ |
| 009 | Metacognitive Report | `metacognitive-learning-*.md`                           | 学習メタ認知                   |
| 011 | K-Content Scenario   | `k-content-*.md`                                        | K-ドラマ、著作権               |
| 012 | Proficiency Test     | `topik-*.md`, `proficiency-*.md`                        | TOPIK、熟練度テスト            |
| 014 | B2B Team Package     | `b2b-*.md`, `foreign_workers_*.md`                      | 企業市場、EPS-TOPIK            |
| 016 | Offline Mode         | -                                                       | (技術的要件)                   |
| 018 | User Acquisition     | `low-cost-marketing-*.md`, `japan-solo-developer-*.md`  | UA戦略、低コストマーケティング |
| 020 | AI Cost Monitoring   | `ai-app-launch-cost-*.md`, `solo-developer-ai-app-*.md` | AIコスト最適化                 |
| 021 | Copyright Policy     | `k-content-copyright-*.md`, `legal-*.md`                | 著作権、法的リスク             |

---

## リサーチカテゴリ別マッピング

### 収益化 (Revenue)

```
関連リサーチ:
- monetization-strategies-2025-2026-research.md
- monetization-strategy-analysis-2025.md
- subscription-pricing-optimization-strategy-2026.md
- arpu-benchmark-verification-2025.md
- market-size-arpu-verification-2025.md
- japan-pricing-trial-optimization-2025.md
- cac-ltv-breakeven-analysis-2025.md

適用 Feature: 008, 018, 019
核心質問: "どのように収益を最大化するか？"
```

### リテンション (Retention)

```
関連リサーチ:
- gamification-retention-research-2025.md
- user-retention-features-analysis-2025.md
- language-app-user-retention-deep-strategy-2026.md
- language-app-user-cohort-churn-prediction-guide-2026.md
- push-notification-optimization-strategies-2026.md
- intermediate-plateau-phenomenon-strategies-2025.md
- intermediate-plateau-content-roi-analysis-2026.md

適用 Feature: 015, 010, 019, 005, 006
核心質問: "ユーザーはなぜ離れ、どのように引き留めるか？"
```

### 市場分析 (Market)

```
関連リサーチ:
- competitor-*.md (6個ファイル)
- korean-learning-app-market-*.md
- japan-market-*.md (8個ファイル)
- global-*.md (6個ファイル)
- market-size-*.md

適用 Feature: すべての Feature
核心質問: "競合社対比我々のポジションは？"
```

### AI/技術 (Technology)

```
関連リサーチ:
- ai-tutor-*.md (6個ファイル)
- llm-korean-*.md (3個ファイル)
- gemini-*.md (2個ファイル)
- ai-response-latency-*.md
- ai-content-quality-*.md

適用 Feature: 002, 003, 024
核心質問: "AIコスト対比品質をどのように最適化するか？"
```

### ユーザー研究 (User Research)

```
関連リサーチ:
- learner-pain-points.md ⭐ 核心
- mobile-app-onboarding-ux-*.md
- japan-k-fandom-korean-learning-*.md
- korea_international_students_*.md
- foreign_workers_in_korea_*.md

適用 Feature: すべての Feature
核心質問: "ユーザーの本当の問題は何か？"
```

---

## インサイト抽出パターン

### 収益関連インサイト抽出

```markdown
検索パターン:

- "ARPU", "LTV", "CAC"
- "サブスクリプション", "subscription", "pricing"
- "conversion", "転換率"
- "$", "円", "ウォン"

例示インサイト:

> "[monetization-strategies-2025-2026-research.md]
> 日本言語学習アプリ平均 ARPU: $8-12/月
> Freemium to Premium 転換率: 2-5%
> → 008-Monetization の価格設定根拠"
```

### リテンション関連インサイト抽出

```markdown
検索パターン:

- "D1", "D7", "D30" リテンション
- "churn", "離脱"
- "streak", "ストリーク"
- "notification", "通知"

例示インサイト:

> "[gamification-retention-research-2025.md]
> ストリークシステム導入時 D7 リテンション +15%
> XP システムのみでは効果限定的
> → 015-Gamification のストリーク優先実装根拠"
```

### 差別化関連インサイト抽出

```markdown
検索パターン:

- "競合社", "competitor"
- "差別化", "differentiation"
- "ない", "不在", "gap"
- "unique", "独占"

例示インサイト:

> "[competitor-app-feature-analysis-2025.md]
> 競合アプリ大部分が L1 特化フィードバック未提供
> 発音可視化は1つのアプリのみ提供
> → 007-Pronunciation の差別化価値"
```

---

## 依存性マッピング

### 技術的依存性

```
003 AI Content Pipeline
├── 005 Core Learning Session (コンテンツ消費)
├── 006 SRS Review System (復習コンテンツ)
├── 011 K-Content Scenario (シナリオコンテンツ)
└── 021 Copyright Policy (コンテンツポリシー)

005 Core Learning Session
├── 015 Gamification (学習 → XP)
└── 016 Offline Mode (オフライン学習)

008 Monetization
├── 016 Offline Mode (プレミアム機能)
├── 018 User Acquisition (収益 → マーケティング)
└── 020 AI Cost Monitoring (コスト管理)
```

### ビジネス依存性

```
リテンション依存チェーン:
015 Gamification → 019 Retention Strategy → 010 Push Notification

収益依存チェーン:
008 Monetization → 020 AI Cost Monitoring → 018 User Acquisition
```

---

## 点数計算例示

### Feature: 008-Monetization

```
ビジネスインパクト: 40/40
- 収益貢献度: 15/15 (直接収益)
- リテンション貢献度: 15/15 (プレミアム機能 → ロイヤリティ)
- 市場差別化: 10/10 (多様な価格戦略)

技術的実現性: 28/30
- 現在実装率: 7/10 (45%)
- 依存性解消: 10/10 (独立的)
- 技術複雑度: 7/10 (普通)

ユーザー価値: 20/30
- ユーザーニーズ: 10/15 (一部ユーザーのみ関心)
- 市場適合性: 7/10 (Japan-First 推奨)
- 期待充足: 3/5 (競合アプリ保有)

総点: 88/100 → Tier 1
```

### Feature: 015-Gamification

```
ビジネスインパクト: 32/40
- 収益貢献度: 10/15 (間接収益)
- リテンション貢献度: 15/15 (D7 リテンション核心)
- 市場差別化: 7/10 (競合社同等)

技術的実現性: 22/30
- 現在実装率: 2/10 (0%)
- 依存性解消: 10/10 (005 進行中)
- 技術複雑度: 10/10 (単純)

ユーザー価値: 28/30
- ユーザーニーズ: 15/15 (Top 5 Pain Point)
- 市場適合性: 10/10 (Japan-First 必須)
- 期待充足: 3/5 (競合アプリ保有)

総点: 82/100 → Tier 1
```

---

## 変更履歴

| 日付       | 内容                       |
| ---------- | -------------------------- |
| 2026-01-18 | 初期マッピングテーブル作成 |
