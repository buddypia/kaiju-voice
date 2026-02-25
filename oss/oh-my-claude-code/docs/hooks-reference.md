# Hooks リファレンス

oh-my-claude-code が提供する全 Hook スクリプトの詳細リファレンス。

## 一覧

| #   | ファイル                              | イベント                 | 目的                      |
| --- | ------------------------------------- | ------------------------ | ------------------------- |
| 1   | `scripts/session-start.mjs`           | SessionStart             | 前セッション状態の復元    |
| 2   | `scripts/keyword-detector.mjs`        | UserPromptSubmit         | 自然言語 → Skill 起動     |
| 3   | `scripts/pre-tool-enforcer.mjs`       | PreToolUse               | 状態リマインダー注入      |
| 4   | `scripts/qa-write-guard.mjs`          | PreToolUse (Edit/Write)  | 品質ゲート                |
| 5   | `scripts/merge-guard.mjs`             | PreToolUse (Bash)        | git merge 安全チェック    |
| 6   | `hooks/edit-error-recovery.mjs`       | PostToolUse (Edit)       | Edit 失敗自己修復         |
| 7   | `hooks/web-format.mjs`                | PostToolUse (Write/Edit) | Prettier 自動フォーマット |
| 8   | `scripts/stop-handler.mjs`            | Stop / SubagentStop      | モード別継続/停止判定     |
| 9   | `hooks/compact-context-preserver.mjs` | PreCompact               | コンテキスト保存          |

---

## 1. session-start.mjs

**イベント**: `SessionStart`
**タイムアウト**: 10秒

### 動作

1. `.claude/state/` から全モードの状態ファイルを読み取り
2. アクティブモードがあれば復元メッセージを生成
3. セッション所有権をチェック (compact/resume は引き継ぎ許可)
4. 未完了 Task カウントを確認
5. `additionalContext` で復元メッセージを注入

### モード別復元メッセージ

- **Persistent**: iteration 進行状況 + 元の作業内容
- **QA**: cycle 進行状況 + 実行すべきコマンド
- **Turbo**: reinforcement カウント + 元の作業内容

### 出力例

```json
{
  "continue": true,
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "<session-restore>\n[PERSISTENT MODE RESTORED]\n前のセッションで有効化された...\n</session-restore>"
  }
}
```

---

## 2. keyword-detector.mjs

**イベント**: `UserPromptSubmit`
**バージョン**: v2.1

### 動作

1. stdin から JSON でプロンプトを受信
2. `cleanPromptForMatching()` でノイズ除去 (コードブロック、テーブル、引用等)
3. 2層パターンマッチング (`intentPatterns` → `mentionPatterns`)
4. 否定文脈チェック (「〜について」「〜とは」等は拒否)
5. 競合解決 (優先順位ベース)
6. 状態ファイル生成 (createsState: true のモード)
7. Skill 呼び出しメッセージを `additionalContext` で注入

### 前処理で除去されるもの

- フェンスドコードブロック (\`\`\`...\`\`\`)
- インラインコード (\`...\`)
- Markdown テーブル行
- Markdown 引用文
- 括弧内容 ((), 「」, [])
- ボールド/イタリック内部
- ファイルパスパターン
- JSON/設定リテラル

### キーワード追加方法

`KEYWORD_DEFINITIONS` 配列に追加:

```javascript
{
  name: 'my-skill',           // 識別名
  skill: 'my-skill',          // 起動する Skill 名
  intentPatterns: [            // 動詞/命令形 (即時起動)
    /スキル実行して/,
    /\b(my-skill)\b/i,
  ],
  mentionPatterns: [           // 名詞形 (否定文脈チェック後に起動)
    /スキル/,
  ],
  negativeContext: [           // この文脈なら起動しない
    /スキル[はがのを]/,
  ],
  exclusive: false,            // true = 他のマッチを無視
  createsState: false,         // true = 状態ファイルを作成
  stateFile: 'my-skill',      // createsState: true の場合
  defaultState: {              // createsState: true の場合
    active: true,
    iteration: 0,
  },
}
```

---

## 3. pre-tool-enforcer.mjs (Sisyphus)

**イベント**: `PreToolUse`
**タイムアウト**: 5秒

### 動作

1. アクティブモードの状態を読み取り
2. 未完了 Task カウントを取得
3. 状態プレフィックスを生成 (`[PERSISTENT 3/20 | TURBO #5 | Tasks: 2]`)
4. ツール別最適化ヒントを追加
5. `additionalContext` でリマインダーを注入

### ツール別ヒント

| ツール     | ヒント                                 |
| ---------- | -------------------------------------- |
| Bash       | 並列実行可能なコマンドは同時に呼び出し |
| Task       | 独立作業は並列エージェントで実行       |
| Edit/Write | 変更後の動作確認 + lint/test通過確認   |
| Read       | 関連ファイルは並列で読む               |
| Grep/Glob  | 複数検索は並列で実行                   |

### アクティブモードがなければ

何も注入せずパススルー (`{ continue: true }`)。

---

## 4. qa-write-guard.mjs

**イベント**: `PreToolUse` (matcher: `Edit|Write`)
**タイムアウト**: 5秒

### 動作

Edit/Write 実行前に品質関連のガードチェックを実行。

---

## 5. merge-guard.mjs

**イベント**: `PreToolUse` (matcher: `Bash`)
**タイムアウト**: 5秒

### 動作

git merge 系コマンドの実行前に、staged changes の有無をチェック。

---

## 6. edit-error-recovery.mjs

**イベント**: `PostToolUse` (matcher: `Edit`)
**タイムアウト**: 5秒

### 動作

1. Edit ツールの出力を受信
2. 失敗パターンを検出 (`is not unique`, `was not found`, `does not exist` 等)
3. 失敗タイプに応じた復旧ガイダンスを生成
4. `additionalContext` で Claude に「Read してから再 Edit」を促す

### 失敗タイプ別ガイダンス

| タイプ         | 原因                          | ガイダンス                             |
| -------------- | ----------------------------- | -------------------------------------- |
| not found      | Prettier 等によるファイル変更 | Read で最新内容を取得してから再 Edit   |
| not unique     | 複数箇所マッチ                | 周辺コードを含めて old_string を一意に |
| does not exist | ファイルなし                  | パス確認、新規なら Write 使用          |

---

## 7. web-format.mjs

**イベント**: `PostToolUse` (matcher: `Write|Edit`)
**タイムアウト**: 10秒

### 動作

1. Write/Edit の `tool_input.file_path` を取得
2. フォーマット対象拡張子かチェック
3. `npx --no-install prettier --write` を実行
4. Prettier 未インストールでも安全にスキップ

### 対象拡張子

`.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs`, `.json`, `.css`, `.scss`, `.sass`, `.less`, `.html`, `.md`, `.mdx`, `.yaml`, `.yml`

### 除外

- `.min.js`, `.min.css` (minified)
- `.map` (sourcemap)

---

## 8. stop-handler.mjs

**イベント**: `Stop` / `SubagentStop`
**タイムアウト**: 15秒

### 動作

1. Safety Gate チェック (4段階)
2. アクティブモード検出
3. モード別ハンドラー実行
4. 継続判定: `{ decision: "block", reason: "..." }` または `{}`

### Safety Gates (順序)

1. **Context Limit** → `{}` (即時停止許可)
2. **User Cancel** → `{}` (即時停止許可)
3. **Same Error ×3** → `{ decision: "block", reason: "構造的問題..." }` (強制中断)
4. **Mode Handler** → モード別判定

### Persistent Handler

- `<promise>DONE</promise>` 検出 → 正常終了
- Plan チェックボックス全完了 → 正常終了
- Max iterations 到達 → 正常終了
- 上記以外 → block + continuation prompt

### QA Handler

- Transcript で analyze pass + test pass → 正常終了
- `<promise>QA_COMPLETE</promise>` 検出 → 正常終了
- `all_passing: true` in state → 正常終了
- Max cycles 到達 → 正常終了
- 上記以外 → block + 失敗詳細

### Turbo Handler

- Max reinforcements 到達 → 正常終了
- 上記以外 → block + Task カウント

---

## 9. compact-context-preserver.mjs

**イベント**: `PreCompact`

### 動作

Context 圧縮前に7つの核心コンテキストを自動保存:

1. Git ブランチ + 最近5コミット
2. 変更ファイルリスト (staged + unstaged)
3. アクティブモード状態 (進行状況付き)
4. 未完了タスク一覧
5. 最近のエラー履歴
6. Plan ファイル進行状態
7. 作業ディレクトリコンテキスト

### 出力例

```json
{
  "hookSpecificOutput": {
    "additionalContext": "# Compaction Context (自動保存)\n\n## Git 状態\n- ブランチ: feature/xxx\n..."
  }
}
```
