# Architecture of oh-my-claude-code

oh-my-claude-code は Claude Code の Hooks API を活用し、セッション管理・自動継続・品質ゲート・自己修復といった高度な開発体験を実現するフレームワークである。本ドキュメントではその内部アーキテクチャを技術的に解説する。

---

## 1. Hook Event Flow

Claude Code Hooks API は 7 つのイベントを提供する。oh-my-claude-code はその全てを活用し、セッションのライフサイクル全体を制御する。

```
                         Claude Code Session
                               |
  ┌────────────────────────────┼────────────────────────────┐
  |                            |                            |
  |  ┌─── SessionStart ───────┤                            |
  |  |    session-start.mjs    |                            |
  |  |    (状態復元)            |                            |
  |  |                         |                            |
  |  ├─── UserPromptSubmit ────┤                            |
  |  |    keyword-detector.mjs |                            |
  |  |    (意図検出 -> Skill)   |                            |
  |  |                         |                            |
  |  ├─── PreToolUse ──────────┤                            |
  |  |    pre-tool-enforcer.mjs|  (Sisyphus: 状態リマインダー) |
  |  |    qa-write-guard.mjs   |  (Edit/Write 品質ゲート)    |
  |  |    merge-guard.mjs      |  (git merge 安全チェック)    |
  |  |                         |                            |
  |  ├─── PostToolUse ─────────┤                            |
  |  |    edit-error-recovery  |  (Edit 自己修復)            |
  |  |    web-format.mjs       |  (Prettier 自動フォーマット) |
  |  |                         |                            |
  |  ├─── Stop ────────────────┤                            |
  |  |    stop-handler.mjs     |  (モード別 継続/停止判定)    |
  |  |                         |                            |
  |  ├─── SubagentStop ────────┤                            |
  |  |    stop-handler.mjs     |  (同一ハンドラ + 作業検証)   |
  |  |    + prompt (検証指示)    |                            |
  |  |                         |                            |
  |  └─── PreCompact ──────────┤                            |
  |       compact-context-     |                            |
  |       preserver.mjs        |  (コンテキスト保存)         |
  └────────────────────────────┴────────────────────────────┘
```

### 各 Hook イベントの詳細

#### SessionStart -> session-start.mjs

セッション開始時に前セッションのアクティブ状態を復元する。Context compaction や resume でセッションが再起動された際、AI は以前の作業状態を失っている。このフックが `.claude/state/` から状態を読み取り、`hookSpecificOutput.additionalContext` で復元メッセージを注入する。

処理フロー:

1. `.claude/state/` ディレクトリでアクティブなモード (persistent / web-qa / turbo) を検索
2. 各モードの staleness チェック (24時間)
3. セッション所有権チェック (`session_id` フィールド)
4. compact/resume の場合はセッション引き継ぎを許可 (所有権を現セッションに移譲)
5. 未完了 Task カウントの取得
6. 復元メッセージの組み立てと注入

#### UserPromptSubmit -> keyword-detector.mjs

ユーザーの自然言語入力からスキル呼び出し意図を検出し、対応する Skill を自動起動する。詳細は「3. Keyword Detection Pipeline」を参照。

#### PreToolUse -> pre-tool-enforcer.mjs (Sisyphus Pattern)

**Sisyphus パターン**は oh-my-opencode から移植された核心的設計思想である。「岩は決して止まらない (The boulder never stops)」という哲学に基づき、**全てのツール呼び出し前**にアクティブな作業状態をリマインダーとして注入する。

```
Claude がツールを呼ぶたびに:
  ┌──────────────────────────────────────────────────┐
  | [PERSISTENT 3/20 | QA 2/10 | Tasks: 5]          |
  | 並列実行可能なコマンドは同時に呼び出してください。|
  └──────────────────────────────────────────────────┘
  ↑ これが additionalContext として注入される
```

目的: AI が長いセッションでコンテキストを失いがちな問題に対する根本的解決。短い状態プレフィックスを毎回注入することで、AI は常に「今何をしているか」を把握し続ける。

#### PreToolUse -> qa-write-guard.mjs

QA モードがアクティブな場合に Edit/Write 操作を監視する 3 つのガード:

| Guard                       | 対象                          | ブロック条件                  |
| --------------------------- | ----------------------------- | ----------------------------- |
| Guard 1: 生成成果物保護     | `.d.ts`, `.min.js`, `.map` 等 | 生成ファイルの直接編集        |
| Guard 2: テスト削除防止     | `Write` on test files         | 既存テストファイルの空化/削除 |
| Guard 3: Assertion 削除防止 | `Edit` on test files          | `expect()` 文の全削除         |

設計原則: "If tests fail, fix the CODE not the tests" (oh-my-opencode Ultrawork ルールの移植)

#### PreToolUse -> merge-guard.mjs

`git merge` コマンド実行前に staged changes の有無を確認し、コミットされていない変更が merge により破壊されることを防止する。

```
典型的な危険シナリオ:
  1. git add で変更を stage
  2. git commit が pre-commit hook で失敗
  3. AI が git merge を試行 → staging area 破壊!

merge-guard がステップ 3 を阻止:
  - git diff --cached で staged changes を確認
  - staged changes がある場合は deny を返却
  - git merge --abort は安全なため除外
```

#### PostToolUse -> edit-error-recovery.mjs

Edit ツール失敗を検出し、自己修復ガイダンスを注入する。詳細は「5. Self-Healing Loop」を参照。

#### PostToolUse -> web-format.mjs

Write/Edit 後に変更されたファイルに対して Prettier を自動実行する。

- 対象拡張子: `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs`, `.json`, `.css`, `.scss`, `.html`, `.md`, `.yaml` 等
- `npx --no-install prettier --write` で実行 (Prettier 未インストール時は安全にスキップ)
- `.min.js`, `.map` 等の生成物は除外

#### Stop -> stop-handler.mjs

モードがアクティブな場合にセッション停止を制御する。詳細は「4. Stop Handler Safety Architecture」を参照。

#### SubagentStop -> stop-handler.mjs + prompt

SubagentStop イベントでは stop-handler.mjs に加えて、settings.json に定義された検証用 prompt が注入される:

```json
{
  "type": "prompt",
  "prompt": "サブエージェントの作業結果を検証してください。次の基準:
    (1) 要求した作業を実際に実行したか？
    (2) '〜できます'のような可能性だけでなく具体的な結果を返したか？
    (3) ファイルパス、コード、データ等の具体的な証拠があるか？"
}
```

この 2 層構造により、サブエージェントの「作業をしたふり」を防止する。

#### PreCompact -> compact-context-preserver.mjs

Context compaction (コンテキスト圧縮) 前に核心コンテキストを自動保存する。保存する 7 項目:

1. **Git 状態** -- 現在のブランチと最近 5 件のコミット
2. **アクティブモード** -- persistent/web-qa/turbo の進捗状態
3. **変更ファイルリスト** -- staged + unstaged の変更ファイル (最大 20 件)
4. **未完了タスク** -- pending/in_progress 状態のタスク一覧
5. **エラー履歴** -- 各モードの最近 3 件のエラー
6. **Plan ファイル進捗** -- チェックボックス完了率
7. **作業ディレクトリコンテキスト** -- プロジェクトパスと構造

---

## 2. State Management

### ファイルベース状態システム

oh-my-opencode ではプラグインのインメモリ Map (`storage.ts`) で状態を管理していたが、Claude Code Hooks は毎回新しいプロセスとして起動されるため、**ファイルベース**の状態管理に再設計された。

```
.claude/state/                    <- ensureStateDir() で自動作成
├── persistent-state.json         <- Persistent Mode の状態
├── web-qa-state.json             <- QA Mode の状態
└── turbo-state.json              <- Turbo Mode の状態
```

### 3 つのモード

| モード         | State ファイル          | 主要フィールド                                                                                          |
| -------------- | ----------------------- | ------------------------------------------------------------------------------------------------------- |
| **persistent** | `persistent-state.json` | `active`, `iteration`, `max_iterations` (default: 20), `error_history`, `completion`, `original_prompt` |
| **web-qa**     | `web-qa-state.json`     | `active`, `cycle`, `max_cycles` (default: 10), `all_passing`, `last_failure`, `error_history`           |
| **turbo**      | `turbo-state.json`      | `active`, `reinforcement_count`, `max_reinforcements` (default: 30), `original_prompt`                  |

### 共通フィールド

全モードの状態ファイルに含まれる共通フィールド:

```json
{
  "active": true,
  "started_at": "2026-02-24T10:00:00.000Z",
  "last_checked_at": "2026-02-24T10:05:00.000Z",
  "activated_by": "keyword-detector",
  "session_id": "abc123",
  "original_prompt": "完了まで実装して"
}
```

### Atomic Writes (POSIX Atomic Rename)

状態ファイルの書き込みは race condition を防止するため、アトミック書き込みパターンを採用している:

```
writeState() の処理フロー:

  1. 一時ファイルに書き込み:
     persistent-state.json.a1b2c3d4.tmp

  2. renameSync() で一時ファイルを本ファイルに置換:
     persistent-state.json.a1b2c3d4.tmp → persistent-state.json

  3. POSIX では rename(2) はアトミック操作
     → 読み取り側は常に完全な JSON を取得する
     → 部分書き込みによる破損を防止

  4. rename 失敗時は一時ファイルをクリーンアップ
```

### 24 時間 Staleness Check

ゾンビ状態 (プロセスが異常終了した際に残るアクティブ状態) を防止するため、`last_checked_at` または `started_at` から 24 時間経過した状態は stale と判定する。

```javascript
// isStale() のロジック
const recent = Math.max(
  new Date(state.last_checked_at).getTime(),
  new Date(state.started_at).getTime(),
);
return Date.now() - recent > 24 * 60 * 60 * 1000; // 24h
```

初期値は 2 時間だったが、夜間作業や長期作業のサポートのため 24 時間に変更された (BUG-8 修正)。

### Session-Scoped State Ownership

複数のセッションが同一プロジェクトで同時に動作する場合のクロスセッション干渉を防止する (BUG-9 修正):

```
isSessionOwned(state, sessionId) のルール:

  state に session_id なし (レガシー)  →  全セッションにマッチ (後方互換)
  sessionId が空文字列               →  全セッションにマッチ (安全フォールバック)
  両方あり                           →  完全一致比較
```

session-start.mjs では compact/resume 時にセッション所有権を引き継ぐ:

```
source === 'compact' || 'resume'  →  state.session_id を現在のセッション ID に更新
source === 'startup' || 'clear'   →  他セッションのモードは復元しない
```

---

## 3. Keyword Detection Pipeline

keyword-detector.mjs は 2 層パターンマッチングと否定文脈分析により、ユーザーの自然言語入力から正確にスキル呼び出し意図を検出する。

### 全体フロー

````
User Prompt
    |
    v
┌─────────────────────────────────┐
│ 1. 前処理: cleanPromptForMatching() │
│    - コードブロック除去 (```...```)    │
│    - インラインコード除去 (`...`)     │
│    - マークダウンテーブル除去         │
│    - 括弧内容除去                    │
│    - ファイルパス除去                 │
│    - JSON リテラル除去               │
└─────────────────────────────────┘
    |
    v
┌─────────────────────────────────┐
│ 2. 2層パターンマッチング             │
│                                     │
│  Layer 1: intentPatterns             │
│    動詞/命令形 → 即時有効化          │
│    例: 「完了まで実装して」           │
│         ↓                           │
│    MATCH → キーワード確定            │
│                                     │
│  Layer 2: mentionPatterns            │
│    名詞形 → 否定文脈チェック後に決定  │
│    例: 「バグ修正」                  │
│         ↓                           │
│    negativeContext チェック           │
│    例: 「バグ修正について」→ 拒否     │
│         ↓                           │
│    GLOBAL_NEGATIVE_CONTEXT チェック   │
│    例: 「〜について」「〜ですか」     │
│         ↓                           │
│    通過 → キーワード確定             │
└─────────────────────────────────┘
    |
    v
┌─────────────────────────────────┐
│ 3. 競合解決: resolveConflicts()      │
└─────────────────────────────────┘
    |
    v
┌─────────────────────────────────┐
│ 4. State 生成 + Skill 呼び出し       │
│    hookSpecificOutput.               │
│      additionalContext で注入        │
└─────────────────────────────────┘
````

### Layer 1: intentPatterns (動詞/命令形)

高確信度のパターン。マッチすると即座にキーワードが有効化される。

```
intentPatterns の例:
  persistent: /完了まで\s*(して|完成|進行|作業|実装|...)/
  turbo:      /ターボ\s*(モード|で)/
  cancel:     /キャンセルして/, /\/cancel/i
  web-qa:     /QA\s*(サイクル|回して|実行|開始)/
```

### Layer 2: mentionPatterns (名詞形)

低確信度のパターン。否定文脈チェックを通過した場合のみ有効化される。

```
mentionPatterns の例:
  persistent: /完了まで.{0,15}(して|し|完成|実装|...)/
  turbo:      /ターボ/
  bug-fix:    /バグ\s*修正/
```

### Global Negative Context

全キーワードに共通適用される否定文脈パターン:

```javascript
const GLOBAL_NEGATIVE_CONTEXT = [
  /について/,      // 説明文脈: 「〜について」
  /に関して/,      // 参照文脈: 「〜に関して」
  /という/,        // 引用文脈: 「〜という」
  /なのか/,        // 質問文脈: 「〜なのか」
  /ですか/,        // 質問文脈: 「〜ですか」
  /できる/,        // 可能性文脈: 「〜できる」
  /すべき/,        // 義務文脈: 「〜すべき」
  /場合/,          // 状況文脈: 「〜の場合」
  ...
];
```

これにより「persistent モードについて教えて」のような質問でモードが誤起動することを防止する。

### 競合解決ルール

```
resolveConflicts() の優先順位ルール:

  1. cancel は排他的
     cancel + (任意のキーワード) → cancel のみ

  2. research-pilot > feature-pilot
     research-pilot が feature-pilot の前段 Discovery 段階

  3. feature-pilot > bug-fix
     feature-pilot 内部に BUG_FIX パイプラインを内蔵

  4. analyze-pipeline > competitive-tracker
     analyze-pipeline が competitive-tracker を Stage 1 で内部呼び出し

  5. persistent + turbo 自動連携
     persistent を有効化すると turbo も自動的に有効化
     (oh-my-opencode の ralph + ultrawork 連携の移植)

  6. 優先順位順ソート
     KEYWORD_DEFINITIONS の配列順序 = 優先順位
```

### Skill 呼び出しメカニズム

検出されたキーワードは `hookSpecificOutput.additionalContext` を通じて Skill 呼び出し指示として Claude に注入される:

```
[MAGIC KEYWORD: PERSISTENT]

You MUST invoke the skill using the Skill tool:

Skill: persistent-mode

User request:
完了まで実装して

IMPORTANT: Invoke the skill IMMEDIATELY.
```

---

## 4. Stop Handler Safety Architecture

stop-handler.mjs は Stop と SubagentStop の両イベントを処理する統合ハンドラである。4 つの安全ゲートとモード別ハンドラから構成される。

### 処理フロー

```
Stop / SubagentStop Event
    |
    v
┌─────────────────────────────────────────────┐
│ Safety Gate 1: Context Limit                 │
│   isContextLimitStop(data) ?                 │
│   → YES: output({}) -- 絶対にブロックしない  │
│          (deadlock 防止)                     │
└──────────────────────┬──────────────────────┘
                       | NO
                       v
┌─────────────────────────────────────────────┐
│ Safety Gate 2: User Cancel                   │
│   isUserAbort(data) ?                        │
│   → YES: output({}) -- ユーザー意思を尊重    │
└──────────────────────┬──────────────────────┘
                       | NO
                       v
┌─────────────────────────────────────────────┐
│ Mode Detection                               │
│   getActiveModeForSession(stateDir, sid)     │
│   → null: output({}) -- 正常終了             │
└──────────────────────┬──────────────────────┘
                       | mode found
                       v
┌─────────────────────────────────────────────┐
│ Safety Gate 3: Same Error x3                 │
│   hasSameErrorRepeated(state, 3) ?           │
│   → YES: block + "構造的問題" メッセージ     │
│          (修正不能なエラーの無限ループ防止)    │
└──────────────────────┬──────────────────────┘
                       | NO
                       v
┌─────────────────────────────────────────────┐
│ Mode-Specific Handler Dispatch               │
│   persistent → handlePersistent()            │
│   web-qa    → handleWebQa()                  │
│   turbo     → handleTurbo()                  │
└─────────────────────────────────────────────┘
```

### Safety Gate 詳細

#### Gate 1: Context Limit -> 即時停止許可

Context window が満杯になった場合、Stop Hook がブロックすると **deadlock** が発生する (Claude は続行できず、Hook はブロックし続ける)。このため context limit 関連の停止理由を検出した場合は無条件で停止を許可する。

検出パターン: `context_limit`, `context_window`, `max_tokens`, `conversation_too_long` 等。

#### Gate 2: User Cancel -> 即時停止許可

ユーザーが明示的にキャンセルした場合は、どのモードがアクティブであっても即座に停止を許可する。

検出パターン: `user_requested` フラグ、`aborted`, `cancel`, `ctrl_c` 等の stop_reason。

#### Gate 3: Same Error x3 -> 強制停止

同一エラーが 3 回繰り返された場合、構造的問題と判断して強制停止する。2 段階の検査ロジック:

```
hasSameErrorRepeated() の検査ロジック:

  検査 1: 完全一致
    最近 3 件のエラーが全て同一文字列
    例: ["lint:fail", "lint:fail", "lint:fail"] → 構造的問題

  検査 2: 核心失敗パターン繰り返し
    エラー文字列から失敗コンポーネントを抽出し、
    同一コンポーネントが全エラーに存在すれば構造的問題
    例: ["analyze:false,test:true",
         "analyze:false,test:false",
         "analyze:false,test:true"]
    → "analyze" が全てで false → 構造的問題
```

#### Gate 4: Max Iterations -> 安全終了

各モードの最大反復回数に達した場合、状態をクリーンアップして停止を許可する。これが無限ループに対する最終的なセーフガードとなる。

### 3 つのモードハンドラ

#### Persistent Mode Handler

```
handlePersistent() の判定フロー:

  1. Completion Marker 検査
     transcript で <promise>DONE</promise> を検索
     → 検出: clearState + 正常終了

  2. Plan チェックボックス完了チェック
     plan_file のチェックボックス完了率を計算
     → 全完了: clearState + 正常終了
     → 未完了: block + 残りタスクのプレビュー表示

  3. Max Iterations チェック
     iteration >= max_iterations (default: 20)
     → 到達: clearState + 正常終了

  4. Iteration Increment + Block
     state.iteration++ して writeState
     → block + continuation prompt
     → "作業が完了していません。続行してください。"
     → 元の作業内容と未完了 Task 数を含む

  writeState 失敗時の安全策:
     iteration が未増加のまま block すると無限ループ
     → writeState 失敗時は停止を許可
```

#### QA Mode Handler

```
handleWebQa() の判定フロー:

  1. Transcript ベース完了検出 (核心機能)
     detectQaCompletion() で analyze/test 結果をパース
     → 両方 pass: clearState + 正常終了

  2. Completion Marker チェック
     <promise>QA_COMPLETE</promise> を検索
     → 検出: clearState + 正常終了

  3. State ファイル all_passing チェック (レガシーフォールバック)
     → true: clearState + 正常終了

  4. Max Cycles チェック
     cycle >= max_cycles (default: 10)
     → 到達: clearState + 正常終了

  5. Error History 追跡
     analyze/test の結果シグネチャを記録
     → Safety Gate 3 (同一エラー x3) のデータ源

  6. Cycle Increment + Block
     → block + 具体的な失敗情報
     → "analyze: FAIL / test: PASS" 等の結果表示
     → 実行順序の案内
```

#### Turbo Mode Handler

```
handleTurbo() の判定フロー:

  1. Max Reinforcements チェック
     count > max_reinforcements (default: 30)
     → 到達: clearState + 正常終了

  2. 未完了 Task カウント
     countIncompleteTasks() で残タスク数を取得

  3. Reinforcement Count Increment + Block
     → block + "未完了 Task: N 個"
     → 3 回目以降: "/cancel で終了してください" を追加
     → 元の作業内容を含む
```

---

## 5. Self-Healing Loop

Edit ツール失敗時の自己修復サイクルは、web-format.mjs と edit-error-recovery.mjs の連携によって実現される。

### 問題の発生メカニズム

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Claude が Write/Edit でファイルを変更                  │
│                                                              │
│   Claude: Edit("app.tsx", old_string="...", new_string="...") │
│   → 成功                                                     │
│                                                              │
│ Step 2: PostToolUse Hook が web-format.mjs を実行             │
│                                                              │
│   web-format.mjs: npx prettier --write "app.tsx"              │
│   → Prettier がインデント・空白・改行を変更                    │
│                                                              │
│ Step 3: Claude が同じファイルに追加 Edit を試行                │
│                                                              │
│   Claude: Edit("app.tsx", old_string="<古い内容>", ...)       │
│   → 失敗! old_string が見つからない                           │
│     (Prettier がフォーマットを変えたため)                       │
└─────────────────────────────────────────────────────────────┘
```

### 自己修復サイクル

```
┌────────────────────────────────────────────────────────┐
│                                                         │
│  ┌─────────┐    ┌──────────┐    ┌───────────────────┐  │
│  │ Claude   │    │ Prettier │    │ edit-error-       │  │
│  │ Edit     │───>│ 自動     │    │ recovery.mjs      │  │
│  │ (失敗)   │    │ format   │    │ (PostToolUse)     │  │
│  └────┬─────┘    └──────────┘    └────────┬──────────┘  │
│       │                                    │             │
│       │  Edit 失敗を検出                    │             │
│       │<───────────────────────────────────┘             │
│       │                                                  │
│       │  additionalContext で注入:                        │
│       │  "Read ツールで現在の内容を読んでから                │
│       │   再度 Edit してください"                          │
│       │                                                  │
│       v                                                  │
│  ┌─────────┐                                             │
│  │ Claude   │                                             │
│  │ Read     │  ← 最新のフォーマット済み内容を取得           │
│  └────┬─────┘                                             │
│       │                                                  │
│       v                                                  │
│  ┌─────────┐                                             │
│  │ Claude   │                                             │
│  │ Edit     │  ← 正しい old_string で成功                  │
│  │ (成功)   │                                             │
│  └──────────┘                                             │
│                                                          │
└────────────────────────────────────────────────────────┘
```

### 失敗タイプ別の復旧ガイダンス

edit-error-recovery.mjs は Edit の出力メッセージを分析し、失敗タイプに応じた具体的なガイダンスを生成する:

| 失敗タイプ          | 検出パターン                             | ガイダンス                                                          |
| ------------------- | ---------------------------------------- | ------------------------------------------------------------------- |
| old_string 不一致   | `not found`, `no match`, `did not match` | "Read ツールで現在の内容を読んでから再度 Edit してください"         |
| old_string 複数一致 | `not unique`, `multiple`                 | "周辺コードをより多く含めて old_string を一意にしてください"        |
| ファイル不存在      | `does not exist`                         | "ファイルパスを確認してください。新規なら Write を使用してください" |

---

## 6. Pipeline as Code

### 概要

開発ワークフローを YAML ファイルとして宣言的に定義するシステム。`.claude/pipelines/` に配置され、feature-pilot 等のオーケストレータースキルが参照する。

### 4 つのパイプラインタイプ

| パイプライン       | ファイル              | 用途                       | Tier           |
| ------------------ | --------------------- | -------------------------- | -------------- |
| **NEW_FEATURE**    | `new-feature.yaml`    | 新機能をスクラッチから開発 | S / M / L / XL |
| **MODIFY_FEATURE** | `modify-feature.yaml` | 既存機能の差分修正         | S / M / L      |
| **BUG_FIX**        | `bug-fix.yaml`        | バグ修正 (Red->Green TDD)  | default (単一) |
| **INFRA_DEPLOY**   | `infra-deploy.yaml`   | インフラデプロイ           | S / M          |

### Tier ベース実行

プロジェクトの規模と複雑さに応じてステップ構成が変わる:

```
NEW_FEATURE パイプライン:

  Tier S (小規模):
    architect → spec → ui_approval → readiness_gate
    → implement → quality_gate → dod_verification

  Tier M (中規模):
    architect → constraints_load → discovery_lite → spec
    → ui_approval → readiness_gate → implement → wiring
    → status_sync → quality_gate → dod_verification

  Tier L/XL (大規模):
    architect → constraints_load → discovery_full → spec
    → ui_approval → readiness_gate → implement → wiring
    → status_sync → priority_calc → quality_gate → dod_verification
```

### Step 定義構造

各ステップは以下のフィールドを持つ:

```yaml
steps:
  implement:
    skill: feature-implementer # 実行する Skill
    model: sonnet # 使用する AI モデル
    tdd: true # TDD モード有効化
    batch_order: # 実行バッチ順序
      - name: 'Data Layer'
        parallel: true # 並列実行可能
        items: ['Type + Schema', 'API']
      - name: 'Logic Layer'
        parallel: false
        items: ['Custom Hook']
    retry:
      max: 3 # 最大リトライ回数
      fallback: null
    compensation: # 失敗時の補償アクション
      action: '失敗バッチのみ再実装'
      revert_to: implement
```

### Model Fallback

全パイプラインに共通のモデルフォールバック設定:

```
haiku → sonnet → opus

  Step 実行
    |
    v
  haiku で試行 (3 回失敗まで)
    |
    v (失敗)
  sonnet にエスカレーション (3 回失敗まで)
    |
    v (失敗)
  opus にエスカレーション (3 回失敗まで)
    |
    v (失敗)
  パイプライン中断 + エスカレーション
```

### Evidence Caching

パイプライン実行中の検証結果をキャッシュし、同一セッション内での繰り返し検証を最小化する:

```yaml
global:
  evidence_caching: true
  evidence_cache_path: '.claude/state/evidence-cache.json'
```

| 検証タイプ    | 有効時間 | 無効化条件                        |
| ------------- | -------- | --------------------------------- |
| lint          | 30 分    | `src/**/*` 変更時                 |
| test          | 30 分    | `test/**/*`, `src/**/*` 変更時    |
| security-scan | 1 時間   | `.env*` 変更時                    |
| build         | 1 時間   | `src/**/*`, `package.json` 変更時 |

### Compensation (補償アクション)

各ステップには失敗時の補償アクションが定義されている。これにより、パイプラインは部分的な失敗から回復可能:

```
implement ステップが失敗した場合:
  compensation:
    action: '失敗バッチのみ再実装（成功バッチは保持）'
    revert_to: implement

quality_gate ステップが失敗した場合:
  compensation:
    action: 'make q.fix 実行後、再検証'
    revert_to: quality_gate
```

---

## 7. Origins: oh-my-opencode -> oh-my-claude-code

### 背景

oh-my-opencode は [OpenCode](https://github.com/anthropics/opencode) エディタのプラグインとして開発された。OpenCode のプラグインシステムは Go ベースのエディタにインメモリで統合され、`session.prompt()` API でリアルタイムに AI セッションを制御できた。

oh-my-claude-code は、この設計思想とメカニズムを Claude Code の Hooks API に移植したものである。

### アーキテクチャ上の根本的差異

```
oh-my-opencode (Plugin)              oh-my-claude-code (Hooks)
┌─────────────────────┐              ┌─────────────────────────┐
│ Go プロセス内で動作   │              │ 独立 Node.js プロセス     │
│                      │              │ (毎回新規起動)            │
│ ┌──────────────┐     │              │                          │
│ │ In-Memory    │     │              │  ┌──────────────────┐    │
│ │ Map          │     │              │  │ .claude/state/   │    │
│ │ (storage.ts) │     │              │  │ JSON files       │    │
│ └──────────────┘     │              │  └──────────────────┘    │
│                      │              │                          │
│ session.prompt()     │              │  {"decision": "block",   │
│  → 直接注入          │              │   "reason": "..."}       │
│                      │              │  → Claude が reason を    │
│ session.idle event   │              │    continuation prompt    │
│  → コールバック       │              │    として解釈            │
│                      │              │                          │
│ session.todo()       │              │  countIncompleteTasks()  │
│  → タスク直接アクセス │              │  → ファイルシステム経由   │
│                      │              │                          │
│ 常駐プロセス          │              │  毎イベントで起動→終了    │
│  → 状態はメモリに保持 │              │  → 状態はファイルに永続化  │
└─────────────────────┘              └─────────────────────────┘
```

### コンポーネント対応表

| oh-my-opencode コンポーネント       | oh-my-claude-code 対応物              | 移植時の変更点                                              |
| ----------------------------------- | ------------------------------------- | ----------------------------------------------------------- |
| `ralph-loop` (session.idle handler) | `stop-handler.mjs` (Stop event)       | `session.prompt()` -> `{"decision":"block","reason":"..."}` |
| `todo-continuation-enforcer`        | `countIncompleteTasks()` in utils.mjs | `session.todo()` -> Task ファイル直接読み取り               |
| `stop-continuation-guard`           | `isUserAbort()` in utils.mjs          | `stoppedSessions Set` -> `stop_reason` パース               |
| `keyword-detector` plugin           | `keyword-detector.mjs` hook           | ロジック同一、I/O を stdin/stdout JSON に変更               |
| `edit-error-recovery` plugin        | `edit-error-recovery.mjs` hook        | 同上                                                        |
| `storage.ts` (In-Memory Map)        | `state.mjs` (File-based)              | アトミック書き込み追加、staleness チェック追加              |
| `session.prompt()` 注入             | `additionalContext` 注入              | 直接注入 -> Hook 規格経由の間接注入                         |
| HUD (状態表示バー)                  | `pre-tool-enforcer.mjs` (Sisyphus)    | UI バー -> テキストプレフィックスとして注入                 |
| Notepad システム                    | (削除)                                | 不要と判断して未移植                                        |
| Global 状態チェック                 | (削除)                                | local のみ使用                                              |

### 設計判断の根拠

**なぜファイルベースか**: Claude Code Hooks は毎イベントで新しい Node.js プロセスを起動する。インメモリ状態は保持できないため、ファイルシステムが唯一の永続化手段となる。

**なぜ `decision: "block"` か**: oh-my-opencode では `session.prompt()` で次のプロンプトを直接注入できた。Claude Code Hooks にはこの API がないため、Stop イベントの `block` decision と `reason` フィールドを continuation prompt として代用する。Claude は `reason` に含まれる指示を次のアクション指針として解釈する。

**なぜ Sisyphus パターンか**: oh-my-opencode では常駐プロセスが HUD (状態表示バー) を管理し、AI は常に現在の状態を視覚的に確認できた。Hooks ではこの UI がないため、PreToolUse イベントで毎回テキストベースの状態プレフィックスを注入することで同等の効果を実現する。
