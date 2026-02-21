# スキル テンプレート ガイド

> **目的**: 新規スキル作成時に MANIFEST 欠落を防止し一貫した構造を保証する標準テンプレート

## 📁 ディレクトリ 構造

```
_templates/
├── README.md           # このファイル
└── skill-template/
    ├── SKILL.md        # スキル定義文書テンプレート
    └── MANIFEST.json   # メタデータテンプレート
```

## 🚀 使用方法

### 1. ディレクトリ コピー

```bash
# 新規スキルディレクトリ作成
cp -r .claude/skills/_templates/skill-template .claude/skills/{{new-skill-name}}
```

### 2. プレースホルダー 置換

全ての `{{PLACEHOLDER}}`を実際の値で置き換えます。

**SKILL.md 必須プレースホルダー**:

| プレースホルダー        | 説明                      | 例                                    |
| ----------------------- | ------------------------- | ------------------------------------- |
| `{{SKILL_ID}}`          | スキル固有ID (kebab-case) | `flutter-qa`                          |
| `{{SKILL_NAME}}`        | スキル英文名              | `Flutter QA`                          |
| `{{SKILL_KOREAN_NAME}}` | スキル日本語名            | `Flutter 品質検査`                    |
| `{{SKILL_DESCRIPTION}}` | 簡単な説明 (1-2文)        | `Flutter プロジェクトのQAサイクル...` |
| `{{TRIGGER_KEYWORD_N}}` | トリガーキーワード        | `QA`, `品質検査`                      |

**MANIFEST.json 必須プレースホルダー**:

| プレースホルダー       | 説明                           | 有効値                                |
| ---------------------- | ------------------------------ | ------------------------------------- |
| `{{TIER}}`             | スキル階層                     | `1`, `2`, `3`                         |
| `{{TIER_DESCRIPTION}}` | 階層説明                       | `Orchestrator`, `Pipeline`, `Utility` |
| `{{PARENT_SKILL_N}}`   | このスキルを呼び出す上位スキル | `feature-pilot`                       |
| `{{CHILD_SKILL_N}}`    | このスキルが呼び出す下位スキル | `pre-quality-gate`                    |
| `{{OUTPUT_TYPE}}`      | 出力タイプ                     | `report`, `log`, `file`, `state`      |

### 3. 依存関係双方向参照確認

**重要**: `calls`と`called_by`は双方向で一致しなければなりません。

```
A.calls = ["B"]  →  B.called_by = ["A"]
```

例: `flutter-qa`が`pre-quality-gate`を呼び出す場合:

- `flutter-qa/MANIFEST.json`: `"calls": ["pre-quality-gate"]`
- `pre-quality-gate/MANIFEST.json`: `"called_by": ["flutter-qa"]`

### 4. バージョンスキーマ準拠

- 形式: `MAJOR.MINOR.PATCH`
- 例: `1.0.0`, `2.1.3`
- v 接頭辞なし (MANIFESTで)
- 変更履歴では`v1.0`形式使用可能

---

## 📋 チェックリスト

新規スキル生成時必ず確認:

- [ ] SKILL.md 生成済み
- [ ] MANIFEST.json 生成済み
- [ ] 全てのプレースホルダー置換済み
- [ ] tierが1, 2, 3のいずれか
- [ ] skill_versionがMAJOR.MINOR.PATCH形式
- [ ] calls ↔ called_by 双方向参照一致
- [ ] trigger_keywordsが2個以上

---

## 🔗 参照文書

- [GOVERNANCE.md](../GOVERNANCE.md) - ガバナンスルール
- [skill-health-check](../skill-health-check/SKILL.md) - 自動監査スキル

---

## Tier ガイド

| Tier | 名前         | 役割                             | 例                                        |
| :--: | ------------ | -------------------------------- | ----------------------------------------- |
|  1   | Orchestrator | 他のスキルを統制する最上位スキル | `feature-pilot`, `turbo-mode`             |
|  2   | Pipeline     | パイプラインの特定段階を担当     | `feature-implementer`, `pre-quality-gate` |
|  3   | Utility      | 独立実行可能な原子スキル         | `flutter-qa`, `security-scan`             |

---

**最終更新**: 2026-02-01
