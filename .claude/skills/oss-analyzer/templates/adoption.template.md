# {{OSS_NAME}} — Adoption

> **分析日**: {{ANALYSIS_DATE}}
> **分析者**: oss-analyzer v4.0
> **方法論**: Adoption Engineering (ATAM-lite + TW Radar + Recipe)

---

## Executive Summary

**分析対象**: {{OSS_NAME}}
**発見された Decision**: {{DECISION_COUNT}}個
**定義された Problem**: {{PROBLEM_COUNT}}個

### Adoption Decision 分布

| Decision |        数        | Decision 一覧   |
| -------- | :--------------: | --------------- |
| Adopt    | {{ADOPT_COUNT}}  | {{ADOPT_LIST}}  |
| Trial    | {{TRIAL_COUNT}}  | {{TRIAL_LIST}}  |
| Assess   | {{ASSESS_COUNT}} | {{ASSESS_LIST}} |
| Hold     |  {{HOLD_COUNT}}  | {{HOLD_LIST}}   |

### 核心発見

{{KEY_FINDINGS}}

---

## Context Comparison

| 属性         | {{OSS_NAME}}    | プロジェクト            |   Gap   |
| ------------ | --------------- | ------------------------ | :-----: |
| Language     | {{OSS_LANG}}    | TypeScript/Next.js             | {{GAP}} |
| Runtime      | {{OSS_RUNTIME}} | Mobile (iOS/Android)     | {{GAP}} |
| Architecture | {{OSS_ARCH}}    | Feature-First + React Hooks | {{GAP}} |
| Scale        | {{OSS_SCALE}}   | Solo dev + AI assisted   | {{GAP}} |
| Backend      | {{OSS_BACKEND}} | Supabase (PostgreSQL)    | {{GAP}} |
| Hook System  | {{OSS_HOOKS}}   | Claude Code Hooks (.mjs) | {{GAP}} |
| Deployment   | {{OSS_DEPLOY}}  | App Store releases       | {{GAP}} |

---

## Adoption Decisions

### {{DECISION_1_NAME}}

- **Decision**: {{ADOPT_TRIAL_ASSESS_HOLD}}
- **Context Fit**: {{FIT}}
- **Impact**: {{IMPACT}}
- **Problem**: {{PROBLEM_REF}}
- **Rationale**: {{RATIONALE}}

### {{DECISION_2_NAME}}

...

---

## Impact × Fit Matrix

```
              High Fit      Medium Fit     Low Fit
High Impact │ {{CELL}}     │ {{CELL}}      │ {{CELL}}
Medium      │ {{CELL}}     │ {{CELL}}      │ {{CELL}}
Low Impact  │ {{CELL}}     │ {{CELL}}      │ {{CELL}}
```

---

## Recipes

> Adopt/Trial Decisionに対する具体的適用レシピです。
> Pseudocodeで意図を明確にしつつ、実装は実行時点で決定します。

### Recipe: {{RECIPE_1_NAME}}

**Goal**: {{RECIPE_1_GOAL}}

**Prerequisites**:

- {{PREREQ_1}}
- {{PREREQ_2}}

**Adaptation Notes**:

- {{ADAPT_NOTE_1}}

**Steps** (Pseudocode):

1. {{STEP_1}}: {{STEP_1_DESC}}

   ```pseudo
   {{STEP_1_PSEUDOCODE}}
   ```

2. {{STEP_2}}: {{STEP_2_DESC}}
   ```pseudo
   {{STEP_2_PSEUDOCODE}}
   ```

**Verification**:

- [ ] {{VERIFY_1}}
- [ ] {{VERIFY_2}}

**Rollback**:

- {{ROLLBACK_PLAN}}

### Recipe: {{RECIPE_2_NAME}}

...

---

## Adoption Log

> Decisionが実際に適用される際に以下に記録します。
> oss-analyzerではなく **適用作業者**が更新します。

| 日付 | Decision | 以前の判定 | 新判定 | 実装位置 | 備考 |
| ---- | -------- | :--------: | :----: | -------- | ---- |

{{ADOPTION_LOG}}

---

## Quality Scorecard

| #   | 領域                 | 基準                        |       点数        | 備考                 |
| --- | -------------------- | --------------------------- | :---------------: | -------------------- |
| 1   | Forces 完全性        | Decision当たり Forces 2個+  |   {{SCORE}}/20    | {{NOTE}}             |
| 2   | Alternative 多様性   | Decision当たり代替案 1個+   |   {{SCORE}}/20    | {{NOTE}}             |
| 3   | Recipe 具体性        | Adopt/TrialにRecipe         |   {{SCORE}}/20    | {{NOTE}}             |
| 4   | Problem マッピング率 | Decision→Problem マッピング |   {{SCORE}}/20    | {{NOTE}}             |
| 5   | Evidence 充実度      | ForcesにEvidence タグ       |   {{SCORE}}/20    | {{NOTE}}             |
|     | **総点**             |                             | **{{TOTAL}}/100** | {{PASS_REVIEW_FAIL}} |

---

**前へ**: [decisions.md](./decisions.md)
