# スキャン結果出力形式

> スキャン完了後ユーザーに報告するマークダウンテンプレート

---

## 標準出力形式

````markdown
## Market Intelligence Scan 結果

> **スキャン日**: YYYY-MM-DD
> **分析文書**: N個
> **発見候補**: M個
> **Deep Research 実行**: 2回 (リサーチギャップ 1, Low Confidence 1) または 未使用

---

### 要約

| 順位 | ID               | 候補名   | ICE | J-Fit | 根拠    | Deep |
| :--: | ---------------- | -------- | :-: | :---: | ------- | :--: |
|  1   | `feature-name-a` | [機能名] | 8.5 |   9   | 3個文書 |  -   |
|  2   | `feature-name-b` | [機能名] | 7.2 |   8   | Deep    |  -   |

> **ID**: `--accept`, `--reject` 等のサブコマンドにそのまま使用可能な短縮 ID (日付接頭辞除外)

---

### 新規候補詳細

#### 1. [Feature Name]

| 項目          | 内容                     |
| ------------- | ------------------------ |
| **Problem**   | [解決する問題]           |
| **Solution**  | [提案ソリューション]     |
| **Evidence**  | [根拠文書リンク]         |
| **ICE Score** | I: ? / C: ? / E: ? = ?.? |
| **Japan-Fit** | ?/10 - [理由]            |

**生成ファイル**: `docs/features/candidates/market/YYYY-MM-DD-feature-name.md`

---

### 次のステップ

1. [ ] `/market-intelligence-scanner --list` で候補現況確認
2. [ ] 候補別承認/却下/保留決定 (単一または複数 ID):
   - `/market-intelligence-scanner --accept <id> [id2 ...]` → 承認 + Feature 自動生成
   - `/market-intelligence-scanner --reject <id> [id2 ...]` → 却下 (共通事由記録)
   - `/market-intelligence-scanner --defer <id> [id2 ...]` → 保留 (共通事由/再検討時期)
   - `/market-intelligence-scanner --merge <id> <feature-id>` → 既存 Feature に統合 (単一のみ)
   ```bash
   # 例: 複数承認
   /market-intelligence-scanner --accept feature-a feature-b feature-c
   # 例: 複数却下
   /market-intelligence-scanner --reject feature-x feature-y
   ```
````

3. [ ] `/market-intelligence-scanner --triage` で一括分類
4. [ ] 必要時 `/priority-analyzer` で全体優先順位再評価

````

---

## 候補なし時の出力

```markdown
## Market Intelligence Scan 結果

> **スキャン日**: YYYY-MM-DD
> **分析文書**: N個
> **発見候補**: 0個

### 分析結果

既存 Feature で十分にカバーされる領域です。新規ギャップは発見されませんでした。

**スキャンした主要領域**:
- [領域 1]: 既存 Feature XXX でカバー
- [領域 2]: 既存 Feature YYY でカバー
````
