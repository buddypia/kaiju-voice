# Glossary セクション構造および分類基準

この文書は `docs/glossary.md` のセクション構造と各セクションにどの用語を追加すべきかを案内する。

## セクション構造

```
1. ビジネスドメイン用語
   1.1 ユーザー関連
   1.2 コンテンツ階層
   1.3 ゲーミフィケーション
   1.4 L1(母語) 特化
   1.5 シナリオおよびロールプレイ
   1.6 収益化

2. 学習システム用語
   2.1 アクティビティタイプ
   2.2 復習システム
   2.3 進度管理
   2.4 レベルテストおよびアダプティブ評価
   2.5 オンボーディング
   2.6 レッスンセッション
   2.7 誤答ノート (Wrong Note)
   2.8 SRS 詳細パラメータ

3. 技術用語
   3.1 アーキテクチャ
      3.1.1 Edge Functions
      3.1.2 Bridge Grammar アーキテクチャ
      3.1.3 Nunchi AI Coach アーキテクチャ
   3.2 状態管理
   3.3 データ層

4. データベース用語
   4.1 テーブル定義
   4.2 カラム命名

5. UI/UX 用語
   5.1 UI 構造
   5.2 UI パターン
   5.3 主要ページ

6. AI・音声処理用語
   6.1 AI チューター
   6.2 音声処理
   6.3 発音評価
   6.4 AI 生成および分析
   6.5 Nunchi AI Coach
   6.6 Bridge Grammar Engine
   6.7 発音フィードバック詳細
   6.8 Director 状態マシン
   6.9 チューターオンボーディングプロフィール

7. ゲーミフィケーション詳細
   7.1 ストリークシステム
   7.2 デイリーヒーロー

8. K-コンテンツ/K-シナリオ

9. プッシュ通知

10. システム運用用語

11. 略語・頭字語集

12. 禁止用語
```

## セクション別分類基準

### 1. ビジネスドメイン用語

- **1.1 ユーザー関連**: User, Profile, Guest, Premium 等ユーザーアカウント/設定
- **1.2 コンテンツ階層**: Course, Unit, Lesson, Activity, Step 等学習コンテンツ構造
- **1.3 ゲーミフィケーション**: XP, Streak, Badge, Combo 等基本ゲーミフィケーション概念
- **1.4 L1 特化**: L1 Interference, Negative Transfer 等母語関連
- **1.5 シナリオ/ロールプレイ**: Scenario Preset, Success Criteria 等シナリオ概念
- **1.6 収益化**: Monetization Tier, AI Pro, Free Tier Limit 等

### 2. 学習システム用語

- **2.1 アクティビティタイプ**: Dialogue Practice, Fill in the Blank 等学習活動タイプ
- **2.2 復習システム**: SRS, Review Queue, Ease Factor 等基本復習概念
- **2.3 進度管理**: Progress State, Completion Rate, Score 等
- **2.4 レベルテスト**: IRT, Ability Estimation, Adaptive Testing 等
- **2.5 オンボーディング**: Onboarding Flow, Interest Selection 等
- **2.6 レッスンセッション**: Lesson Phase (Introduction/Dialogue/Vocabulary/Quiz/Result)
- **2.7 誤答ノート**: Wrong Note, Confusion Analysis, Memory Tip 等
- **2.8 SRS 詳細**: Learning Stage, Virtual Day, Fuzzing Factor 等

### 3. 技術用語

- **3.1 アーキテクチャ**: Feature-First + Simplified Clean Architecture, React Hooks, Zod, Repository Pattern
- **3.1.1 Edge Functions**: cloud-tts, ai-tutor-chat 等 Supabase 関数
- **3.1.2 Bridge Grammar**: BridgeStrategy, JapaneseBridgeStrategy 等
- **3.1.3 Nunchi AI Coach**: Director-Actor-Coach, Three-Layer Feedback
- **3.2 状態管理**: ViewModel, State, Notifier, AsyncNotifier 等
- **3.3 データ層**: DataSource, Repository, DTO, Entity, Mapper

### 4. データベース用語

- **4.1 テーブル定義**: 実際のDBテーブル名と用途 (カテゴリ別分類)
- **4.2 カラム命名**: id, _*id, created_at, is*_ 等命名パターン

### 5. UI/UX 用語

- **5.1 UI 構造**: Page, Fragment, Component, Component
- **5.2 UI パターン**: Modal, Bottom Sheet, Snackbar, Skeleton 等
- **5.3 主要ページ**: AI Tutor Page, Role Play Page 等実際のページ

### 6. AI・音声処理用語

- **6.1 AI チューター**: AI Tutor, Conversation, Message, Correction
- **6.2 音声処理**: TTS, STT, Audio Playback, Recording
- **6.3 発音評価**: Pronunciation Assessment, Grade, Score
- **6.4 AI 生成/分析**: Voice Search, Learning Insight, Roleplay Analytics
- **6.5 Nunchi**: Pragmatics, Cushion Word, Honorific Level 等 Nunchi 関連
- **6.6 Bridge Grammar**: L1 Interference Pattern, Particle Bridge 等
- **6.7 発音フィードバック詳細**: Syllable Score, Phoneme Analysis, STT Confidence
- **6.8 Director 状態マシン**: Director Mode (7種), Stuck Type 等
- **6.9 チューターオンボーディング**: Speech Style, Focus Area, Weakness Type 等

### 7. ゲーミフィケーション詳細

- **7.1 ストリーク**: Streak Status, Freeze, Recovery, Milestone 等詳細実装
- **7.2 デイリーヒーロー**: Daily Hero, Hero Content, Mission Completion 等

### 8. K-コンテンツ/K-シナリオ

- K-Scenario, Scene Type, Ending Type, Culture Note 等 K-コンテンツ関連

### 9. プッシュ通知

- Notification Type, FCM Token, DND, Streak Reminder 等

### 10. システム運用用語

- RLS, MFA, OAuth, CDN, Edge Function, Rate Limiting 等インフラ関連

### 11. 略語・頭字語集

- API, SRS, TTS, STT, IRT, TOPIK 等全略語

### 12. 禁止用語

- 「学生」、「失敗」、「暗記」等 UX 観点で避けるべき用語

## テーブル形式

### 4列形式 (ビジネス/学習システム)

```markdown
| 用語     | 韓国語   | 説明         | 実装例                       |
| -------- | -------- | ------------ | ---------------------------- |
| **Term** | 韓国語名 | 説明テキスト | `file.ts` またはテーブル名 |
```

### 3列形式 (技術/AI/UI)

```markdown
| 用語     | 説明         | 実装        |
| -------- | ------------ | ----------- |
| **Term** | 説明テキスト | `file.ts` |
```

### 略語形式

```markdown
| 略語    | 正式名称  | 韓国語   | 用途     |
| ------- | --------- | -------- | -------- |
| **ABC** | Full Name | 韓国語名 | 使用箇所 |
```

## 改訂履歴更新

用語追加後は必ず改訂履歴セクションを更新する:

```markdown
| 1.X | 202X-XX-XX | 変更内容要約 | Claude Code |
```

バージョン番号はマイナーバージョン増加 (1.3 → 1.4)。
