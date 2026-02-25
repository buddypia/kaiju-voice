# oh-my-claude-code

Claude Code の開発体験を劇的に向上させる Hook & Skill フレームワーク。

> oh-my-zsh が zsh を拡張するように、oh-my-claude-code は Claude Code を拡張します。

## 何ができるか

| 機能                     | 説明                                                        |
| ------------------------ | ----------------------------------------------------------- |
| **Persistent Mode**      | `完了まで実装して` → 作業が完了するまで Claude が止まらない |
| **Turbo Mode**           | `ターボで` → 並列実行 + 自動継続                            |
| **QA Mode**              | `QA回して` → lint/test が全通過するまで自動ループ           |
| **Keyword Detection**    | 日本語/英語の自然言語でスキルを自動起動                     |
| **Self-Healing Edit**    | Edit 失敗時に自動で Read → 再 Edit を促す                   |
| **Auto Format**          | Write/Edit 後に Prettier を自動実行                         |
| **Context Preservation** | compaction 前に作業状態を自動保存                           |
| **Pipeline as Code**     | YAML でワークフローを定義、Tier別に実行                     |

## クイックスタート

```bash
# 1. リポジトリをクローン
git clone https://github.com/yourname/oh-my-claude-code.git

# 2. プロジェクトに .claude/ をコピー
cp -r oh-my-claude-code/.claude /path/to/your-project/.claude

# 3. settings.json をカスタマイズ
# (テンプレートから不要な設定を削除/変更)
```

または、インストールスクリプトを使用:

```bash
curl -fsSL https://raw.githubusercontent.com/yourname/oh-my-claude-code/main/install.sh | bash
```

## アーキテクチャ

```
Claude Code Session
    │
    ├── SessionStart ─────→ session-start.mjs (状態復元)
    │
    ├── UserPromptSubmit ──→ keyword-detector.mjs (意図検出 → Skill起動)
    │
    ├── PreToolUse ────────→ pre-tool-enforcer.mjs (状態リマインダー注入)
    │                     → qa-write-guard.mjs (Edit/Write 品質ゲート)
    │                     → merge-guard.mjs (git merge 安全チェック)
    │
    ├── PostToolUse ───────→ edit-error-recovery.mjs (Edit 自己修復)
    │                     → web-format.mjs (Prettier 自動フォーマット)
    │
    ├── Stop ──────────────→ stop-handler.mjs (モード別継続/停止判定)
    │
    ├── SubagentStop ──────→ stop-handler.mjs (サブエージェント作業検証)
    │
    └── PreCompact ────────→ compact-context-preserver.mjs (コンテキスト保存)
```

### 核心メカニズム: Stop Hook による自動継続

```
通常の Claude Code:
  User → Claude 作業 → 自動停止 → User が再度指示

oh-my-claude-code:
  User → Claude 作業 → Stop Hook が判定:
    ├── 完了マーカー検出 → 正常終了
    ├── Max iterations 到達 → 安全終了
    ├── ユーザーキャンセル → 即時停止
    └── 未完了 → block + continuation prompt → 作業続行
```

## ディレクトリ構成

```
.claude/
├── settings.json              # Hook 登録 & 設定 (SSOT)
├── hooks/                     # PostToolUse / PreCompact Hook
│   ├── edit-error-recovery.mjs  # Edit 失敗 → 自己修復ガイダンス
│   ├── web-format.mjs           # Prettier 自動フォーマット
│   └── compact-context-preserver.mjs  # compaction 前コンテキスト保存
├── scripts/                   # SessionStart / UserPromptSubmit / PreToolUse / Stop Hook
│   ├── session-start.mjs        # セッション開始 → 状態復元
│   ├── keyword-detector.mjs     # キーワード検出 → Skill 起動
│   ├── stop-handler.mjs         # Stop → 継続/停止判定
│   ├── pre-tool-enforcer.mjs    # ツール実行前 → 状態リマインダー
│   ├── qa-write-guard.mjs       # Write/Edit 前 → 品質チェック
│   ├── merge-guard.mjs          # git merge 前 → 安全チェック
│   └── lib/                     # 共有ライブラリ
│       ├── state.mjs              # アトミックファイル状態管理
│       ├── utils.mjs              # stdin/stdout, 安全チェック
│       └── transcript.mjs         # Transcript パース, 完了検出
├── pipelines/                 # Pipeline as Code (YAML)
│   ├── new-feature.yaml         # 新機能開発 (S/M/L/XL Tier)
│   ├── modify-feature.yaml      # 既存機能修正
│   ├── bug-fix.yaml             # バグ修正 (Red→Green TDD)
│   └── infra-deploy.yaml        # インフラデプロイ
├── skills/                    # Skill 定義 (SKILL.md + MANIFEST.json)
│   ├── feature-pilot/           # 機能開発オーケストレーター
│   ├── persistent-mode/         # 完了まで止まらないモード
│   ├── turbo-mode/              # 並列実行モード
│   ├── bug-fix/                 # バグ修正ワークフロー
│   └── ...                      # 40+ スキル
└── state/                     # ランタイム状態 (.gitignore 推奨)
    ├── persistent-state.json
    ├── web-qa-state.json
    └── turbo-state.json
```

## 3つのモード

### 1. Persistent Mode (完了まで)

```
ユーザー: 「この機能を完了まで実装して」
```

- Stop Hook が completion marker (`<promise>DONE</promise>`) を監視
- Plan ファイルのチェックボックス完了を自動検出
- 最大 20 iterations のセーフガード
- 同一エラー 3回繰り返しで自動中断

### 2. Turbo Mode (並列実行)

```
ユーザー: 「ターボで実装して」
```

- 並列エージェント実行を促進
- 未完了 Task カウントで作業を追跡
- 最大 30 reinforcements のセーフガード

### 3. QA Mode (品質検証ループ)

```
ユーザー: 「QA回して」
```

- `npm run lint` → `npm test` を自動ループ
- Transcript から結果を自動パース (pass/fail 検出)
- 全通過で自動終了
- 最大 10 cycles のセーフガード

## Keyword Detector (自然言語 → Skill 起動)

2層パターンマッチングによる意図検出:

| 優先度 | キーワード   | 起動 Skill      | 例                             |
| ------ | ------------ | --------------- | ------------------------------ |
| 0      | cancel       | cancel          | 「キャンセルして」「/cancel」  |
| 1      | persistent   | persistent-mode | 「完了まで実装して」           |
| 2      | turbo        | turbo-mode      | 「ターボで」「並列で実行」     |
| 3      | research     | research-pilot  | 「リサーチして」               |
| 4      | feature      | feature-pilot   | 「新機能追加して」             |
| 5      | qa           | web-qa          | 「QA回して」「テスト実行して」 |
| 6      | security     | security-scan   | 「セキュリティ検査して」       |
| 7      | bug-fix      | bug-fix         | 「バグ直して」                 |
| 8      | deep-explain | deep-explain    | 「深層分析して」               |

### マッチングの仕組み

```
Layer 1: intentPatterns (動詞/命令形) → 即時起動
  例: 「完了まで実装して」→ persistent 即時有効化

Layer 2: mentionPatterns (名詞形) → 否定文脈チェック後に決定
  例: 「バグ修正」→ 「バグ修正について教えて」なら拒否 (否定文脈 "について")
```

### 競合解決

- `cancel` は排他的 (他のマッチをすべて無視)
- `persistent` + 他のモード → 両方アクティブ
- `feature-pilot` + `bug-fix` → `feature-pilot` 優先

## Pipeline as Code

YAML で開発ワークフローを定義:

```yaml
# new-feature.yaml
name: NEW_FEATURE
tiers:
  S: [architect, spec, implement, quality_gate]
  M: [architect, discovery_lite, spec, implement, wiring, quality_gate]
  L: [architect, discovery_full, spec, implement, wiring, priority_calc, quality_gate]

steps:
  architect:
    skill: feature-architect
    model: sonnet
    outputs: [BRIEF.md, CONTEXT.json]
    retry: { max: 2 }

  implement:
    skill: feature-implementer
    model: sonnet
    tdd: true
    batch_order:
      - { name: 'Data Layer', parallel: true, items: ['Type + Schema', 'API'] }
      - { name: 'Logic Layer', items: ['Custom Hook'] }
      - { name: 'Presentation', items: ['Component'] }
      - { name: 'Tests', items: ['API Test', 'Hook Test', 'Component Test'] }

global:
  model_fallback:
    enabled: true
    order: [haiku, sonnet, opus]
    max_failures_before_escalation: 3
```

## 共有ライブラリ

### state.mjs — アトミックファイル状態管理

```javascript
import { readState, writeState, clearState, isStale } from './lib/state.mjs';

// 読み取り
const state = readState(stateDir, 'persistent');

// アトミック書き込み (tmp → rename)
writeState(stateDir, 'persistent', { active: true, iteration: 1 });

// 削除 (モード非アクティブ化)
clearState(stateDir, 'persistent');

// ゾンビ状態チェック (24時間)
if (isStale(state)) {
  /* ... */
}
```

### transcript.mjs — Transcript パース

```javascript
import { detectCompletionMarker, detectQaCompletion } from './lib/transcript.mjs';

// 完了マーカー検出
if (detectCompletionMarker(transcriptPath, 'DONE')) {
  /* 完了 */
}

// QA 結果検出
const result = detectQaCompletion(transcriptPath);
// { complete: true/false, analyzeResult: true/false/null, testResult: true/false/null }
```

## Safety Gates

Stop Hook には4つの安全ゲートがあります:

| Gate           | 動作         | 理由             |
| -------------- | ------------ | ---------------- |
| Context Limit  | 即時停止許可 | deadlock 防止    |
| User Cancel    | 即時停止許可 | ユーザー意思尊重 |
| Same Error ×3  | 強制中断     | 構造的問題の検出 |
| Max Iterations | 正常終了     | 無限ループ防止   |

## カスタマイズ

### 環境変数

| 変数                    | デフォルト     | 説明                       |
| ----------------------- | -------------- | -------------------------- |
| `CLAUDE_QA_ANALYZE_CMD` | `npm run lint` | QA Mode の静的分析コマンド |
| `CLAUDE_QA_TEST_CMD`    | `npm test`     | QA Mode のテストコマンド   |

### settings.json の調整

```jsonc
{
  // 使わない Hook は削除可能
  "hooks": {
    "SessionStart": [
      /* session-start.mjs */
    ],
    "UserPromptSubmit": [
      /* keyword-detector.mjs */
    ],
    "PreToolUse": [
      /* pre-tool-enforcer.mjs, qa-write-guard.mjs, merge-guard.mjs */
    ],
    "PostToolUse": [
      /* edit-error-recovery.mjs, web-format.mjs */
    ],
    "Stop": [
      /* stop-handler.mjs */
    ],
    "SubagentStop": [
      /* stop-handler.mjs */
    ],
    "PreCompact": [
      /* compact-context-preserver.mjs */
    ],
  },
}
```

### キーワード追加

`keyword-detector.mjs` の `KEYWORD_DEFINITIONS` 配列に追加:

```javascript
{
  name: 'my-skill',
  skill: 'my-skill',
  intentPatterns: [/スキル実行して/],
  mentionPatterns: [/スキル/],
  negativeContext: [/スキル[はがのを]/],
  createsState: false,
}
```

## 実績: Gemini 3 ハッカソン東京 準優勝

oh-my-claude-code の開発パイプラインを使って「KAIJU VOICE」(声で戦う怪獣バトルゲーム) を開発し、
Gemini 3 ハッカソン東京 (Cerebral Valley) で**準優勝**を達成しました。

パイプラインが実際に生み出したもの:

| パイプライン     | 入力                   | 出力                                            |
| ---------------- | ---------------------- | ----------------------------------------------- |
| architect → spec | 「声で戦う怪獣バトル」 | SPEC (型定義, FR, API契約, ダメージ式)          |
| implement: Type  | SPEC §0.2              | 12型 + 12アクション (discriminated union)       |
| implement: API   | SPEC §2.x              | 6 API ルート (Gemini Flash, Imagen, TTS, Lyria) |
| implement: UI    | SPEC + screens/        | 4画面 + 20コンポーネント + 7 VFX                |
| quality_gate     | 全ファイル             | lint 0 errors, test pass, build success         |

- 開発時間: 約6時間
- 総コード: 50+ファイル / 5,000行
- Gemini API: 6エンドポイント
- Feature: 8機能 (Feature-First 構造)

詳細: [Case Study: KAIJU VOICE](docs/case-study-kaiju-voice.md)

---

## 起源

このプロジェクトは [oh-my-opencode](https://github.com/anthropics/opencode) のプラグインシステムを
Claude Code Hooks API に移植したものです。

| oh-my-opencode (Plugin)      | oh-my-claude-code (Hooks)      |
| ---------------------------- | ------------------------------ |
| `ralph-loop`                 | `stop-handler.mjs`             |
| `session.idle` event         | `Stop` event                   |
| `session.prompt()` injection | `decision: "block"` + `reason` |
| `todo-continuation-enforcer` | `countIncompleteTasks()`       |
| `stop-continuation-guard`    | `isUserAbort()` check          |
| In-memory Map (storage.ts)   | File-based state (state.mjs)   |
| `keyword-detector` plugin    | `keyword-detector.mjs` hook    |
| `edit-error-recovery` plugin | `edit-error-recovery.mjs` hook |

## ライセンス

MIT License
