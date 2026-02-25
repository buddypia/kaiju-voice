# Deep Research 統合マイグレーションガイド

## 📋 変更事項サマリー

**2026-02-04**: `openai-deep-research`と`google-deep-research`の2つのスキルを`deep-research`ひとつに統合しました。

### 以前の構造 (Deprecated)

```
.claude/skills/
├── openai-deep-research/     ❌ Deprecated
│   ├── SKILL.md
│   ├── MANIFEST.json
│   └── scripts/openai_deep_research.py
└── google-deep-research/      ❌ Deprecated
    ├── SKILL.md
    ├── MANIFEST.json
    └── scripts/google_deep_research.py
```

### 新しい構造

```
.claude/skills/
└── deep-research/             ✅ Active
    ├── SKILL.md
    ├── MANIFEST.json
    └── scripts/deep_research.py   (--provider フラグサポート)
```

---

## 🔄 マイグレーション方法

### スキル呼び出し変更

#### Before (Deprecated)

```bash
# OpenAI 使用
/openai-deep-research "AIゲームアプリのトレンド分析"

# Google 使用
/google-deep-research "日本市場AIゲームアプリ分析"
```

#### After (推奨)

```bash
# OpenAI プロバイダー選択
/deep-research --provider openai "AIゲームアプリのトレンド分析"

# Google プロバイダー選択
/deep-research --provider google "日本市場AIゲームアプリ分析"

# デフォルト値 (openai)
/deep-research "競合機能分析"
```

### SKILL.md 文書参照更新

#### Before

```markdown
| スキル                 | 用途                   | コスト |
| ---------------------- | ---------------------- | ------ |
| `openai-deep-research` | 深層分析、長文レポート | 高     |
| `google-deep-research` | 最新データ、幅広い検索 | 中     |
```

#### After

```markdown
| Provider | 用途                   | コスト | 使用法                            |
| -------- | ---------------------- | ------ | --------------------------------- |
| `openai` | 深層分析、長文レポート | 高     | `deep-research --provider openai` |
| `google` | 最新データ、幅広い検索 | 中     | `deep-research --provider google` |
```

### Python スクリプト呼び出し変更

#### Before

```bash
python .claude/skills/openai-deep-research/scripts/openai_deep_research.py "topic"
python .claude/skills/google-deep-research/scripts/google_deep_research.py "topic"
```

#### After

```bash
python .claude/skills/deep-research/scripts/deep_research.py --provider openai "topic"
python .claude/skills/deep-research/scripts/deep_research.py --provider google "topic"
```

---

## 🎯 Provider 選択ガイド

| 状況                 | 推奨 Provider | 理由                                    |
| -------------------- | :-----------: | --------------------------------------- |
| **学術的深層分析**   |   `openai`    | 構造化された長文レポートに強み          |
| **最新トレンド調査** |   `google`    | リアルタイムWeb検索基盤、最新性に優れる |
| **競合機能分析**     |   `google`    | 多様なソース収集に有利                  |
| **市場データ収集**   |   `google`    | 幅広い検索範囲                          |
| **概念確立リサーチ** |   `openai`    | 深みのある分析                          |
| **高速スキャン**     |   `google`    | 検索速度優秀                            |

### デフォルト動作

`--provider` フラグを省略すると **OpenAIがデフォルト**として使用されます。

```bash
# 以下2つのコマンドは同一
/deep-research "テーマ"
/deep-research --provider openai "テーマ"
```

---

## 🔗 依存関係更新チェックリスト

次のスキルのSKILL.mdでdeprecatedスキル参照が更新されました:

- [x] `research-gap-analyzer` - Provider 選択テーブルに変更
- [x] `market-intelligence-scanner` - Phase 3.1, 4.1 呼び出し構文更新
- [x] `priority-analyzer` - 関連スキルテーブル更新

MANIFEST.json 依存関係も同期されました:

- [x] `deep-research` - `called_by` フィールド追加
- [x] `research-gap-analyzer` - `calls`, `dependencies`, `external_tools` 更新
- [x] `market-intelligence-scanner` - `calls`, `dependencies`, `external_tools` 更新
- [x] deprecated スキル - `called_by` historical record 保存

---

## ⚠️ Deprecated スキル処理

### ステータス変更

`openai-deep-research`と`google-deep-research`は **Deprecated** ステータスに転換されました:

```json
{
  "status": "Deprecated",
  "deprecated_date": "2026-02-04",
  "superseded_by": "deep-research"
}
```

### SKILL.md 警告

各 deprecated スキルのSKILL.md上部に警告追加:

```markdown
> ⚠️ **DEPRECATED** - このスキルは deep-research スキルに統合されました。
> deep-research --provider openai|google を使用してください。
```

### 下位互換性

Deprecated スキルは **当分の間動作**しますが、近いうちに削除予定です:

- 現在: 動作するがdeprecation警告を出力
- 今後: スキルディレクトリ削除予定 (2026-03以降)

**推奨措置**: 全ての参照を`deep-research`に即座にマイグレーションしてください。

---

## 📚 追加参考文書

- [deep-research/SKILL.md](./SKILL.md) - 統合スキル使用法
- [deep-research/MANIFEST.json](./MANIFEST.json) - 依存関係グラフ
- [openai-deep-research/SKILL.md](../openai-deep-research/SKILL.md) - Deprecated
- [google-deep-research/SKILL.md](../google-deep-research/SKILL.md) - Deprecated

---

## ❓ FAQ

### Q1: なぜ統合したのですか?

**A**: 単一エントリポイント(CLI標準パターン)、メンテナンスコスト削減、コード重複除去が目的です。
`--provider` フラグ方式は業界標準(例: `aws`, `kubectl`)に従います。

### Q2: 既存のスキルはいつ削除されますか?

**A**: 2026-03以降削除予定です。全ての依存スキルがマイグレーション後に削除されます。

### Q3: 2つのproviderを同時に使用できますか?

**A**: 単一呼び出しでは1つのproviderのみ使用可能です。
比較が必要な場合は2回呼び出してください:

```bash
/deep-research --provider openai "テーマ" > openai_result.md
/deep-research --provider google "テーマ" > google_result.md
```

### Q4: 新しいproviderを追加できますか?

**A**: `scripts/deep_research.py`にproviderロジックを追加すれば可能です。
今後 Anthropic, Perplexity等追加の可能性があります。

### Q5: Smart Provider Selectionはどのように動作しますか?

**A**: Phase 4で追加された機能で、クエリ内容を分析して最適なProviderを自動選択します。
キーワードベースのスコア計算と使用パターン学習を組み合わせて段階的に精度が向上します。

```bash
# 自動選択
/deep-research --auto "最新AIトレンド"

# 戦略選択
/deep-research --strategy quality "深層分析"
```

### Q6: エラー発生時に自動的に他のProviderを試行しますか?

**A**: Phase 3で追加された`--enable-fallback`フラグを使用すれば可能です。
OpenAI失敗時にGoogleへ自動フォールバックされます。

```bash
/deep-research --provider openai --enable-fallback "テーマ"
```

---

## 🚀 Phase 3 & 4: 高度な機能追加 (2026-02-05)

### Phase 3: エラーハンドリング強化

**追加された機能**:

- **Retry ロジック**: 指数バックオフ (1s → 2s → 4s, 最大3回)
- **Graceful Degradation**: `--enable-fallback` フラグで自動フォールバック
- **Error History**: JSONベースのエラーロギング (`.claude/skills/deep-research/logs/`)
- **Enhanced Error Messages**: ユーザーフレンドリーなエラーメッセージ + 解決策

**使用例**:

```bash
# 自動フォールバック有効化
/deep-research --provider openai --enable-fallback "テーマ"
# OpenAI失敗時 → Googleへ自動再試行

# エラーログ確認
cat .claude/skills/deep-research/logs/error_history.json
```

**技術詳細**:

- Retry Decorator: `@retry_with_exponential_backoff(max_retries=3)`
- Circuit Breaker パターン: retryable vs non-retryable エラー区分
- Structured Logging: Python logging モジュール + JSON ファイル保存
- ErrorHistory クラス: 最近100件維持、タイムスタンプ/コンテキスト含む

### Phase 4: Smart Provider Selection

**追加された機能**:

- **キーワードベース自動選択**: クエリからキーワード抽出してProvider推奨
- **使用パターン学習**: 成功/失敗履歴記録 (`.claude/skills/deep-research/logs/usage_patterns.json`)
- **戦略選択**: `auto`, `quality`, `cost`, `manual` 4つのモード
- **設定ファイル**: `config.yaml`でキーワードルールのカスタマイズ

**新しいフラグ**:

```bash
--auto, -a              # Smart Provider Selection 有効化
--strategy STRATEGY     # 戦略選択 (auto/quality/cost/manual)
```

**使用例**:

```bash
# 自動選択 (キーワード分析)
/deep-research --auto "最新AIトレンド"
# → GOOGLE 自動選択 ("最新" キーワード認識)

/deep-research --auto "深層分析必要"
# → OPENAI 自動選択 ("深層", "分析" キーワード認識)

# 戦略選択
/deep-research --strategy quality "重要なリサーチ"  # OpenAI 優先
/deep-research --strategy cost "予算制限"        # Google 優先
```

**キーワードルール** (`config.yaml`):

- **OpenAI**: 深層、deep、分析、analysis、学術、academic、研究、research
- **Google**: 最新、latest、トレンド、trend、ニュース、news、市場、market

**学習メカニズム**:

1. 各実行後に結果(成功/失敗、レスポンス時間)記録
2. 最近100件の履歴維持
3. 最小10件以上のデータ蓄積時に学習開始
4. 成功率の高いProviderを優先推奨

### アップグレードガイド

**既存ユーザー**:

```bash
# 既存方式 (依然として動作)
/deep-research --provider openai "テーマ"

# 新方式 (推奨)
/deep-research --auto "テーマ"
```

**新しい依存関係**:

```bash
pip install pyyaml  # config.yaml パース用
```

### テストカバレッジ

Phase 3 & 4 追加で **14個のテスト** 作成:

- Provider 選択ロジック: 5個
- 依存関係チェック: 2個
- 統合シナリオ: 3個
- エラーハンドリング: 4個

```bash
# テスト実行
cd .claude/skills/deep-research/tests
./run_tests.sh
```

---

**マイグレーション完了日**: 2026-02-04 (Phase 1-2), 2026-02-05 (Phase 3-4)
**文書バージョン**: 2.0
