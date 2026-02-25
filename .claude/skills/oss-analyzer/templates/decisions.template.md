# {{OSS_NAME}} — Decisions

> **分析日**: {{ANALYSIS_DATE}}
> **分析者**: oss-analyzer v4.0
> **方法論**: Decision Archaeology (ADR + Pattern Language Forces + GoF Mechanism)

---

## Decision 要約

| #   | Decision | Problem | Adoption | Forces | Alternatives |
| --- | -------- | ------- | :------: | :----: | :----------: |

{{DECISION_SUMMARY_TABLE}}

---

## Decision #1: {{DECISION_1_NAME}}

### Problem & Forces

**Problem**: {{PROBLEM_REF}} — {{PROBLEM_TITLE}}

**Forces**:

- **F1**: {{FORCE_1}} — Evidence: {{EVIDENCE_1}}
- **F2**: {{FORCE_2}} — Evidence: {{EVIDENCE_2}}
- _({{WHY_FORCES_CONFLICT}})_

### Decision & Alternatives

**Chosen**: {{CHOSEN_APPROACH}}
**Why This Way**: {{WHY_THIS_WAY}}

**Alternatives Considered**:

| 代替案    | 却下理由        | Evidence           |
| --------- | --------------- | ------------------ |
| {{ALT_1}} | {{REJECTION_1}} | {{ALT_EVIDENCE_1}} |

### Mechanism

- **Symbol**: {{SYMBOL}} ← Primary Identifier
- **Module**: {{MODULE}}
- **File**: {{FILE_PATH}}
- **Ref**: 行 {{LINE}} 付近 (参考用)

**Interface**:

Input:

```{{LANG}}
{{INPUT_TYPE}}
```

Output:

```{{LANG}}
{{OUTPUT_TYPE}}
```

**How It Works**:

1. {{STEP_1}}: {{STEP_1_DESC}}
   ```{{LANG}}
   {{STEP_1_CODE}}
   ```
2. {{STEP_2}}: {{STEP_2_DESC}}
   ...

### Consequences

| タイプ      | 説明         | Evidence     |
| ----------- | ------------ | ------------ |
| ✅ Positive | {{POSITIVE}} | {{EVIDENCE}} |
| ⚠️ Negative | {{NEGATIVE}} | {{EVIDENCE}} |
| ↔️ Tradeoff | {{TRADEOFF}} | {{EVIDENCE}} |

### プロジェクト Relevance

- **Problem Match**: {{LK_PROBLEM_MATCH}}
- **Forces Match**: {{LK_FORCES_MATCH}}
- **Forces Mismatch**: {{LK_FORCES_MISMATCH}}
- **Adaptation Needed**: {{ADAPTATION_NEEDED}}

---

## Decision #2: {{DECISION_2_NAME}}

...

---

**前へ**: [reconnaissance.md](./reconnaissance.md)
**次へ**: [adoption.md](./adoption.md) — Adoption Engineering
