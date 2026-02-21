# CLAUDE.md

このプロジェクトはGemini 3 ハッカソン 東京のプロジェクトです。
このファイルは、AIコーディングアシスタントのためのプロジェクトガイドラインです。グローバル前提およびルールの**唯一の真実のソース**です。

---

# ハッカソン分析サマリー
| 分析項目 | 重要ポイント |
| --- | --- |
| **テーマ** | 「AIを活用したゲーム」および「ゲーム開発ツールの強化」が中心。Supercellの協賛もあり、ゲーム分野への強いフォーカスが伺える。 |
| **主要技術** | `Nano Banana`（画像生成）、`Live API`（リアルタイム音声・映像対話）、`エージェント機能`の活用が明確に推奨されている。 |
| **禁止事項** | メンタルヘルス、基本的なRAG、Streamlitアプリなど、特定の分野・技術が明確に禁止されているため、これらを回避する必要がある。 |
| **審査基準** | 「デモ（50%）」と「インパクト（25%）」の比重が極めて高い。アイデアを実際に動作する形で示し、その将来性や有用性を伝えることが最重要。 |
| **過去の受賞傾向** | 1) 開発者向けツール、2) リアルタイム・インタラクティブ性、3) マルチモーダルなエージェント機能、の3つの方向性が高く評価される傾向にある。 |

## プロジェクト識別情報

| 項目                 | 値                                              |
| -------------------- | ----------------------------------------------- |
| **プロジェクト名**   | [Project Name]                                  |
| **プラットフォーム** | Web                                             |
| **フレームワーク**   | Next.js 16 / React 19                           |
| **言語**             | TypeScript                                      |
| **スタイリング**     | Tailwind CSS 4                                  |
| **アーキテクチャ**   | Feature-First + Simplified Clean Architecture   |
| **ランタイム**       | Node.js LTS                                     |
| **テーマ**           | ダークモード専用                                |
| **AIプロバイダー**   | Gemini専用 (`@google/genai` + `@ai-sdk/google`) |
| **UI言語**           | 日本語専用                                      |

## **コア特徴**: [プロジェクトのコア特徴をここに記載]

## 準拠事項 (Rules to Follow)

### 必須ルール (MUST)

1. **Feature-First構造**: 機能単位でディレクトリを分割し、関心の分離を徹底。
2. **TypeScript厳格モード**: `strict: true`を有効化し、`any`型の使用を最小限に。
3. **不変データ**: 状態管理ではイミュータブルな更新パターンを使用（スプレッド構文、`Readonly<T>`等）。
4. **日本語コメント**: 公開関数/コンポーネントに日本語のJSDocコメント(`/** */`)必須。
5. **エラーハンドリング**: 非同期処理は`try-catch`で適切にエラーを捕捉し、ロガーで記録。
6. **テスト必須**: 新機能/バグ修正時にはテスト作成（Jest / Vitest）。
7. **Fail-Fast原則**: 不正な入力/状態は即座に失敗処理、サイレントフォールバック禁止。
8. **型安全性**: 型アサーション(`as`)の濫用禁止、型ガードやZod等のバリデーションを活用。
9. **Gemini Structured Output**: JSON応答には`responseJsonSchema`（標準JSON Schema）を使用。Zodスキーマを SSOT とし `toJSONSchema()` で導出。`responseSchema`（Gemini独自形式）は使用禁止。

### 禁止事項 (MUST NOT)

| パターン                           | 代替                                        |
| ---------------------------------- | ------------------------------------------- |
| `any`型の多用                      | 適切な型定義、`unknown` + 型ガード          |
| 可変グローバル状態                 | 状態管理ライブラリを使用                    |
| ハードコーディング文字列（UI表示） | `MESSAGES`定数（`messages.ts`）を使用       |
| `console.log`（本番コード）        | 専用ロガーを使用                            |
| エラー無視 (`catch (e) {}`)        | 適切なエラーハンドリング + ロギング         |
| `innerHTML`直接操作                | Reactの安全なレンダリング                   |
| `responseSchema`（Gemini独自形式） | `responseJsonSchema` + Zod `toJSONSchema()` |

### 品質チェック

```bash
npm run lint             # 静的分析 + セキュリティ (エラー 0 必須)
npm test                 # テスト実行
npm run test:coverage    # カバレッジ閾値検証
npm run build            # ビルド確認
```

### Executable SSOT (コード生成)

- `docs/ui-flow/ui-flow.json` → コード + 図表 を自動生成
- `make codegen` で再生成、`make codegen.check` で鮮度検証（CI統合）
- `*.generated.ts` ファイルは手動編集禁止
- ui-flow.json 変更時は必ず `make codegen` を実行

### Evidence Freshness (検証キャッシュルール)

> **目標**: 同一セッション内の繰り返し検証を最小化して時間/トークン節約

| 検証タイプ      | 有効時間 | 無効化条件                       |
| --------------- | -------- | -------------------------------- |
| `lint`          | 30分     | `src/**/*`変更時                 |
| `test`          | 30分     | `test/**/*`, `src/**/*`変更時    |
| `security-scan` | 1時間    | `.env*`変更時                    |
| `build`         | 1時間    | `src/**/*`, `package.json`変更時 |

**動作ルール**:

- 前回の検証後有効時間内に同一検証要求 → **キャッシュ使用**（再実行省略）
- 無効化条件満たす場合 → **強制再実行**
- 明示的な`--force`要求の場合 → **強制再実行**

---

## エージェント運用ガイド

### 動作原則

- **日本語応答**: すべての対話と説明は日本語で作成（コード/技術用語は原文保持）。
- **正確性**: 要求範囲のみ実行、範囲逸脱禁止。
- **既存優先**: 新規ファイル最小化、既存ファイル編集優先。
- **文書制限**: 明示的な要求無く新規\*.md/README作成禁止。
- **テスト同時生成**: 新規機能/修正にはテスト必須。

### 問題解決哲学

> **核心**: 時間がかかっても**根本的解決策**を見つける必要があり、**一時的な手段（Workaround）**は禁止。

**批判的思考5段階**:

1. なぜこの問題が発生したのか？（根本原因把握）
2. この解決策は問題を完全に解決するのか？
3. 業界標準の方法は何か？
4. 他の代替案はないか？（最低2つ検討）
5. 長期的影響は？（技術的負債考慮）

**禁止行動**: `// TODO: 後で`残すこと、ハードコーディングで迅速な解決、COPY-Pasteコード。

### 思考の5段階プロセス

> 答えを出す前に必ず以下のステップを順番に実行してください。

| ステップ    | 説明                                   |
| ----------- | -------------------------------------- |
| **1. 分解** | 課題を要素別に分ける                   |
| **2. 解決** | 各要素の答えを導き出す                 |
| **3. 検証** | 論理の矛盾や誤りがないか厳密にチェック |
| **4. 統合** | 全体を一つの回答に整理                 |
| **5. 反省** | 回答の抜け道や他の視点がないか検討     |

### 実行フロー

1. **要件分析** → 既存コード/パターン確認。
2. **実装** → 既存ファイル優先変更、パターン遵守。
3. **テスト** → 正常/異常ケース単体テスト追加。
4. **品質** → `npm run lint`通過確認。

### モデルルーティングガイド

> **目標**: 作業の複雑さに基づくモデル選択によりトークンコストを30-50%削減。

**原則**: Haiku（探索/検索）→ Sonnet（標準実装）→ Opus（アーキテクチャ/セキュリティ）。

| 複雑さ                | モデル | 例                                       |
| --------------------- | ------ | ---------------------------------------- |
| 低 (ファイル5個以下)  | Haiku  | 探索、単純修正                           |
| 標準 (ファイル6-20個) | Sonnet | 機能実装、文書作成                       |
| 高 (ファイル20個以上) | Opus   | アーキテクチャ設計、セキュリティレビュー |

**自動フォールバック**: 3回連続エラー時自動昇格（Haiku → Sonnet → Opus）。
**Opus失敗3回**: 根本問題判断 → 即時中断 + エスカレーション。

### AIが参照する文書優先順位

| 優先順位 | 文書              | 用途                                       |
| :------: | ----------------- | ------------------------------------------ |
|    1     | **SPEC-XXX.md**   | テクニカルコントラクト - 実装+テストの核心 |
|    2     | **screens/\*.md** | UIレイアウト + Element ID                  |
|    3     | **PRD-XXX.md**    | ビジネス目標、意思決定基準                 |

### 総合コストKPI

| 指標             |      目標      | 意味         |
| ---------------- | :------------: | ------------ |
| **総合コスト**   | Tier × 1.5以内 | コアKPI      |
| AI追加質問       |     ≤ 3回      | 参考指標     |
| 初回ビルド成功率 |     ≥ 80%      | 仕様の正確性 |
| 手動修正コミット |     ≤ 3回      | 実装品質     |

---

## アーキテクチャ概要

```
pages(routes)/ ↔ features/ ↔ shared/
(UI + Hooks)    (ドメイン)   (共通ユーティリティ)
       ↓            ↓            ↓
      [状態管理を通じた反応型結合]
```

- **ページ/ルート**: Next.js App RouterまたはPages Router - ルーティング + レイアウト。
- **フィーチャー**: 機能単位のドメインロジック + UI コンポーネント + 状態管理。
- **共有**: 共通コンポーネント、ユーティリティ、型定義。

### Feature-First依存関係ルール

```
許可:
  feature/ui → feature/hooks → feature/api
  feature → shared
  feature → feature (バレルファイル(index.ts)を通じてのみ)

禁止:
  shared → feature
  feature 内部 直接 import (バレルファイル回避)
  循環依存 (A → B → A)
```

---

## プロジェクト構造

```
src/
├── app/              # Next.js App Router (ページ/レイアウト)
├── features/         # 機能単位モジュール
│   └── [feature]/
│       ├── components/   # 機能固有UIコンポーネント
│       ├── hooks/        # 機能固有カスタムフック
│       ├── api/          # API呼び出し/データフェッチ
│       ├── types/        # 機能固有型定義
│       └── index.ts      # バレルファイル (公開API)
├── shared/
│   ├── components/   # 再利用UIコンポーネント
│   ├── hooks/        # 共通カスタムフック
│   ├── lib/          # ユーティリティ関数
│   └── types/        # 共通型定義
├── styles/           # グローバルスタイル/テーマ
└── config/           # アプリ設定

tests/                # テスト (ソースと同じ構造)
public/               # 静的アセット
```

---

## デザインシステム

> **スタイル**: Terminal Noir + Contextual Accent — 統一基盤テーマ + アクセントカラー可変 + マイクロインタラクション
>
> **設計思想**: 背景・パネル・タイポグラフィは統一し、**アクセントカラーのみ**で文脈を伝達する。業界標準準拠。

### コンテキスト別アクセントカラー

`data-accent` 属性でCSS変数 `--accent` / `--accent-glow` を切替。背景・パネルは不変。

| コンテキスト             | アクセント       | 用途                     |
| ------------------------ | ---------------- | ------------------------ |
| **primary** (デフォルト) | Cyan `#22D3EE`   | メインアクション         |
| **secondary**            | Violet `#C4B5FD` | サブアクション、情報提示 |
| **accent**               | Amber `#FBBF24`  | 強調、完了通知           |

```css
/* CSS実装: data属性でアクセント切替 */
[data-accent='primary'] {
  --accent: #22d3ee;
  --accent-glow: rgba(34, 211, 238, 0.15);
}
[data-accent='secondary'] {
  --accent: #c4b5fd;
  --accent-glow: rgba(196, 181, 253, 0.15);
}
[data-accent='accent'] {
  --accent: #fbbf24;
  --accent-glow: rgba(251, 191, 36, 0.15);
}
```

> **WCAG AAA検証済み**: 全アクセントカラーは背景 `#0b1120` に対して 7:1以上のコントラスト比を確保。
> Cyan `#22D3EE` (10.3:1), Violet `#C4B5FD` (8.5:1), Amber `#FBBF24` (11.2:1)

### マイクロインタラクション仕様

| 要素                   | エフェクト                        | タイミング | トリガー        |
| ---------------------- | --------------------------------- | ---------- | --------------- |
| 分析ボタン押下         | リップルエフェクト                | 400ms      | onClick         |
| AI処理中ボーダー       | アクセントカラーのグロー脈動      | 2.5s loop  | isAnalyzing     |
| ストリーミングテキスト | タイプライターカーソル点滅        | 1s loop    | isStreaming     |
| タブ切替               | クロスフェード + スライド         | 250ms      | onNavigate      |
| クイズ正解             | パーティクルバースト + XPカウンタ | 600ms      | isCorrect       |
| クイズ不正解           | 軽いシェイク (translateX)         | 300ms      | !isCorrect      |
| 分析完了               | コンフェティアニメーション        | 1.5s       | status=complete |
| 新コンテンツバッジ     | バウンスアニメーション            | 500ms      | new-content     |

### ブランドカラー & シェードスケール

| Shade   | Hex           | 用途                                 |
| ------- | ------------- | ------------------------------------ |
| 50      | `#EFF6FF`     | ハイライト背景                       |
| 100     | `#DBEAFE`     | ホバー状態                           |
| 200     | `#BFDBFE`     | ボーダー（ライトモード）             |
| 300     | `#93C5FD`     | 無効テキスト                         |
| 400     | `#60A5FA`     | ミュートテキスト（ダーク）           |
| **500** | **`#3B82F6`** | **ブランドカラー（Education Blue）** |
| 600     | `#2563EB`     | プライマリボタン                     |
| 700     | `#1D4ED8`     | ホバー on プライマリ                 |
| 800     | `#1E40AF`     | ボーダー（ダーク）                   |
| 900     | `#1E3A8A`     | カード背景                           |
| 950     | `#172554`     | ページ背景                           |

### セマンティックトークン (Dark Mode)

```css
@theme {
  --color-background: #0b1120; /* 深いネイビーブラック */
  --color-foreground: #e2e8f0; /* ソフトホワイト */
  --color-card: rgba(30, 58, 138, 0.3); /* ガラス効果カード */
  --color-card-foreground: #e2e8f0;
  --color-primary: #3b82f6;
  --color-primary-foreground: #ffffff;
  --color-muted: #1e293b;
  --color-muted-foreground: #60a5fa;
  --color-border: rgba(59, 130, 246, 0.2);
  --color-ring: #3b82f6;
  --color-destructive: #ef4444;
  --color-success: #10b981;
  --color-warning: #f59e0b;
}
```

### タイポグラフィ

| 用途   | フォント   | Weight |
| ------ | ---------- | ------ |
| 見出し | Geist      | 600    |
| 本文   | Geist      | 400    |
| コード | Geist Mono | 400    |

### ビジュアルスタイルルール

| 要素         | Tailwindクラス                                                  |
| ------------ | --------------------------------------------------------------- |
| パネル       | `backdrop-blur-xl bg-white/5 border border-white/10 rounded-xl` |
| カード上昇感 | 背景より明るいガラスレイヤー（シャドウ不要）                    |
| アクセント   | `shadow-[0_0_20px_var(--accent-glow)]` (コンテキスト連動)       |
| コード入力   | `bg-black/40 font-mono border-l-2 border-[var(--accent)]`       |
| アイコン     | SVGアイコン使用（Lucide/Heroicons）、絵文字禁止                 |

### インタラクション

| タイミング | 値                              | 用途                   |
| ---------- | ------------------------------- | ---------------------- |
| micro      | 150ms                           | ホバー、クリック反応   |
| small      | 250ms                           | トグル、ドロップダウン |
| medium     | 400ms                           | モーダル、パネル遷移   |
| easing     | `cubic-bezier(0.16, 1, 0.3, 1)` | ease-out標準           |

### アクセシビリティ

- **コントラスト比**: WCAG AAA (7:1+) 目標 — 全アクセントカラー検証済み
- **Pure Black禁止**: `#000000`は使用しない（ダークグレー使用）
- **減速モーション対応**: `@media (prefers-reduced-motion: reduce)` 必須
- **フォーカスリング**: `ring-blue-500` で明確に表示
- **タッチターゲット**: モバイルで最小44px

---

## ビジネスコンテキスト

**コア戦略**: AI主導開発、高品質・迅速なイテレーション。

**プロジェクト目標**: [プロジェクトの目標をここに記載]

**主要機能**:

- [コア機能 1]
- [コア機能 2]
- [コア機能 3]

---

## 環境変数

`.env.local` / `.env.production` (git無視) に管理。

| 変数名           | 必須 | 説明                   |
| ---------------- | :--: | ---------------------- |
| `GEMINI_API_KEY` | 必須 | Google Gemini API キー |

> **AIプロバイダーポリシー**: Gemini専用。OpenAI/Anthropic/Groq等の他プロバイダーは使用しない。

---

## Git/GitHubワークフロー

- **ブランチ**: `master` (プロダクション)、`develop` (開発)、`feature/xxx`。
- **コミット**: `feat:` | `fix:` | `refactor:` | `test:` | `docs:` | `chore:`。
- **PR**: `gh pr create --base master --head develop`。

---

**注意**: コード変更後は必ず`npm run lint`と`npm test`を実行。

---

#### NEW_FEATURE（新機能開発）

| Tier     | ステップ                                                                 |
| -------- | ------------------------------------------------------------------------ |
| **S**    | architect → spec → readiness_gate → implement → quality_gate             |
| **M**    | + constraints_load → discovery_lite → ui_approval → wiring → status_sync |
| **L/XL** | + discovery_full → priority_calc                                         |

#### MODIFY_FEATURE（既存機能修正）

| Tier  | ステップ                                                |
| ----- | ------------------------------------------------------- |
| **S** | spec_update → readiness_gate → implement → quality_gate |
| **M** | + impact_analysis → wiring → status_sync                |
| **L** | + priority_calc                                         |

#### BUG_FIX（バグ修正）

```
analyze → root_cause → regression_test(Red) → fix(Green) → quality_gate
```

> 全パイプライン共通: `evidence_caching: true`、モデルフォールバック (haiku → sonnet → opus)

### 品質ゲートシステム (Makefile SSOT)

```bash
make q.check              # 全体品質検査（コミット前必須）
make q.fix                # 自動修正後再検査
make q.format.check       # [Critical] フォーマット確認
make q.analyze            # [Critical] 静的分析 + セキュリティ
make q.check-architecture # [Critical] Feature-Firstアーキテクチャ検証
make q.ui-flow            # [Critical] UI Flow Graph検証
make q.test               # [Critical] テスト実行
make q.build              # [Critical] ビルド実行
make q.coverage           # [Major] カバレッジ閾値検証
make q.test-exists        # [Major] テストファイル存在確認
make spec.validate SPEC=001  # SPEC文書検証（単一）
make spec.validate-all       # SPEC文書検証（全体）
```

深刻度 (3-Tier):

- **Critical** (q.critical): 失敗時コミット/PR不可 — format, lint+security, architecture, ui-flow, test, build
- **Major** (q.major.warn): 警告表示、進行可能 — coverage, test existence
- **Info** (q.info): 参考情報のみ

### CI/CD (.github/workflows/quality-gate.yml)

| トリガー     | 条件                       |
| ------------ | -------------------------- |
| Pull Request | master, develop ブランチへ |
| Push         | develop ブランチへ         |
| 手動         | workflow_dispatch          |

**自動実行ステップ**:

1. `[Critical]` Format Check → Lint+Security → Architecture → UI Flow → Tests → Build
2. `[Major]` Test File Existence, Coverage Threshold (continue-on-error)
3. SPEC Validation (featureラベル付きPRのみ)
4. Documentation Check (PR時、変更ファイルのドキュメント存在確認)

### 主要スキル（Tier別）

#### Tier 1: Orchestrator（統合制御）

| スキル                  | 起動方法                         | 機能                 |
| ----------------------- | -------------------------------- | -------------------- |
| `turbo-mode`            | `/turbo` または「並列で」        | 並列実行エンジン     |
| `persistent-mode`       | `/persistent` または「完了まで」 | 完了まで自動継続     |
| `analyze-what-to-build` | 「次に何を作る？」               | 競合分析パイプライン |

#### Tier 2: Pipeline（ワークフロー）

| スキル                  | 起動方法               | 機能                        |
| ----------------------- | ---------------------- | --------------------------- |
| `domain-modeler`        | 「ドメインモデル作成」 | DDD戦略設計・Event Storming |
| `architecture-selector` | 「アーキテクチャ選定」 | ATAM Lite評価・ADR生成      |
| `system-designer`       | 「システム設計」       | C4モデル (Level 1+2)        |
| `priority-analyzer`     | 「優先順位分析」       | RICE モデル分析             |
| `competitive-tracker`   | 「競合比較」           | 6社ベンチマーク             |
| `research-pilot`        | 「リサーチして」       | Product Discovery           |
| `deep-research`         | 「ディープリサーチ」   | OpenAI/Gemini Deep Research |
| `spec-validator`        | 「SPEC検証」           | JSON Schema・API検証        |

#### Tier 3: Utility（単一タスク）

| スキル               | 起動方法                 | 機能                   |
| -------------------- | ------------------------ | ---------------------- |
| `skill-health-check` | 「スキルヘルスチェック」 | ガバナンス自動監査     |
| `sync-agents-md`     | 「AGENTS.md同期」        | プロジェクト指針更新   |
| `feature-doctor`     | 「CONTEXT修復」          | CONTEXT.json自動復旧   |
| `cancel`             | `/cancel`                | 持続モード安全終了     |
| `deep-explain`       | `/deep-explain [対象]`   | 構造化された深掘り分析 |

#### UI/UXスキル

| スキル                  | 起動方法               | 機能                                           |
| ----------------------- | ---------------------- | ---------------------------------------------- |
| `ui-ux-pro-max`         | UI設計時               | デザインシステム生成（50スタイル・97パレット） |
| `frontend-design`       | UI実装時               | 独創的フロントエンド設計                       |
| `color-palette`         | カラー設計時           | ブランドHexから11段階スケール生成              |
| `interaction-design`    | インタラクション設計時 | マイクロインタラクション・モーション           |
| `web-design-guidelines` | UIレビュー時           | Web Interface Guidelines準拠チェック           |

### 自動実行フロー図

```
[セッション開始] → session-start.mjs → Wisdom読み込み
         ↓
[ユーザー入力] → keyword-detector.mjs → スキル自動起動判定
         ↓
[ツール実行前] → pre-tool-enforcer.mjs → 権限チェック
              → qa-write-guard.mjs → 品質ゲート（Edit/Write時）
         ↓
[ツール実行後] → edit-error-recovery.mjs → エラー自動回復（Edit時）
              → web-format.mjs → フォーマット自動適用（Write/Edit時）
         ↓
[コンパクト化前] → compact-context-preserver.mjs → コンテキスト保持
         ↓
[停止時] → stop-handler.mjs → 状態保存・クリーンアップ
```

### 権限設定

```json
{
  "deny": ["Bash(sudo:*)", "Bash(git reset:*)", "Bash(git rebase:*)"]
}
```

> `sudo`、`git reset`、`git rebase` は明示的に禁止。
