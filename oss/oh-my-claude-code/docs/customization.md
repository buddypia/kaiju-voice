# カスタマイズガイド

oh-my-claude-code をプロジェクトに合わせてカスタマイズする方法。

## 目次

1. [Hook の選択的有効化](#hook-の選択的有効化)
2. [キーワード追加・変更](#キーワード追加変更)
3. [QA コマンドの変更](#qa-コマンドの変更)
4. [Pipeline のカスタマイズ](#pipeline-のカスタマイズ)
5. [フォーマッターの変更](#フォーマッターの変更)
6. [安全パラメータの調整](#安全パラメータの調整)

---

## Hook の選択的有効化

すべての Hook を使う必要はありません。`settings.json` から不要な Hook を削除するだけです。

### 最小構成 (Persistent Mode のみ)

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "node \"$CLAUDE_PROJECT_DIR\"/.claude/scripts/keyword-detector.mjs"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "node \"$CLAUDE_PROJECT_DIR\"/.claude/scripts/stop-handler.mjs",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

### 推奨構成 (自動継続 + 自己修復)

上記に加えて:

- `SessionStart` → session-start.mjs (セッション復元)
- `PostToolUse[Edit]` → edit-error-recovery.mjs (Edit 修復)
- `PreCompact` → compact-context-preserver.mjs (コンテキスト保存)

### フル構成

`settings.json` をそのまま使用。

---

## キーワード追加・変更

### 新しいキーワードを追加

`keyword-detector.mjs` の `KEYWORD_DEFINITIONS` 配列に追加:

```javascript
// 既存の定義の後に追加
{
  name: 'deploy',
  skill: 'deploy',
  intentPatterns: [
    /デプロイして/,
    /デプロイ\s*(して|してください|開始)/,
    /\b(deploy)\b/i,
  ],
  mentionPatterns: [
    /デプロイ/,
  ],
  negativeContext: [
    /デプロイ[はがのを]/,
    /デプロイ\s*(手順|方法|設定)[はがのをに]/,
  ],
  createsState: false,
},
```

### キーワードの優先順位を変更

`KEYWORD_DEFINITIONS` 配列内の順序 = 優先順位。
上にあるものほど高優先。

### 競合解決ルールを追加

`resolveConflicts()` 関数に条件を追加:

```javascript
// 例: deploy と feature-pilot が同時にマッチしたら feature-pilot 優先
if (names.includes('feature-pilot') && names.includes('deploy')) {
  resolved = resolved.filter((k) => k.name !== 'deploy');
}
```

---

## QA コマンドの変更

### 環境変数で設定

```bash
# .env または shell
export CLAUDE_QA_ANALYZE_CMD="npm run lint"
export CLAUDE_QA_TEST_CMD="npm test"
```

### プロジェクト別の例

| プロジェクト | ANALYZE_CMD         | TEST_CMD        |
| ------------ | ------------------- | --------------- |
| Next.js      | `npm run lint`      | `npm test`      |
| Python       | `ruff check .`      | `pytest`        |
| Rust         | `cargo clippy`      | `cargo test`    |
| Go           | `golangci-lint run` | `go test ./...` |
| Flutter      | `flutter analyze`   | `flutter test`  |

### Transcript パターンの拡張

`transcript.mjs` の `ANALYZE_PASS_PATTERNS` / `TEST_PASS_PATTERNS` に
プロジェクト固有のパターンを追加:

```javascript
// 例: pytest 用
const TEST_PASS_PATTERNS = [
  // ...既存パターン
  /\d+ passed/i,
  /all tests passed/i,
];
```

---

## Pipeline のカスタマイズ

### Tier の調整

`pipelines/new-feature.yaml` で各 Tier のステップを変更:

```yaml
tiers:
  S:
    - spec
    - implement
    - quality_gate
  M:
    - spec
    - implement
    - quality_gate
    - dod_verification
```

### ステップの追加

```yaml
steps:
  my_custom_step:
    skill: my-custom-skill
    model: sonnet
    outputs:
      - my-output.md
    retry:
      max: 2
    compensation:
      action: '出力を削除して再実行'
      revert_to: my_custom_step
```

### Quality Gate コマンドの変更

```yaml
quality_gate:
  checks:
    - lint_analyze
    - test
  retry:
    auto_fix_command: 'make fix' # プロジェクトに合わせて変更
```

### Model Fallback の変更

```yaml
global:
  model_fallback:
    enabled: true
    order: [haiku, sonnet, opus]
    max_failures_before_escalation: 3 # 3回失敗でモデル昇格
```

---

## フォーマッターの変更

### Prettier 以外を使う

`hooks/web-format.mjs` の `runPrettier()` を変更:

```javascript
// Biome を使う場合
function runFormatter(filePath) {
  execSync(`npx --no-install biome format --write "${filePath}"`, {
    timeout: 10000,
    stdio: ['pipe', 'pipe', 'pipe'],
  });
}
```

### 対象拡張子の変更

```javascript
const FORMATTABLE_EXTENSIONS = new Set([
  '.js',
  '.jsx',
  '.ts',
  '.tsx',
  // プロジェクトに合わせて追加/削除
  '.py', // Black for Python
  '.rs', // rustfmt for Rust
]);
```

### フォーマットを無効化

`settings.json` から `web-format.mjs` の Hook を削除するだけ。

---

## 安全パラメータの調整

### Persistent Mode

`keyword-detector.mjs`:

```javascript
defaultState: {
  active: true,
  iteration: 0,
  max_iterations: 20,  // 最大 iteration 数 (デフォルト: 20)
}
```

### Turbo Mode

```javascript
defaultState: {
  active: true,
  reinforcement_count: 0,
  max_reinforcements: 30,  // 最大 reinforcement 数 (デフォルト: 30)
}
```

### QA Mode

```javascript
defaultState: {
  active: true,
  cycle: 0,
  max_cycles: 10,  // 最大サイクル数 (デフォルト: 10)
}
```

### 同一エラー閾値

`stop-handler.mjs`:

```javascript
const SAME_ERROR_THRESHOLD = 3; // 同一エラー繰り返し許容回数
```

### Staleness タイムアウト

`lib/state.mjs`:

```javascript
const DEFAULT_STALE_MS = 24 * 60 * 60 * 1000; // 24時間 (デフォルト)
```

---

## Tips

### 1. Hook のデバッグ

各 Hook は `console.error()` でログを出力します。
Claude Code のログで確認できます。

### 2. 状態のリセット

```bash
# 全モードの状態をリセット
rm -f .claude/state/*.json
```

### 3. 特定モードだけリセット

```bash
rm -f .claude/state/persistent-state.json
```

### 4. settings.json のバリデーション

JSON の構文エラーがあると全 Hook が動作しません。
変更後は必ず JSON バリデーションを行ってください:

```bash
python3 -c "import json; json.load(open('.claude/settings.json'))"
```
