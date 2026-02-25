# OSS Analyzer v4.0

> OSS プロジェクトから**我々の問題（Problem）に対する設計決定（Decision）を逆追跡**し、具体的な適用**レシピ（Recipe）**を導出するスキル

## Quick Start

```bash
# OSS 分析
/oss-analyzer --source oss-sources/<OSS名>/

# 特定問題に集中
/oss-analyzer --source oss-sources/<OSS名>/ --problem P-HOOK-01

# 特定領域に集中
/oss-analyzer --source oss-sources/<OSS名>/ --focus hooks

# キャッシュ無視して再分析
/oss-analyzer --source oss-sources/<OSS名>/ --force
```

---

## 方法論: Problem-Decision-Recipe (PDR)

5つの業界標準を組み合わせたハイブリッドフレームワーク:

| Phase                | 方法論                                 | 質問                           |
| -------------------- | -------------------------------------- | ------------------------------ |
| Reconnaissance       | C4 lightweight + **Problem Discovery** | 「我々の問題は何か？」         |
| Decision Archaeology | ADR + **Forces** + GoF                 | 「なぜこの方式で解決したか？」 |
| Adoption Engineering | ATAM-lite + TW Radar + **Recipe**      | 「どのように適用するか？」     |

**v3 → v4 核心転換**:

```
v3: OSS スキャン → Mechanism 発見 → 抽象的評価 → 適用 0
v4: 我々の Problem → OSS で Decision 逆追跡 → 具体的 Recipe → 適用追跡
```

---

## 出力結果

```
docs/oss/{oss-name}/v4/
├── reconnaissance.md   # OSS Context + Problem Registry + Hypothesis
├── decisions.md        # Decision Archaeology (Forces + Alternatives + Mechanism)
└── adoption.md         # Adoption Decisions + Recipes (Pseudocode)
```

**核心確認ポイント**: `adoption.md` の Recipes

| Decision   | 意味         | Recipe  |
| ---------- | ------------ | ------- |
| **Adopt**  | 即時適用推奨 | ✅ 必須 |
| **Trial**  | 非コアで試行 | ✅ 必須 |
| **Assess** | 調査価値あり | 選択的  |
| **Hold**   | 現在不適合   | 不要    |

---

## オプション

| オプション        | 説明                                       | 必須 |
| ----------------- | ------------------------------------------ | :--: |
| `--source <path>` | OSS ソースパス                             |  ✅  |
| `--problem <id>`  | 特定 Problem に集中                        |      |
| `--focus <area>`  | 特定領域に集中                             |      |
| `--oss-only`      | OSS スキャンのみ（Problem Discovery 省略） |      |
| `--force`         | キャッシュ無視して再分析                   |      |

---

## 使用シナリオ

### 新規 OSS 分析

```bash
# 1. oss-sources/ にソース配置
cp -r ~/Downloads/new-oss oss-sources/new-oss/

# 2. 分析実行
/oss-analyzer --source oss-sources/new-oss/

# 3. 結果確認（Recipes から）
cat docs/oss/new-oss/v4/adoption.md
```

### 特定問題に対する OSS ソリューション探索

```bash
/oss-analyzer --source oss-sources/<OSS名>/ --problem P-HOOK-04
```

### カタログ確認

```bash
cat docs/oss/_catalog/catalog.json
```

---

## 特徴

- **Problem-First**: 「何があるか？」ではなく「我々の問題は何か？」から開始
- **Forces**: 衝突する制約を明示して「なぜこの方式か」深さを提供
- **Alternatives**: すべての Decision に代替案最低1個（批判的思考保証）
- **Recipe**: Pseudocode + Verification + Rollback（行動可能な成果物）
- **READ-ONLY**: コード修正なし
- **シンボル中心**: 行番号ではなく関数名/クラス名で識別

---

## 注意事項

- 分析結果に実際の Dart/言語別実装コードは含まれない（Pseudocode のみ）
- 「根拠のない抽象的判断」禁止
- 「代替案のない Decision」禁止（Alternative Blindness）
- 「衝突のない Forces」禁止（Shallow Forces）
- 既存 v1/v2/v3 成果物は `archive/` ディレクトリに保管

---

**Version**: v4.0.0 | **Methodology**: PDR (ADR+Forces+ATAM+TW Radar+Recipe) | [SKILL.md](./SKILL.md)
