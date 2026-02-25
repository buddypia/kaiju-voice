# {{OSS_NAME}} — Reconnaissance

> **分析日**: {{ANALYSIS_DATE}}
> **分析者**: oss-analyzer v4.0
> **方法論**: C4 lightweight + Problem Discovery (PDR Phase 1)

---

## Part A: OSS Context

### プロジェクト正体性

**プロジェクト名**: {{OSS_NAME}}
**リポジトリ**: {{REPOSITORY_URL}}
**一行要約**: {{ONE_LINE_SUMMARY}}

### 技術スタック

| 項目             | 値                   |
| ---------------- | -------------------- |
| Primary Language | {{LANGUAGE}}         |
| Runtime          | {{RUNTIME}}          |
| Package Manager  | {{PACKAGE_MANAGER}}  |
| 核心依存性       | {{KEY_DEPENDENCIES}} |

### ディレクトリ構造

```
{{DIRECTORY_TREE}}
```

### 核心モジュール TOP 5

| #   | モジュール | 役割 | Import 回数 | 核心度 |
| --- | ---------- | ---- | :---------: | :----: |

{{TOP_5_MODULES}}

### Entry & Extension Points

**Entry Points**:
{{ENTRY_POINTS}}

**Extension Points**:
{{EXTENSION_POINTS}}

---

## Part B: Problem Registry (プロジェクト)

> 以下は プロジェクトの Pain Pointsを構造化した Problem 一覧です。
> 各 Problemには **Forces(衝突する制約)**が最小 2個定義されます。

### Problem: {{PROBLEM_1_ID}} — {{PROBLEM_1_TITLE}}

**Statement**: {{PROBLEM_1_STATEMENT}}

**Forces** (衝突する制約):

- **F1**: {{FORCE_1}} — Evidence: {{EVIDENCE_1}}
- **F2**: {{FORCE_2}} — Evidence: {{EVIDENCE_2}}
- _({{WHY_FORCES_CONFLICT}})_

**Current State**: {{CURRENT_STATE}}

### Problem: {{PROBLEM_2_ID}} — {{PROBLEM_2_TITLE}}

...

---

## Part C: Problem-Module Hypothesis

> OSS モジュールがどの Problemを解決できるか仮説を立てます。
> Phase 2で仮説にマッピングされたモジュールを **優先探索**します。

| Problem | OSS モジュール (仮説) | 根拠 | Phase 2 優先順位 |
| ------- | --------------------- | ---- | :--------------: |

{{HYPOTHESIS_MATRIX}}

---

## 統計

| 指標                  | 値                   |
| --------------------- | -------------------- |
| 総ファイル数          | {{TOTAL_FILES}}      |
| ソースコードファイル  | {{CODE_FILES}}       |
| 文書ファイル          | {{DOC_FILES}}        |
| 定義された Problem 数 | {{PROBLEM_COUNT}}    |
| 仮説マッピング数      | {{HYPOTHESIS_COUNT}} |

---

**次へ**: [decisions.md](./decisions.md) — Decision Archaeology
