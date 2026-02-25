# Skills Directory

プロジェクト プロジェクトのAIスキル定義を管理するディレクトリです。

---

## 階層分類 (Tier System)

スキルはFeature-Firstアーキテクチャ原則に従い3つの階層に分類されます。

### Tier 1: Orchestrator (オーケストレーター)

> **役割**: ユーザーリクエストの単一エントリーポイント、下位スキル調整
> **MANIFEST.json**: 必須

| スキル                        | 役割                                                                 |
| ----------------------------- | -------------------------------------------------------------------- |
| `feature-pilot`               | すべての開発リクエストの最上位エントリーポイント、作業タイプ自動判別 |
| `market-intelligence-scanner` | 市場分析基盤の機能候補生成パイプライン                               |
| `research-gap-analyzer`       | リサーチギャップ分析および自動ディープリサーチパイプライン           |

### Tier 2: Pipeline (パイプライン)

> **役割**: 特定ワークフローの実行、複数ステップで構成
> **MANIFEST.json**: コアスキルに推奨

| スキル                   | 役割                                   | MANIFEST |
| ------------------------ | -------------------------------------- | :------: |
| `feature-architect`      | CONTEXT.json生成、意図分析             |    ✅    |
| `feature-spec-generator` | SPEC.md + Screen文書生成               |    ✅    |
| `feature-spec-updater`   | 既存SPEC修正                           |    ✅    |
| `ui-approval-gate` ★     | SPEC生成後UIワイヤーフレーム承認ゲート |    ✅    |
| `feature-implementer`    | SPEC基盤TDDコード実装                  |    ✅    |
| `feature-wiring`         | データソース + ナビゲーション統合連携  |    ✅    |
| `feature-status-sync`    | CONTEXT.json ↔ index.md同期            |    ✅    |
| `bug-fix`                | バグ分析およびTDD基盤修正              |    ✅    |
| `priority-analyzer`      | AI-Adjusted WSJF Lite優先順位分析      |    ✅    |
| `pre-quality-gate`       | 品質検証 (Makefile q.check実行)        |    ✅    |

### Tier 3: Utility (ユーティリティ)

> **役割**: 単一作業実行、独立的
> **MANIFEST.json**: 不要

大部分のスキルがこの階層に属します:

- `arb-sync`, `migration-sync`, `test-coverage-check`
- `hardcoded-scan`, `hardcoded-text-finder`, `hardcoded-color-finder`
- `edge-function-validator`, `spec-validator`, `glossary-updater`
- `google-deep-research`, `openai-deep-research`
- その他...

---

## 依存性グラフ

```
                         ┌──────────────────┐
                         │  feature-pilot   │ (Tier 1 Orchestrator)
                         └────────┬─────────┘
                                  │ calls
     ┌──────────┬─────────┬───────┼───────┬─────────┬──────────┬──────────┐
     ↓          ↓         ↓       ↓       ↓         ↓          ↓          ↓
┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌───────┐┌───────┐┌─────────┐┌─────────┐
│feature- ││feature- ││feature- ││ui-     ★││feature││feature││bug-fix  ││pre-     │
│architect││spec-    ││spec-    ││approval-││implem-││wiring ││         ││quality- │
│         ││generator││updater  ││gate     ││enter  ││       ││         ││gate     │
└────┬────┘└────┬────┘└─────────┘└────┬────┘└───────┘└───────┘└─────────┘└─────────┘
     │ calls    │                     │ calls (必須)
     └──────────┘                     ↓
                              ┌─────────────┐
                              │wireframe-   │ (Tier 3)
                              │manager      │
                              └─────────────┘

                    ┌──────────────────┐     ┌──────────────────┐
                    │priority-analyzer │ ←── │feature-status-   │
                    │                  │     │sync              │
                    └────────┬─────────┘     └──────────────────┘
                             │ calls
                             ↓
                    ┌──────────────────┐
                    │research-gap-     │ (Tier 1 Orchestrator)
                    │analyzer          │
                    └────────┬─────────┘
                             │ calls
              ┌──────────────┴──────────────┐
              ↓                             ↓
       ┌─────────────┐              ┌─────────────┐
       │openai-deep- │              │google-deep- │
       │research     │              │research     │
       └─────────────┘              └─────────────┘

                    ┌────────────────────┐
                    │market-intelligence-│ (Tier 1 Orchestrator)
                    │scanner             │
                    └────────┬───────────┘
                             │ calls
              ┌──────────────┼──────────────┐
              ↓              ↓              ↓
       ┌─────────────┐┌─────────────┐┌─────────────┐
       │feature-     ││google-deep- ││(候補承認時) │
       │architect    ││research     ││feature-pilot│
       └─────────────┘└─────────────┘└─────────────┘
```

### 状態遷移フロー

```
Idle → Briefing → SpecDrafting → UiApproval → Implementing → SyncingStatus → Reviewing → Done
          ↑             ↑              ↑              ↑               ↑
    feature-      feature-       ui-approval-  feature-      feature-status-
    architect     spec-gen       gate ★        implementer   sync / bug-fix
                  /updater                     /wiring
```

---

## MANIFEST.json

コアスキル(Tier 1 + Tier 2主要スキル)は`MANIFEST.json`ファイルで依存性と契約を明示します。

### スキーマ

- **位置**: `.claude/skills/_schemas/skill-manifest-schema.json`
- **検証**: `python -c "import json; from jsonschema import validate; ..."`

### 必須フィールド

| フィールド       | 説明                                         |
| ---------------- | -------------------------------------------- |
| `schema_version` | スキーマバージョン (現在 `1`)                |
| `skill_id`       | スキル固有識別子 (kebab-case)                |
| `tier`           | 階層 (1, 2, 3)                               |
| `public_api`     | ユーザー呼び出し可否およびトリガーキーワード |

### 選択フィールド

| フィールド     | 説明                           |
| -------------- | ------------------------------ |
| `dependencies` | 必須/選択的依存スキル          |
| `called_by`    | このスキルを呼び出す上位スキル |
| `calls`        | このスキルが呼び出す下位スキル |
| `outputs`      | 成果物リスト                   |
| `ssot_files`   | 管理するSSOTファイル           |

---

## Deprecatedスキル

以下のスキルは統合スキルに置き換えられました:

| Deprecated                  | 代替スキル       | 理由                      |
| --------------------------- | ---------------- | ------------------------- |
| `feature-data-wiring`       | `feature-wiring` | データ/ナビゲーション統合 |
| `feature-navigation-wiring` | `feature-wiring` | データ/ナビゲーション統合 |

DeprecatedスキルのSKILL.md上部には以下の警告が含まれます:

```markdown
> ⚠️ **DEPRECATED**: このスキルは`feature-wiring`に統合されました。
```

---

## スキルファイル構造

```
.claude/skills/
├── _schemas/
│   └── skill-manifest-schema.json  # MANIFESTスキーマ
├── README.md                       # このファイル
├── <skill-name>/
│   ├── SKILL.md                    # スキル定義 (必須)
│   ├── MANIFEST.json               # 依存性仕様 (Tier 1-2コア)
│   ├── assets/                     # 状態ファイル (選択)
│   └── references/                 # 参照文書 (選択)
└── ...
```

---

## 検証方法

### MANIFEST.jsonスキーマ検証

```bash
python3 -c "
import json, glob
from jsonschema import validate

with open('.claude/skills/_schemas/skill-manifest-schema.json') as f:
    schema = json.load(f)

for manifest in glob.glob('.claude/skills/*/MANIFEST.json'):
    with open(manifest) as f:
        validate(json.load(f), schema)
    print(f'✅ {manifest}')
"
```

### 依存性一貫性検証 (手動)

1. Aの`dependencies.required`にBがあれば、Bの`called_by`にAがあるべき
2. Aの`calls`にBがあれば、Bの`called_by`にAがあるべき
3. 循環依存性がないことを確認

---

## 変更履歴

| 日付       | 変更内容                                                                            |
| ---------- | ----------------------------------------------------------------------------------- |
| 2026-02-01 | ui-approval-gate追加 - SPEC生成後UI承認ゲート (Step 2.5), wireframe-manager必須依存 |
| 2026-02-01 | 初期バージョン - Tier System, MANIFEST.jsonスキーマ導入                             |
